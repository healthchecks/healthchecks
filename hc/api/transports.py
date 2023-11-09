from __future__ import annotations

import json
import logging
import os
import socket
import time
import uuid
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, NoReturn, cast
from urllib.parse import quote, urlencode, urljoin

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.timezone import now
from pydantic import BaseModel, ValidationError

from hc.accounts.models import Profile
from hc.front.templatetags.hc_extras import (
    absolute_site_logo_url,
    fix_asterisks,
    sortchecks,
)
from hc.lib import curl, emails
from hc.lib.date import format_duration
from hc.lib.html import extract_signal_styles
from hc.lib.signing import sign_bounce_id
from hc.lib.string import replace
from hc.lib.typealias import JSONDict, JSONList, JSONValue

if TYPE_CHECKING:
    from hc.api.models import Channel, Check, Notification, Ping

try:
    import apprise
except ImportError:
    # Enforce
    settings.APPRISE_ENABLED = False

logger = logging.getLogger(__name__)


def tmpl(template_name: str, **ctx: Any) -> str:
    template_path = f"integrations/{template_name}"
    # \xa0 is non-breaking space. It causes SMS messages to use UCS2 encoding
    # and cost twice the money.
    return render_to_string(template_path, ctx).strip().replace("\xa0", " ")


def get_ping_body(ping: Ping | None, maxlen: int | None = None) -> str | None:
    """Return ping body for a given Ping object.

    Does two extra things in addition to simply calling Ping.get_body():
    * if body has not been uploaded to object storage yet, waits 5 seconds
      and tries to fetch it again
    * if body is longer than the `maxlen` argument, truncate it
    """
    body = None
    if ping and ping.has_body():
        body = ping.get_body()
        if body is None and ping.object_size:
            # Body is not uploaded to object storage yet.
            # Wait 5 seconds, then fetch the body again.
            time.sleep(5)
            body = ping.get_body()

    if body and maxlen and len(body) > maxlen:
        body = body[:maxlen] + "\n[truncated]"

    return body


class TransportError(Exception):
    def __init__(self, message: str, permanent: bool = False) -> None:
        self.message = message
        self.permanent = permanent


class Transport(object):
    def __init__(self, channel: Channel):
        self.channel = channel

    def notify(self, check: Check, notification: Notification) -> None:
        """Send notification about current status of the check.

        This method raises TransportError on error, and returns None
        on success.

        """

        raise NotImplementedError()

    def is_noop(self, check: Check) -> bool:
        """Return True if transport will ignore check's current status.

        This method is overridden in Webhook subclass where the user can
        configure webhook urls for "up" and "down" events, and both are
        optional.

        """

        return False

    def down_checks(self, check: Check) -> list[Check] | None:
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

    def last_ping(self, check: Check) -> Ping | None:
        """Return the last Ping object for this check."""

        if check.pk:
            return check.ping_set.order_by("created").last()

        return None


class RemovedTransport(Transport):
    """Dummy transport class for obsolete integrations: hipchat, pagerteam."""

    def is_noop(self, check: Check) -> bool:
        return True


class Email(Transport):
    def notify(self, check: Check, notification: Notification) -> None:
        if not self.channel.email_verified:
            raise TransportError("Email not verified")

        unsub_link = self.channel.get_unsub_link()

        headers = {
            "List-Unsubscribe": "<%s>" % unsub_link,
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "X-Bounce-ID": sign_bounce_id("n.%s" % notification.code),
        }

        from hc.accounts.models import Profile

        # If this email address has an associated account, include
        # a summary of projects the account has access to
        try:
            profile = Profile.objects.get(user__email=self.channel.email.value)
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

        emails.alert(self.channel.email.value, ctx, headers)

    def is_noop(self, check: Check) -> bool:
        if check.status == "down":
            return not self.channel.email.notify_down
        else:
            return not self.channel.email.notify_up


