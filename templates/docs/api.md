# API Reference

SITE_NAME REST API supports listing, creating, updating, pausing and deleting
checks in user's account.

## API Endpoints

Endpoint Name                                         | Endpoint Address
------------------------------------------------------|-------
[Get a list of existing checks](#list-checks)         | `GET SITE_ROOT/api/v1/checks/`
[Get a single check](#get-check)                   | `GET SITE_ROOT/api/v1/checks/<uuid>`
[Create a new check](#create-check)                   | `POST SITE_ROOT/api/v1/checks/`
[Update an existing check](#update-check)             | `POST SITE_ROOT/api/v1/checks/<uuid>`
[Pause monitoring of a check](#pause-check)           | `POST SITE_ROOT/api/v1/checks/<uuid>/pause`
[Delete check](#delete-check)                         | `DELETE SITE_ROOT/api/v1/checks/<uuid>`
[Get a list of existing integrations](#list-channels) | `GET SITE_ROOT/api/v1/channels/`

## Authentication

Your requests to SITE_NAME REST API must authenticate using an
API key. Each project in your SITE_NAME account has separate API keys.
There are no account-wide API keys. By default, a project on SITE_NAME doesn't have
an API key. You can create read-write and read-only API keys in the
**Project Settings** page.

Key Type           | Description
-------------------|------------
Regular API key    | Have full access to all documented API endpoints.
Read-only API key  | Only work with the [Get a list of existing checks](#list-checks) endpoint. Some fields are omitted from the API responses.

The client can authenticate itself by sending an appropriate HTTP
request header. The header's name should be `X-Api-Key` and
its value should be your API key.


Alternatively, for POST requests with a JSON request body,
the client can include an `api_key` field in the JSON document.
See below the "Create a check" section for an example.

## API Requests

For POST requests, the SITE_NAME API expects request body to be
a JSON document (*not* a `multipart/form-data` encoded form data).

## API Responses

SITE_NAME uses HTTP status codes wherever possible.
In general, 2xx class indicates success, 4xx indicates an client error,
and 5xx indicates a server error.

The response may contain a JSON document with additional data.

## Get a List of Existing Checks {: #list-checks .rule }

`GET SITE_ROOT/api/v1/checks/`

Returns a list of checks belonging to the user, optionally filtered by
one or more tags.

### Query String Parameters

tag=&lt;value&gt;
:   Filters the checks, and returns only the checks that are tagged with the
    specified value.

    This parameter can be repeated multiple times.

    Example:

    `SITE_ROOT/api/v1/checks/?tag=foo&tag=bar`

### Response Codes

200 OK
:   The request succeeded.

401 Unauthorized
:   The API key is either missing or invalid.

### Example Request

```bash
curl --header "X-Api-Key: your-api-key" SITE_ROOT/api/v1/checks/
```

### Example Response

```json
{
  "checks": [
    {
      "name": "Filesystem Backup",
      "tags": "backup fs",
      "desc": "Runs incremental backup every hour",
      "grace": 600,
      "n_pings": 1,
      "status": "up",
      "last_ping": "2020-03-24T14:02:03+00:00",
      "next_ping": "2020-03-24T15:02:03+00:00",
      "ping_url": "PING_ENDPOINT31365bce-8da9-4729-8ff3-aaa71d56b712",
      "update_url": "SITE_ROOT/api/v1/checks/31365bce-8da9-4729-8ff3-aaa71d56b712",
      "pause_url": "SITE_ROOT/api/v1/checks/31365bce-8da9-4729-8ff3-aaa71d56b712/pause",
      "channels": "1bdea468-03bf-47b8-ab27-29a9dd0e4b94,51c6eb2b-2ae1-456b-99fe-6f1e0a36cd3c",
      "timeout": 3600
    },
    {
      "name": "Database Backup",
      "tags": "production db",
      "desc": "Runs ~/db-backup.sh",
      "grace": 1200,
      "n_pings": 7,
      "status": "down",
      "last_ping": "2020-03-23T10:19:32+00:00",
      "next_ping": null,
      "ping_url": "PING_ENDPOINT803f680d-e89b-492b-82ef-2be7b774a92d",
      "update_url": "SITE_ROOT/api/v1/checks/803f680d-e89b-492b-82ef-2be7b774a92d",
      "pause_url": "SITE_ROOT/api/v1/checks/803f680d-e89b-492b-82ef-2be7b774a92d/pause",
      "channels": "1bdea468-03bf-47b8-ab27-29a9dd0e4b94,51c6eb2b-2ae1-456b-99fe-6f1e0a36cd3c",
      "schedule": "15 5 * * *",
      "tz": "UTC"
    }
  ]
}
```

When using the read-only API key, the following fields are omitted:
`ping_url`, `update_url`, `pause_url`, `channels`.  An extra `unique_key` field
is added. This identifier is stable across API calls. Example:

```json
{
  "checks": [
    {
      "name": "Filesystem Backup",
      "tags": "backup fs",
      "desc": "Runs incremental backup every hour",
      "grace": 600,
      "n_pings": 1,
      "status": "up",
      "last_ping": "2020-03-24T14:02:03+00:00",
      "next_ping": "2020-03-24T15:02:03+00:00",
      "unique_key": "a6c7b0a8a66bed0df66abfdab3c77736861703ee",
      "timeout": 3600
    },
    {
      "name": "Database Backup",
      "tags": "production db",
      "desc": "Runs ~/db-backup.sh",
      "grace": 1200,
      "n_pings": 7,
      "status": "down",
      "last_ping": "2020-03-23T10:19:32+00:00",
      "next_ping": null,
      "unique_key": "124f983e0e3dcaeba921cfcef46efd084576e783",
      "schedule": "15 5 * * *",
      "tz": "UTC"
    }
  ]
}
```

## Get a Single Check {: #get-check .rule }
`GET SITE_ROOT/api/v1/checks/<uuid>`

Returns a JSON representation of a single check.

### Response Codes

200 OK
:   The request succeeded.

401 Unauthorized
:   The API key is either missing or invalid.

403 Forbidden
:   Access denied, wrong API key.

404 Not Found
:   The specified check does not exist.


### Example Request

```bash
curl --header "X-Api-Key: your-api-key" SITE_ROOT/api/v1/checks/<uuid>
```

### Example Response

```json
{
  "name": "Database Backup",
  "tags": "production db",
  "desc": "Runs ~/db-backup.sh",
  "grace": 1200,
  "n_pings": 7,
  "status": "down",
  "last_ping": "2020-03-23T10:19:32+00:00",
  "next_ping": null,
  "ping_url": "PING_ENDPOINT803f680d-e89b-492b-82ef-2be7b774a92d",
  "update_url": "SITE_ROOT/api/v1/checks/803f680d-e89b-492b-82ef-2be7b774a92d",
  "pause_url": "SITE_ROOT/api/v1/checks/803f680d-e89b-492b-82ef-2be7b774a92d/pause",
  "channels": "1bdea468-03bf-47b8-ab27-29a9dd0e4b94,51c6eb2b-2ae1-456b-99fe-6f1e0a36cd3c",
  "schedule": "15 5 * * *",
  "tz": "UTC"
}
```

### Example Read-Only Response

When using the read-only API key, the following fields are omitted:
`ping_url`, `update_url`, `pause_url`, `channels`.  An extra `unique_key` field is
added. This identifier is stable across API calls.


Note: the `ping_url`, `update_url` and `pause_url` fields, although omitted, are not
really secret. The client already knows the check's unique UUID and so can easily
construct these URLs by itself.

```json
{
  "name": "Database Backup",
  "tags": "production db",
  "desc": "Runs ~/db-backup.sh",
  "grace": 1200,
  "n_pings": 7,
  "status": "down",
  "last_ping": "2020-03-23T10:19:32+00:00",
  "next_ping": null,
  "unique_key": "124f983e0e3dcaeba921cfcef46efd084576e783",
  "schedule": "15 5 * * *",
  "tz": "UTC"
}
```


## Create a Check {: #create-check .rule }
`POST SITE_ROOT/api/v1/checks/`

Creates a new check and returns its ping URL.
All request parameters are optional and will use their default
values if omitted.

This API call can be used to create both "simple" and "cron" checks.
To create a "simple" check, specify the "timeout" parameter.
To create a "cron" check, specify the "schedule" and "tz" parameters.

### Request Parameters

name
:   string, optional, default value: ""

    Name for the new check.

tags
:   string, optional, default value: ""

    A space-delimited list of tags for the new check.
    Example:

    <pre>{"tags": "reports staging"}</pre>

desc
:   string, optional.

    Description for the check.

timeout
:   number, optional, default value: {{ default_timeout }}.

    A number of seconds, the expected period of this check.

    Minimum: 60 (one minute), maximum: 2592000 (30 days).

    Example for 5 minute timeout:

    <pre>{"kind": "simple", "timeout": 300}</pre>

grace
:   number, optional, default value: {{ default_grace }}.

    A number of seconds, the grace period for this check.

    Minimum: 60 (one minute), maximum: 2592000 (30 days).

schedule
:   string, optional, default value: "* * * * *".

    A cron expression defining this check's schedule.

    If you specify both "timeout" and "schedule" parameters, "timeout" will be
    ignored and "schedule" will be used.

    Example for a check running every half-hour:

    <pre>{"schedule": "0,30 * * * *"}</pre>

tz
:   string, optional, default value: "UTC".

    Server's timezone. This setting only has effect in combination with the
    "schedule" paremeter.

    Example:

    <pre>{"tz": "Europe/Riga"}</pre>

channels
:   string, optional

    By default, if a check is created through API, no notification channels
    (integrations) are assigned to it. So, when the check goes up or down, no
    notifications will get sent.

    Set this field to a special value "*" to automatically assign all existing
    integrations.

    To assign specific integrations, use a comma-separated list of integration
    identifiers. Use the [Get a List of Existing Integrations](#list-channels) call to
    look up integration identifiers.

unique
:   array of string values, optional, default value: [].

    Before creating a check, look for existing checks, filtered by fields listed
    in `unique`. If a matching check is found, return it with HTTP status code 200.
    If no matching check is found, proceed as normal: create a check and return it
    with HTTP status code 201.

    The accepted values are: `name`, `tags`, `timeout` and `grace`.

    Example:

    <pre>{"name": "Backups", unique: ["name"]}</pre>

    In this example, if a check named "Backups" exists, it will be returned.
    Otherwise, a new check will be created and returned.

### Response Codes

201 Created
:   The check was successfully created.

200 OK
:   The `unique` parameter was used and an existing check was matched.

400 Bad Request
:   The request is not well-formed, violates schema, or uses invalid
    field values.

401 Unauthorized
:   The API key is either missing or invalid.

403 Forbidden
:   The account's check limit has been reached. For free accounts,
    the limit is 20 checks per account.

### Example Request

```bash
curl SITE_ROOT/api/v1/checks/ \
    --header "X-Api-Key: your-api-key" \
    --data '{"name": "Backups", "tags": "prod www", "timeout": 3600, "grace": 60}'
```

Or, alternatively:

```bash
curl SITE_ROOT/api/v1/checks/ \
    --data '{"api_key": "your-api-key", "name": "Backups", "tags": "prod www", "timeout": 3600, "grace": 60}'
```

### Example Response

```json
{
  "channels": "",
  "desc": "",
  "grace": 60,
  "last_ping": null,
  "n_pings": 0,
  "name": "Backups",
  "next_ping": null,
  "pause_url": "SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "new",
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc",
}
```

## Update an Existing Check {: #update-check .rule }

`POST SITE_ROOT/api/v1/checks/<uuid>`

Updates an existing check. All request parameters are optional. The check is
updated only with the supplied request parameters. If any parameter is omitted,
its value is left unchanged.

### Request Parameters

name
:   string, optional.

    Name for the check.

tags
:   string, optional.

    A space-delimited list of tags for the check.

    Example:

    <pre>{"tags": "reports staging"}</pre>

desc
:   string, optional.

    Description for the check.

timeout
:   number, optional.

    A number of seconds, the expected period of this check.

    Minimum: 60 (one minute), maximum: 2592000 (30 days).

    Example for 5 minute timeout:

    <pre>{"kind": "simple", "timeout": 300}</pre>

grace
:   number, optional.

    A number of seconds, the grace period for this check.

    Minimum: 60 (one minute), maximum: 2592000 (30 days).

schedule
:   string, optional.

    A cron expression defining this check's schedule.

    If you specify both "timeout" and "schedule" parameters, "timeout" will be
    ignored and "schedule" will be used.

    Example for a check running every half-hour:

    <pre>{"schedule": "0,30 * * * *"}</pre>

tz
:   string, optional.

    Server's timezone. This setting only has effect in combination with the
    "schedule" paremeter.

    Example:

    <pre>{"tz": "Europe/Riga"}</pre>

channels
:   string, optional.

    Set this field to a special value "*" to automatically assign all existing
    notification channels.

    Set this field to a special value "" (empty string) to automatically *unassign*
    all notification channels.

    Set this field to a comma-separated list of channel identifiers to assign
    specific notification channels.

    Example:

    <pre>{"channels": "4ec5a071-2d08-4baa-898a-eb4eb3cd6941,746a083e-f542-4554-be1a-707ce16d3acc"}</pre>


### Response Codes

200 OK
:   The check was successfully updated.

400 Bad Request
:   The request is not well-formed, violates schema, or uses invalid
    field values.

401 Unauthorized
:   The API key is either missing or invalid.

403 Forbidden
:   Access denied, wrong API key.

404 Not Found
:   The specified check does not exist.


### Example Request

```bash
curl SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc \
    --header "X-Api-Key: your-api-key" \
    --data '{"name": "Backups", "tags": "prod www", "timeout": 3600, "grace": 60}'
```

Or, alternatively:

```bash
curl SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc \
    --data '{"api_key": "your-api-key", "name": "Backups", "tags": "prod www", "timeout": 3600, "grace": 60}'
```

### Example Response

```json
{
  "channels": "",
  "desc": "",
  "grace": 60,
  "last_ping": null,
  "n_pings": 0,
  "name": "Backups",
  "next_ping": null,
  "pause_url": "SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "new",
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc",
}
```

## Pause Monitoring of a Check {: #pause-check .rule }

`POST SITE_ROOT/api/v1/checks/<uuid>/pause`

Disables monitoring for a check, without removing it. The check goes into a "paused"
state. You can resume monitoring of the check by pinging it.

This API call has no request parameters.

### Response Codes

200 OK
:   The check was successfully paused.

401 Unauthorized
:   The API key is either missing or invalid.

403 Forbidden
:   Access denied, wrong API key.

404 Not Found
:   The specified check does not exist.

### Example Request

```bash
curl SITE_ROOT/api/v1/checks/0c8983c9-9d73-446f-adb5-0641fdacc9d4/pause \
    --request POST --header "X-Api-Key: your-api-key" --data ""
```

Note: the `--data ""` argument forces curl to send a `Content-Length` request header
even though the request body is empty. For HTTP POST requests, the `Content-Length`
header is sometimes required by some network proxies and web servers.

### Example Response

```json
{
  "channels": "",
  "desc": "",
  "grace": 60,
  "last_ping": null,
  "n_pings": 0,
  "name": "Backups",
  "next_ping": null,
  "pause_url": "SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "paused",
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc"
}
```

## Delete Check {: #delete-check .rule }

`DELETE SITE_ROOT/api/v1/checks/<uuid>`

Permanently deletes the check from user's account. Returns JSON representation of the
check that was just deleted.

This API call has no request parameters.

### Response Codes

200 OK
:   The check was successfully deleted.

401 Unauthorized
:   The API key is either missing or invalid.

403 Forbidden
:   Access denied, wrong API key.

404 Not Found
:   The specified check does not exist.

### Example Request

```bash
curl SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc \
    --request DELETE --header "X-Api-Key: your-api-key"
```

### Example Response

```json
{
  "channels": "",
  "desc": "",
  "grace": 60,
  "last_ping": null,
  "n_pings": 0,
  "name": "Backups",
  "next_ping": null,
  "pause_url": "SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "new",
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v1/checks/f618072a-7bde-4eee-af63-71a77c5723bc",
}
```

## Get a List of Existing Integrations {: #list-channels .rule }

`GET SITE_ROOT/api/v1/channels/`

Returns a list of integrations belonging to the user.

### Response Codes

200 OK
:   The request succeeded.

401 Unauthorized
:   The API key is either missing or invalid.

### Example Request

```bash
curl --header "X-Api-Key: your-api-key" SITE_ROOT/api/v1/channels/
```

### Example Response

```json
{
  "channels": [
    {
      "id": "4ec5a071-2d08-4baa-898a-eb4eb3cd6941",
      "name": "My Work Email",
      "kind": "email"
    },
    {
      "id": "746a083e-f542-4554-be1a-707ce16d3acc",
      "name": "My Phone",
      "kind": "sms"
    }
  ]
}
```
