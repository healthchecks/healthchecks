from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import json
import requests
from urllib.parse import quote, urlencode

from hc.accounts.models import Profile
from hc.lib import emails

try:
    import apprise
except ImportError:
    # Enforce
    settings.APPRISE_ENABLED = False


def tmpl(template_name, **ctx):
    template_path = "integrations/%s" % template_name
    # \xa0 is non-breaking space. It causes SMS messages to use UCS2 encoding
    # and cost twice the money.
    return render_to_string(template_path, ctx).strip().replace("\xa0", " ")


class Transport(object):
    def __init__(self, channel):
        self.channel = channel

    def notify(self, check):
        """ Send notification about current status of the check.

        This method returns None on success, and error message
        on error.

        """

        raise NotImplementedError()

    def is_noop(self, check):
        """ Return True if transport will ignore check's current status.

        This method is overriden in Webhook subclass where the user can
        configure webhook urls for "up" and "down" events, and both are
        optional.

        """

        return False

    def checks(self):
        return self.channel.project.check_set.order_by("created")


class Email(Transport):
    def notify(self, check, bounce_url):
        if not self.channel.email_verified:
            return "Email not verified"

        unsub_link = self.channel.get_unsub_link()

        headers = {"X-Bounce-Url": bounce_url, "List-Unsubscribe": unsub_link}

        try:
            # Look up the sorting preference for this email address
            p = Profile.objects.get(user__email=self.channel.email_value)
            sort = p.sort
        except Profile.DoesNotExist:
            # Default sort order is by check's creation time
            sort = "created"

        # list() executes the query, to avoid DB access while
        # rendering a template
        ctx = {
            "check": check,
            "checks": list(self.checks()),
            "sort": sort,
            "now": timezone.now(),
            "unsub_link": unsub_link,
        }

        emails.alert(self.channel.email_value, ctx, headers)

    def is_noop(self, check):
        if not self.channel.email_verified:
            return True

        if check.status == "down":
            return not self.channel.email_notify_down
        else:
            return not self.channel.email_notify_up


class HttpTransport(Transport):
    @classmethod
    def _request(cls, method, url, **kwargs):
        try:
            options = dict(kwargs)
            options["timeout"] = 5
            if "headers" not in options:
                options["headers"] = {}
            if "User-Agent" not in options["headers"]:
                options["headers"]["User-Agent"] = "healthchecks.io"

            r = requests.request(method, url, **options)
            if r.status_code not in (200, 201, 202, 204):
                return "Received status code %d" % r.status_code
        except requests.exceptions.Timeout:
            # Well, we tried
            return "Connection timed out"
        except requests.exceptions.ConnectionError:
            return "Connection failed"

    @classmethod
    def get(cls, url, **kwargs):
        # Make 3 attempts--
        for x in range(0, 3):
            error = cls._request("get", url, **kwargs)
            if error is None:
                break

        return error

    @classmethod
    def post(cls, url, **kwargs):
        # Make 3 attempts--
        for x in range(0, 3):
            error = cls._request("post", url, **kwargs)
            if error is None:
                break

        return error

    @classmethod
    def put(cls, url, **kwargs):
        # Make 3 attempts--
        for x in range(0, 3):
            error = cls._request("put", url, **kwargs)
            if error is None:
                break

        return error


class Webhook(HttpTransport):
    def prepare(self, template, check, urlencode=False):
        """ Replace variables with actual values.

        There should be no bad translations if users use $ symbol in
        check's name or tags, because $ gets urlencoded to %24

        """

        def safe(s):
            return quote(s) if urlencode else s

        result = template
        if "$CODE" in result:
            result = result.replace("$CODE", str(check.code))

        if "$STATUS" in result:
            result = result.replace("$STATUS", check.status)

        if "$NOW" in result:
            s = timezone.now().replace(microsecond=0).isoformat()
            result = result.replace("$NOW", safe(s))

        if "$NAME" in result:
            result = result.replace("$NAME", safe(check.name))

        if "$TAGS" in result:
            result = result.replace("$TAGS", safe(check.tags))

        if "$TAG" in result:
            for i, tag in enumerate(check.tags_list()):
                placeholder = "$TAG%d" % (i + 1)
                result = result.replace(placeholder, safe(tag))

        return result

    def is_noop(self, check):
        if check.status == "down" and not self.channel.url_down:
            return True

        if check.status == "up" and not self.channel.url_up:
            return True

        return False

    def notify(self, check):
        spec = self.channel.webhook_spec(check.status)
        assert spec["url"]

        url = self.prepare(spec["url"], check, urlencode=True)
        headers = {}
        for key, value in spec["headers"].items():
            headers[key] = self.prepare(value, check)

        body = spec["body"]
        if body:
            body = self.prepare(body, check)

        if spec["method"] == "GET":
            return self.get(url, headers=headers)
        elif spec["method"] == "POST":
            return self.post(url, data=body.encode(), headers=headers)
        elif spec["method"] == "PUT":
            return self.put(url, data=body.encode(), headers=headers)