class Shell(Transport):
    def prepare(self, template: str, check: Check) -> str:
        """Replace placeholders with actual values."""

        ctx = {
            "$CODE": str(check.code),
            "$STATUS": check.status,
            "$NOW": now().replace(microsecond=0).isoformat(),
            "$NAME": check.name,
            "$TAGS": check.tags,
        }

        for i, tag in enumerate(check.tags_list()):
            ctx["$TAG%d" % (i + 1)] = tag

        return replace(template, ctx)

    def is_noop(self, check: Check) -> bool:
        if check.status == "down" and not self.channel.shell.cmd_down:
            return True

        if check.status == "up" and not self.channel.shell.cmd_up:
            return True

        return False

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.SHELL_ENABLED:
            raise TransportError("Shell commands are not enabled")

        if check.status == "up":
            cmd = self.channel.shell.cmd_up
        elif check.status == "down":
            cmd = self.channel.shell.cmd_down

        cmd = self.prepare(cmd, check)
        code = os.system(cmd)

        if code != 0:
            raise TransportError("Command returned exit code %d" % code)


class HttpTransport(Transport):
    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        # Subclasses can override this method to produce a more specific message.
        raise TransportError(f"Received status code {response.status_code}")

    @classmethod
    def _request(
        cls,
        method: str,
        url: str,
        *,
        params: curl.Params,
        data: curl.Data,
        json: Any,
        headers: curl.Headers,
        auth: curl.Auth,
    ) -> None:
        try:
            r = curl.request(
                method,
                url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                auth=auth,
                timeout=10,
            )
            if r.status_code not in (200, 201, 202, 204):
                cls.raise_for_response(r)
        except curl.CurlError as e:
            raise TransportError(e.message)

    @classmethod
    def request(
        cls,
        method: str,
        url: str,
        *,
        retry: bool,
        params: curl.Params = None,
        data: curl.Data = None,
        json: Any = None,
        headers: curl.Headers = None,
        auth: curl.Auth = None,
    ) -> None:
        start = time.time()
        tries_left = 3 if retry else 1
        while True:
            try:
                return cls._request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                    auth=auth,
                )
            except TransportError as e:
                tries_left = 0 if e.permanent else tries_left - 1

                # If we have no tries left *or* have already used more than
                # 15 seconds of time then abort the retry loop by re-raising
                # the exception:
                if tries_left == 0 or time.time() - start > 15:
                    raise e

    # Convenience wrapper around self.request for making "POST" requests
    @classmethod
    def post(
        cls,
        url: str,
        retry: bool = True,
        *,
        params: curl.Params = None,
        data: curl.Data = None,
        json: Any = None,
        headers: curl.Headers = None,
        auth: curl.Auth = None,
    ) -> None:
        cls.request(
            "post",
            url,
            retry=retry,
            params=params,
            data=data,
            json=json,
            headers=headers,
            auth=auth,
        )


class Webhook(HttpTransport):
    def prepare(
        self,
        template: str,
        check: Check,
        urlencode: bool = False,
        latin1: bool = False,
        allow_ping_body: bool = False,
    ) -> str:
        """Replace variables with actual values."""

        def safe(s: str) -> str:
            return quote(s) if urlencode else s

        ctx = {
            "$CODE": str(check.code),
            "$STATUS": check.status,
            "$NOW": safe(now().replace(microsecond=0).isoformat()),
            "$NAME": safe(check.name),
            "$TAGS": safe(check.tags),
            "$JSON": safe(json.dumps(check.to_dict())),
        }

        # Materialize ping body only if template refers to it.
        if allow_ping_body and "$BODY" in template:
            body = get_ping_body(self.last_ping(check))
            ctx["$BODY"] = body if body else ""

        if "$EXITSTATUS" in template:
            ctx["$EXITSTATUS"] = "-1"
            lp = self.last_ping(check)
            if lp and lp.exitstatus is not None:
                ctx["$EXITSTATUS"] = str(lp.exitstatus)

        for i, tag in enumerate(check.tags_list()):
            ctx["$TAG%d" % (i + 1)] = safe(tag)

        result = replace(template, ctx)
        if latin1:
            # Replace non-latin-1 characters with XML character references.
            result = result.encode("latin-1", "xmlcharrefreplace").decode("latin-1")

        return result

    def is_noop(self, check: Check) -> bool:
        spec = self.channel.webhook_spec(check.status)
        if not spec.url:
            return True

        return False

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.WEBHOOKS_ENABLED:
            raise TransportError("Webhook notifications are not enabled.")

        spec = self.channel.webhook_spec(check.status)
        if not spec.url:
            raise TransportError("Empty webhook URL")

        url = self.prepare(spec.url, check, urlencode=True)
        headers = {}
        for key, value in spec.headers.items():
            # Header values should contain ASCII and latin-1 only
            headers[key] = self.prepare(value, check, latin1=True)

        body, body_bytes = spec.body, None
        if body and spec.method in ("POST", "PUT"):
            body = self.prepare(body, check, allow_ping_body=True)
            body_bytes = body.encode()

        retry = True
        if notification.owner is None:
            # This is a test notification.
            # When sending a test notification, don't retry on failures.
            retry = False

        method = spec.method.lower()
        self.request(method, url, retry=retry, data=body_bytes, headers=headers)


