# Python

If you are already using the [requests](https://requests.readthedocs.io/en/master/)
library, it is convenient to also use it here:

```python
import requests

try:
    requests.get("PING_URL", timeout=10)
except requests.RequestException as e:
    # Log ping failure here...
    print("Ping failed: %s" % e)
```

Otherwise, you can use the [urllib.request](https://docs.python.org/3/library/urllib.request.html)
module from Python 3 standard library:

```python
import socket
import urllib.request

try:
    urllib.request.urlopen("PING_URL", timeout=10)
except socket.error as e:
    # Log ping failure here...
    print("Ping failed: %s" % e)
```

You can include additional diagnostic information in the request body (for POST requests):

```python
# Passing diagnostic information in the POST body:
import requests
requests.post("PING_URL", data="temperature=-7")
```
