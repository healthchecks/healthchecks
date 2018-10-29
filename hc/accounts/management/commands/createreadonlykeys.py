from base64 import urlsafe_b64encode
import os

from django.core.management.base import BaseCommand

from hc.accounts.models import Profile


class Command(BaseCommand):
    help = """Create read-only API keys."""

    def handle(self, *args, **options):
        c = 0
        q = Profile.objects.filter(api_key_readonly="").exclude(api_key="")
        for profile in q:
            profile.api_key_readonly = urlsafe_b64encode(os.urandom(24)).decode()
            profile.save()
            c += 1

        return "Done! Generated %d readonly keys." % c