class SlackFields(list[JSONValue]):
    """Helper class for preparing [{"title": ..., "value": ... }, ...] structures."""

    def add(self, title: str, value: str, short: bool = True) -> None:
        field: JSONDict = {"title": title, "value": value}
        if short:
            field["short"] = True
        self.append(field)


class Slackalike(HttpTransport):
    """Base class for transports that use Slack-compatible incoming webhooks."""

    def payload(self, check: Check) -> JSONDict:
        """Prepare JSON-serializable payload for Slack-compatible incoming webhook."""
        name = check.name_then_code()
        fields = SlackFields()
        result: JSONDict = {
            "username": settings.SITE_NAME,
            "icon_url": absolute_site_logo_url(),
            "attachments": [
                {
                    "color": "good" if check.status == "up" else "danger",
                    "fallback": f'The check "{name}" is {check.status.upper()}.',
                    "mrkdwn_in": ["fields"],
                    "title": f"“{name}” is {check.status.upper()}.",
                    "title_link": check.cloaked_url(),
                    "fields": fields,
                }
            ],
        }

        if check.desc:
            fields.add("Description", check.desc, short=False)

        if check.project.name:
            fields.add("Project", check.project.name)

        if tags := check.tags_list():
            fields.add("Tags", " ".join(f"`{tag}`" for tag in tags))

        if check.kind == "simple":
            fields.add("Period", format_duration(check.timeout))

        if check.kind == "cron":
            fields.add("Schedule", fix_asterisks(check.schedule))
            fields.add("Time Zone", check.tz)

        fields.add("Total Pings", str(check.n_pings))

        if ping := self.last_ping(check):
            created_str = naturaltime(ping.created)
            formatted_kind = ping.get_kind_display()
            fields.add("Last Ping", f"{formatted_kind}, {created_str}")
        else:
            fields.add("Last Ping", "Never")

        body = get_ping_body(ping, maxlen=1000)
        if body and "```" not in body:
            fields.add("Last Ping Body", f"```\n{body}\n```", short=False)

        return result

    def notify(self, check: Check, notification: Notification) -> None:
        self.post(self.channel.slack_webhook_url, json=self.payload(check))


class Slack(Slackalike):
    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        if response.status_code == 400:
            logger.debug("Slack returned HTTP 400 with body: %s", response.content)

        message = f"Received status code {response.status_code}"

        permanent = False
        if response.status_code == 404:
            # If Slack returns 404, this endpoint is unlikely to ever work again
            # https://api.slack.com/messaging/webhooks#handling_errors
            permanent = True
        elif response.status_code == 400 and response.content == b"invalid_token":
            # If Slack returns 400 with "invalid_token" in response body,
            # we're using a deactivated user's token to post to a private channel.
            # In theory this condition can recover (a deactivated user can be
            # activated), but in practice it is unlikely to happen.
            permanent = True

        raise TransportError(message, permanent=permanent)

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.SLACK_ENABLED:
            raise TransportError("Slack notifications are not enabled.")

        self.post(self.channel.slack_webhook_url, json=self.payload(check))


class Mattermost(Slackalike):
    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.MATTERMOST_ENABLED:
            raise TransportError("Mattermost notifications are not enabled.")

        self.post(self.channel.slack_webhook_url, json=self.payload(check))


class Discord(Slackalike):
    def notify(self, check: Check, notification: Notification) -> None:
        url = self.channel.discord_webhook_url + "/slack"
        self.post(url, json=self.payload(check))


