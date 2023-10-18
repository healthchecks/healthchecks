from __future__ import annotations

from getpass import getpass
from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from hc.accounts.forms import LowercaseEmailField
from hc.accounts.views import _make_user


class Command(BaseCommand):
    help = """Create a super-user account."""

    def handle(self, **options: Any) -> str:
        email = None
        password = None

        while not email:
            raw = input("Email address:")
            try:
                email = LowercaseEmailField().clean(raw)
            except ValidationError as e:
                self.stderr.write("Error: " + " ".join(e.messages))
                continue
            if User.objects.filter(email=email).exists():
                self.stderr.write(f"Error: email {email} is already taken")
                email = None
                continue

        while not password:
            p1 = getpass()
            p2 = getpass("Password (again):")
            if p1.strip() == "":
                self.stderr.write("Error: Blank passwords aren't allowed.")
                continue
            if p1 != p2:
                self.stderr.write("Error: Your passwords didn't match.")
                continue

            password = p1

        user = _make_user(email)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        return "Superuser created successfully."
