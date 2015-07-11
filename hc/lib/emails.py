from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send(to, template_directory, ctx):
    """ Send HTML email using Mandrill.

    Expect template_directory to be a path containing
        - subject.txt
        - body.html

    """

    from_email = settings.DEFAULT_FROM_EMAIL
    subject = render_to_string("%s/subject.txt" % template_directory, ctx)
    body = render_to_string("%s/body.html" % template_directory, ctx)
    send_mail(subject, "", from_email, [to], html_message=body)
