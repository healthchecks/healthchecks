from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase


class ServeDocTestCase(TestCase):
    def test_it_serves_introduction(self):
        r = self.client.get("/docs/")
        self.assertEqual(r.status_code, 200)

        self.assertContains(r, "<strong>keeps silent</strong>")

    def test_it_serves_subpage(self):
        r = self.client.get("/docs/reliability_tips/")
        self.assertEqual(r.status_code, 200)

        self.assertContains(r, "Pinging Reliability Tips")

    def test_it_handles_bad_url(self):
        r = self.client.get("/docs/does_not_exist/")
        self.assertEqual(r.status_code, 404)

    @patch("hc.front.views.os.path.exists")
    def test_it_rejects_bad_characters(self, mock_exists):
        r = self.client.get("/docs/NAUGHTY/")
        self.assertEqual(r.status_code, 404)

        # URL dispatcher's slug filter lets the uppercase letters through,
        # but the view should still reject them, before any filesystem
        # operations

        self.assertFalse(mock_exists.called)
