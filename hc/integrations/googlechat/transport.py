from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport
from hc.lib.date import format_duration
from hc.lib.typealias import JSONValue


class GoogleChatFields(list[JSONValue]):
    """Helper class for preparing [{"title": ..., "value": ... }, ...] structures."""

    def add(self, title: str, value: str) -> None:
        self.append({"decoratedText": {"topLabel": title, "text": value}})


class GoogleChat(HttpTransport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        ping = self.last_ping(flip)
        check = flip.owner

        fields = GoogleChatFields()

        emoji = "🔴" if flip.new_status == "down" else "🟢"
        title = f"{emoji} <b>{check.name_then_code()}</b> is <b>{flip.new_status.upper()}</b>. "
        if flip.reason:
            title += f"Reason: {flip.reason_long()}."
        fields.append({"textParagraph": {"text": title}})

        if check.project.name:
            fields.add("Project", check.project.name)

        if tags := check.tags_list():
            fields.add("Tags", ", ".join(tags))

        if check.kind == "simple":
            fields.add("Period", format_duration(check.timeout))

        if check.kind in ("cron", "oncalendar"):
            fields.add("Schedule", check.schedule)
            fields.add("Time Zone", check.tz)

        if ping := self.last_ping(flip):
            fields.add("Total Pings", str(ping.n))
            fields.add("Last Ping", ping.formatted_kind_created())
        else:
            fields.add("Total Pings", "0")
            fields.add("Last Ping", "Never")

        fields.append(
            {
                "buttonList": {
                    "buttons": [
                        {
                            "text": f"View in {settings.SITE_NAME}",
                            "type": "FILLED",
                            "onClick": {"openLink": {"url": check.cloaked_url()}},
                        },
                    ]
                }
            }
        )

        payload = {
            "cardsV2": [
                {
                    "card": {
                        "sections": {
                            "collapsible": True,
                            "uncollapsibleWidgetsCount": 1,
                            "widgets": fields,
                        }
                    }
                }
            ]
        }

        self.post(self.channel.value, json=payload)
