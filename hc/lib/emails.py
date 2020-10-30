import smtplib
from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string as render


class EmailThread(Thread):
    MAX_TRIES = 3

    def __init__(self, subject, text, html, to, headers):
        Thread.__init__(self)
        self.subject = subject
        self.text = text
        self.html = html
        self.to = to
        self.headers = headers

    def run(self):
        for attempt in range(0, self.MAX_TRIES):
            try:
                msg = EmailMultiAlternatives(
                    self.subject, self.text, to=(self.to,), headers=self.headers
                )

                msg.attach_alternative(self.html, "text/html")
                msg.send()
            except smtplib.SMTPServerDisconnected as e:
                if attempt + 1 == self.MAX_TRIES:
                    # This was the last attempt and it failed:
                    # re-raise the exception
                    raise e
            else:
                # There was no exception, break out of the retry loop
                break


def send(name, to, ctx, headers={}):
    ctx["SITE_ROOT"] = settings.SITE_ROOT

    subject = render("emails/%s-subject.html" % name, ctx).strip()
    text = render("emails/%s-body-text.html" % name, ctx)
    html = render("emails/%s-body-html.html" % name, ctx)

    t = EmailThread(subject, text, html, to, headers)
    if hasattr(settings, "BLOCKING_EMAILS"):
        # In tests, we send emails synchronously
        # so we can inspect the outgoing messages
        t.run()
    else:
        # Outside tests, we send emails on thread,
        # so there is no delay for the user.
        t.start()


def login(to, ctx):
    send("login", to, ctx)


def transfer_request(to, ctx):
    send("transfer-request", to, ctx)


def set_password(to, ctx):
    send("set-password", to, ctx)


def change_email(to, ctx):
    send("change-email", to, ctx)


def alert(to, ctx, headers={}):
    send("alert", to, ctx, headers)


def verify_email(to, ctx):
    send("verify-email", to, ctx)


def report(to, ctx, headers={}):
    send("report", to, ctx, headers)


def deletion_notice(to, ctx, headers={}):
    send("deletion-notice", to, ctx, headers)


def sms_limit(to, ctx):
    send("sms-limit", to, ctx)


def call_limit(to, ctx):
    send("phone-call-limit", to, ctx)
