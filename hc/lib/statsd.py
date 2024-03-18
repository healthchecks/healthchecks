from __future__ import annotations

from django.conf import settings
from statsd.client.base import StatsClientBase
from statsd.client.udp import StatsClient


class NoopClient(StatsClientBase):
    """A client for statsd that does nothing."""

    _prefix = None

    def _send(self, data: str) -> None:
        pass

    def close(self) -> None:
        pass

    def pipeline(self) -> None:
        pass


def get_client() -> StatsClientBase:
    """Initialize and return statsd client.

    If settings.STATSD_HOST is set, initialize a UDP client.
    Otherwise, initialize a no-op client.

    The syntax for settings.STATSD_HOST is "example.org" (will assume port 8125)
    or "example.org:1234" (will use port 1234).

    """

    if settings.STATSD_HOST:
        parts = settings.STATSD_HOST.split(":", maxsplit=1)
        host, port = parts[0], 8125
        if len(parts) == 2:
            port = int(parts[1])
        return StatsClient(host=host, port=port)

    return NoopClient()


statsd = get_client()