class Slack(HttpTransport):
    def notify(self, check):
        text = tmpl("slack_message.json", check=check)
        payload = json.loads(text)
        return self.post(self.channel.slack_webhook_url, json=payload)


class HipChat(HttpTransport):
    def is_noop(self, check):
        return True


class OpsGenie(HttpTransport):
    def notify(self, check):
        headers = {
            "Conent-Type": "application/json",
            "Authorization": "GenieKey %s" % self.channel.value,
        }

        payload = {"alias": str(check.code), "source": settings.SITE_NAME}

        if check.status == "down":
            payload["tags"] = check.tags_list()
            payload["message"] = tmpl("opsgenie_message.html", check=check)
            payload["note"] = tmpl("opsgenie_note.html", check=check)
            payload["description"] = tmpl("opsgenie_description.html", check=check)

        url = "https://api.opsgenie.com/v2/alerts"
        if check.status == "up":
            url += "/%s/close?identifierType=alias" % check.code

        return self.post(url, json=payload, headers=headers)


class PagerDuty(HttpTransport):
    URL = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"

    def notify(self, check):
        description = tmpl("pd_description.html", check=check)
        payload = {
            "vendor": settings.PD_VENDOR_KEY,
            "service_key": self.channel.pd_service_key,
            "incident_key": str(check.code),
            "event_type": "trigger" if check.status == "down" else "resolve",
            "description": description,
            "client": settings.SITE_NAME,
            "client_url": settings.SITE_ROOT,
        }

        return self.post(self.URL, json=payload)


class PagerTree(HttpTransport):
    def notify(self, check):
        url = self.channel.value
        headers = {"Conent-Type": "application/json"}
        payload = {
            "incident_key": str(check.code),
            "event_type": "trigger" if check.status == "down" else "resolve",
            "title": tmpl("pagertree_title.html", check=check),
            "description": tmpl("pagertree_description.html", check=check),
            "client": settings.SITE_NAME,
            "client_url": settings.SITE_ROOT,
            "tags": ",".join(check.tags_list()),
        }

        return self.post(url, json=payload, headers=headers)


class PagerTeam(HttpTransport):
    def notify(self, check):
        url = self.channel.value
        headers = {"Content-Type": "application/json"}
        payload = {
            "incident_key": str(check.code),
            "event_type": "trigger" if check.status == "down" else "resolve",
            "title": tmpl("pagerteam_title.html", check=check),
            "description": tmpl("pagerteam_description.html", check=check),
            "client": settings.SITE_NAME,
            "client_url": settings.SITE_ROOT,
            "tags": ",".join(check.tags_list()),
        }

        return self.post(url, json=payload, headers=headers)


class Pushbullet(HttpTransport):
    def notify(self, check):
        text = tmpl("pushbullet_message.html", check=check)
        url = "https://api.pushbullet.com/v2/pushes"
        headers = {
            "Access-Token": self.channel.value,
            "Conent-Type": "application/json",
        }
        payload = {"type": "note", "title": settings.SITE_NAME, "body": text}

        return self.post(url, json=payload, headers=headers)


