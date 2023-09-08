from __future__ import annotations

import time
from email.utils import make_msgid
from smtplib import SMTPDataError, SMTPServerDisconnected
from threading import Thread
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives as Message
from django.template.loader import render_to_string as render


class EmailThread(Thread):
    MAX_TRIES = 3

    def __init__(self, message: Message) -> None:
        Thread.__init__(self)
        self.message = message

    def run(self) -> None:
        for attempt in range(0, self.MAX_TRIES):
            try:
                # Make sure each retry creates a new connection:
                self.message.connection = None
                self.message.send()
                # No exception--great! Return from the retry loop
                return
            except (SMTPServerDisconnected, SMTPDataError) as e:
                if attempt + 1 == self.MAX_TRIES:
                    # This was the last attempt and it failed:
                    # re-raise the exception
                    raise e

                # Wait 1s before retrying
                time.sleep(1)


def make_message(
    name: str, to: str | list[str], ctx: dict[str, Any], headers: dict[str, str] = {}
) -> Message:
    subject = render("emails/%s-subject.html" % name, ctx).strip()
    body = render("emails/%s-body-text.html" % name, ctx)
    html = render("emails/%s-body-html.html" % name, ctx)

    domain = settings.DEFAULT_FROM_EMAIL.split("@")[-1].strip(">")
    headers["Message-ID"] = make_msgid(domain=domain)

    # Make sure the From: header contains our display From: address
    if "From" not in headers:
        headers["From"] = settings.DEFAULT_FROM_EMAIL

    # If EMAIL_MAIL_FROM_TMPL is set, prepare a custom MAIL FROM address
    bounce_id = headers.pop("X-Bounce-ID", "bounces")
    if settings.EMAIL_MAIL_FROM_TMPL:
        from_email = settings.EMAIL_MAIL_FROM_TMPL % bounce_id
    else:
        from_email = settings.DEFAULT_FROM_EMAIL

    to_list = [to] if isinstance(to, str) else to
    msg = Message(subject, body, from_email, to_list, headers=headers)
    msg.attach_alternative(html, "text/html")
    return msg


def send(message: Message, block: bool = False) -> None:
    assert settings.EMAIL_HOST, (
        "No SMTP configuration,"
        " see https://github.com/healthchecks/healthchecks#sending-emails"
    )

    t = EmailThread(message)
    if block or hasattr(settings, "BLOCKING_EMAILS"):
        # In tests, we send emails synchronously
        # so we can inspect the outgoing messages
        t.run()
    else:
        # Outside tests, we send emails on thread,
        # so there is no delay for the user.
        t.start()


def login(to: str, ctx: dict[str, Any]) -> None:
    send(make_message("login", to, ctx))


def transfer_request(to: str, ctx: dict[str, Any]) -> None:
    send(make_message("transfer-request", to, ctx))


def alert(to: str, ctx: dict[str, Any], headers: dict[str, str]) -> None:
    send(make_message("alert", to, ctx, headers=headers))


def verify_email(to: str, ctx: dict[str, Any]) -> None:
    send(make_message("verify-email", to, ctx))


def report(to: str, ctx: dict[str, Any], headers: dict[str, str]) -> None:
    m = make_message("report", to, ctx, headers=headers)
    send(m, block=True)


def nag(to: str, ctx: dict[str, Any], headers: dict[str, str]) -> None:
    m = make_message("nag", to, ctx, headers=headers)
    send(m, block=True)


def deletion_notice(to: str, ctx: dict[str, Any]) -> None:
    m = make_message("deletion-notice", to, ctx)
    send(m, block=True)


def deletion_scheduled(to: list[str], ctx: dict[str, Any]) -> None:
    m = make_message("deletion-scheduled", to, ctx)
    send(m, block=True)


def sms_limit(to: str, ctx: dict[str, Any]) -> None:
    send(make_message("sms-limit", to, ctx))


def call_limit(to: str, ctx: dict[str, Any]) -> None:
    send(make_message("phone-call-limit", to, ctx))


def sudo_code(to: str, ctx: dict[str, Any]) -> None:
    send(make_message("sudo-code", to, ctx))


def signal_rate_limited(to: str, ctx: dict[str, Any]) -> None:
    send(make_message("signal-rate-limited", to, ctx))
