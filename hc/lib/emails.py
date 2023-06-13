from __future__ import annotations

import time
from email.utils import make_msgid
from smtplib import SMTPDataError, SMTPServerDisconnected
from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string as render


class EmailThread(Thread):
    MAX_TRIES = 3

    def __init__(self, message):
        Thread.__init__(self)
        self.message = message

    def run(self):
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


def make_message(name, to, ctx, headers={}):
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

    msg = EmailMultiAlternatives(
        subject, body, from_email=from_email, to=(to,), headers=headers
    )
    msg.attach_alternative(html, "text/html")
    return msg


def send(msg, block=False):
    assert settings.EMAIL_HOST, (
        "No SMTP configuration,"
        " see https://github.com/healthchecks/healthchecks#sending-emails"
    )

    t = EmailThread(msg)
    if block or hasattr(settings, "BLOCKING_EMAILS"):
        # In tests, we send emails synchronously
        # so we can inspect the outgoing messages
        t.run()
    else:
        # Outside tests, we send emails on thread,
        # so there is no delay for the user.
        t.start()


def login(to, ctx):
    send(make_message("login", to, ctx))


def transfer_request(to, ctx):
    send(make_message("transfer-request", to, ctx))


def alert(to, ctx, headers={}):
    send(make_message("alert", to, ctx, headers=headers))


def verify_email(to, ctx):
    send(make_message("verify-email", to, ctx))


def report(to, ctx, headers={}):
    m = make_message("report", to, ctx, headers=headers)
    send(m, block=True)


def deletion_notice(to, ctx, headers={}):
    m = make_message("deletion-notice", to, ctx, headers=headers)
    send(m, block=True)


def sms_limit(to, ctx):
    send(make_message("sms-limit", to, ctx))


def call_limit(to, ctx):
    send(make_message("phone-call-limit", to, ctx))


def sudo_code(to, ctx):
    send(make_message("sudo-code", to, ctx))


def signal_rate_limited(to, ctx):
    send(make_message("signal-rate-limited", to, ctx))
