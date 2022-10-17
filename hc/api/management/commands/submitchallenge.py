from __future__ import annotations

import json
import uuid

from django.core.management.base import BaseCommand

from hc.api.transports import Signal


class Command(BaseCommand):
    help = "Submit Signal rate-limit challenge."

    def add_arguments(self, parser):
        parser.add_argument("challenge", help="challenge token from Signal")
        parser.add_argument(
            "captcha",
            help="solved CAPTCHA from https://signalcaptchas.org/challenge/generate.html",
        )

    def handle(self, challenge, captcha, *args, **options):

        payload = {
            "jsonrpc": "2.0",
            "method": "submitRateLimitChallenge",
            "params": {"challenge": challenge, "captcha": captcha},
            "id": str(uuid.uuid4()),
        }

        payload_bytes = (json.dumps(payload) + "\n").encode()
        for reply_bytes in Signal(None)._read_replies(payload_bytes):
            try:
                reply = json.loads(reply_bytes.decode())
            except ValueError:
                return "submitRateLimitChallenge failed, could not parse response"

            if reply.get("id") == payload["id"]:
                return reply_bytes.decode()
