from __future__ import annotations

from hc.test import BaseTestCase


class StatusTestCase(BaseTestCase):
    url = "/api/v1/status/"

    def test_it_works(self) -> None:
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.assertNumQueries(1)
        self.assertEqual(r.content, b"OK")
