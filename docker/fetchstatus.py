#!/usr/bin/env python

"""Probe the /api/v3/status/ endpoint and return status 0 if successful.

The /api/v3/status/ endpoint tests if the database connection is alive.
This script is intended to be used in the Dockerfile, in the
HEALTHCHECK instruction.

When making the HTTP request, we must pass a valid Host header and a valid
path (in case the app is not running at the root of the domnain). To
figure this out, we need to see `settings.SITE_ROOT`. Loading full
Django settings is a heavy operation so instead we replicate the logic that
settings.py uses for reading SITE_ROOT:

* Load it from `SITE_ROOT` environment variable
* if hc/local_settings.py exists, import it and read it from there

"""

from __future__ import annotations

import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Read SITE_ROOT from environment, same as settings.py would do:
SITE_ROOT = os.getenv("SITE_ROOT", "http://localhost:8000")
# If local_settings.py exists, load it from there
if os.path.exists("hc/local_settings.py"):
    from hc import local_settings

    SITE_ROOT = getattr(local_settings, "SITE_ROOT", SITE_ROOT)

parsed_site_root = urlparse(SITE_ROOT.removesuffix("/"))
url = f"http://localhost:8000{parsed_site_root.path}/api/v3/status/"
headers = {"Host": parsed_site_root.netloc}
with urlopen(Request(url, headers=headers)) as response:
    assert response.status == 200

print("Status OK")
