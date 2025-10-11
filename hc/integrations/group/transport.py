from __future__ import annotations

from hc.api.models import Flip, Notification
from hc.api.transports import Transport, TransportError


class Group(Transport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        channels = self.channel.group_channels
        # If notification's owner field is None then this is a test notification,
        # and we should pass is_test=True to channel.notify() calls
        is_test = notification.owner is None
        error_count = 0
        for channel in channels:
            error = channel.notify(flip, is_test=is_test)
            if error and error != "no-op":
                error_count += 1
        if error_count:
            raise TransportError(
                f"{error_count} out of {len(channels)} notifications failed"
            )
