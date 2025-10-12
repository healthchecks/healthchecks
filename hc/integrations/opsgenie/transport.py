from __future__ import annotations

from typing import NoReturn, cast

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.lib import curl
from hc.lib.date import format_duration
from hc.lib.typealias import JSONDict, JSONValue
from pydantic import BaseModel, ValidationError


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
            payload["message"] = self.tmpl("opsgenie_message.html", **ctx)
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
