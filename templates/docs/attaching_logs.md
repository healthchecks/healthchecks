# Attaching Logs

SITE_NAME ping endpoints accept HTTP HEAD, GET and POST request methods.

When using HTTP POST, **you can include arbitrary payload in the request body**.
If the request body looks like a UTF-8 string, SITE_NAME will log the first 10 kilobytes of
the request body, so you can inspect it later.

## Logging Command Output

In this example, we run `certbot renew`, capture its output, and submit
the captured output to SITE_NAME:

```bash
#!/bin/sh

m=$(/usr/bin/certbot renew 2>&1)
curl -fsS --retry 3 --data-raw "$m" PING_URL
```

## In Combination with the `/fail` Endpoint

We can extend the previous example and signal either success or failure
depending on the exit code:

```bash
#!/bin/sh

url=PING_URL

m=$(/usr/bin/certbot renew 2>&1)

if [ $? -ne 0 ]; then url=$url/fail; fi
curl -fsS --retry 3 --data-raw "$m" $url
```

## All in One Line

Finally, all of the above can be packaged in a single line. The one-line
version can be put directly in crontab, without using a wrapper script.

```bash
m=$(/usr/bin/certbot renew 2>&1); curl -fsS --data-raw "$m" "PING_URL$([ $? -ne 0 ] && echo -n /fail)"
```
