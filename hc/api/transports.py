from __future__ import annotations

import email
import json
import logging
import os
import time
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any, NoReturn, cast
from urllib.parse import quote, urlencode

from django.conf import settings
from django.template.loader import render_to_string
from hc.accounts.models import Profile
from hc.front.templatetags.hc_extras import absolute_site_logo_url, sortchecks
from hc.lib import curl, emails
from hc.lib.date import format_duration
from hc.lib.signing import sign_bounce_id
from hc.lib.string import replace
from hc.lib.typealias import JSONDict, JSONValue
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from hc.api.models import Channel, Check, Flip, Notification, Ping


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


class Transport:
    def __init__(self, channel: Channel):
        self.channel = channel

    def notify(self, flip: Flip, notification: Notification) -> None:
        """Send notification about current status of the check.

        This method raises TransportError on error, and returns None
        on success.

        """

        raise NotImplementedError()

    def is_noop(self, status: str) -> bool:
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

    def last_ping(self, flip: Flip) -> Ping | None:
        """Return the last Ping object received before this flip."""

        if not flip.owner.pk:
            return None

        # Sort by "created". Sorting by "id" can cause postgres to pick api_ping.id
        # index (slow if the api_ping table is big)
        q = flip.owner.ping_set.order_by("created")
        # Make sure we're not selecting pings that occurred after the flip
        q = q.filter(created__lte=flip.created)

        return q.last()


class RemovedTransport(Transport):
    """Dummy transport class for obsolete integrations."""

    def is_noop(self, status: str) -> bool:
        return True


