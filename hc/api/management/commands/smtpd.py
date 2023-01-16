from __future__ import annotations

import asyncore
import email
import email.policy
import re
from smtpd import SMTPServer

from django.core.management.base import BaseCommand
from django.db import connections

from hc.api.models import Check
from hc.lib.html import html2text

RE_UUID = re.compile(
    "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[8|9|aA|bB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$"
)


def _match(subject, keywords):
    for s in keywords.split(","):
        s = s.strip()
        if s and s in subject:
            return True

    return False


def _to_text(message, with_subject, with_body):
    chunks = []
    if with_subject:
        chunks.append(message.get("subject", ""))
    if with_body:
        plain_mime_part = message.get_body(("plain",))
        if plain_mime_part:
            chunks.append(plain_mime_part.get_content())

        html_mime_part = message.get_body(("html",))
        if html_mime_part:
            html = html_mime_part.get_content()
            chunks.append(html2text(html))

    return "\n".join(chunks)


def _process_message(remote_addr, mailfrom, mailto, data):
    to_parts = mailto.split("@")
    code = to_parts[0]

    if not RE_UUID.match(code):
        return f"Not an UUID: {code}"

    try:
        check = Check.objects.get(code=code)
    except Check.DoesNotExist:
        return f"Check not found: {code}"

    action = "success"
    if check.filter_subject or check.filter_body:
        data_str = data.decode(errors="replace")
        # Specify policy, the default policy does not decode encoded headers:
        message = email.message_from_string(data_str, policy=email.policy.SMTP)
        text = _to_text(message, check.filter_subject, check.filter_body)

        action = "ign"
        if check.failure_kw and _match(text, check.failure_kw):
            action = "fail"
        elif check.success_kw and _match(text, check.success_kw):
            action = "success"
        elif check.start_kw and _match(text, check.start_kw):
            action = "start"

    ua = "Email from %s" % mailfrom
    check.ping(remote_addr, "email", "", ua, data, action, None)

    return f"Processed ping for {code}"


class Listener(SMTPServer):
    def __init__(self, localaddr, stdout):
        self.stdout = stdout
        super(Listener, self).__init__(localaddr, None, decode_data=False)

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        # get a new db connection in case the old one has timed out:
        connections.close_all()

        for rcptto in rcpttos:
            result = _process_message(peer[0], mailfrom, rcptto, data)
            self.stdout.write(result)


class Command(BaseCommand):
    help = "Listen for ping emails"

    def add_arguments(self, parser):
        parser.add_argument(
            "--host", help="ip address to listen on, default 0.0.0.0", default="0.0.0.0"
        )
        parser.add_argument(
            "--port", help="port to listen on, default 25", type=int, default=25
        )

    def handle(self, host, port, *args, **options):
        _ = Listener((host, port), self.stdout)
        print("Starting SMTP listener on %s:%d ..." % (host, port))
        asyncore.loop()
