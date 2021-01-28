import os

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape
import json
import requests
from urllib.parse import quote, urlencode

from hc.accounts.models import Profile
from hc.lib import emails
from hc.lib.string import replace

try:
    import apprise
except ImportError:
    # Enforce
    settings.APPRISE_ENABLED = False

try:
    import dbus
except ImportError:
    # Enforce
    dbus = None
    settings.SIGNAL_CLI_ENABLED = False


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

        This method is overridden in Webhook subclass where the user can
        configure webhook urls for "up" and "down" events, and both are
        optional.

        """

        return False

    def checks(self):
        return self.channel.project.check_set.order_by("created")


class Email(Transport):
    def notify(self, check):
        if not self.channel.email_verified:
            return "Email not verified"

        unsub_link = self.channel.get_unsub_link()

        headers = {
            "X-Status-Url": check.status_url,
            "List-Unsubscribe": "<%s>" % unsub_link,
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

        from hc.accounts.models import Profile

        # If this email address has an associated account, include
        # a summary of projects the account has access to
        try:
            profile = Profile.objects.get(user__email=self.channel.email_value)
            projects = list(profile.projects())
        except Profile.DoesNotExist:
            projects = None

        ctx = {
            "check": check,
            "ping": check.ping_set.order_by("created").last(),
            "projects": projects,
            "unsub_link": unsub_link,
        }

        emails.alert(self.channel.email_value, ctx, headers)

    def is_noop(self, check):
        if check.status == "down":
            return not self.channel.email_notify_down
        else:
            return not self.channel.email_notify_up


class Shell(Transport):
    def prepare(self, template, check):
        """ Replace placeholders with actual values. """

        ctx = {
            "$CODE": str(check.code),
            "$STATUS": check.status,
            "$NOW": timezone.now().replace(microsecond=0).isoformat(),
            "$NAME": check.name,
            "$TAGS": check.tags,
        }

        for i, tag in enumerate(check.tags_list()):
            ctx["$TAG%d" % (i + 1)] = tag

        return replace(template, ctx)

    def is_noop(self, check):
        if check.status == "down" and not self.channel.cmd_down:
            return True

        if check.status == "up" and not self.channel.cmd_up:
            return True

        return False

    def notify(self, check):
        if not settings.SHELL_ENABLED:
            return "Shell commands are not enabled"

        if check.status == "up":
            cmd = self.channel.cmd_up
        elif check.status == "down":
            cmd = self.channel.cmd_down

        cmd = self.prepare(cmd, check)
        code = os.system(cmd)

        if code != 0:
            return "Command returned exit code %d" % code


class HttpTransport(Transport):
    @classmethod
    def get_error(cls, response):
        # Override in subclasses: look for a specific error message in the
        # response and return it.
        return None

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
                m = cls.get_error(r)
                if m:
                    return f'Received status code {r.status_code} with a message: "{m}"'

                return f"Received status code {r.status_code}"

        except requests.exceptions.Timeout:
            # Well, we tried
            return "Connection timed out"
        except requests.exceptions.ConnectionError:
            return "Connection failed"

    @classmethod
    def get(cls, url, num_tries=3, **kwargs):
        for x in range(0, num_tries):
            error = cls._request("get", url, **kwargs)
            if error is None:
                break

        return error

    @classmethod
    def post(cls, url, num_tries=3, **kwargs):
        for x in range(0, num_tries):
            error = cls._request("post", url, **kwargs)
            if error is None:
                break

        return error

    @classmethod
    def put(cls, url, num_tries=3, **kwargs):
        for x in range(0, num_tries):
            error = cls._request("put", url, **kwargs)
            if error is None:
                break

        return error


class Webhook(HttpTransport):
    def prepare(self, template, check, urlencode=False):
        """ Replace variables with actual values. """

        def safe(s):
            return quote(s) if urlencode else s

        ctx = {
            "$CODE": str(check.code),
            "$STATUS": check.status,
            "$NOW": safe(timezone.now().replace(microsecond=0).isoformat()),
            "$NAME": safe(check.name),
            "$TAGS": safe(check.tags),
        }

        for i, tag in enumerate(check.tags_list()):
            ctx["$TAG%d" % (i + 1)] = safe(tag)

        return replace(template, ctx)

    def is_noop(self, check):
        if check.status == "down" and not self.channel.url_down:
            return True

        if check.status == "up" and not self.channel.url_up:
            return True

        return False

    def notify(self, check):
        spec = self.channel.webhook_spec(check.status)
        if not spec["url"]:
            return "Empty webhook URL"

        url = self.prepare(spec["url"], check, urlencode=True)
        headers = {}
        for key, value in spec["headers"].items():
            headers[key] = self.prepare(value, check)

        body = spec["body"]
        if body:
            body = self.prepare(body, check).encode()

        num_tries = 3
        if getattr(check, "is_test"):
            # When sending a test notification, don't retry on failures.
            num_tries = 1

        if spec["method"] == "GET":
            return self.get(url, num_tries=num_tries, headers=headers)
        elif spec["method"] == "POST":
            return self.post(url, num_tries=num_tries, data=body, headers=headers)
        elif spec["method"] == "PUT":
            return self.put(url, num_tries=num_tries, data=body, headers=headers)


class Slack(HttpTransport):
    def notify(self, check):
        text = tmpl("slack_message.json", check=check)
        payload = json.loads(text)
        return self.post(self.channel.slack_webhook_url, json=payload)


class HipChat(HttpTransport):
    def is_noop(self, check):
        return True


class OpsGenie(HttpTransport):
    @classmethod
    def get_error(cls, response):
        try:
            return response.json().get("message")
        except ValueError:
            pass

    def notify(self, check):
        headers = {
            "Conent-Type": "application/json",
            "Authorization": "GenieKey %s" % self.channel.opsgenie_key,
        }

        payload = {"alias": str(check.code), "source": settings.SITE_NAME}

        if check.status == "down":
            payload["tags"] = check.tags_list()
            payload["message"] = tmpl("opsgenie_message.html", check=check)
            payload["note"] = tmpl("opsgenie_note.html", check=check)
            payload["description"] = tmpl("opsgenie_description.html", check=check)

        url = "https://api.opsgenie.com/v2/alerts"
        if self.channel.opsgenie_region == "eu":
            url = "https://api.eu.opsgenie.com/v2/alerts"

        if check.status == "up":
            url += "/%s/close?identifierType=alias" % check.code

        return self.post(url, json=payload, headers=headers)


class PagerDuty(HttpTransport):
    URL = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"

    def notify(self, check):
        description = tmpl("pd_description.html", check=check)
        payload = {
            "service_key": self.channel.pd_service_key,
            "incident_key": str(check.code),
            "event_type": "trigger" if check.status == "down" else "resolve",
            "description": description,
            "client": settings.SITE_NAME,
            "client_url": check.details_url(),
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
    def is_noop(self, check):
        return True


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
        pieces = self.channel.value.split("|")
        user_key, prio = pieces[0], pieces[1]
        # The third element, if present, is the priority for "up" events
        if len(pieces) == 3 and check.status == "up":
            prio = pieces[2]

        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_pushover(user_key):
            return "Rate limit exceeded"

        others = self.checks().filter(status="down").exclude(code=check.code)
        # list() executes the query, to avoid DB access while
        # rendering a template
        ctx = {"check": check, "down_checks": list(others)}
        text = tmpl("pushover_message.html", **ctx)
        title = tmpl("pushover_title.html", **ctx)

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
    def get_error(cls, response):
        try:
            return response.json().get("description")
        except ValueError:
            pass

    @classmethod
    def send(cls, chat_id, text):
        # Telegram.send is a separate method because it is also used in
        # hc.front.views.telegram_bot to send invite links.
        return cls.post(
            cls.SM, json={"chat_id": chat_id, "text": text, "parse_mode": "html"}
        )

    def notify(self, check):
        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_telegram(self.channel.telegram_id):
            return "Rate limit exceeded"

        text = tmpl("telegram_message.html", check=check)
        return self.send(self.channel.telegram_id, text)


class Sms(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    def is_noop(self, check):
        return check.status != "down"

    def notify(self, check):
        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            profile.send_sms_limit_notice("SMS")
            return "Monthly SMS limit exceeded"

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = tmpl("sms_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": settings.TWILIO_FROM,
            "To": self.channel.phone_number,
            "Body": text,
            "StatusCallback": check.status_url,
        }

        return self.post(url, data=data, auth=auth)


class Call(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Calls.json"

    def is_noop(self, check):
        return check.status != "down"

    def notify(self, check):
        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_call():
            profile.send_call_limit_notice()
            return "Monthly phone call limit exceeded"

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        twiml = tmpl("call_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": settings.TWILIO_FROM,
            "To": self.channel.phone_number,
            "Twiml": twiml,
            "StatusCallback": check.status_url,
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
            profile.send_sms_limit_notice("WhatsApp")
            return "Monthly message limit exceeded"

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = tmpl("whatsapp_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": "whatsapp:%s" % settings.TWILIO_FROM,
            "To": "whatsapp:%s" % self.channel.phone_number,
            "Body": text,
            "StatusCallback": check.status_url,
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
            return "Apprise is disabled and/or not installed"

        a = apprise.Apprise()
        title = tmpl("apprise_title.html", check=check)
        body = tmpl("apprise_description.html", check=check)

        a.add(self.channel.value)

        notify_type = (
            apprise.NotifyType.SUCCESS
            if check.status == "up"
            else apprise.NotifyType.FAILURE
        )

        return (
            "Failed"
            if not a.notify(body=body, title=title, notify_type=notify_type)
            else None
        )


class MsTeams(HttpTransport):
    def escape_md(self, s):
        # Escape special HTML characters
        s = escape(s)
        # Escape characters that have special meaning in Markdown
        for c in r"\`*_{}[]()#+-.!|":
            s = s.replace(c, "\\" + c)
        return s

    def notify(self, check):
        text = tmpl("msteams_message.json", check=check)
        payload = json.loads(text)

        # MS Teams escapes HTML special characters in the summary field.
        # It does not interpret summary content as Markdown.
        name = check.name_then_code()
        payload["summary"] = f"“{name}” is {check.status.upper()}."

        # MS teams *strips* HTML special characters from the title field.
        # To avoid that, we use escape().
        # It does not interpret title as Markdown.
        safe_name = escape(name)
        payload["title"] = f"“{safe_name}” is {check.status.upper()}."

        # MS teams allows some HTML in the section text.
        # It also interprets the section text as Markdown.
        # We want to display the raw content, angle brackets and all,
        # so we run escape() and then additionally escape Markdown:
        payload["sections"][0]["text"] = self.escape_md(check.desc)

        return self.post(self.channel.value, json=payload)


class Zulip(HttpTransport):
    @classmethod
    def get_error(cls, response):
        try:
            return response.json().get("msg")
        except ValueError:
            pass

    def notify(self, check):
        url = self.channel.zulip_site + "/api/v1/messages"
        auth = (self.channel.zulip_bot_email, self.channel.zulip_api_key)
        data = {
            "type": self.channel.zulip_type,
            "to": self.channel.zulip_to,
            "topic": tmpl("zulip_topic.html", check=check),
            "content": tmpl("zulip_content.html", check=check),
        }

        return self.post(url, data=data, auth=auth)


class Spike(HttpTransport):
    def notify(self, check):
        url = self.channel.value
        headers = {"Conent-Type": "application/json"}
        payload = {
            "check_id": str(check.code),
            "title": tmpl("spike_title.html", check=check),
            "message": tmpl("spike_description.html", check=check),
            "status": check.status,
        }

        return self.post(url, json=payload, headers=headers)


class LineNotify(HttpTransport):
    URL = "https://notify-api.line.me/api/notify"

    def notify(self, check):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Bearer %s" % self.channel.linenotify_token,
        }
        payload = {"message": tmpl("linenotify_message.html", check=check)}
        return self.post(self.URL, headers=headers, params=payload)


class Signal(Transport):
    def is_noop(self, check):
        if check.status == "down":
            return not self.channel.signal_notify_down
        else:
            return not self.channel.signal_notify_up

    def get_service(self):
        bus = dbus.SystemBus()
        signal_object = bus.get_object("org.asamk.Signal", "/org/asamk/Signal")
        return dbus.Interface(signal_object, "org.asamk.Signal")

    def notify(self, check):
        if not settings.SIGNAL_CLI_ENABLED:
            return "Signal notifications are not enabled"

        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_signal(self.channel.phone_number):
            return "Rate limit exceeded"

        text = tmpl("signal_message.html", check=check, site_name=settings.SITE_NAME)

        try:
            dbus.SystemBus().call_blocking(
                "org.asamk.Signal",
                "/org/asamk/Signal",
                "org.asamk.Signal",
                "sendMessage",
                "sasas",
                (text, [], [self.channel.phone_number]),
                timeout=30,
            )
        except dbus.exceptions.DBusException as e:
            if "NotFoundException" in str(e):
                return "Recipient not found"

            return "signal-cli call failed"
