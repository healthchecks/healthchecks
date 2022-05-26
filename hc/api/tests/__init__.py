from django.conf import settings
from django.test.runner import DiscoverRunner


class CustomRunner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        # For speed:
        settings.PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

        # Send emails synchronously
        settings.BLOCKING_EMAILS = True

        super(CustomRunner, self).__init__(*args, **kwargs)
