# Signaling failures

You can actively signal a failure to SITE_NAME by slightly changing the
ping URL: append either `/fail` or `/{exit-status}` to your normal ping URL.
The exit status should be a 0-255 integer. SITE_NAME will interpret
exit status 0 as success and all non-zero values as failures.

Examples:

```bash

# Reports failure by appending the /fail suffix:
curl --retry 3 PING_URL/fail

# Reports failure by appending a non-zero exit status:
curl --retry 3 PING_URL/1
```

By actively signaling failures to SITE_NAME, you can minimize the delay from your
monitored service encountering a problem to you getting notified about it.

## Shell Scripts

The below shell script appends `$?` (a special variable that contains the
exit status of the last executed command) to the ping URL:

```bash
#!/bin/sh

/usr/bin/certbot renew
curl --retry 3 PING_URL/$?

```

## Python

Below is a skeleton code example in Python which signals a failure when the
work function returns an unexpected value or throws an exception:

```python
import requests
URL = "PING_URL"

def do_work():
    # Do your number crunching, backup dumping, newsletter sending work here.
    # Return a truthy value on success.
    # Return a falsy value or throw an exception on failure.
    return True

success = False
try:
    success = do_work()
finally:
    # On success, requests PING_URL
    # On failure, requests PING_URL/fail
    requests.get(URL if success else URL + "/fail")
```
