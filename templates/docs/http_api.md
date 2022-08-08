# Pinging API

With the Pinging API, you can signal **success**, **start**, and **failure** events from
your systems.

## General Notes

All ping endpoints support:

* HTTP and HTTPS
* HTTP 1.0, HTTP 1.1 and HTTP 2
* IPv4 and IPv6
* HEAD, GET, and POST requests methods. The HTTP POST requests
can optionally include diagnostic information in the request body.
If the request body looks like a UTF-8 string, SITE_NAME stores the request body
(limited to the first 10KB for each received ping).

Successful responses will have the "200 OK" HTTP response status code and a short
"OK" string in the response body.

## UUIDs and Slugs

Each Pinging API request needs to uniquely identify a check.
SITE_NAME supports two ways of identifying a check: by check's UUID,
or by a combination of project's Ping Key and check's slug.

**Check's UUID** is automatically assigned when the check is created. It is
immutable. You cannot replace the automatically assigned UUID with a manually
chosen one. When you delete a check, you also lose its UUID and cannot get it back.

You can look up UUIDs of your checks in web UI or via [Management API](../api/) calls.

**Check's slug** is derived from check's name using Django's
[slugify](https://docs.djangoproject.com/en/3.2/ref/utils/#django.utils.text.slugify)
function. It applies the following transformations:

* Convert to ASCII.
* Convert to lowercase.
* Remove characters that aren't alphanumerics, underscores, hyphens, or whitespace.
* Replace any whitespace or repeated hyphens with single hyphens.
* Remove leading and trailing whitespace, hyphens, and underscores.

For example, if check's name is "Database Backup", its slug is `database-backup`.

Check's slug **can change**. SITE_NAME updates check's slug whenever its name changes.

Check's slug is **not guaranteed to be unique**. If multiple checks in the project
have the same name, they also have the same slug. If you make a Pinging API
request using a non-unique slug, SITE_NAME will return the "409 Conflict" HTTP status
code and ignore the request.

## Endpoints

Endpoint Name                                               | Endpoint Address
------------------------------------------------------------|-------
[Success (UUID)](#success-uuid)       | `PING_ENDPOINT<uuid>`
[Start (UUID)](#start-uuid)           | `PING_ENDPOINT<uuid>/start`
[Failure (UUID)](#fail-uuid)          | `PING_ENDPOINT<uuid>/fail`
[Log (UUID)](#log-uuid)               | `PING_ENDPOINT<uuid>/log`
[Report script's exit status (UUID)](#exitcode-uuid)           | `PING_ENDPOINT<uuid>/<exit-status>`
[Success (slug)](#success-slug)       | `PING_ENDPOINT<ping-key>/<slug>`
[Start (slug)](#start-slug)           | `PING_ENDPOINT<ping-key>/<slug>/start`
[Failure (slug)](#fail-slug)          | `PING_ENDPOINT<ping-key>/<slug>/fail`
[Log (slug)](#log-slug)               | `PING_ENDPOINT<ping-key>/<slug>/log`
[Report script's exit status (slug)](#exitcode-slug)           | `PING_ENDPOINT<ping-key>/<slug>/<exit-status>`

## Send a "success" Signal Using UUID {: #success-uuid .rule }

```text
HEAD|GET|POST PING_ENDPOINT<uuid>
```

Signals to SITE_NAME that the job has completed successfully (or,
a continuously running process is still running and healthy).

SITE_NAME identifies the check by the UUID value included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

404 not found
:   Could not find a check with the specified UUID.

**Example**

```http
GET /5bf66975-d4c7-4bf5-bcc8-b8d8a82ea278 HTTP/1.0
Host: hc-ping.com
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Send a "start" Signal Using UUID {: #start-uuid .rule }

```text
HEAD|GET|POST PING_ENDPOINT<uuid>/start
```

Sends a "job has started!" message to SITE_NAME. Sending a "start" signal is optional,
but it enables a few extra features:

* SITE_NAME will measure and display job execution times
* SITE_NAME will detect if the job runs longer than its configured grace time

SITE_NAME identifies the check by the UUID value included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

404 not found
:   Could not find a check with the specified UUID.

**Example**

```http
GET /5bf66975-d4c7-4bf5-bcc8-b8d8a82ea278/start HTTP/1.0
Host: hc-ping.com
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Send a "failure" Signal Using UUID {: #fail-uuid .rule }

```text
HEAD|GET|POST PING_ENDPOINT<uuid>/fail
```

Signals to SITE_NAME that the job has failed. Actively signaling a failure
minimizes the delay from your monitored service failing to you receiving an alert.

SITE_NAME identifies the check by the UUID value included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

404 not found
:   Could not find a check with the specified UUID.

**Example**

```http
GET /5bf66975-d4c7-4bf5-bcc8-b8d8a82ea278/fail HTTP/1.0
Host: hc-ping.com
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Send a "log" Signal Using UUID {: #log-uuid .rule }

```text
HEAD|GET|POST PING_ENDPOINT<uuid>/log
```

Sends logging information to SITE_NAME without signalling success or failure.
SITE_NAME will log the event and display it in check's "Events" section with the
"Log" label. The check's status will not change.

SITE_NAME identifies the check by the UUID value included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

404 not found
:   Could not find a check with the specified UUID.

**Example**

```http
POST /5bf66975-d4c7-4bf5-bcc8-b8d8a82ea278/log HTTP/1.1
Host: hc-ping.com
Content-Type: text/plain
Content-Length: 11

Hello World
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Report Script's Exit Status (Using UUID) {: #exitcode-uuid .rule }

```text
HEAD|GET|POST PING_ENDPOINT<uuid>/<exit-status>
```

Sends a success or failure signal depending on the exit status
included in the URL. The exit status is a 0-255 integer. SITE_NAME
interprets 0 as success and all other values as failure.

SITE_NAME identifies the check by the UUID value included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

400 invalid url format
:   The URL does not match the expected format.

404 not found
:   Could not find a check with the specified UUID.

**Example**

```http
GET /5bf66975-d4c7-4bf5-bcc8-b8d8a82ea278/1 HTTP/1.0
Host: hc-ping.com
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Send a "success" Signal (Using Slug) {: #success-slug .rule }

```text
HEAD|GET|POST PING_ENDPOINT<ping-key>/<slug>
```

Signals to SITE_NAME that the job has completed successfully (or,
a continuously running process is still running and healthy).

SITE_NAME identifies the check by project's ping key and check's slug
included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

404 not found
:   Could not find a check with the specified ping key and slug combination.

409 ambiguous slug
:   Ambiguous, the slug matched multiple checks.

**Example**

```http
GET /fqOOd6-F4MMNuCEnzTU01w/database-backup HTTP/1.0
Host: hc-ping.com
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Send a "start" Signal (Using Slug) {: #start-slug .rule }

```text
HEAD|GET|POST PING_ENDPOINT<ping-key>/<slug>/start
```

Sends a "job has started!" message to SITE_NAME. Sending a "start" signal is
optional, but it enables a few extra features:

* SITE_NAME will measure and display job execution times
* SITE_NAME will detect if the job runs longer than its configured grace time

SITE_NAME identifies the check by project's ping key and check's slug
included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

404 not found
:   Could not find a check with the specified ping key and slug combination.

409 ambiguous slug
:   Ambiguous, the slug matched multiple checks.

**Example**

```http
GET /fqOOd6-F4MMNuCEnzTU01w/database-backup/start HTTP/1.0
Host: hc-ping.com
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Send a "failure" Signal (Using slug) {: #fail-slug .rule }

```text
HEAD|GET|POST PING_ENDPOINT<ping-key/<slug>/fail
```

Signals to SITE_NAME that the job has failed. Actively signaling a failure
minimizes the delay from your monitored service failing to you receiving an alert.

SITE_NAME identifies the check by project's ping key and check's slug
included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

404 not found
:   Could not find a check with the specified ping key and slug combination.

409 ambiguous slug
:   Ambiguous, the slug matched multiple checks.

**Example**

```http
GET /fqOOd6-F4MMNuCEnzTU01w/database-backup/fail HTTP/1.0
Host: hc-ping.com
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Send a "log" Signal (Using slug) {: #log-slug .rule }

```text
HEAD|GET|POST PING_ENDPOINT<ping-key/<slug>/log
```

Sends logging information to SITE_NAME without signalling success or failure.
SITE_NAME will log the event and display it in check's "Events" section with the
"Log" label. The check's status will not change.

SITE_NAME identifies the check by project's ping key and check's slug
included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

404 not found
:   Could not find a check with the specified ping key and slug combination.

409 ambiguous slug
:   Ambiguous, the slug matched multiple checks.

**Example**

```http
POST /fqOOd6-F4MMNuCEnzTU01w/database-backup/log HTTP/1.1
Host: hc-ping.com
Content-Type: text/plain
Content-Length: 11

Hello World
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

## Report Script's Exit Status (Using Slug) {: #exitcode-slug .rule }

```text
HEAD|GET|POST PING_ENDPOINT<ping-key>/<slug>/<exit-status>
```

Sends a success or failure signal depending on the exit status
included in the URL. The exit status is a 0-255 integer. SITE_NAME
interprets 0 as success and all other values as failure.

SITE_NAME identifies the check by project's ping key and check's slug
included in the URL.

The response may optionally contain a `Ping-Body-Limit: <n>` response header.
If this header is present, its value is an integer, and it specifies how many
bytes from the request body SITE_NAME will store per request. For example, if n=100,
but the client sends 123 bytes in the request body, SITE_NAME will store the first
100 bytes, and ignore the remaining 23. The client can use this header to decide
how much data to send in the request bodies of subsequent requests.

### Response Codes

200 OK
:   The request succeeded.

400 invalid url format
:   The URL does not match the expected format.

404 not found
:   Could not find a check with the specified ping key and slug combination.

409 ambiguous slug
:   Ambiguous, the slug matched multiple checks.

**Example**

```http
GET /fqOOd6-F4MMNuCEnzTU01w/database-backup/1 HTTP/1.0
Host: hc-ping.com
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 29 Jan 2020 09:58:23 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 2
Connection: close
Access-Control-Allow-Origin: *
Ping-Body-Limit: PING_BODY_LIMIT

OK
```

