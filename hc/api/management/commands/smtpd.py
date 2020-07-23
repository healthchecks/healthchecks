import asyncore
import email
import re
from smtpd import SMTPServer

from django.core.management.base import BaseCommand
from django.db import connections
from hc.api.models import Check

RE_UUID = re.compile(
    "^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[8|9|aA|bB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$"
)


def _match(subject, keywords):
    for s in keywords.split(","):
        s = s.strip()
        if s and s in subject:
            return True

    return False


def _process_message(remote_addr, mailfrom, mailto, data):
    to_parts = mailto.split("@")
    code = to_parts[0]

    try:
        data = data.decode()
    except UnicodeError:
        data = "[binary data]"

    if not RE_UUID.match(code):
        return f"Not an UUID: {code}"

    try:
        check = Check.objects.get(code=code)
    except Check.DoesNotExist:
        return f"Check not found: {code}"

    action = "success"
    if check.subject or check.subject_fail:
        action = "ign"
        subject = email.message_from_string(data).get("subject", "")
        if check.subject and _match(subject, check.subject):
            action = "success"
        elif check.subject_fail and _match(subject, check.subject_fail):
            action = "fail"

    ua = "Email from %s" % mailfrom
    check.ping(remote_addr, "email", "", ua, data, action)

    return f"Processed ping for {code}"


class Listener(SMTPServer):
    def __init__(self, localaddr, stdout):
        self.stdout = stdout
        super(Listener, self).__init__(localaddr, None, decode_data=False)

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        # get a new db connection in case the old one has timed out:
        connections.close_all()

        result = _process_message(peer[0], mailfrom, rcpttos[0], data)
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
