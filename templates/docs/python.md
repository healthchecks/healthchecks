# Python

If you are already using the requests library, it's convenient to also use it here:

```python
# using requests:
import requests
requests.get("PING_URL")
```

Otherwise, you can use the urllib standard module.

```python
# urllib with python 3.x:
import urllib.request
urllib.request.urlopen("PING_URL")
```

```python
# urllib with python 2.x:
import urllib
urllib.urlopen("PING_URL")
```

You can include additional diagnostic information in the in the request body (for POST requests), or in the "User-Agent" request header:

```python
# Passing diagnostic information in the POST body:
import requests
requests.post("PING_URL", data="temperature=-7")
```

```python
# Passing diagnostic information in the User-Agent header:
import requests
requests.get("PING_URL", headers={"User-Agent": "temperature=-7"})
```
