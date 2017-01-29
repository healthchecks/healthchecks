from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string as render


class EmailThread(Thread):
    def __init__(self, name, to, ctx):
        Thread.__init__(self)
        self.name = name
        self.to = to
        self.ctx = ctx

    def run(self):
        self.ctx["SITE_ROOT"] = settings.SITE_ROOT

        subject = render('emails/%s-subject.html' % self.name, self.ctx)
        subject = subject.strip()

        text = render('emails/%s-body-text.html' % self.name, self.ctx)
        html = render('emails/%s-body-html.html' % self.name, self.ctx)

        msg = EmailMultiAlternatives(subject, text, to=(self.to, ))

        msg.attach_alternative(html, "text/html")
        msg.send()


def send(name, to, ctx):
    t = EmailThread(name, to, ctx)
    if hasattr(settings, "BLOCKING_EMAILS"):
        t.run()
    else:
        t.start()


def login(to, ctx):
    send("login", to, ctx)


def set_password(to, ctx):
    send("set-password", to, ctx)


def alert(to, ctx):
    send("alert", to, ctx)


def verify_email(to, ctx):
    send("verify-email", to, ctx)


def report(to, ctx):
    send("report", to, ctx)
