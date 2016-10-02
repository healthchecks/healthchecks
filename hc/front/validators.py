from django.core.exceptions import ValidationError
from six.moves.urllib_parse import urlparse


class WebhookValidator(object):
    message = "Enter a valid URL."

    def __call__(self, value):
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https"):
            raise ValidationError(message=self.message)

        if parsed.hostname in ("127.0.0.1", "localhost"):
            raise ValidationError(message=self.message)
