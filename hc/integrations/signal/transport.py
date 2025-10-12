from __future__ import annotations

import json
import logging
import socket
import time
import uuid
from collections.abc import Iterator

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import Transport, TransportError
from hc.lib.html import extract_signal_styles
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class SignalRateLimitFailure(TransportError):
    def __init__(self, token: str, reply: bytes):
        super().__init__("CAPTCHA proof required")
        self.token = token
        self.reply = reply


class Signal(Transport):
    TIMEOUT = 60

    class Result(BaseModel):
        type: str
        token: str | None = None

    class Response(BaseModel):
        results: list[Signal.Result]

    class Data(BaseModel):
        response: Signal.Response

    class Error(BaseModel):
        code: int
        data: Signal.Data | None = None

    class Reply(BaseModel):
        id: str = ""
        error: Signal.Error | None = None

        def get_results(self) -> list[Signal.Result]:
            assert self.error
            if self.error.data is None:
                return []
            return self.error.data.response.results

    def is_noop(self, status: str) -> bool:
        if status == "down":
            return not self.channel.phone.notify_down
        else:
            return not self.channel.phone.notify_up

    @classmethod
    def send(cls, recipient: str, message: str) -> None:
        plaintext, styles = extract_signal_styles(message)
        if "." in recipient:
            # usernames must be prefixed with "u:"
            recipient = f"u:{recipient}"
        payload = {
            "jsonrpc": "2.0",
            "method": "send",
            "params": {
                "recipient": [recipient],
                "message": plaintext,
                "textStyle": styles,
            },
            "id": str(uuid.uuid4()),
        }

        payload_bytes = (json.dumps(payload) + "\n").encode()
        for reply_bytes in cls._read_replies(payload_bytes):
            try:
                reply = Signal.Reply.model_validate_json(reply_bytes)
            except ValidationError:
                logger.error("unexpected signal-cli response: %s", reply_bytes)
                raise TransportError("signal-cli call failed (unexpected response)")

            if reply.id != payload["id"]:
                continue

            if reply.error is None:
                break  # success!

            for result in reply.get_results():
                if result.type == "UNREGISTERED_FAILURE":
                    raise TransportError("Recipient not found", permanent=True)

                if result.type == "RATE_LIMIT_FAILURE" and result.token:
                    raise SignalRateLimitFailure(result.token, reply_bytes)

            msg = f"signal-cli call failed ({reply.error.code})"
            msg_with_extras = f"{msg} for {recipient}\n{reply_bytes.decode()}"
            # Include signal-cli reply in the message we log for ourselves
            logger.error(msg_with_extras)
            # Do not include signal-cli reply in the message we show to the user
            raise TransportError(msg)

    @classmethod
    def _read_replies(cls, payload_bytes: bytes) -> Iterator[bytes]:
        """Send a request to signal-cli over UNIX socket. Read and yield replies.

        This method:
        * opens UNIX socket
        * sends the request data (JSON RPC data encoded as bytes)
        * reads newline-terminated responses and yields them

        Individual sendall and recv operations have a timeout of 15 seconds.
        This method also keeps track of total time spent in the method, and raises
        an exception when the total time exceeds 15 seconds.

        """

        if not settings.SIGNAL_CLI_SOCKET:
            raise TransportError("Signal notifications are not enabled")

        start = time.time()
        address: str | tuple[str, int]
        if ":" in settings.SIGNAL_CLI_SOCKET:
            stype = socket.AF_INET
            parts = settings.SIGNAL_CLI_SOCKET.split(":")
            address = (parts[0], int(parts[1]))
        else:
            stype = socket.AF_UNIX
            address = settings.SIGNAL_CLI_SOCKET

        with socket.socket(stype, socket.SOCK_STREAM) as s:
            s.settimeout(cls.TIMEOUT)
            try:
                s.connect(address)
                s.sendall(payload_bytes)
                s.shutdown(socket.SHUT_WR)  # we are done sending

                buffer = []
                while True:
                    ch = s.recv(1)
                    buffer.append(ch)
                    if ch in (b"\n", b""):
                        yield b"".join(buffer)
                        buffer = []

                    if time.time() - start > cls.TIMEOUT:
                        raise TransportError("signal-cli call timed out")

            except OSError as e:
                msg = f"signal-cli call failed ({e})"
                # Log the exception, so any configured logging handlers can pick it up
                logger.exception(msg)

                # And then report it the same as other errors
                raise TransportError(msg)

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.SIGNAL_CLI_SOCKET:
            raise TransportError("Signal notifications are not enabled")

        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_signal(self.channel.phone.value):
            raise TransportError("Rate limit exceeded")

        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "ping": self.last_ping(flip),
            "down_checks": self.down_checks(flip.owner),
        }
        text = self.tmpl("signal_message.html", **ctx)
        tries_left = 2
        while True:
            try:
                return self.send(self.channel.phone.value, text)
            except SignalRateLimitFailure as e:
                self.channel.send_signal_captcha_alert(e.token, e.reply.decode())
                plaintext, _ = extract_signal_styles(text)
                self.channel.send_signal_rate_limited_notice(text, plaintext)
                raise e
            except TransportError as e:
                tries_left -= 1
                if e.permanent or tries_left == 0:
                    raise e
                logger.debug("Retrying signal-cli call")
