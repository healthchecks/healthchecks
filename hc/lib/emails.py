from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string as render


class EmailThread(Thread):
    def __init__(self, subject, text, html, to, headers):
        Thread.__init__(self)
        self.subject = subject
        self.text = text
        self.html = html
        self.to = to
        self.headers = headers

    def run(self):
        msg = EmailMultiAlternatives(
            self.subject, self.text, to=(self.to,), headers=self.headers
        )

        msg.attach_alternative(self.html, "text/html")
        msg.send()


def send(name, to, ctx, headers={}):
    ctx["SITE_ROOT"] = settings.SITE_ROOT

    subject = render("emails/%s-subject.html" % name, ctx).strip()
    text = render("emails/%s-body-text.html" % name, ctx)
    html = render("emails/%s-body-html.html" % name, ctx)

    t = EmailThread(subject, text, html, to, headers)
    if hasattr(settings, "BLOCKING_EMAILS"):
        t.run()
    else:
        t.start()


def login(to, ctx):
    send("login", to, ctx)


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


def invoice(to, ctx, filename, pdf_data):
    ctx["SITE_ROOT"] = settings.SITE_ROOT
    subject = render("emails/invoice-subject.html", ctx).strip()
    text = render("emails/invoice-body-text.html", ctx)
    html = render("emails/invoice-body-html.html", ctx)

    msg = EmailMultiAlternatives(subject, text, to=(to,))
    msg.attach_alternative(html, "text/html")
    msg.attach(filename, pdf_data, "application/pdf")
    msg.send()


def deletion_notice(to, ctx, headers={}):
    send("deletion-notice", to, ctx, headers)
