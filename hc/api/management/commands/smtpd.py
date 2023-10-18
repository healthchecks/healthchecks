from __future__ import annotations

import email
import email.policy
import re
import time
from argparse import ArgumentParser
from email.message import EmailMessage
from typing import Any, Protocol

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from django.db import connection

from hc.api.models import Check
from hc.lib.html import html2text

RE_UUID = re.compile(
    "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[8|9|aA|bB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$"
)


class LogSink(Protocol):
    def write(self, text: str) -> None:
        ...


class Session(Protocol):
    peer: list[str]


class Envelope(Protocol):
    mail_from: str
    content: bytes
    rcpt_tos: list[str]


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
            assert isinstance(plain_mime_part, EmailMessage)
            chunks.append(plain_mime_part.get_content())

        html_mime_part = message.get_body(("html",))
        if html_mime_part:
            assert isinstance(html_mime_part, EmailMessage)
            html = html_mime_part.get_content()
            chunks.append(html2text(html))

    return "\n".join(chunks)


def _process_message(remote_addr: str, mailfrom: str, mailto: str, data: bytes) -> str:
    to_parts = mailto.split("@")
    code = to_parts[0]

    if not RE_UUID.match(code):
        return f"Not an UUID: {code}"

    # Get a new db connection in case the old one has timed out.
    # The if condition makes sure this does not run during tests.
    if not connection.in_atomic_block:
        connection.close()

    try:
        check = Check.objects.get(code=code)
    except Check.DoesNotExist:
        return f"Check not found: {code}"

    action = "success"
    if check.filter_subject or check.filter_body:
        data_str = data.decode(errors="replace")
        # Specify policy, the default policy does not decode encoded headers:
        message = email.message_from_string(data_str, policy=email.policy.SMTP)
        assert isinstance(message, EmailMessage)
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


class PingHandler:
    def __init__(self, stdout: LogSink) -> None:
        self.stdout = stdout
        self.process_message = sync_to_async(_process_message)

    async def handle_DATA(
        self, server: SMTP, session: Session, envelope: Envelope
    ) -> str:
        assert session.peer
        remote_addr = session.peer[0]
        mailfrom = envelope.mail_from
        data = envelope.content
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
