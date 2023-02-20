from __future__ import annotations

import re

from django.views.debug import SafeExceptionReporterFilter


class ExceptionReporterFilter(SafeExceptionReporterFilter):
    # Adds "TWILIO_AUTH" to the default keywords
    hidden_settings = re.compile(
        "API|TOKEN|KEY|SECRET|PASS|SIGNATURE|TWILIO_AUTH", flags=re.I
    )
