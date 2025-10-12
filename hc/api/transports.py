from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, NoReturn

from django.template.loader import render_to_string
from hc.front.templatetags.hc_extras import sortchecks
from hc.lib import curl

if TYPE_CHECKING:
    from hc.api.models import Channel, Check, Flip, Notification, Ping


logger = logging.getLogger(__name__)


def get_ping_body(ping: Ping | None, maxlen: int | None = None) -> str | None:
    """Return ping body for a given Ping object.

    Does two extra things in addition to simply calling Ping.get_body():
    * if body has not been uploaded to object storage yet, waits 5 seconds
      and tries to fetch it again
    * if body is longer than the `maxlen` argument, truncate it
    """
    body = None
    if ping and ping.has_body():
        body = ping.get_body()
        if body is None and ping.object_size:
            # Body is not uploaded to object storage yet.
            # Wait 5 seconds, then fetch the body again.
            time.sleep(5)
            body = ping.get_body()

    if body and maxlen and len(body) > maxlen:
        body = body[:maxlen] + "\n[truncated]"

    return body


class TransportError(Exception):
    def __init__(self, message: str, permanent: bool = False) -> None:
        self.message = message
        self.permanent = permanent


class Transport:
    def __init__(self, channel: Channel):
        self.channel = channel

    def notify(self, flip: Flip, notification: Notification) -> None:
        """Send notification about current status of the check.

        This method raises TransportError on error, and returns None
        on success.

        """

        raise NotImplementedError()

    def is_noop(self, status: str) -> bool:
        """Return True if transport will ignore check's current status.

        This method is overridden in Webhook subclass where the user can
        configure webhook urls for "up" and "down" events, and both are
        optional.

        """

        return False

    def down_checks(self, check: Check) -> list[Check] | None:
        """Return a sorted list of other checks in the same project that are down.

        If there are no other hecks in the project, return None instead of empty list.
        Templates can check for None to decide whether to show or not show the
        "All other checks are up" note.

        """

        siblings = self.channel.project.check_set.exclude(id=check.id)
        if not siblings.exists():
            return None

        down_siblings = list(siblings.filter(status="down"))
        sortchecks(down_siblings, "name")

        return down_siblings

    def last_ping(self, flip: Flip) -> Ping | None:
        """Return the last Ping object received before this flip."""

        if not flip.owner.pk:
            return None

        # Sort by "created". Sorting by "id" can cause postgres to pick api_ping.id
        # index (slow if the api_ping table is big)
        q = flip.owner.ping_set.order_by("created")
        # Make sure we're not selecting pings that occurred after the flip
        q = q.filter(created__lte=flip.created)

        return q.last()

    def tmpl(self, template_name: str, **ctx: Any) -> str:
        # \xa0 is non-breaking space. It causes SMS messages to use UCS2 encoding
        # and cost twice the money.
        return render_to_string(template_name, ctx).strip().replace("\xa0", " ")


class RemovedTransport(Transport):
    """Dummy transport class for obsolete integrations."""

    def is_noop(self, status: str) -> bool:
        return True


class HttpTransport(Transport):
    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        # Subclasses can override this method to produce a more specific message.
        raise TransportError(f"Received status code {response.status_code}")

    @classmethod
    def _request(
        cls,
        method: str,
        url: str,
        *,
        params: curl.Params,
        data: curl.Data,
        json: Any,
        headers: curl.Headers,
        auth: curl.Auth,
    ) -> None:
        try:
            r = curl.request(
                method,
                url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                auth=auth,
                timeout=30,
            )
            if r.status_code not in (200, 201, 202, 204):
                cls.raise_for_response(r)
        except curl.CurlError as e:
            raise TransportError(e.message)

    @classmethod
    def request(
        cls,
        method: str,
        url: str,
        *,
        retry: bool,
        params: curl.Params = None,
        data: curl.Data = None,
        json: Any = None,
        headers: curl.Headers = None,
        auth: curl.Auth = None,
    ) -> None:
        tries_left = 3 if retry else 1
        while True:
            try:
                return cls._request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                    auth=auth,
                )
            except TransportError as e:
                tries_left = 0 if e.permanent else tries_left - 1
                # If we have no tries left then abort the retry loop by re-raising
                # the exception:
                if tries_left == 0:
                    raise e

    # Convenience wrapper around self.request for making "POST" requests
    @classmethod
    def post(
        cls,
        url: str,
        retry: bool = True,
        *,
        params: curl.Params = None,
        data: curl.Data = None,
        json: Any = None,
        headers: curl.Headers = None,
        auth: curl.Auth = None,
    ) -> None:
        cls.request(
            "post",
            url,
            retry=retry,
            params=params,
            data=data,
            json=json,
            headers=headers,
            auth=auth,
        )
