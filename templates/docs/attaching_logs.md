# Attaching Logs

SITE_NAME ping endpoints accept HTTP HEAD, GET and POST request methods.

When using HTTP POST, **you can include arbitrary payload in the request body**.
If the request body looks like a UTF-8 string, SITE_NAME will log the
first 10 kilobytes (10 000 bytes) of the request body, so you can inspect it later.

## Logging Command Output

In this example, we run `certbot renew`, capture its output (both the stdout
and stderr streams), and submit the captured output to SITE_NAME:

```bash
#!/bin/sh

m=$(/usr/bin/certbot renew 2>&1)
curl -fsS -m 10 --retry 5 --data-raw "$m" PING_URL
```

## In Combination with the `/fail` and `/{exit-status}` Endpoints

We can extend the previous example and signal either success or failure
depending on the exit code:

```bash
#!/bin/sh

m=$(/usr/bin/certbot renew 2>&1)
curl -fsS -m 10 --retry 5 --data-raw "$m" PING_URL/$?
```

## Using Runitor

[Runitor](https://github.com/bdd/runitor) is a third party utility that runs the
supplied command, captures its output and and reports to SITE_NAME.
It also measures the execution time, and retries HTTP requests on transient errors.
Best of all, the syntax is simple and clean:

```bash
runitor -uuid your-uuid-here -- /usr/bin/certbot renew
```

## Handling More Than 10KB of Logs

While SITE_NAME can store a small amount of logs in a pinch, it is not specifically
designed for that. If you run into the issue of logs getting cut off, consider
the following options:

* See if the logs can be made less verbose. For example, if you have a batch job
that outputs a line of text per item processed, perhaps it can output a short
summary with the totals instead.
* If the important content is usually at the end, submit the **last 10KB** instead
of the first. Here is an example that submits the last 10KB of `dmesg` output:

```bash
#!/bin/sh

m=$(dmesg | tail --bytes=10000)
curl -fsS -m 10 --retry 5 --data-raw "$m" PING_URL
```

* Finally, if for your use case it is critical to capture the entire log output,
consider using a dedicated log aggregation service for capturing the logs.
