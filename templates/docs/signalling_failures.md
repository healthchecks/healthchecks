# Signalling failures

Append `/fail` to a ping URL and use it to actively signal a failure.
Requesting the `/fail` URL will immediately mark the check as "down".
You can use this feature to minimize the delay from your monitored service failing
to you getting a notification.

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
