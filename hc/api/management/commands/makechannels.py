import sys

from django.core.management.base import BaseCommand

from django.contrib.auth.models import User
from hc.api.models import Channel, Check


def _log(message):
    sys.stdout.write(message)
    sys.stdout.flush()


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'

    def handle(self, *args, **options):

        for user in User.objects.all():
            q = Channel.objects.filter(user=user)
            q = q.filter(kind="email", email_verified=True, value=user.email)
            if q.count() > 0:
                continue

            print("Creating default channel for %s" % user.email)
            channel = Channel(user=user)
            channel.kind = "email"
            channel.value = user.email
            channel.email_verified = True
            channel.save()

            channel.checks.add(*Check.objects.filter(user=user))
