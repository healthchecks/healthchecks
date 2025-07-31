from __future__ import annotations

import sys
from argparse import ArgumentParser
from getpass import getpass
from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from hc.accounts.forms import LowercaseEmailField
from hc.accounts.views import _make_user


class Command(BaseCommand):
    help = """Create a super-user account."""

    def validate_email(self, raw_email: str) -> str | None:
        try:
            email = LowercaseEmailField().clean(raw_email)
        except ValidationError as e:
            self.stderr.write("Error: " + " ".join(e.messages))
            return None

        if User.objects.filter(email=email).exists():
            self.stderr.write(f"Error: email {email} is already taken")
            return None

        return email

    def validate_password(self, password: str) -> str | None:
        if password.strip() == "":
            self.stderr.write("Error: Blank passwords aren't allowed.")
            return None

        return password

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--email",
            type=str,
            help="Email address of the account. If this isn't provided or the value is invalid, will prompt for the email address.",
        )
        parser.add_argument(
            "--password",
            "--pass",
            type=str,
            help="Password of the account. If this isn't provided or the value is invalid, will prompt for the password.",
        )

    def handle(self, **options: Any) -> str:
        email = options["email"]
        password = options["password"]

        if email is not None:
            email = self.validate_email(email)

        if password is not None:
            password = self.validate_password(password)

        if sys.stdin.isatty():
            while email is None:
                raw = input("Email address:")
                email = self.validate_email(raw)
        elif email is None:
            self.stderr.write("Missing or invalid required argument: --email")
            sys.exit(2)

        if sys.stdin.isatty():
            while password is None:
                p1 = getpass()
                p2 = getpass("Password (again):")

                if p1 != p2:
                    self.stderr.write("Error: Your passwords didn't match.")
                    password = None
                    continue

                password = self.validate_password(p1)
        elif password is None:
            self.stderr.write("Missing or invalid required argument: --password/--pass")
            sys.exit(2)

        user = _make_user(email)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        return "Superuser created successfully."
