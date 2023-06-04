# Attaching Logs

SITE_NAME ping endpoints accept HTTP HEAD, GET and POST request methods.

When using HTTP POST, **you can include an arbitrary payload in the request body**.
SITE_NAME will log the first PING_BODY_LIMIT_FORMATTED (PING_BODY_LIMIT bytes) of the
request body, so that you can inspect it later.

## Logging Command Output

In this example, we run `certbot renew`, capture its output (both the stdout
and stderr streams), and submit the captured output to SITE_NAME:

```bash
#!/bin/sh

m=$(/usr/bin/certbot renew 2>&1)
curl -fsS -m 10 --retry 5 --data-raw "$m" PING_URL
```

We can extend the previous example and signal either success or failure
depending on the exit code:

```bash
#!/bin/sh

m=$(/usr/bin/certbot renew 2>&1)
curl -fsS -m 10 --retry 5 --data-raw "$m" PING_URL/$?
```

If the command produces a lot of output, you may run into the following error:

```
/usr/bin/curl: Argument list too long
```

In that case, one workaround is to save the output to a temporary file,
then tell curl to send the file as the request body:

```bash
#!/bin/sh

/usr/bin/certbot renew > /tmp/certbot-renew.log 2>&1
curl -fsS -m 10 --retry 5 --data-binary @/tmp/certbot-renew.log PING_URL/$?
```

## Using Runitor

[Runitor](https://github.com/bdd/runitor) is a third-party utility that runs the
supplied command, captures its output and reports to SITE_NAME.
It also measures the execution time and retries HTTP requests on transient errors.
Best of all, the syntax is simple and clean:

```bash
runitor -uuid your-uuid-here -- /usr/bin/certbot renew
```

## Sending Logs Without Signalling Success or Failure

You may sometimes want to log diagnostic information without altering the check's
current state. SITE_NAME provides the [/log endpoint](../http_api#log-uuid) just for
that. When you send an HTTP POST request to this endpoint, SITE_NAME will log the event
and display it in check's "Events" section but will keep the check's state unchanged.

## Handling More Than PING_BODY_LIMIT_FORMATTED of Logs

While SITE_NAME can store a small amount of logs in a pinch, it is not specifically
designed for that. If you run into the issue of logs getting cut off, consider
the following options:

* See if the logs can be made less verbose. For example, if you have a batch job
that outputs a line of text per item processed, perhaps it can output a summary with
the totals instead.
* If the important content is usually at the end, submit the
**last PING_BODY_LIMIT_FORMATTED** instead of the first. Here is an example that
submits the last PING_BODY_LIMIT_FORMATTED of `dmesg` output:

```bash
#!/bin/sh

m=$(dmesg | tail --bytes=PING_BODY_LIMIT)
curl -fsS -m 10 --retry 5 --data-raw "$m" PING_URL
```

* Finally, if it is critical to capture the entire log output,
consider using a dedicated log aggregation service for capturing the logs.


## Where to See Captured Logs

In the check's details page, Events section, click on individual events to see
full event details, including the captured log information.

![The Events section](IMG_URL/events.png)

In the dialog that opens, use the "Download Original" link to download the request
body data, exactly as it was submitted to SITE_NAME:

![The Ping Details dialog](IMG_URL/ping_details.png)
