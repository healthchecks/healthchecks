#!/usr/bin/env python

"""Probe the /health endpoint and return status 0 if successful.

The /health endpoint tests if the database connection is alive.
The /health endpoint skips the ALLOWED_HOSTS checks so we do not need to
pass the Host: request header.

This script is intended to be used in the Dockerfile, in the HEALTHCHECK instruction.

"""

from urllib.request import urlopen

with urlopen("http://127.0.0.1:8000/health") as response:
    assert response.status == 200

print("Status OK")
