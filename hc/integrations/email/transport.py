from __future__ import annotations

import email
from email.message import EmailMessage

from hc.accounts.models import Profile
from hc.api.models import Flip, Notification
from hc.api.transports import Transport, TransportError, get_ping_body_bytes
from hc.lib import emails
from hc.lib.signing import sign_bounce_id


class Email(Transport):
    def bytes_to_sanitized_message(self, data: bytes) -> EmailMessage:
        m = email.message_from_bytes(data, policy=email.policy.SMTP)
        if m.is_multipart():
            parts = m.get_payload()
            # If is_multipart=True then get_payload() returns list[Message].
            # Mypy does not know this, hence the assert.
            assert isinstance(parts, list)
            # use list() here so we don't mutate the same list we're iterating
            for part in list(parts):
                if part.get_content_type() == "message/rfc822":
                    # Drop message/rfc822 parts to avoid recursion issues with
                    # deep attachment-within-attachment stacks.
                    parts.remove(part)
                if part.get_content_maintype() == "text":
                    # Call set_content to force correct content-transfer-encoding
                    # selection and line wrapping
                    part.set_content(part.get_content())
        else:
            # Call set_content to force correct content-transfer-encoding
            # selection and line wrapping
            m.set_content(m.get_content())
        return m

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not self.channel.email_verified:
            raise TransportError("Email not verified")

        unsub_link = self.channel.get_unsub_link()

        headers = {
            "List-Unsubscribe": f"<{unsub_link}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "X-Bounce-ID": sign_bounce_id(f"n.{notification.code}"),
        }

        # If this email address has an associated account,
        # - include a summary of projects the account has access to
        # - use their preferred time zone to format datetimes
        # Otherwise, use the channel owner's preferred time zone.
        try:
            profile = Profile.objects.get(user__email=self.channel.email.value)
            projects = list(profile.projects())
        except Profile.DoesNotExist:
            profile = Profile.objects.for_user(self.channel.project.owner)
            projects = None

        ping = self.last_ping(flip)
        body_bytes = get_ping_body_bytes(ping)
        subject, attachment = None, None
        if ping is not None and ping.scheme == "email" and body_bytes:
            attachment = self.bytes_to_sanitized_message(body_bytes)
            subject = attachment.get("subject", "")

        ctx = {
            "flip": flip,
            "check": flip.owner,
            "ping": ping,
            "body": body_bytes.decode(errors="replace") if body_bytes else None,
            "subject": subject,
            "projects": projects,
            "unsub_link": unsub_link,
            "tz": profile.tz,
            "ping_attached": attachment is not None,
        }

        emails.alert(self.channel.email.value, ctx, headers, attachment)

    def is_noop(self, status: str) -> bool:
        if status == "down":
            return not self.channel.email.notify_down
        else:
            return not self.channel.email.notify_up
