from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.front.templatetags.hc_extras import absolute_site_logo_url
from hc.integrations.slack.transport import SlackFields
from hc.lib.date import format_duration
from hc.lib.typealias import JSONDict


class RocketChat(HttpTransport):
    def fix_asterisks(self, s: str) -> str:
        # In Rocket.Chat notifications asterisks should be escaped with a backslash
        return s.replace("*", r"\*")

    def payload(self, flip: Flip) -> JSONDict:
        check = flip.owner
        url = check.cloaked_url()
        color = "#5cb85c" if flip.new_status == "up" else "#d9534f"
        fields = SlackFields()
        result: JSONDict = {
            "alias": settings.SITE_NAME,
            "avatar": absolute_site_logo_url(),
            "text": self.tmpl("rocketchat_message.html", flip=flip, check=check),
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

        if check.kind in ("cron", "oncalendar"):
            fields.add("Schedule", self.fix_asterisks(check.schedule))
            fields.add("Time Zone", check.tz)

        if ping := self.last_ping(flip):
            fields.add("Total Pings", str(ping.n))
            fields.add("Last Ping", ping.formatted_kind_created())
            if body_size := ping.get_body_size():
                bytes_str = "byte" if body_size == 1 else "bytes"
                ping_url = f"{url}#ping-{ping.n}"
                text = f"{body_size} {bytes_str}, [show body]({ping_url})"
                fields.add("Last Ping Body", text)
        else:
            fields.add("Total Pings", "0")
            fields.add("Last Ping", "Never")

        return result

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.ROCKETCHAT_ENABLED:
            raise TransportError("Rocket.Chat notifications are not enabled.")

        prepared_payload = self.payload(flip)
        self.post(self.channel.value, json=prepared_payload)
