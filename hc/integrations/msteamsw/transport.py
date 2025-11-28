from __future__ import annotations

from django.conf import settings
from django.utils.html import escape
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError, get_ping_body
from hc.integrations.slack.transport import SlackFields
from hc.lib.date import format_duration
from hc.lib.typealias import JSONDict, JSONList


class MsTeamsWorkflow(HttpTransport):
    def fix_asterisks(self, s: str) -> str:
        """Escape asterisks so that they are not recognized as Markdown syntax."""
        return s.replace("*", "\u034f*")

    def payload(self, flip: Flip) -> JSONDict:
        check = flip.owner
        name = check.name_then_code()
        fields = SlackFields()
        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
        }
        text = self.tmpl("msteamsw_message.html", **ctx)

        blocks: JSONList = [
            {
                "type": "TextBlock",
                "text": text,
                "weight": "bolder",
                "size": "medium",
                "wrap": True,
                "style": "heading",
            },
            {
                "type": "FactSet",
                "facts": fields,
            },
        ]

        result: JSONDict = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "fallbackText": f"“{escape(name)}” is {flip.new_status.upper()}.",
                        "version": "1.2",
                        "body": blocks,
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": f"View in {settings.SITE_NAME}",
                                "url": check.cloaked_url(),
                            }
                        ],
                    },
                }
            ],
        }

        if check.desc:
            fields.add("Description:", check.desc.replace("\n", "\n\n"))

        if check.project.name:
            fields.add("Project:", check.project.name)

        if tags := check.tags_list():
            formatted_tags = " ".join(tags)
            fields.add("Tags:", formatted_tags)

        if check.kind == "simple":
            fields.add("Period:", format_duration(check.timeout))

        if check.kind in ("cron", "oncalendar"):
            fields.add("Schedule:", self.fix_asterisks(check.schedule))
            fields.add("Time Zone:", check.tz)

        if ping := self.last_ping(flip):
            fields.add("Total Pings:", str(ping.n))
            fields.add("Last Ping:", ping.formatted_kind_created())
        else:
            fields.add("Total Pings:", "0")
            fields.add("Last Ping:", "Never")

        if body := get_ping_body(ping, maxlen=1000):
            blocks.append(
                {
                    "type": "TextBlock",
                    "text": "Last Ping Body:",
                    "weight": "bolder",
                }
            )
            blocks.append(
                {
                    "type": "CodeBlock",
                    "codeSnippet": body,
                    "language": "PlainText",
                }
            )

        return result

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.MSTEAMS_ENABLED:
            raise TransportError("MS Teams notifications are not enabled.")

        self.post(self.channel.value, json=self.payload(flip))
