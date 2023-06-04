# Shell Scripts

You can easily add SITE_NAME monitoring to a shell script. All you
have to do is make an HTTP request at an appropriate place in the script.
[curl](https://curl.haxx.se/docs/manpage.html) and
[wget](https://www.gnu.org/software/wget/manual/wget.html)
are two common command-line HTTP clients you can use.

```bash
# Sends an HTTP GET request with curl:
curl -m 10 --retry 5 PING_URL

# Silent version (no stdout/stderr output unless curl hits an error):
curl -fsS -m 10 --retry 5 -o /dev/null PING_URL

```

Here's what each curl parameter does:

**-m &lt;seconds&gt;**
:   Maximum time in seconds that you allow the whole operation to take.

**--retry &lt;num&gt;**
:   If an HTTP request fails, retry up to this many times. By default, curl
    uses an increasing delay between each retry (1s, 2s, 4s, 8s, ...).
    See also [--retry-delay](https://curl.haxx.se/docs/manpage.html#--retry-delay).

**-f, --fail**
:   Makes curl treat non-200 responses as errors.

**-s, --silent**
:   Silent or quiet mode. Hides the progress meter, but also
    hides error messages.

**-S, --show-error**
:   Re-enables error messages when -s is used.

**-o /dev/null**
:   Redirect curl's stdout to /dev/null (error messages still go to stderr).

## Signaling Failure from Shell Scripts

You can append `/fail` or `/{exit-status}` to any ping URL and use the resulting URL
to actively signal a failure. The exit status should be a 0-255 integer.
SITE_NAME will interpret exit status 0 as success and all non-zero values as failures.

The following example runs `/usr/bin/certbot renew`, and uses the `$?` variable to
look up its exit status:

```bash
#!/bin/sh

# Payload here:
/usr/bin/certbot renew
# Ping SITE_NAME
curl -m 10 --retry 5 PING_URL/$?
```

## Logging Command Output

When pinging with HTTP POST, you can put extra diagnostic information in the request
body. If the request body looks like a valid UTF-8 string, SITE_NAME
will accept and store the first PING_BODY_LIMIT_FORMATTED of the request body.

In the below example, certbot's output is captured and submitted via HTTP POST:

```bash
#!/bin/sh

m=$(/usr/bin/certbot renew 2>&1)
curl -fsS -m 10 --retry 5 --data-raw "$m" PING_URL
```

## Auto-provisioning New Checks

This example uses SITE_NAME [Management API](../api/) to create a check "on the fly"
(if it does not already exist) and retrieve its ping URL.
Using this technique, you can write services that automatically
register with SITE_NAME the first time they run.


```bash
#!/bin/bash

API_KEY=your-api-key-here

# Check's parameters. This example uses system's hostname for check's name.
PAYLOAD='{"name": "'`hostname`'", "timeout": 60, "grace": 60, "unique": ["name"]}'

# Create the check if it does not exist.
# Grab the ping_url from JSON response using the jq utility:
URL=`curl -s SITE_ROOT/api/v1/checks/  -H "X-Api-Key: $API_KEY" -d "$PAYLOAD"  | jq -r .ping_url`

# Finally, send a ping:
curl -m 10 --retry 5 $URL
```
