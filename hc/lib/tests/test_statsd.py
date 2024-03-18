from __future__ import annotations

from unittest import TestCase

from django.test.utils import override_settings
from statsd.client.udp import StatsClient

from hc.lib.statsd import NoopClient, get_client


class StatsdTestCase(TestCase):
    @override_settings(STATSD_HOST="localhost")
    def test_it_initializes_udp_client(self) -> None:
        client = get_client()
        self.assertTrue(isinstance(client, StatsClient))
        self.assertEqual(client._addr, ("127.0.0.1", 8125))

    @override_settings(STATSD_HOST="localhost:1234")
    def test_it_parses_port(self) -> None:
        client = get_client()
        self.assertTrue(isinstance(client, StatsClient))
        self.assertEqual(client._addr, ("127.0.0.1", 1234))

    @override_settings(STATSD_HOST=None)
    def test_it_initializes_noop_client(self) -> None:
        client = get_client()
        self.assertTrue(isinstance(client, NoopClient))
