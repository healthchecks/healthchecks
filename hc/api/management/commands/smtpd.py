import asyncore
import re
from smtpd import SMTPServer

from django.core.management.base import BaseCommand
from hc.api.models import Check

RE_UUID = re.compile("^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[8|9|aA|bB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$")


class Listener(SMTPServer):
    def __init__(self, localaddr, stdout):
        self.stdout = stdout
        super(Listener, self).__init__(localaddr, None)

    def process_message(self, peer, mailfrom, rcpttos, data):
        to_parts = rcpttos[0].split("@")
        code = to_parts[0]

        if not RE_UUID.match(code):
            self.stdout.write("Not an UUID: %s" % code)
            return

        try:
            check = Check.objects.get(code=code)
        except Check.DoesNotExist:
            self.stdout.write("Check not found: %s" % code)
            return

        ua = "Email from %s" % mailfrom
        check.ping(peer[0], "email", "", ua, data)
        self.stdout.write("Processed ping for %s" % code)


class Command(BaseCommand):
    help = "Listen for ping emails"

    def add_arguments(self, parser):
        parser.add_argument("--host",
                            help="ip address to listen on, default 0.0.0.0",
                            default="0.0.0.0")
        parser.add_argument('--port',
                            help="port to listen on, default 25",
                            type=int,
                            default=25)

    def handle(self, host, port, *args, **options):
        listener = Listener((host, port), self.stdout)
        print("Starting SMTP listener on %s:%d ..." % (host, port))
        asyncore.loop()
