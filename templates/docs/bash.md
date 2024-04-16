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
:   Maximum time in seconds that you allow the HTTP request to take.
    If you use the `--retry` parameter, then the time counter is reset
    at the start of each retry.

**--retry &lt;num&gt;**
:   On transient errors, retry up to this many times. By default, curl
    uses an increasing delay between each retry (1s, 2s, 4s, 8s, ...).
    See also [--retry-delay](https://curl.haxx.se/docs/manpage.html#--retry-delay).
    Transient errors are: timeouts, HTTP status codes 408, 429, 500, 502, 503, 504.

**-f, --fail**
:   Makes curl treat non-200 responses as errors, and
    [return error 22](https://curl.se/docs/manpage.html#-f).

**-s, --silent**
:   Silent or quiet mode. Hides the progress meter, but also
    hides error messages.

**-S, --show-error**
:   Re-enables error messages when -s is used.

**-o /dev/null**
:   Redirects curl's stdout to /dev/null (error messages still go to stderr).

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

Note on pipelines (`command1 | command2 | command3`) in Bash scripts: by default, a
pipeline's exit status is the exit status of the rightmost command in the pipeline.
Use `set -o pipefail` if you need the pipeline to return non-zero exit status if *any*
part of the pipeline fails:

```bash
#!/bin/sh

set -o pipefail
pg_dump somedb | gpg --encrypt --recipient alice@example.org --output somedb.sql.gpg
# Without pipefail, if pg_dump command fails, but gpg succeeds, $? will be 0,
# and the script will report success.
# With pipefail, if pg_dump fails, the script will report the exit code returned by pg_dump.
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

## Auto Provisioning New Checks

This example uses SITE_NAME [auto provisioning feature](../autoprovisioning/) to
create a check "on the fly" if it does not already exist. Using this technique, you can
write services that automatically register with SITE_NAME the first time they run.


```bash
#!/bin/bash

PING_KEY=fixme-your-ping-key-here

# Use system's hostname as check's slug
SLUG=$(hostname)

# Construct a ping URL and append "?create=1" at the end:
URL=PING_ENDPOINT$PING_KEY/$SLUG?create=1

# Send a ping:
curl -m 10 --retry 5 $URL
```
