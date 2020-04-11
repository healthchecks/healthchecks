import getpass

from django.core.management.base import BaseCommand
from hc.accounts.forms import AvailableEmailForm
from hc.accounts.views import _make_user


class Command(BaseCommand):
    help = """Create a super-user account."""

    def handle(self, *args, **options):
        email = None
        password = None

        while not email:
            raw = input("Email address:")
            form = AvailableEmailForm({"identity": raw})
            if not form.is_valid():
                self.stderr.write("Error: " + " ".join(form.errors["identity"]))
                continue

            email = form.cleaned_data["identity"]

        while not password:
            p1 = getpass.getpass()
            p2 = getpass.getpass("Password (again):")
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
