from __future__ import annotations

import email
import logging
from email.message import EmailMessage
from smtplib import SMTPDataError, SMTPServerDisconnected

from hc.accounts.models import Profile
from hc.api.models import Flip, Notification
from hc.api.transports import Transport, TransportError, get_ping_body_bytes
from hc.lib import emails
from hc.lib.signing import sign_bounce_id

logger = logging.getLogger(__name__)


def _rewrap(m: EmailMessage) -> None:
    """Call set_content(get_content()).

    This forces correct content-transfer-encoding selection and line wrapping.
    """
    charset = m.get_param("charset")
    if charset is not None:
        # If the message has invalid charset then get_content() will raise.
        # Test if the charset is something we can decode.
        # If we can not, remove charset (will fall back to ASCII)
        try:
            b"dummy".decode(str(charset))
        except LookupError:
            m.del_param("charset")

    content = m.get_content()
    if isinstance(content, bytes):
        maintype = m.get_content_maintype()
        subtype = m.get_content_subtype()
        m.set_content(content, maintype, subtype)
    else:
        m.set_content(content)


class Email(Transport):
    @classmethod
    def bytes_to_sanitized_message(cls, data: bytes) -> EmailMessage:
        m = email.message_from_bytes(data, policy=email.policy.SMTP)
        if not m.is_multipart():
            _rewrap(m)
            return m

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
            else:
                _rewrap(part)
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
            try:
                attachment = self.bytes_to_sanitized_message(body_bytes)
                subject = attachment.get("subject", "")
            except Exception:
                logger.exception(f"Exception while parsing email (ping {ping.id})")

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

        try:
            emails.alert(self.channel.email.value, ctx, headers, attachment)
        except (SMTPServerDisconnected, SMTPDataError, ConnectionRefusedError):
            logger.exception("Exception while sending email")
            raise TransportError("SMTP connection error")

    def is_noop(self, status: str) -> bool:
        if status == "down":
            return not self.channel.email.notify_down
        else:
            return not self.channel.email.notify_up
