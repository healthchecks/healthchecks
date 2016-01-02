from django.conf import settings
from django.test.runner import DiscoverRunner


class CustomRunner(DiscoverRunner):

    def __init__(self, *args, **kwargs):
        # For speed:
        settings.PASSWORD_HASHERS = \
            ('django.contrib.auth.hashers.MD5PasswordHasher', )

        super(CustomRunner, self).__init__(*args, **kwargs)