class Opsgenie(HttpTransport):
    class ErrorModel(BaseModel):
        message: str

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        try:
            r = Opsgenie.ErrorModel.model_validate_json(response.content)
            message += f' with a message: "{r.message}"'
        except ValidationError:
            pass

        raise TransportError(message)

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.OPSGENIE_ENABLED:
            raise TransportError("Opsgenie notifications are not enabled.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": "GenieKey %s" % self.channel.opsgenie.key,
        }

        payload: JSONDict = {"alias": str(check.code), "source": settings.SITE_NAME}

        if check.status == "down":
            payload["tags"] = cast(JSONValue, check.tags_list())
            payload["message"] = tmpl("opsgenie_message.html", check=check)
            payload["note"] = tmpl("opsgenie_note.html", check=check)
            payload["description"] = tmpl("opsgenie_description.html", check=check)

        url = "https://api.opsgenie.com/v2/alerts"
        if self.channel.opsgenie.region == "eu":
            url = "https://api.eu.opsgenie.com/v2/alerts"

        if check.status == "up":
            url += "/%s/close?identifierType=alias" % check.code

        self.post(url, json=payload, headers=headers)


class PagerDuty(HttpTransport):
    URL = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"

    def notify(self, check: Check, notification: Notification) -> None:
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
            details["Time zone"] = check.tz

        description = tmpl("pd_description.html", check=check)
        payload = {
            "service_key": self.channel.pd.service_key,
            "incident_key": str(check.code),
            "event_type": "trigger" if check.status == "down" else "resolve",
            "description": description,
            "client": settings.SITE_NAME,
            "client_url": check.details_url(),
            "details": details,
        }

        self.post(self.URL, json=payload)


class PagerTree(HttpTransport):
    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.PAGERTREE_ENABLED:
            raise TransportError("PagerTree notifications are not enabled.")

        url = self.channel.value
        headers = {"Content-Type": "application/json"}
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
    def notify(self, check: Check, notification: Notification) -> None:
        text = tmpl("pushbullet_message.html", check=check)
        url = "https://api.pushbullet.com/v2/pushes"
        headers = {
            "Access-Token": self.channel.value,
            "Content-Type": "application/json",
        }
        payload = {"type": "note", "title": settings.SITE_NAME, "body": text}
        self.post(url, json=payload, headers=headers)


class Pushover(HttpTransport):
    URL = "https://api.pushover.net/1/messages.json"
    CANCEL_TMPL = "https://api.pushover.net/1/receipts/cancel_by_tag/%s.json"

    def is_noop(self, check: Check) -> bool:
        pieces = self.channel.value.split("|")
        _, prio = pieces[0], pieces[1]

        # The third element, if present, is the priority for "up" events
        if check.status == "up" and len(pieces) == 3:
            prio = pieces[2]

        return int(prio) == -3

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.PUSHOVER_API_TOKEN:
            raise TransportError("Pushover notifications are not enabled.")

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


class RocketChat(HttpTransport):
    def payload(self, check: Check) -> JSONDict:
        url = check.cloaked_url()
        color = "#5cb85c" if check.status == "up" else "#d9534f"
        fields = SlackFields()
        result: JSONDict = {
            "alias": settings.SITE_NAME,
            "avatar": absolute_site_logo_url(),
            "text": f"[{check.name_then_code()}]({url}) is {check.status.upper()}.",
            "attachments": [{"color": color, "fields": fields}],
        }

        if check.desc:
            fields.add("Description", check.desc, short=False)

        if check.project.name:
            fields.add("Project", check.project.name)

        if tags := check.tags_list():
            fields.add("Tags", " ".join(f"`{tag}`" for tag in tags))

        if check.kind == "simple":
            fields.add("Period", format_duration(check.timeout))

        if check.kind == "cron":
            fields.add("Schedule", fix_asterisks(check.schedule))
            fields.add("Time Zone", check.tz)

        fields.add("Total Pings", str(check.n_pings))

        if ping := self.last_ping(check):
            created_str = naturaltime(ping.created)
            formatted_kind = ping.get_kind_display()
            fields.add("Last Ping", f"{formatted_kind}, {created_str}")
            if body_size := ping.get_body_size():
                bytes_str = "byte" if body_size == 1 else "bytes"
                ping_url = f"{url}#ping-{ping.n}"
                text = f"{body_size} {bytes_str}, [show body]({ping_url})"
                fields.add("Last Ping Body", text)
        else:
            fields.add("Last Ping", "Never")

        return result

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.ROCKETCHAT_ENABLED:
            raise TransportError("Rocket.Chat notifications are not enabled.")
        self.post(self.channel.value, json=self.payload(check))


