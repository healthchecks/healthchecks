# Pinging API

The SITE_NAME pinging API is used for submitting "start", "success" and "fail"
signals ("pings") from the monitored systems.

## General Notes

All ping endpoints support:

* HTTP and HTTPS
* HTTP 1.0, HTTP 1.1 and HTTP 2
* IPv4 and IPv6
* HEAD, GET and POST requests methods. The HTTP POST requests
can optionally include diagnostic information in the request body.
If the request body looks like a UTF-8 string, SITE_NAME stores the request body
(limited to first 10KB for each received ping).

Successful responses will have the "200 OK" HTTP response status code and a short
and simple string "OK" in the response body.

## Send a "success" Signal

```text
HEAD|GET|POST PING_ENDPOINT{uuid}
```

Signals to SITE_NAME that the job has completed successfully (or, for
continuously running processes, is still running and healthy). The `uuid` parameter
is unique for each check.

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

OK
```

## Send a "fail" Signal

```text
HEAD|GET|POST PING_ENDPOINT{uuid}/fail
```

Signals to SITE_NAME that the job has failed. Actively signalling a failure
minimizes the delay from your monitored service failing to you receiving an alert.

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

OK
```

## Send a "start" Signal

```text
HEAD|GET|POST PING_ENDPOINT{uuid}/start
```

Sends a "job has started!" message to SITE_NAME. This is
optional but enables a few extra features:

* SITE_NAME will measure and display job execution times
* SITE_NAME will detect if the job runs longer than its configured grace time

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

OK
```
