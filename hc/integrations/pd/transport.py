from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.lib.date import format_duration
from hc.lib.typealias import JSONDict


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
        description = self.tmpl("pd_description.html", **ctx)
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
