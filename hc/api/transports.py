import json
import logging
import os
import socket
import time
from typing import Optional
from urllib.parse import quote, urlencode, urljoin
import uuid

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape

from hc.accounts.models import Profile
from hc.api.schemas import telegram_migration
from hc.front.templatetags.hc_extras import sortchecks
from hc.lib import curl, emails, jsonschema
from hc.lib.date import format_duration
from hc.lib.string import replace


try:
    import apprise
except ImportError:
    # Enforce
    settings.APPRISE_ENABLED = False


def tmpl(template_name, **ctx) -> str:
    template_path = "integrations/%s" % template_name
    # \xa0 is non-breaking space. It causes SMS messages to use UCS2 encoding
    # and cost twice the money.
    return render_to_string(template_path, ctx).strip().replace("\xa0", " ")


def get_nested(obj, path, default=None):
    """Retrieve a field from nested dictionaries.

    Example:

    >>> get_nested({"foo": {"bar": "baz"}}, "foo.bar")
    'baz'

    """

    needle = obj
    for key in path.split("."):
        if key not in needle:
            return default
        needle = needle[key]
    return needle


def get_ping_body(ping) -> Optional[str]:
    body = None
    if ping and ping.has_body():
        body = ping.get_body()
        if body is None and ping.object_size:
            # Body is not uploaded to object storage yet.
            # Wait 5 seconds, then fetch the body again.
            time.sleep(5)
            body = ping.get_body()

    return body


class TransportError(Exception):
    def __init__(self, message, permanent=False) -> None:
        self.message = message
        self.permanent = permanent


class Transport(object):
    def __init__(self, channel):
        self.channel = channel

    def notify(self, check, notification=None) -> None:
        """Send notification about current status of the check.

        This method raises TransportError on error, and returns None
        on success.

        """

        raise NotImplementedError()

    def is_noop(self, check) -> bool:
        """Return True if transport will ignore check's current status.

        This method is overridden in Webhook subclass where the user can
        configure webhook urls for "up" and "down" events, and both are
        optional.

        """

        return False

    def down_checks(self, check):
        """Return a sorted list of other checks in the same project that are down.

        If there are no other hecks in the project, return None instead of empty list.
        Templates can check for None to decide whether to show or not show the
        "All other checks are up" note.

        """

        siblings = self.channel.project.check_set.exclude(id=check.id)
        if not siblings.exists():
            return None

        down_siblings = list(siblings.filter(status="down"))
        sortchecks(down_siblings, "name")

        return down_siblings

    def last_ping(self, check):
        """Return the last Ping object for this check."""

        if check.pk:
            return check.ping_set.order_by("created").last()


class RemovedTransport(Transport):
    """Dummy transport class for obsolete integrations: hipchat, pagerteam."""

    def is_noop(self, check) -> bool:
        return True