class VictorOps(HttpTransport):
    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        # If the endpoint returns 404, this endpoint is unlikely to ever work again
        permanent = response.status_code == 404
        raise TransportError(message, permanent=permanent)

    def notify(self, check: Check, notification: Notification) -> None:
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
    def get_url(self) -> str:
        s = quote(self.channel.value)

        assert isinstance(settings.MATRIX_HOMESERVER, str)
        url = settings.MATRIX_HOMESERVER
        url += "/_matrix/client/r0/rooms/%s/send/m.room.message?" % s
        url += urlencode({"access_token": settings.MATRIX_ACCESS_TOKEN})
        return url

    def notify(self, check: Check, notification: Notification) -> None:
        plain = tmpl("matrix_description.html", check=check)
        formatted = tmpl("matrix_description_formatted.html", check=check)
        payload = {
            "msgtype": "m.text",
            "body": plain,
            "format": "org.matrix.custom.html",
            "formatted_body": formatted,
        }

        self.post(self.get_url(), json=payload)


class MigrationRequiredError(TransportError):
    def __init__(self, message: str, new_chat_id: int):
        super().__init__(message, permanent=True)
        self.new_chat_id = new_chat_id


class Telegram(HttpTransport):
    SM = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"

    class MigrationParameters(BaseModel):
        migrate_to_chat_id: int

    class ErrorModel(BaseModel):
        description: str
        parameters: Telegram.MigrationParameters | None = None

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        try:
            m = Telegram.ErrorModel.model_validate_json(response.content)
        except ValidationError:
            raise TransportError(message)

        if m.parameters:
            # If the error payload contains the migrate_to_chat_id field,
            # raise MigrationRequiredError, with the new chat_id included
            chat_id = m.parameters.migrate_to_chat_id
            raise MigrationRequiredError(m.description, chat_id)

        permanent = False
        message += f' with a message: "{m.description}"'
        if m.description == "Forbidden: the group chat was deleted":
            permanent = True
        if m.description == "Forbidden: bot was blocked by the user":
            permanent = True

        raise TransportError(message, permanent=permanent)

    @classmethod
    def send(cls, chat_id: int, thread_id: int | None, text: str) -> None:
        # Telegram.send is a separate method because it is also used in
        # hc.front.views.telegram_bot to send invite links.
        payload = {
            "chat_id": chat_id,
            "message_thread_id": thread_id,
            "text": text,
            "parse_mode": "html",
        }
        cls.post(cls.SM, json=payload)

    def notify(self, check: Check, notification: Notification) -> None:
        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_telegram(self.channel.telegram.id):
            raise TransportError("Rate limit exceeded")

        ping = self.last_ping(check)
        ctx = {
            "check": check,
            "down_checks": self.down_checks(check),
            "ping": ping,
            # Telegram's message limit is 4096 chars, but clip body at 1000 for
            # consistency
            "body": get_ping_body(ping, maxlen=1000),
        }
        text = tmpl("telegram_message.html", **ctx)

        try:
            self.send(self.channel.telegram.id, self.channel.telegram.thread_id, text)
        except MigrationRequiredError as e:
            # Save the new chat_id, then try sending again:
            self.channel.update_telegram_id(e.new_chat_id)
            self.send(self.channel.telegram.id, self.channel.telegram.thread_id, text)


