# Auto Provisioning

You can instruct SITE_NAME to automatically create missing checks on the first
received ping. To enable auto provisiong, use slug-based ping endpoints, and
append `?create=1` at the end:

```bash
# Do some work
sleep 5
# Send success signal to SITE_NAME
curl -m 10 --retry 5 PING_ENDPOINTmy-ping-key/srv01?create=1
```

In this example, SITE_NAME will look up project with the Ping Key `my-ping-key`,
and check if a check with a slug `srv01` exists there.

* If the check does not exist yet, SITE_NAME will create it, ping it, and return
  an HTTP 201 response.
* If the check exists, SITE_NAME will ping it and return an HTTP 200 response.

Auto provisioning works with all slug-based ping endpoints:

* [Success](../http_api/#success-slug)
* [Start](../http_api/#start-slug)
* [Failure](../http_api/#failure-slug)
* [Log](../http_api/#log-slug)
* [Exit status](../http_api/#exitcode-slug)

Auto provisioning is handy when working with dynamic infrastructure: if you distribute
the Ping Key to your monitoring clients, each client can pick its own slug
(for example, derived from the server’s hostname), construct a ping URL, and
register with SITE_NAME "on the fly" while sending its first ping.

## Auto Provisioned Checks Use Default Configuration

The checks created via auto provisioning will use the default parameters:

* Period: 1 day.
* Grace time: 1 hour.
* All integrations enabled.

It is currently not possible to specify a custom period, grace time, or other
parameters through the ping URL. If you need to change any parameters, you will need
to do this either from the web dashboard, or through [Management API](../api/).

## Auto Provisioning and Account Limits

Each SITE_NAME account has a specific limit of how many checks it is allowed to
create: 20 checks for free accounts; 100 or 1000 checks for paid accounts. To reduce
friction and the risk of silent failures, the auto provisioning functionality
**is allowed to temporarily exceed the account’s check limit up to two times**.
Meaning, if your account is already maxed out, auto provisioning will still be able to
create new checks until you hit two times the limit.