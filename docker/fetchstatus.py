#!/usr/bin/env python

"""Probe the /health endpoint and return status 0 if successful.

The /health endpoint tests if the database connection is alive.
The /health endpoint skips the ALLOWED_HOSTS checks so we do not need to
pass the Host: request header.

This script is intended to be used in the Dockerfile, in the HEALTHCHECK instruction.

"""

from os import getenv
from urllib.request import urlopen

port = getenv("GUNICORN_PORT", "8000")
with urlopen(f"http://127.0.0.1:{port}/health") as response:
    assert response.status == 200

print("Status OK")