class Sms(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    def is_noop(self, check: Check) -> bool:
        if check.status == "down":
            return not self.channel.phone.notify_down
        else:
            return not self.channel.phone.notify_up

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.TWILIO_ACCOUNT or not settings.TWILIO_AUTH:
            raise TransportError("SMS notifications are not enabled")

        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            profile.send_sms_limit_notice("SMS")
            raise TransportError("Monthly SMS limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = tmpl("sms_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "To": self.channel.phone.value,
            "Body": text,
            "StatusCallback": notification.status_url(),
        }

        if settings.TWILIO_MESSAGING_SERVICE_SID:
            data["MessagingServiceSid"] = settings.TWILIO_MESSAGING_SERVICE_SID
        else:
            assert settings.TWILIO_FROM
            data["From"] = settings.TWILIO_FROM

        self.post(url, data=data, auth=auth)


class Call(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Calls.json"

    def is_noop(self, check: Check) -> bool:
        return check.status != "down"

    def notify(self, check: Check, notification: Notification) -> None:
        if (
            not settings.TWILIO_ACCOUNT
            or not settings.TWILIO_AUTH
            or not settings.TWILIO_FROM
        ):
            raise TransportError("Call notifications are not enabled")

        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_call():
            profile.send_call_limit_notice()
            raise TransportError("Monthly phone call limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        twiml = tmpl("call_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "From": settings.TWILIO_FROM,
            "To": self.channel.phone.value,
            "Twiml": twiml,
            "StatusCallback": notification.status_url(),
        }

        self.post(url, data=data, auth=auth)


class WhatsApp(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    def is_noop(self, check: Check) -> bool:
        if check.status == "down":
            return not self.channel.phone.notify_down
        else:
            return not self.channel.phone.notify_up

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.TWILIO_ACCOUNT or not settings.TWILIO_AUTH:
            raise TransportError("WhatsApp notifications are not enabled")

        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            profile.send_sms_limit_notice("WhatsApp")
            raise TransportError("Monthly message limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = tmpl("whatsapp_message.html", check=check, site_name=settings.SITE_NAME)

        data = {
            "To": f"whatsapp:{self.channel.phone.value}",
            "Body": text,
            "StatusCallback": notification.status_url(),
        }

        if settings.TWILIO_MESSAGING_SERVICE_SID:
            data["MessagingServiceSid"] = settings.TWILIO_MESSAGING_SERVICE_SID
        else:
            data["From"] = f"whatsapp:{settings.TWILIO_FROM}"

        self.post(url, data=data, auth=auth)


class Trello(HttpTransport):
    URL = "https://api.trello.com/1/cards"

    def is_noop(self, check: Check) -> bool:
        return check.status != "down"

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.TRELLO_APP_KEY:
            raise TransportError("Trello notifications are not enabled.")

        params = {
            "idList": self.channel.trello.list_id,
            "name": tmpl("trello_name.html", check=check),
            "desc": tmpl("trello_desc.html", check=check),
            "key": settings.TRELLO_APP_KEY,
            "token": self.channel.trello.token,
        }

        self.post(self.URL, params=params)


class Apprise(HttpTransport):
    def notify(self, check: Check, notification: Notification) -> None:
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
    def payload(self, check: Check) -> JSONDict:
        name = check.name_then_code()
        facts: JSONList = []
        sections: JSONList = [{"text": check.desc, "facts": facts}]
        result: JSONDict = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "title": f"“{escape(name)}” is {check.status.upper()}.",
            "summary": f"“{name}” is {check.status.upper()}.",
            "themeColor": "5cb85c" if check.status == "up" else "d9534f",
            "sections": sections,
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": f"View in {settings.SITE_NAME}",
                    "targets": [{"os": "default", "uri": check.cloaked_url()}],
                }
            ],
        }

        if tags := check.tags_list():
            formatted_tags = " ".join(f"`{tag}`" for tag in tags)
            facts.append({"name": "Tags:", "value": formatted_tags})

        if check.kind == "simple":
            facts.append({"name": "Period:", "value": format_duration(check.timeout)})

        if check.kind == "cron":
            facts.append({"name": "Schedule:", "value": fix_asterisks(check.schedule)})
            facts.append({"name": "Time Zone:", "value": check.tz})

        facts.append({"name": "Total Pings:", "value": str(check.n_pings)})

        if ping := self.last_ping(check):
            text = f"{ping.get_kind_display()}, {naturaltime(ping.created)}"
            facts.append({"name": "Last Ping:", "value": text})
        else:
            facts.append({"name": "Last Ping:", "value": "Never"})

        body = get_ping_body(ping, maxlen=1000)
        if body and "```" not in body:
            section_text = f"**Last Ping Body**:\n```\n{ body }\n```"
            sections.append({"text": section_text})

        return result

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.MSTEAMS_ENABLED:
            raise TransportError("MS Teams notifications are not enabled.")

        self.post(self.channel.value, json=self.payload(check))


class Zulip(HttpTransport):
    class ErrorModel(BaseModel):
        msg: str

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        try:
            f = Zulip.ErrorModel.model_validate_json(response.content)
            message += f' with a message: "{f.msg}"'
        except ValidationError:
            pass

        raise TransportError(message)

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.ZULIP_ENABLED:
            raise TransportError("Zulip notifications are not enabled.")

        topic = self.channel.zulip.topic
        if not topic:
            topic = tmpl("zulip_topic.html", check=check)

        url = self.channel.zulip.site + "/api/v1/messages"
        auth = (self.channel.zulip.bot_email, self.channel.zulip.api_key)
        data = {
            "type": self.channel.zulip.mtype,
            "to": self.channel.zulip.to,
            "topic": topic,
            "content": tmpl("zulip_content.html", check=check),
        }

        self.post(url, data=data, auth=auth)


class Spike(HttpTransport):
    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.SPIKE_ENABLED:
            raise TransportError("Spike notifications are not enabled.")

        url = self.channel.value
        headers = {"Content-Type": "application/json"}
        payload = {
            "check_id": str(check.code),
            "title": tmpl("spike_title.html", check=check),
            "message": tmpl("spike_description.html", check=check),
            "status": check.status,
        }

        self.post(url, json=payload, headers=headers)


class LineNotify(HttpTransport):
    URL = "https://notify-api.line.me/api/notify"

    def notify(self, check: Check, notification: Notification) -> None:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Bearer %s" % self.channel.linenotify_token,
        }
        payload = {"message": tmpl("linenotify_message.html", check=check)}
        self.post(self.URL, headers=headers, params=payload)


