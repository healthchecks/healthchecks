from __future__ import annotations

import logging
from typing import NoReturn

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError, get_ping_body
from hc.front.templatetags.hc_extras import absolute_site_logo_url
from hc.lib import curl
from hc.lib.date import format_duration
from hc.lib.typealias import JSONDict, JSONValue

logger = logging.getLogger(__name__)


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
