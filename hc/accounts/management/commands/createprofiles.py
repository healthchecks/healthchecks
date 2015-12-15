from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from hc.accounts.models import Profile


class Command(BaseCommand):
    help = 'Make sure all users have profiles'

    def handle(self, *args, **options):
        for user in User.objects.all():
            # this should create profile object if it does not exist
            Profile.objects.for_user(user)

        print("Done.")
