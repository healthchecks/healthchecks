from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from hc.accounts.management.commands.createsuperuser import Command
from hc.test import BaseTestCase


class CreateSuperuserTestCase(BaseTestCase):
    @patch(Command.__module__ + ".sys.stdin.isatty", Mock(return_value=True))
    @patch(Command.__module__ + ".getpass")
    @patch(Command.__module__ + ".input")
    def test_it_works(self, mock_input: Mock, mock_getpass: Mock) -> None:
        cmd = Command(stdout=Mock())
        mock_input.return_value = "superuser@example.org"
        mock_getpass.return_value = "hunter2"
        cmd.handle(email=None, password=None)

        u = User.objects.get(email="superuser@example.org")
        self.assertTrue(u.is_superuser)

    @patch(Command.__module__ + ".sys.stdin.isatty", Mock(return_value=True))
    @patch(Command.__module__ + ".getpass")
    @patch(Command.__module__ + ".input")
    def test_it_rejects_duplicate_email(
        self, mock_input: Mock, mock_getpass: Mock
    ) -> None:
        cmd = Command(stdout=Mock(), stderr=Mock())
        mock_input.side_effect = ["alice@example.org", "alice2@example.org"]
        mock_getpass.return_value = "hunter2"
        cmd.handle(email=None, password=None)

        u = User.objects.get(email="alice2@example.org")
        self.assertTrue(u.is_superuser)

    def test_it_accepts_arguments(self) -> None:
        cmd = Command(stdout=Mock())
        cmd.handle(email="superuser@example.org", password="hunter2")

        u = User.objects.get(email="superuser@example.org")
        self.assertTrue(u.is_superuser)