class Email(Transport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        if not self.channel.email_verified:
            raise TransportError("Email not verified")

        unsub_link = self.channel.get_unsub_link()

        headers = {
            "List-Unsubscribe": f"<{unsub_link}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "X-Bounce-ID": sign_bounce_id(f"n.{notification.code}"),
        }

        # If this email address has an associated account, include
        # a summary of projects the account has access to
        try:
            profile = Profile.objects.get(user__email=self.channel.email.value)
            projects = list(profile.projects())
        except Profile.DoesNotExist:
            projects = None

        ping = self.last_ping(flip)
        body = get_ping_body(ping)
        subject = None
        if ping is not None and ping.scheme == "email" and body:
            parsed = email.message_from_string(body, policy=email.policy.SMTP)
            assert isinstance(parsed, EmailMessage)
            subject = parsed.get("subject", "")

        ctx = {
            "flip": flip,
            "check": flip.owner,
            "ping": ping,
            "body": body,
            "subject": subject,
            "projects": projects,
            "unsub_link": unsub_link,
        }

        emails.alert(self.channel.email.value, ctx, headers)

    def is_noop(self, status: str) -> bool:
        if status == "down":
            return not self.channel.email.notify_down
        else:
            return not self.channel.email.notify_up


class Shell(Transport):
    def prepare(self, template: str, flip: Flip) -> str:
        """Replace placeholders with actual values."""

        check = flip.owner
        ctx = {
            "$CODE": str(check.code),
            "$STATUS": flip.new_status,
            "$NOW": flip.created.replace(microsecond=0).isoformat(),
            "$NAME": check.name,
            "$TAGS": check.tags,
        }

        for i, tag in enumerate(check.tags_list()):
            ctx["$TAG%d" % (i + 1)] = tag

        return replace(template, ctx)

    def is_noop(self, status: str) -> bool:
        if status == "down" and not self.channel.shell.cmd_down:
            return True

        if status == "up" and not self.channel.shell.cmd_up:
            return True

        return False

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.SHELL_ENABLED:
            raise TransportError("Shell commands are not enabled")

        if flip.new_status == "up":
            cmd = self.channel.shell.cmd_up
        elif flip.new_status == "down":
            cmd = self.channel.shell.cmd_down

        cmd = self.prepare(cmd, flip)
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
                timeout=30,
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
                # If we have no tries left then abort the retry loop by re-raising
                # the exception:
                if tries_left == 0:
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
        flip: Flip,
        urlencode: bool = False,
        latin1: bool = False,
        allow_ping_body: bool = False,
    ) -> str:
        """Replace variables with actual values."""

        def safe(s: str) -> str:
            return quote(s) if urlencode else s

        check = flip.owner
        ctx = {
            "$CODE": str(check.code),
            "$STATUS": flip.new_status,
            "$NOW": safe(flip.created.replace(microsecond=0).isoformat()),
            "$NAME_JSON": safe(json.dumps(check.name)),
            "$NAME": safe(check.name),
            "$SLUG": check.slug,
            "$TAGS": safe(check.tags),
            "$JSON": safe(json.dumps(check.to_dict())),
        }

        # Materialize ping body only if template refers to it.
        if allow_ping_body and "$BODY" in template:
            body = get_ping_body(self.last_ping(flip))
            ctx["$BODY_JSON"] = json.dumps(body if body else "")
            ctx["$BODY"] = body if body else ""

        if "$EXITSTATUS" in template:
            ctx["$EXITSTATUS"] = "-1"
            lp = self.last_ping(flip)
            if lp and lp.exitstatus is not None:
                ctx["$EXITSTATUS"] = str(lp.exitstatus)

        for i, tag in enumerate(check.tags_list()):
            ctx["$TAG%d" % (i + 1)] = safe(tag)

        result = replace(template, ctx)
        if latin1:
            # Replace non-latin-1 characters with XML character references.
            result = result.encode("latin-1", "xmlcharrefreplace").decode("latin-1")

        return result

    def is_noop(self, status: str) -> bool:
        spec = self.channel.webhook_spec(status)
        if not spec.url:
            return True

        return False

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.WEBHOOKS_ENABLED:
            raise TransportError("Webhook notifications are not enabled.")

        spec = self.channel.webhook_spec(flip.new_status)
        if not spec.url:
            raise TransportError("Empty webhook URL")

        method = spec.method.lower()
        url = self.prepare(spec.url, flip, urlencode=True)
        retry = True
        if notification.owner is None:
            # This is a test notification.
            # When sending a test notification, don't retry on failures.
            retry = False

        body, body_bytes = spec.body, None
        if body and spec.method in ("POST", "PUT"):
            body = self.prepare(body, flip, allow_ping_body=True)
            body_bytes = body.encode()

        headers = {}
        for key, value in spec.headers.items():
            # Header values should contain ASCII and latin-1 only
            headers[key] = self.prepare(value, flip, latin1=True)

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

    def payload(self, flip: Flip) -> JSONDict:
        """Prepare JSON-serializable payload for Slack-compatible incoming webhook."""
        check = flip.owner
        name = check.name_then_code()
        fields = SlackFields()
        result: JSONDict = {
            "username": settings.SITE_NAME,
            "icon_url": absolute_site_logo_url(),
            "attachments": [
                {
                    "color": "good" if flip.new_status == "up" else "danger",
                    "fallback": f'The check "{name}" is {flip.new_status.upper()}.',
                    "mrkdwn_in": ["fields"],
                    "title": f"“{name}” is {flip.new_status.upper()}.",
                    "title_link": check.cloaked_url(),
                    "text": f"Reason: {flip.reason_long()}." if flip.reason else None,
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

        if check.kind in ("cron", "oncalendar"):
            fields.add("Schedule", self.fix_asterisks(check.schedule))
            fields.add("Time Zone", check.tz)

        if ping := self.last_ping(flip):
            fields.add("Total Pings", str(ping.n))
            fields.add("Last Ping", ping.formatted_kind_created())
        else:
            fields.add("Total Pings", "0")
            fields.add("Last Ping", "Never")

        body = get_ping_body(ping, maxlen=1000)
        if body and "```" not in body:
            fields.add("Last Ping Body", f"```\n{body}\n```", short=False)

        return result

    def fix_asterisks(self, s: str) -> str:
        """Escape asterisks so that they are not recognized as Markdown syntax."""

        # The base implementation prepends asterisks with "Combining Grapheme Joiner"
        # characters but subclasses can override this function and escape
        # asterisks differently
        return s.replace("*", "\u034f*")

    def notify(self, flip: Flip, notification: Notification) -> None:
        self.post(self.channel.slack_webhook_url, json=self.payload(flip))


class Slack(Slackalike):
    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        permanent = False
        if response.status_code == 404:
            # If Slack returns 404, this endpoint is unlikely to ever work again
            # https://api.slack.com/messaging/webhooks#handling_errors
            permanent = True
        elif response.status_code == 400:
            if response.content == b"invalid_token":
                # If Slack returns 400 with "invalid_token" in response body,
                # we're using a deactivated user's token to post to a private channel.
                # In theory this condition can recover (a deactivated user can be
                # activated), but in practice it is unlikely to happen.
                permanent = True
            else:
                # Log it for later inspection
                logger.debug("Slack returned HTTP 400 with body: %s", response.content)

        raise TransportError(message, permanent=permanent)

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.SLACK_ENABLED:
            raise TransportError("Slack notifications are not enabled.")

        self.post(self.channel.slack_webhook_url, json=self.payload(flip))


class Mattermost(Slackalike):
    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.MATTERMOST_ENABLED:
            raise TransportError("Mattermost notifications are not enabled.")

        prepared_payload = self.payload(flip)
        self.post(self.channel.slack_webhook_url, json=prepared_payload)


class Discord(Slackalike):
    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        # Consider 404 a permanent failure
        permanent = response.status_code == 404
        raise TransportError(message, permanent=permanent)

    def notify(self, flip: Flip, notification: Notification) -> None:
        url = self.channel.discord_webhook_url + "/slack"

        prepared_payload = self.payload(flip)
        self.post(url, json=prepared_payload)

    def fix_asterisks(self, s: str) -> str:
        # In Discord notifications asterisks should be escaped with a backslash
        return s.replace("*", r"\*")


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

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.OPSGENIE_ENABLED:
            raise TransportError("Opsgenie notifications are not enabled.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"GenieKey {self.channel.opsgenie.key}",
        }

        check = flip.owner
        payload: JSONDict = {
            "alias": str(check.unique_key),
            "source": settings.SITE_NAME,
        }

        if flip.new_status == "down":
            ctx = {"flip": flip, "check": check, "ping": self.last_ping(flip)}
            payload["tags"] = cast(JSONValue, check.tags_list())
            payload["message"] = tmpl("opsgenie_message.html", **ctx)
            payload["description"] = check.desc

            details: JSONDict = {}
            details["Project"] = check.project.name
            if ping := self.last_ping(flip):
                details["Total pings"] = ping.n
                details["Last ping"] = ping.formatted_kind_created()
            else:
                details["Total pings"] = 0
                details["Last ping"] = "Never"

            if check.kind == "simple":
                details["Period"] = format_duration(check.timeout)
            if check.kind in ("cron", "oncalendar"):
                details["Schedule"] = f"<code>{check.schedule}</code>"
                details["Time zone"] = check.tz
            details["Full details"] = check.cloaked_url()
            payload["details"] = details

        url = "https://api.opsgenie.com/v2/alerts"
        if self.channel.opsgenie.region == "eu":
            url = "https://api.eu.opsgenie.com/v2/alerts"

        if flip.new_status == "up":
            url += f"/{check.unique_key}/close?identifierType=alias"

        self.post(url, json=payload, headers=headers)


class PagerDuty(HttpTransport):
    URL = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.PD_ENABLED:
            raise TransportError("PagerDuty notifications are not enabled.")

        check = flip.owner
        details: JSONDict = {
            "Project": check.project.name,
        }
        if ping := self.last_ping(flip):
            details["Total pings"] = ping.n
            details["Last ping"] = ping.formatted_kind_created()
        else:
            details["Total pings"] = 0
            details["Last ping"] = "Never"

        if check.desc:
            details["Description"] = check.desc
        if check.tags:
            details["Tags"] = ", ".join(check.tags_list())
        if check.kind == "simple":
            details["Period"] = format_duration(check.timeout)
        if check.kind in ("cron", "oncalendar"):
            details["Schedule"] = check.schedule
            details["Time zone"] = check.tz

        ctx = {"flip": flip, "check": check, "status": flip.new_status}
        description = tmpl("pd_description.html", **ctx)
        payload = {
            "service_key": self.channel.pd.service_key,
            "incident_key": check.unique_key,
            "event_type": "trigger" if flip.new_status == "down" else "resolve",
            "description": description,
            "client": settings.SITE_NAME,
            "client_url": check.details_url(),
            "details": details,
        }

        self.post(self.URL, json=payload)


class PagerTree(HttpTransport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.PAGERTREE_ENABLED:
            raise TransportError("PagerTree notifications are not enabled.")

        url = self.channel.value
        headers = {"Content-Type": "application/json"}
        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "ping": self.last_ping(flip),
        }
        payload = {
            "incident_key": str(flip.owner.unique_key),
            "event_type": "trigger" if flip.new_status == "down" else "resolve",
            "title": tmpl("pagertree_title.html", **ctx),
            "description": tmpl("pagertree_description.html", **ctx),
            "client": settings.SITE_NAME,
            "client_url": settings.SITE_ROOT,
            "tags": " ".join(flip.owner.tags_list()),
        }

        self.post(url, json=payload, headers=headers)