class SignalRateLimitFailure(TransportError):
    def __init__(self, token: str, reply: bytes):
        super().__init__("CAPTCHA proof required")
        self.token = token
        self.reply = reply


class Signal(Transport):
    class Recipient(BaseModel):
        number: str

    class Result(BaseModel):
        type: str
        recipientAddress: Signal.Recipient
        token: str | None = None

    class Response(BaseModel):
        results: list[Signal.Result]

    class Data(BaseModel):
        response: Signal.Response

    class Error(BaseModel):
        code: int
        data: Signal.Data | None = None

    class Reply(BaseModel):
        id: str = ""
        error: Signal.Error | None = None

        def get_results(self) -> list[Signal.Result]:
            assert self.error
            if self.error.data is None:
                return []
            return self.error.data.response.results

    def is_noop(self, check: Check) -> bool:
        if check.status == "down":
            return not self.channel.phone.notify_down
        else:
            return not self.channel.phone.notify_up

    @classmethod
    def send(cls, recipient: str, message: str) -> None:
        plaintext, styles = extract_signal_styles(message)
        payload = {
            "jsonrpc": "2.0",
            "method": "send",
            "params": {
                "recipient": [recipient],
                "message": plaintext,
                "textStyle": styles,
            },
            "id": str(uuid.uuid4()),
        }

        payload_bytes = (json.dumps(payload) + "\n").encode()
        for reply_bytes in cls._read_replies(payload_bytes):
            try:
                reply = Signal.Reply.model_validate_json(reply_bytes)
            except ValidationError:
                logger.error("unexpected signal-cli response: %s", reply_bytes)
                raise TransportError("signal-cli call failed (unexpected response)")

            if reply.id != payload["id"]:
                continue

            if reply.error is None:
                break  # success!

            for result in reply.get_results():
                if result.recipientAddress.number != recipient:
                    continue

                if result.type == "UNREGISTERED_FAILURE":
                    raise TransportError("Recipient not found")

                if result.type == "RATE_LIMIT_FAILURE" and result.token:
                    raise SignalRateLimitFailure(result.token, reply_bytes)

            code = reply.error.code
            raise TransportError(f"signal-cli call failed ({code})")

    @classmethod
    def _read_replies(cls, payload_bytes: bytes) -> Iterator[bytes]:
        """Send a request to signal-cli over UNIX socket. Read and yield replies.

        This method:
        * opens UNIX socket
        * sends the request data (JSON RPC data encoded as bytes)
        * reads newline-terminated responses and yields them

        Individual sendall and recv operations have a timeout of 15 seconds.
        This method also keeps track of total time spent in the method, and raises
        an exception when the total time exceeds 15 seconds.

        """

        if not settings.SIGNAL_CLI_SOCKET:
            raise TransportError("Signal notifications are not enabled")

        start = time.time()
        address: str | tuple[str, int]
        if ":" in settings.SIGNAL_CLI_SOCKET:
            stype = socket.AF_INET
            parts = settings.SIGNAL_CLI_SOCKET.split(":")
            address = (parts[0], int(parts[1]))
        else:
            stype = socket.AF_UNIX
            address = settings.SIGNAL_CLI_SOCKET

        with socket.socket(stype, socket.SOCK_STREAM) as s:
            s.settimeout(15)
            try:
                s.connect(address)
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

    def notify(self, check: Check, notification: Notification) -> None:
        if not settings.SIGNAL_CLI_SOCKET:
            raise TransportError("Signal notifications are not enabled")

        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_signal(self.channel.phone.value):
            raise TransportError("Rate limit exceeded")

        ctx = {
            "check": check,
            "ping": self.last_ping(check),
            "down_checks": self.down_checks(check),
        }
        text = tmpl("signal_message.html", **ctx)
        try:
            self.send(self.channel.phone.value, text)
        except SignalRateLimitFailure as e:
            self.channel.send_signal_captcha_alert(e.token, e.reply.decode())
            plaintext, _ = extract_signal_styles(text)
            self.channel.send_signal_rate_limited_notice(text, plaintext)
            raise e


