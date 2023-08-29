from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase

from hc.accounts.models import Profile


class TeamAccessMiddlewareTestCase(TestCase):
    def test_it_handles_missing_profile(self) -> None:
        user = User(username="ned", email="ned@example.org")
        user.set_password("password")
        user.save()

        self.client.login(username="ned@example.org", password="password")
        r = self.client.get("/docs/")
        self.assertEqual(r.status_code, 200)

        self.assertEqual(Profile.objects.count(), 1)
