from io import BytesIO
import ipaddress
import json
from urllib.parse import urlencode
import socket

from django.conf import settings
import pycurl


class CurlError(Exception):
    def __init__(self, message) -> None:
        self.message = message


class Response(object):
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content

    def json(self):
        return json.loads(self.content.decode())

    @property
    def text(self):
        return self.content.decode()


def opensocket(purpose, curl_address):
    family, socktype, protocol, address = curl_address
    if not settings.INTEGRATIONS_ALLOW_PRIVATE_IPS:
        if ipaddress.ip_address(address[0]).is_private:
            return pycurl.SOCKET_BAD

    return socket.socket(family, socktype, protocol)


def request(method, url, **kwargs):
    c = pycurl.Curl()
    c.setopt(c.PROTOCOLS, c.PROTO_HTTP | c.PROTO_HTTPS)
    c.setopt(c.OPENSOCKETFUNCTION, opensocket)
    c.setopt(c.FOLLOWLOCATION, True)  # Allow redirects
    c.setopt(c.MAXREDIRS, 3)
    if "timeout" in kwargs:
        c.setopt(c.TIMEOUT, kwargs["timeout"])

    if "params" in kwargs:
        url += "?" + urlencode(kwargs["params"])
    c.setopt(c.URL, url.encode())

    if "auth" in kwargs:
        c.setopt(c.USERPWD, "%s:%s" % kwargs["auth"])

    headers = kwargs.get("headers", {})
    data = kwargs.get("data", "")

    if "json" in kwargs:
        data = json.dumps(kwargs["json"])
        headers["Content-Type"] = "application/json"

    headers_list = [k + ":" + v for k, v in headers.items()]
    c.setopt(pycurl.HTTPHEADER, headers_list)

    if method in ("post", "put"):
        if isinstance(data, dict):
            c.setopt(c.POSTFIELDS, urlencode(data))

        if isinstance(data, str):
            data = data.encode()

        if isinstance(data, bytes):
            c.setopt(c.UPLOAD, 1)
            c.setopt(c.READDATA, BytesIO(data))

        c.setopt(c.CUSTOMREQUEST, method.upper())

    buffer = BytesIO()
    c.setopt(c.WRITEDATA, buffer)

    try:
        c.perform()
    except pycurl.error as e:
        errcode = e.args[0]
        if errcode == pycurl.E_OPERATION_TIMEDOUT:
            raise CurlError("Connection timed out")
        elif errcode == pycurl.E_COULDNT_CONNECT:
            raise CurlError("Connection failed")
        elif errcode == pycurl.E_TOO_MANY_REDIRECTS:
            raise CurlError("Too many redirects")
        elif errcode == pycurl.E_PEER_FAILED_VERIFICATION:
            raise CurlError("Failed certificate verification")

        raise CurlError(f"HTTP request failed, code: {errcode}")

    status = c.getinfo(c.RESPONSE_CODE)
    c.close()

    return Response(status, buffer.getvalue())


def post(url, data=None, **kwargs):
    return request("post", url, data=data, **kwargs)
