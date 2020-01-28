# Shell Scripts

You can easily add SITE_NAME monitoring to a shell script. All you
have to do is make a HTTP request at the end of the script.
[curl](https://curl.haxx.se/docs/manpage.html) and
[wget](https://www.gnu.org/software/wget/manual/wget.html)
are two common command line HTTP clients you can use.

```bash
# Sending a HTTP GET request with curl:
curl --retry 3 PING_URL

# Silent version (no stdout/stderr output unless curl hits an error):
curl -fsS --retry 3 PING_URL

# Sending a HTTP GET request with wget:
wget PING_URL -O /dev/null
```

## Signalling Failure from Shell Scripts

You can append `/fail` to any ping URL and  use the resulting URL to actively
signal a failure. The below example:

* runs `/usr/bin/certbot renew`
* if the certbot command is successful (exit code 0), send HTTP GET to `PING_URL`
* otherwise, send HTTP GET to `PING_URL/fail`

```bash
#!/bin/sh

# Payload here:
/usr/bin/certbot renew
# Ping SITE_NAME
curl --retry 3 "PING_URL$([ $? -ne 0 ] && echo -n /fail)"
```

## Logging Command Output

When pinging with HTTP POST, you can put extra diagnostic information in request
body. If the request body looks like a valid UTF-8 string, SITE_NAME
will accept and store first 10KB of the request body.

In the below example, certbot's output is captured and submitted via HTTP POST:

```bash
#!/bin/sh

m=$(/usr/bin/certbot renew 2>&1)
curl -fsS --retry 3 -X POST --data-raw "$m" PING_URL
```