class Gotify(HttpTransport):
    def notify(self, check: Check, notification: Notification) -> None:
        url = urljoin(self.channel.gotify.url, "/message")
        url += "?" + urlencode({"token": self.channel.gotify.token})

        ctx = {"check": check, "down_checks": self.down_checks(check)}
        payload = {
            "title": tmpl("gotify_title.html", **ctx),
            "message": tmpl("gotify_message.html", **ctx),
            "extras": {
                "client::display": {"contentType": "text/markdown"},
            },
        }

        self.post(url, json=payload)


class Group(Transport):
    def notify(self, check: Check, notification: Notification) -> None:
        channels = self.channel.group_channels
        # If notification's owner field is None then this is a test notification,
        # and we should pass is_test=True to channel.notify() calls
        is_test = notification.owner is None
        error_count = 0
        for channel in channels:
            error = channel.notify(check, is_test=is_test)
            if error and error != "no-op":
                error_count += 1
        if error_count:
            raise TransportError(
                f"{error_count} out of {len(channels)} notifications failed"
            )


class Ntfy(HttpTransport):
    def priority(self, check: Check) -> int:
        if check.status == "up":
            return self.channel.ntfy.priority_up
        return self.channel.ntfy.priority

    def is_noop(self, check: Check) -> bool:
        return self.priority(check) == 0

    def notify(self, check: Check, notification: Notification) -> None:
        ctx = {
            "check": check,
            "ping": self.last_ping(check),
            "down_checks": self.down_checks(check),
        }
        payload = {
            "topic": self.channel.ntfy.topic,
            "priority": self.priority(check),
            "title": tmpl("ntfy_title.html", **ctx),
            "message": tmpl("ntfy_message.html", **ctx),
            "tags": ["red_circle" if check.status == "down" else "green_circle"],
            "actions": [
                {
                    "action": "view",
                    "label": f"View on {settings.SITE_NAME}",
                    "url": check.cloaked_url(),
                }
            ],
        }

        headers = {}
        if self.channel.ntfy.token:
            headers = {"Authorization": f"Bearer {self.channel.ntfy.token}"}

        self.post(self.channel.ntfy.url, headers=headers, json=payload)
