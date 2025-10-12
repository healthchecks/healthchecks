from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError

try:
    import apprise

    have_apprise = True
except ImportError:
    have_apprise = False


class Apprise(HttpTransport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.APPRISE_ENABLED or not have_apprise:
            raise TransportError("Apprise is disabled and/or not installed")

        a = apprise.Apprise()
        check, status, ping = flip.owner, flip.new_status, self.last_ping(flip)
        title = self.tmpl("apprise_title.html", check=check, status=status)
        body = self.tmpl(
            "apprise_description.html", check=check, status=status, ping=ping
        )

        a.add(self.channel.value)

        notify_type = (
            apprise.NotifyType.SUCCESS if status == "up" else apprise.NotifyType.FAILURE
        )

        if not a.notify(body=body, title=title, notify_type=notify_type):
            raise TransportError("Failed")
