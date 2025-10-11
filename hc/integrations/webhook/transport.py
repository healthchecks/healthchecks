from __future__ import annotations

import json
from urllib.parse import quote

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError, get_ping_body
from hc.lib.string import replace


class Webhook(HttpTransport):
    def prepare(
        self,
        template: str,
        flip: Flip,
        urlencode: bool = False,
        latin1: bool = False,
        allow_ping_body: bool = False,
    ) -> str:
        """Replace variables with actual values."""

        def safe(s: str) -> str:
            return quote(s) if urlencode else s

        check = flip.owner
        ctx = {
            "$CODE": str(check.code),
            "$STATUS": flip.new_status,
            "$NOW": safe(flip.created.replace(microsecond=0).isoformat()),
            "$NAME_JSON": safe(json.dumps(check.name)),
            "$NAME": safe(check.name),
            "$SLUG": check.slug,
            "$TAGS": safe(check.tags),
            "$JSON": safe(json.dumps(check.to_dict())),
        }

        # Materialize ping body only if template refers to it.
        if allow_ping_body and "$BODY" in template:
            body = get_ping_body(self.last_ping(flip))
            ctx["$BODY_JSON"] = json.dumps(body if body else "")
            ctx["$BODY"] = body if body else ""

        if "$EXITSTATUS" in template:
            ctx["$EXITSTATUS"] = "-1"
            lp = self.last_ping(flip)
            if lp and lp.exitstatus is not None:
                ctx["$EXITSTATUS"] = str(lp.exitstatus)

        for i, tag in enumerate(check.tags_list()):
            ctx["$TAG%d" % (i + 1)] = safe(tag)

        result = replace(template, ctx)
        if latin1:
            # Replace non-latin-1 characters with XML character references.
            result = result.encode("latin-1", "xmlcharrefreplace").decode("latin-1")

        return result

    def is_noop(self, status: str) -> bool:
        spec = self.channel.webhook_spec(status)
        if not spec.url:
            return True

        return False

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.WEBHOOKS_ENABLED:
            raise TransportError("Webhook notifications are not enabled.")

        spec = self.channel.webhook_spec(flip.new_status)
        if not spec.url:
            raise TransportError("Empty webhook URL")

        method = spec.method.lower()
        url = self.prepare(spec.url, flip, urlencode=True)
        retry = True
        if notification.owner is None:
            # This is a test notification.
            # When sending a test notification, don't retry on failures.
            retry = False

        body, body_bytes = spec.body, None
        if body and spec.method in ("POST", "PUT"):
            body = self.prepare(body, flip, allow_ping_body=True)
            body_bytes = body.encode()

        headers = {}
        for key, value in spec.headers.items():
            # Header values should contain ASCII and latin-1 only
            headers[key] = self.prepare(value, flip, latin1=True)

        self.request(method, url, retry=retry, data=body_bytes, headers=headers)
