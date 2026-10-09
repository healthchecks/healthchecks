from __future__ import annotations

import email
import email.policy
import re
from argparse import ArgumentParser
from email.message import EmailMessage
from typing import Any, Protocol

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
from minismtpd import SMTPServer

from hc.api.models import Check
from hc.lib.html import html2text
from hc.lib.string import match_keywords

RE_UUID = re.compile(
    r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[8|9|aA|bB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$"
)

RE_PING_KEY_SLUG = re.compile(r"^[a-zA-Z0-9_-]{22}\+[a-z0-9-_]+$")


class LogSink(Protocol):
    def write(self, msg: str) -> None: ...


def _to_text(message: EmailMessage, with_subject: bool, with_body: bool) -> str:
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


def _process_message(remote_addr: str, mailfrom: str, mailto: str, data: bytes) -> str:
    # Get a new db connection in case the old one has timed out.
    # The if condition makes sure this does not run during tests.
    if not connection.in_atomic_block:
        close_old_connections()

    to_parts = mailto.split("@")
    mbox = to_parts[0]
    if "+" in mbox:
        # Pinging by slug
        ping_key, slug = mbox.split("+")
        try:
            check = Check.objects.get(slug=slug, project__ping_key=ping_key)
        except Check.DoesNotExist:
            return f"Check not found: {mailto}"
        except Check.MultipleObjectsReturned:
            return f"Ambiguous slug: {mailto}"
    else:
        # Pinging by code
        code = mbox
        try:
            check = Check.objects.get(code=code)
        except Check.DoesNotExist:
            return f"Check not found: {mailto}"

    action = "success"
    if check.filter_subject or check.filter_body:
        # Specify policy, the default policy does not decode encoded headers:
        message = email.message_from_bytes(data, policy=email.policy.SMTP)
        text = _to_text(message, check.filter_subject, check.filter_body)

        if check.failure_kw and match_keywords(text, check.failure_kw):
            action = "fail"
        elif check.success_kw and match_keywords(text, check.success_kw):
            action = "success"
        elif check.start_kw and match_keywords(text, check.start_kw):
            action = "start"
        elif check.filter_default_fail:
            action = "fail"
        else:
            action = "ign"

    check.ping(
        remote_addr=remote_addr,
        scheme="email",
        method="",
        ua=f"Email from {mailfrom}",
        body=data,
        action=action,
        rid=None,
    )

    return f"Processed ping for {mailto}"


class Server(SMTPServer):
    def __init__(self, server_address: tuple[str, int], stdout: LogSink):
        super().__init__(server_address)
        self.stdout = stdout

    def process_rcpt(self, rcptto: str) -> str | None:
        mbox, domain = rcptto.split("@", maxsplit=1)
        if domain != settings.PING_EMAIL_DOMAIN:
            return "550 5.1.1 Recipient rejected"
        if not RE_UUID.match(mbox) and not RE_PING_KEY_SLUG.match(mbox):
            return "550 5.1.1 Invalid mailbox"
        return None

    def process_message(
        self, peer: tuple[str, int], mailfrom: str, rcpttos: list[str], data: bytes
    ) -> str | None:
        for mailto in rcpttos:
            result = _process_message(peer[0], mailfrom, mailto, data)
            self.stdout.write(result)

        return "250 OK"


class Command(BaseCommand):
    help = "Listen for ping emails"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--host", help="ip address to listen on, default 0.0.0.0", default="0.0.0.0"
        )
        parser.add_argument(
            "--port", help="port to listen on, default 25", type=int, default=25
        )

    def handle(self, host: str, port: int, **options: Any) -> None:
        print(f"Starting SMTP listener on {host}:{port} ...")
        with Server((host, port), self.stdout) as server:
            # Run until Ctrl-C
            server.serve_forever()
