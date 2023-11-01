from __future__ import annotations

import logging

from django.db import Error

FORMATTER = logging.Formatter()


class Handler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Import Record now not earlier, to avoid AppRegistryNotReady exception
        from hc.logs.models import Record

        traceback = ""
        if record.exc_info:
            traceback = FORMATTER.formatException(record.exc_info)

        try:
            Record.objects.create(
                name=record.name,
                level=record.levelno,
                message=record.getMessage(),
                traceback=traceback,
            )
        except Error as e:
            print(e)
