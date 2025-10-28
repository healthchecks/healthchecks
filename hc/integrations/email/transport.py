from __future__ import annotations

import email

from hc.accounts.models import Profile
from hc.api.models import Flip, Notification
from hc.api.transports import Transport, TransportError, get_ping_body
from hc.lib import emails
from hc.lib.signing import sign_bounce_id


class Email(Transport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        if not self.channel.email_verified:
            raise TransportError("Email not verified")

        unsub_link = self.channel.get_unsub_link()

        headers = {
            "List-Unsubscribe": f"<{unsub_link}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "X-Bounce-ID": sign_bounce_id(f"n.{notification.code}"),
        }

        # If this email address has an associated account, include
        # a summary of projects the account has access to
        try:
            profile = Profile.objects.get(user__email=self.channel.email.value)
            projects = list(profile.projects())
        except Profile.DoesNotExist:
            projects = None

        ping = self.last_ping(flip)
        body = get_ping_body(ping)
        subject = None
        if ping is not None and ping.scheme == "email" and body:
            parsed = email.message_from_string(body, policy=email.policy.SMTP)
            subject = parsed.get("subject", "")

        ctx = {
            "flip": flip,
            "check": flip.owner,
            "ping": ping,
            "body": body,
            "subject": subject,
            "projects": projects,
            "unsub_link": unsub_link,
        }

        emails.alert(self.channel.email.value, ctx, headers)

    def is_noop(self, status: str) -> bool:
        if status == "down":
            return not self.channel.email.notify_down
        else:
            return not self.channel.email.notify_up
