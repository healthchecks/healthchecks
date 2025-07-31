from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from hc.accounts.management.commands.createsuperuser import Command
from hc.test import BaseTestCase

MOCK_STDIN = Mock()
MOCK_STDIN.isatty.return_value = True


# Convenience wrapper around patch() to patch things inside
# hc.accounts.management.commands.createsuperuser
def patch_local(target, *args, **kwargs):
    return patch(Command.__module__ + "." + target, *args, **kwargs)


# The management command calls sys.stdin.isatty to check if it's
# running in an interactive session. When running tests with "--parallel"
# this will return false, so we may need to patch it.
def patch_tty():
    return patch_local("sys.stdin.isatty", Mock(return_value=True))


class CreateSuperuserTestCase(BaseTestCase):
    @patch_tty()
    @patch_local("getpass")
    @patch_local("input")
    def test_it_works(self, mock_input, mock_getpass) -> None:
        cmd = Command(stdout=Mock())
        mock_input.return_value = "superuser@example.org"
        mock_getpass.return_value = "hunter2"
        cmd.handle(email=None, password=None)

        u = User.objects.get(email="superuser@example.org")
        self.assertTrue(u.is_superuser)

    @patch_tty()
    @patch_local("getpass")
    @patch_local("input")
    def test_it_rejects_duplicate_email(self, mock_input, mock_getpass) -> None:
        cmd = Command(stdout=Mock(), stderr=Mock())
        mock_input.side_effect = ["alice@example.org", "alice2@example.org"]
        mock_getpass.return_value = "hunter2"
        cmd.handle(email=None, password=None)

        u = User.objects.get(email="alice2@example.org")
        self.assertTrue(u.is_superuser)
