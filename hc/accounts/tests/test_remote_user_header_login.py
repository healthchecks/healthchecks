from unittest.mock import patch
from django.test.utils import override_settings
from hc.test import BaseTestCase
from hc.accounts.middleware import CustomHeaderMiddleware
from django.conf import settings

class RemoteUserHeaderTestCase(BaseTestCase):
    @override_settings(REMOTE_USER_HEADER_TYPE="")
    def test_it_does_nothing_when_disabled(self):
        r = self.client.get("/accounts/profile/", AUTH_USER="alice@example.org")
        self.assertRedirects(r, "/accounts/login/?next=/accounts/profile/")

    @override_settings(REMOTE_USER_HEADER_TYPE="EMAIL")
    def test_it_logs_users_in_by_email(self):
        r = self.client.get("/accounts/profile/", AUTH_USER="alice@example.org")
        self.assertContains(r, "alice@example.org")

    @override_settings(REMOTE_USER_HEADER="HTTP_AUTH_TEST", REMOTE_USER_HEADER_TYPE="EMAIL")
    def test_it_allows_customizing_the_header(self):
        # patch the CustomHeaderMiddleware's header value since it's static and
        # won't be updated automatically --- this is OK outside of test, since
        # that value shouldn't change after instantiation anyway
        _old_header = CustomHeaderMiddleware.header
        CustomHeaderMiddleware.header = settings.REMOTE_USER_HEADER
        r = self.client.get("/accounts/profile/", HTTP_AUTH_TEST="alice@example.org")
        self.assertContains(r, "alice@example.org")

        # un-patch the header
        CustomHeaderMiddleware.header = _old_header

    @override_settings(REMOTE_USER_HEADER_TYPE="ID")
    def test_it_logs_users_in_by_id(self):
        r = self.client.get("/accounts/profile/", AUTH_USER="alice")
        self.assertContains(r, "alice@example.org")