from __future__ import annotations

import email
import email.policy
import re
import time
from argparse import ArgumentParser
from email.message import EmailMessage
from typing import Any, Protocol

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP, Envelope, Session
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from hc.api.models import Check
from hc.lib.html import html2text

RE_UUID = re.compile(
    r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[8|9|aA|bB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$"
)

RE_PING_KEY_SLUG = re.compile(r"^[a-zA-Z0-9_-]{22}\+[a-z0-9-_]+$")


class LogSink(Protocol):
    def write(self, msg: str) -> None:
        ...


def _match(subject: str, keywords: str) -> bool:
    for s in keywords.split(","):
        s = s.strip()
        if s and s in subject:
            return True

    return False


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
        connection.close()

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

    ua = f"Email from {mailfrom}"
    check.ping(remote_addr, "email", "", ua, data, action, None)

    return f"Processed ping for {mailto}"


class PingHandler:
    def __init__(self, stdout: LogSink) -> None:
        self.stdout = stdout
        self.process_message = sync_to_async(_process_message)

    async def handle_RCPT(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        address: str,
        rcpt_options: list[str],
    ) -> str:
        mbox, domain = address.split("@", maxsplit=1)
        if domain != settings.PING_EMAIL_DOMAIN:
            return "550 5.1.1 Recipient rejected"
        if not RE_UUID.match(mbox) and not RE_PING_KEY_SLUG.match(mbox):
            return "550 5.1.1 Invalid mailbox"

        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(
        self, server: SMTP, session: Session, envelope: Envelope
    ) -> str:
        assert session.peer
        remote_addr = session.peer[0]
        mailfrom = envelope.mail_from
        assert mailfrom
        data = envelope.content
        assert isinstance(data, bytes)
        for mailto in envelope.rcpt_tos:
            result = await self.process_message(remote_addr, mailfrom, mailto, data)
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
        handler = PingHandler(self.stdout)
        controller = Controller(handler, hostname=host, port=port)
        print(f"Starting SMTP listener on {host}:{port} ...")
        controller.start()
        while True:
            try:
                time.sleep(2**32)  # Sleep with a very large timeout
            except KeyboardInterrupt:
                print("Interrupt received, exiting.")
                break
        controller.stop()
