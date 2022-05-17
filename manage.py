#!/usr/bin/env python
import logging
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hc.settings")

    from django.core.management import execute_from_command_line

    logger = logging.getLogger("django")
    try:
        execute_from_command_line(sys.argv)
    except Exception as e:
        msg = "Admin Command Error: %s"
        logger.error(msg, " ".join(sys.argv), exc_info=sys.exc_info())
        raise e