class Email(Transport):
    def notify(self, check, notification=None) -> None:
        if not self.channel.email_verified:
            raise TransportError("Email not verified")

        unsub_link = self.channel.get_unsub_link()

        headers = {
            "List-Unsubscribe": "<%s>" % unsub_link,
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

        if notification:
            headers["X-Status-Url"] = notification.status_url()

        from hc.accounts.models import Profile

        # If this email address has an associated account, include
        # a summary of projects the account has access to
        try:
            profile = Profile.objects.get(user__email=self.channel.email_value)
            projects = list(profile.projects())
        except Profile.DoesNotExist:
            projects = None

        ping = self.last_ping(check)
        body = get_ping_body(ping)
        ctx = {
            "check": check,
            "ping": ping,
            "body": body,
            "projects": projects,
            "unsub_link": unsub_link,
        }

        emails.alert(self.channel.email_value, ctx, headers)

    def is_noop(self, check) -> bool:
        if check.status == "down":
            return not self.channel.email_notify_down
        else:
            return not self.channel.email_notify_up


class Shell(Transport):
    def prepare(self, template: str, check) -> str:
        """Replace placeholders with actual values."""

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

    def is_noop(self, check) -> bool:
        if check.status == "down" and not self.channel.cmd_down:
            return True

        if check.status == "up" and not self.channel.cmd_up:
            return True

        return False

    def notify(self, check, notification=None) -> None:
        if not settings.SHELL_ENABLED:
            raise TransportError("Shell commands are not enabled")

        if check.status == "up":
            cmd = self.channel.cmd_up
        elif check.status == "down":
            cmd = self.channel.cmd_down

        cmd = self.prepare(cmd, check)
        code = os.system(cmd)

        if code != 0:
            raise TransportError("Command returned exit code %d" % code)


class HttpTransport(Transport):
    @classmethod
    def raise_for_response(cls, response):
        # Subclasses can override this method to produce a more specific message.
        raise TransportError(f"Received status code {response.status_code}")

    @classmethod
    def _request(cls, method, url, **kwargs) -> None:
        kwargs["timeout"] = 10

        try:
            r = curl.request(method, url, **kwargs)
            if r.status_code not in (200, 201, 202, 204):
                cls.raise_for_response(r)
        except curl.CurlError as e:
            raise TransportError(e.message)

    @classmethod
    def _request_with_retries(cls, method, url, use_retries=True, **kwargs) -> None:
        start = time.time()

        tries_left = 3 if use_retries else 1
        while True:
            try:
                return cls._request(method, url, **kwargs)
            except TransportError as e:
                tries_left = 0 if e.permanent else tries_left - 1

                # If we have no tries left *or* have already used more than
                # 15 seconds of time then abort the retry loop by re-raising
                # the exception:
                if tries_left == 0 or time.time() - start > 15:
                    raise e

    @classmethod
    def get(cls, url, **kwargs) -> None:
        cls._request_with_retries("get", url, **kwargs)

    @classmethod
    def post(cls, url, **kwargs) -> None:
        cls._request_with_retries("post", url, **kwargs)

    @classmethod
    def put(cls, url, **kwargs) -> None:
        cls._request_with_retries("put", url, **kwargs)


class Webhook(HttpTransport):
    def prepare(self, template: str, check, urlencode=False, latin1=False, allow_ping_body=False) -> str:
        """Replace variables with actual values."""

        def safe(s: str) -> str:
            return quote(s) if urlencode else s

        ctx = {
            "$CODE": str(check.code),
            "$STATUS": check.status,
            "$NOW": safe(timezone.now().replace(microsecond=0).isoformat()),
            "$NAME": safe(check.name),
            "$TAGS": safe(check.tags),
            "$JSON": safe(json.dumps(check.to_dict())),
        }

        # Materialize ping body only if template refers to it.
        if allow_ping_body and "$BODY" in template:
            body = get_ping_body(self.last_ping(check))
            ctx["$BODY"] = body if body else ""

        for i, tag in enumerate(check.tags_list()):
            ctx["$TAG%d" % (i + 1)] = safe(tag)

        result = replace(template, ctx)
        if latin1:
            # Replace non-latin-1 characters with XML character references.
            result = result.encode("latin-1", "xmlcharrefreplace").decode("latin-1")

        return result

    def is_noop(self, check) -> bool:
        if check.status == "down" and not self.channel.url_down:
            return True

        if check.status == "up" and not self.channel.url_up:
            return True

        return False

    def notify(self, check, notification=None) -> None:
        if not settings.WEBHOOKS_ENABLED:
            raise TransportError("Webhook notifications are not enabled.")

        spec = self.channel.webhook_spec(check.status)
        if not spec["url"]:
            raise TransportError("Empty webhook URL")

        url = self.prepare(spec["url"], check, urlencode=True)
        headers = {}
        for key, value in spec["headers"].items():
            # Header values should contain ASCII and latin-1 only
            headers[key] = self.prepare(value, check, latin1=True)

        body = spec["body"]
        if body:
            body = self.prepare(body, check, allow_ping_body=True).encode()

        # When sending a test notification, don't retry on failures.
        use_retries = True
        if notification and notification.owner is None:
            use_retries = False  # this is a test notification

        if spec["method"] == "GET":
            self.get(url, use_retries=use_retries, headers=headers)
        elif spec["method"] == "POST":
            self.post(url, use_retries=use_retries, data=body, headers=headers)
        elif spec["method"] == "PUT":
            self.put(url, use_retries=use_retries, data=body, headers=headers)


class Slack(HttpTransport):
    @classmethod
    def raise_for_response(cls, response):
        message = f"Received status code {response.status_code}"
        # If Slack returns 404, this endpoint is unlikely to ever work again
        # https://api.slack.com/messaging/webhooks#handling_errors
        permanent = response.status_code == 404
        raise TransportError(message, permanent=permanent)

    def notify(self, check, notification=None) -> None:
        if not settings.SLACK_ENABLED:
            raise TransportError("Slack notifications are not enabled.")

        text = tmpl("slack_message.json", check=check, ping=self.last_ping(check))
        payload = json.loads(text)
        self.post(self.channel.slack_webhook_url, json=payload)


class Mattermost(HttpTransport):
    @classmethod
    def raise_for_response(cls, response):
        message = f"Received status code {response.status_code}"
        raise TransportError(message)

    def notify(self, check, notification=None) -> None:
        if not settings.MATTERMOST_ENABLED:
            raise TransportError("Mattermost notifications are not enabled.")

        text = tmpl("slack_message.json", check=check, ping=self.last_ping(check))
        payload = json.loads(text)
        self.post(self.channel.slack_webhook_url, json=payload)


class Opsgenie(HttpTransport):
    @classmethod
    def raise_for_response(cls, response):
        message = f"Received status code {response.status_code}"
        try:
            details = response.json().get("message")
            if isinstance(details, str):
                message += f' with a message: "{details}"'
        except ValueError:
            pass

        raise TransportError(message)

    def notify(self, check, notification=None) -> None:
        if not settings.OPSGENIE_ENABLED:
            raise TransportError("Opsgenie notifications are not enabled.")

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

        self.post(url, json=payload, headers=headers)


class PagerDuty(HttpTransport):
    URL = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"

    def notify(self, check, notification=None) -> None:
        if not settings.PD_ENABLED:
            raise TransportError("PagerDuty notifications are not enabled.")

        details = {
            "Project": check.project.name,
            "Total pings": check.n_pings,
            "Last ping": tmpl("pd_last_ping.html", check=check),
        }
        if check.desc:
            details["Description"] = check.desc
        if check.tags:
            details["Tags"] = ", ".join(check.tags_list())
        if check.kind == "simple":
            details["Period"] = format_duration(check.timeout)
        if check.kind == "cron":
            details["Schedule"] = check.schedule

        description = tmpl("pd_description.html", check=check)
        payload = {
            "service_key": self.channel.pd_service_key,
            "incident_key": str(check.code),
            "event_type": "trigger" if check.status == "down" else "resolve",
            "description": description,
            "client": settings.SITE_NAME,
            "client_url": check.details_url(),
            "details": details,
        }

        self.post(self.URL, json=payload)


class PagerTree(HttpTransport):
    def notify(self, check, notification=None) -> None:
        if not settings.PAGERTREE_ENABLED:
            raise TransportError("PagerTree notifications are not enabled.")

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

        self.post(url, json=payload, headers=headers)


class Pushbullet(HttpTransport):
    def notify(self, check, notification=None) -> None:
        text = tmpl("pushbullet_message.html", check=check)
        url = "https://api.pushbullet.com/v2/pushes"
        headers = {
            "Access-Token": self.channel.value,
            "Conent-Type": "application/json",
        }
        payload = {"type": "note", "title": settings.SITE_NAME, "body": text}
        self.post(url, json=payload, headers=headers)


class Pushover(HttpTransport):
    URL = "https://api.pushover.net/1/messages.json"
    CANCEL_TMPL = "https://api.pushover.net/1/receipts/cancel_by_tag/%s.json"

    def is_noop(self, check) -> bool:
        pieces = self.channel.value.split("|")
        _, prio = pieces[0], pieces[1]

        # The third element, if present, is the priority for "up" events
        if check.status == "up" and len(pieces) == 3:
            prio = pieces[2]

        return int(prio) == -3

    def notify(self, check, notification=None) -> None:
        pieces = self.channel.value.split("|")
        user_key, down_prio = pieces[0], pieces[1]

        # The third element, if present, is the priority for "up" events
        up_prio = down_prio
        if len(pieces) == 3:
            up_prio = pieces[2]

        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_pushover(user_key):
            raise TransportError("Rate limit exceeded")

        # If down events have the emergency priority,
        # send a cancel call first
        if check.status == "up" and down_prio == "2":
            url = self.CANCEL_TMPL % check.unique_key
            cancel_payload = {"token": settings.PUSHOVER_API_TOKEN}
            self.post(url, data=cancel_payload)

        ctx = {"check": check, "down_checks": self.down_checks(check)}
        text = tmpl("pushover_message.html", **ctx)
        title = tmpl("pushover_title.html", **ctx)
        prio = up_prio if check.status == "up" else down_prio

        payload = {
            "token": settings.PUSHOVER_API_TOKEN,
            "user": user_key,
            "message": text,
            "title": title,
            "html": 1,
            "priority": int(prio),
            "tags": check.unique_key,
        }

        # Emergency notification
        if prio == "2":
            payload["retry"] = settings.PUSHOVER_EMERGENCY_RETRY_DELAY
            payload["expire"] = settings.PUSHOVER_EMERGENCY_EXPIRATION

        self.post(self.URL, data=payload)


class VictorOps(HttpTransport):
    def notify(self, check, notification=None) -> None:
        if not settings.VICTOROPS_ENABLED:
            raise TransportError("Splunk On-Call notifications are not enabled.")

        description = tmpl("victorops_description.html", check=check)
        mtype = "CRITICAL" if check.status == "down" else "RECOVERY"
        payload = {
            "entity_id": str(check.code),
            "message_type": mtype,
            "entity_display_name": check.name_then_code(),
            "state_message": description,
            "monitoring_tool": settings.SITE_NAME,
        }

        self.post(self.channel.value, json=payload)


class Matrix(HttpTransport):
    def get_url(self):
        s = quote(self.channel.value)

        url = settings.MATRIX_HOMESERVER
        url += "/_matrix/client/r0/rooms/%s/send/m.room.message?" % s
        url += urlencode({"access_token": settings.MATRIX_ACCESS_TOKEN})
        return url

    def notify(self, check, notification=None) -> None:
        plain = tmpl("matrix_description.html", check=check)
        formatted = tmpl("matrix_description_formatted.html", check=check)
        payload = {
            "msgtype": "m.text",
            "body": plain,
            "format": "org.matrix.custom.html",
            "formatted_body": formatted,
        }

        self.post(self.get_url(), json=payload)


class Discord(HttpTransport):
    def notify(self, check, notification=None) -> None:
        text = tmpl("slack_message.json", check=check, ping=self.last_ping(check))
        payload = json.loads(text)
        url = self.channel.discord_webhook_url + "/slack"
        self.post(url, json=payload)


class MigrationRequiredError(TransportError):
    def __init__(self, message, new_chat_id: int):
        super().__init__(message, permanent=True)
        self.new_chat_id = new_chat_id


class Telegram(HttpTransport):
    SM = "https://api.telegram.org/bot%s/sendMessage" % settings.TELEGRAM_TOKEN

    @classmethod
    def raise_for_response(cls, response):
        message = f"Received status code {response.status_code}"
        try:
            doc = response.json()
        except ValueError:
            raise TransportError(message)

        # If the error payload contains the migrate_to_chat_id field,
        # raise MigrationRequiredError, with the new chat_id included
        try:
            jsonschema.validate(doc, telegram_migration)
            description = doc["description"]
            chat_id = doc["parameters"]["migrate_to_chat_id"]
            raise MigrationRequiredError(description, chat_id)
        except jsonschema.ValidationError:
            pass

        permanent = False
        description = doc.get("description")
        if isinstance(description, str):
            message += f' with a message: "{description}"'
            if description == "Forbidden: the group chat was deleted":
                permanent = True

        raise TransportError(message, permanent=permanent)

    @classmethod
    def send(cls, chat_id, text):
        # Telegram.send is a separate method because it is also used in
        # hc.front.views.telegram_bot to send invite links.
        cls.post(cls.SM, json={"chat_id": chat_id, "text": text, "parse_mode": "html"})

    def notify(self, check, notification=None) -> None:
        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_telegram(self.channel.telegram_id):
            raise TransportError("Rate limit exceeded")

        ctx = {"check": check, "down_checks": self.down_checks(check)}
        text = tmpl("telegram_message.html", **ctx)

        try:
            self.send(self.channel.telegram_id, text)
        except MigrationRequiredError as e:
            # Save the new chat_id, then try sending again:
            self.channel.update_telegram_id(e.new_chat_id)
            self.send(self.channel.telegram_id, text)


class Sms(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    def is_noop(self, check) -> bool:
        if check.status == "down":
            return not self.channel.sms_notify_down
        else:
            return not self.channel.sms_notify_up

    def notify(self, check, notification=None) -> None:
        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            profile.send_sms_limit_notice("SMS")
            raise TransportError("Monthly SMS limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = tmpl("sms_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": settings.TWILIO_FROM,
            "To": self.channel.phone_number,
            "Body": text,
        }

        if notification:
            data["StatusCallback"] = notification.status_url()

        self.post(url, data=data, auth=auth)


class Call(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Calls.json"

    def is_noop(self, check) -> bool:
        return check.status != "down"

    def notify(self, check, notification=None) -> None:
        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_call():
            profile.send_call_limit_notice()
            raise TransportError("Monthly phone call limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        twiml = tmpl("call_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": settings.TWILIO_FROM,
            "To": self.channel.phone_number,
            "Twiml": twiml,
        }

        if notification:
            data["StatusCallback"] = notification.status_url()

        self.post(url, data=data, auth=auth)


class WhatsApp(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    def is_noop(self, check) -> bool:
        if check.status == "down":
            return not self.channel.whatsapp_notify_down
        else:
            return not self.channel.whatsapp_notify_up

    def notify(self, check, notification=None) -> None:
        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            profile.send_sms_limit_notice("WhatsApp")
            raise TransportError("Monthly message limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = tmpl("whatsapp_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": "whatsapp:%s" % settings.TWILIO_FROM,
            "To": "whatsapp:%s" % self.channel.phone_number,
            "Body": text,
        }

        if notification:
            data["StatusCallback"] = notification.status_url()

        self.post(url, data=data, auth=auth)


class Trello(HttpTransport):
    URL = "https://api.trello.com/1/cards"

    def is_noop(self, check) -> bool:
        return check.status != "down"

    def notify(self, check, notification=None) -> None:
        params = {
            "idList": self.channel.trello_list_id,
            "name": tmpl("trello_name.html", check=check),
            "desc": tmpl("trello_desc.html", check=check),
            "key": settings.TRELLO_APP_KEY,
            "token": self.channel.trello_token,
        }

        self.post(self.URL, params=params)


class Apprise(HttpTransport):
    def notify(self, check, notification=None) -> None:

        if not settings.APPRISE_ENABLED:
            # Not supported and/or enabled
            raise TransportError("Apprise is disabled and/or not installed")

        a = apprise.Apprise()
        title = tmpl("apprise_title.html", check=check)
        body = tmpl("apprise_description.html", check=check)

        a.add(self.channel.value)

        notify_type = (
            apprise.NotifyType.SUCCESS
            if check.status == "up"
            else apprise.NotifyType.FAILURE
        )

        if not a.notify(body=body, title=title, notify_type=notify_type):
            raise TransportError("Failed")


class MsTeams(HttpTransport):
    def escape_md(self, s):
        # Escape special HTML characters
        s = escape(s)
        # Escape characters that have special meaning in Markdown
        for c in r"\`*_{}[]()#+-.!|":
            s = s.replace(c, "\\" + c)
        return s

    def notify(self, check, notification=None) -> None:
        if not settings.MSTEAMS_ENABLED:
            raise TransportError("MS Teams notifications are not enabled.")

        text = tmpl("msteams_message.json", check=check, ping=self.last_ping(check))
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

        self.post(self.channel.value, json=payload)


class Zulip(HttpTransport):
    @classmethod
    def raise_for_response(cls, response):
        message = f"Received status code {response.status_code}"
        try:
            details = response.json().get("msg")
            if isinstance(details, str):
                message += f' with a message: "{details}"'
        except ValueError:
            pass

        raise TransportError(message)

    def notify(self, check, notification=None) -> None:
        if not settings.ZULIP_ENABLED:
            raise TransportError("Zulip notifications are not enabled.")

        url = self.channel.zulip_site + "/api/v1/messages"
        auth = (self.channel.zulip_bot_email, self.channel.zulip_api_key)
        data = {
            "type": self.channel.zulip_type,
            "to": self.channel.zulip_to,
            "topic": tmpl("zulip_topic.html", check=check),
            "content": tmpl("zulip_content.html", check=check),
        }

        self.post(url, data=data, auth=auth)


class Spike(HttpTransport):
    def notify(self, check, notification=None) -> None:
        if not settings.SPIKE_ENABLED:
            raise TransportError("Spike notifications are not enabled.")

        url = self.channel.value
        headers = {"Conent-Type": "application/json"}
        payload = {
            "check_id": str(check.code),
            "title": tmpl("spike_title.html", check=check),
            "message": tmpl("spike_description.html", check=check),
            "status": check.status,
        }

        self.post(url, json=payload, headers=headers)


class LineNotify(HttpTransport):
    URL = "https://notify-api.line.me/api/notify"

    def notify(self, check, notification=None) -> None:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Bearer %s" % self.channel.linenotify_token,
        }
        payload = {"message": tmpl("linenotify_message.html", check=check)}
        self.post(self.URL, headers=headers, params=payload)


class Signal(Transport):
    def is_noop(self, check) -> bool:
        if check.status == "down":
            return not self.channel.signal_notify_down
        else:
            return not self.channel.signal_notify_up

    def send(self, recipient, message):
        payload = {
            "jsonrpc": "2.0",
            "method": "send",
            "params": {"recipient": [recipient], "message": message},
            "id": str(uuid.uuid4()),
        }

        payload_bytes = (json.dumps(payload) + "\n").encode()
        for reply_bytes in self._read_replies(payload_bytes):
            try:
                reply = json.loads(reply_bytes.decode())
            except ValueError:
                raise TransportError("signal-cli call failed (unexpected response)")

            if reply.get("id") == payload["id"]:
                if "error" not in reply:
                    # success!
                    break

                # signal-cli 0.10.0
                message = reply["error"].get("message", "")
                if "UnregisteredUserException" in message:
                    raise TransportError("Recipient not found")

                # signal-cli >= 0.10.2
                for result in get_nested(reply, "error.data.response.results", []):
                    if get_nested(result, "recipientAddress.number") != recipient:
                        continue

                    if result.get("type") == "UNREGISTERED_FAILURE":
                        raise TransportError("Recipient not found")

                    if result.get("type") == "NETWORK_FAILURE" and "token" in result:
                        raw = reply_bytes.decode()
                        self.channel.send_signal_captcha_alert(result["token"], raw)
                        raise TransportError("CAPTCHA proof required")

                    # signal-cli >= 0.10.5 use type=RATE_LIMIT_FAILURE for
                    # CAPTCHA challenges
                    if result.get("type") == "RATE_LIMIT_FAILURE" and "token" in result:
                        raw = reply_bytes.decode()
                        self.channel.send_signal_captcha_alert(result["token"], raw)
                        raise TransportError("CAPTCHA proof required")

                code = reply["error"].get("code")
                raise TransportError("signal-cli call failed (%s)" % code)

    def _read_replies(self, payload_bytes):
        """Send a request to signal-cli over UNIX socket. Read and yield replies.

        This method:
        * opens UNIX socket
        * sends the request data (JSON RPC data encoded as bytes)
        * reads newline-terminated responses and yields them

        Individual sendall and recv operations have a timeout of 15 seconds.
        This method also keeps track of total time spent in the method, and raises
        an exception when the total time exceeds 15 seconds.

        """

        start = time.time()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(15)
            try:
                s.connect(settings.SIGNAL_CLI_SOCKET)
                s.sendall(payload_bytes)
                s.shutdown(socket.SHUT_WR)  # we are done sending

                buffer = []
                while True:
                    ch = s.recv(1)
                    buffer.append(ch)
                    if ch in (b"\n", b""):
                        yield b"".join(buffer)
                        buffer = []

                    if time.time() - start > 15:
                        raise TransportError("signal-cli call timed out")

            except OSError as e:
                msg = "signal-cli call failed (%s)" % e
                # Log the exception, so any configured logging handlers can pick it up
                logging.getLogger(__name__).exception(msg)

                # And then report it the same as other errors
                raise TransportError(msg)

    def notify(self, check, notification=None) -> None:
        if not settings.SIGNAL_CLI_SOCKET:
            raise TransportError("Signal notifications are not enabled")

        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_signal(self.channel.phone_number):
            raise TransportError("Rate limit exceeded")

        ctx = {"check": check, "down_checks": self.down_checks(check)}
        text = tmpl("signal_message.html", **ctx)
        self.send(self.channel.phone_number, text)


class Gotify(HttpTransport):
    def notify(self, check, notification=None) -> None:
        url = urljoin(self.channel.gotify_url, "/message")
        url += "?" + urlencode({"token": self.channel.gotify_token})

        ctx = {"check": check, "down_checks": self.down_checks(check)}
        payload = {
            "title": tmpl("gotify_title.html", **ctx),
            "message": tmpl("gotify_message.html", **ctx),
            "extras": {
                "client::display": {"contentType": "text/markdown"},
            },
        }

        self.post(url, json=payload)
