from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase
from django.urls import reverse

class RetryFailedCheckTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, status="down")

        self.url = f"/checks/{self.check.code}/retry/"
        self.redirect_url = f"/projects/{self.project.code}/checks/"

    def test_it_retries_failed_check(self) -> None:
        """Test that retrying a failed check updates its status and redirects"""
        self.client.login(username="alice@example.org", password="password")
        
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertNotEqual(self.check.status, "down")  # Should be marked as retried

    def test_it_requires_login(self) -> None:
        """Test that unauthenticated users cannot retry a failed job"""
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 302)  # Should redirect to login page

    def test_it_checks_ownership(self) -> None:
        """Test that another user cannot retry someone else's check"""
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 404)  # Should deny access

    def test_it_handles_missing_uuid(self) -> None:
        """Test that trying to retry a non-existent check returns 404"""
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/retry/"
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_get_requests(self) -> None:
        """Test that GET requests to the retry endpoint are rejected"""
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)  # Method Not Allowed