class Pushover(HttpTransport):
    URL = "https://api.pushover.net/1/messages.json"

    def notify(self, check):
        others = self.checks().filter(status="down").exclude(code=check.code)

        # list() executes the query, to avoid DB access while
        # rendering a template
        ctx = {"check": check, "down_checks": list(others)}
        text = tmpl("pushover_message.html", **ctx)
        title = tmpl("pushover_title.html", **ctx)

        pieces = self.channel.value.split("|")
        user_key, prio = pieces[0], pieces[1]
        # The third element, if present, is the priority for "up" events
        if len(pieces) == 3 and check.status == "up":
            prio = pieces[2]

        payload = {
            "token": settings.PUSHOVER_API_TOKEN,
            "user": user_key,
            "message": text,
            "title": title,
            "html": 1,
            "priority": int(prio),
        }

        # Emergency notification
        if prio == "2":
            payload["retry"] = settings.PUSHOVER_EMERGENCY_RETRY_DELAY
            payload["expire"] = settings.PUSHOVER_EMERGENCY_EXPIRATION

        return self.post(self.URL, data=payload)


class VictorOps(HttpTransport):
    def notify(self, check):
        description = tmpl("victorops_description.html", check=check)
        mtype = "CRITICAL" if check.status == "down" else "RECOVERY"
        payload = {
            "entity_id": str(check.code),
            "message_type": mtype,
            "entity_display_name": check.name_then_code(),
            "state_message": description,
            "monitoring_tool": settings.SITE_NAME,
        }

        return self.post(self.channel.value, json=payload)


class Matrix(HttpTransport):
    def get_url(self):
        s = quote(self.channel.value)

        url = settings.MATRIX_HOMESERVER
        url += "/_matrix/client/r0/rooms/%s/send/m.room.message?" % s
        url += urlencode({"access_token": settings.MATRIX_ACCESS_TOKEN})
        return url

    def notify(self, check):
        plain = tmpl("matrix_description.html", check=check)
        formatted = tmpl("matrix_description_formatted.html", check=check)
        payload = {
            "msgtype": "m.text",
            "body": plain,
            "format": "org.matrix.custom.html",
            "formatted_body": formatted,
        }

        return self.post(self.get_url(), json=payload)


class Discord(HttpTransport):
    def notify(self, check):
        text = tmpl("slack_message.json", check=check)
        payload = json.loads(text)
        url = self.channel.discord_webhook_url + "/slack"
        return self.post(url, json=payload)


class Telegram(HttpTransport):
    SM = "https://api.telegram.org/bot%s/sendMessage" % settings.TELEGRAM_TOKEN

    @classmethod
    def send(cls, chat_id, text):
        return cls.post(
            cls.SM, json={"chat_id": chat_id, "text": text, "parse_mode": "html"}
        )

    def notify(self, check):
        text = tmpl("telegram_message.html", check=check)
        return self.send(self.channel.telegram_id, text)


class Sms(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    def is_noop(self, check):
        return check.status != "down"

    def notify(self, check):
        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            return "Monthly SMS limit exceeded"

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = tmpl("sms_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": settings.TWILIO_FROM,
            "To": self.channel.sms_number,
            "Body": text,
        }

        return self.post(url, data=data, auth=auth)


class WhatsApp(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    def is_noop(self, check):
        if check.status == "down":
            return not self.channel.whatsapp_notify_down
        else:
            return not self.channel.whatsapp_notify_up

    def notify(self, check):
        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            return "Monthly message limit exceeded"

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = tmpl("whatsapp_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": "whatsapp:%s" % settings.TWILIO_FROM,
            "To": "whatsapp:%s" % self.channel.sms_number,
            "Body": text,
        }

        return self.post(url, data=data, auth=auth)


class Trello(HttpTransport):
    URL = "https://api.trello.com/1/cards"

    def is_noop(self, check):
        return check.status != "down"

    def notify(self, check):
        params = {
            "idList": self.channel.trello_list_id,
            "name": tmpl("trello_name.html", check=check),
            "desc": tmpl("trello_desc.html", check=check),
            "key": settings.TRELLO_APP_KEY,
            "token": self.channel.trello_token,
        }

        return self.post(self.URL, params=params)

class Apprise(HttpTransport):
    def notify(self, check):

        if not settings.APPRISE_ENABLED:
            # Not supported and/or enabled
            return "Apprise is disabled and/or not installed."

        a = apprise.Apprise()
        title = tmpl("apprise_title.html", check=check)
        body = tmpl("apprise_description.html", check=check)

        a.add(self.channel.value)

        notify_type = apprise.NotifyType.SUCCESS \
            if check.status == "up" else apprise.NotifyType.FAILURE

        return "Failed" if not \
            a.notify(body=body, title=title, notify_type=notify_type) else None
