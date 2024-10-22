#!/usr/bin/env python

"""Probe the /api/v3/status/ endpoint and return status 0 if successful.

The /api/v3/status/ endpoint tests if the database connection is alive.
This script is intended to be used in the Dockerfile, in the
HEALTHCHECK instruction.

When making the HTTP request, we must pass a valid Host header. To
figure this out, we need to see `settings.ALLOWED_HOSTS`. Loading full
Django settings is a heavy operation, and this script runs every 10 seconds,
so instead we replicate the logic that settings.py uses for reading ALLOWED_HOSTS:

* Load it from `ALLOWED_HOSTS` env var
* if hc/local_settings.py exists, import it and read it from there

"""

from __future__ import annotations

import os
from urllib.request import Request, urlopen

# Read ALLOWED_HOSTS from environment, same as settings.py would do:
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
# If local_settings.py exists, load it from there,
# also same as settings.py would do
if os.path.exists("hc/local_settings.py"):
    from hc import local_settings

    ALLOWED_HOSTS = getattr(local_settings, "ALLOWED_HOSTS", ALLOWED_HOSTS)

# Use the first item in ALLOWED_HOSTS in our Host header
# (unless is a wildcard, wildcard would not pass as a valid host value)
host = ALLOWED_HOSTS[0]
if host == "*":
    host = "localhost"

req = Request("http://localhost:8000/api/v3/status/", headers={"Host": host})
with urlopen(req) as response:
    assert response.status == 200

print("Status OK")
