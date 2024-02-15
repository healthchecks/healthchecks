# Management API v3

Version:
<select onchange="document.location = this.value">
    <option value="../apiv1/">v1</option>
    <option value="../apiv2/">v2</option>
    <option value="../api/" selected>v3</option>
</select>

With the Management API, you can programmatically manage checks and integrations
in your account.

## API Endpoints

<div id="api-toc"></div>

Endpoint Name                                         | Endpoint Address
------------------------------------------------------|-----------------
**Checks**                                            |
[List existing checks](#list-checks)                  | `GET SITE_ROOT/api/v3/checks/`
[Get a single check](#get-check)                      | `GET SITE_ROOT/api/v3/checks/<uuid>`<br>`GET SITE_ROOT/api/v3/checks/<unique_key>`
[Create a new check](#create-check)                   | `POST SITE_ROOT/api/v3/checks/`
[Update an existing check](#update-check)             | `POST SITE_ROOT/api/v3/checks/<uuid>`
[Pause monitoring of a check](#pause-check)           | `POST SITE_ROOT/api/v3/checks/<uuid>/pause`
[Resume monitoring of a check](#resume-check)         | `POST SITE_ROOT/api/v3/checks/<uuid>/resume`
[Delete check](#delete-check)                         | `DELETE SITE_ROOT/api/v3/checks/<uuid>`
**Pings**                                             |
[List check's logged pings](#list-pings)              | `GET SITE_ROOT/api/v3/checks/<uuid>/pings/`
[Get a ping's logged body](#ping-body)                | `GET SITE_ROOT/api/v3/checks/<uuid>/pings/<n>/body`
**Flips**                                             |
[List check's status changes](#list-flips)            | `GET SITE_ROOT/api/v3/checks/<uuid>/flips/`<br>`GET SITE_ROOT/api/v3/checks/<unique_key>/flips/`
**Integrations**                                      |
[List existing integrations](#list-channels)          | `GET SITE_ROOT/api/v3/channels/`
**Badges**                                            |
[List project's badges](#list-badges)                 | `GET SITE_ROOT/api/v3/badges/`
**Service status**                                    |
[Check database connectivity](#status)                | `GET SITE_ROOT/api/v3/status/`

## Changes From v2

Management API v3 adds the ability to specify custom check slugs, instead of
auto-generating them from check names. The [Create a new check](#create-check)
and [Update an existing check](#update-check) calls accept a new `slug`
parameter, and use it instead of generating the slug from the check's name.

## Authentication

Your requests to SITE_NAME Management API must authenticate using an
API key. All API keys are project-specific. There are no account-wide API keys.
By default, a project on SITE_NAME doesn't have an API key. You can create read-write
and read-only API keys on the **Project Settings** page.

read-write key
:   Has full access to all documented API endpoints.

read-only key
:   Only works with the following API endpoints:

    * [List existing checks](#list-checks)
    * [Get a single check](#get-check)
    * [List check's status changes](#list-flips)
    * [List project's badges](#list-badges)

    Omits sensitive information from the API responses. See the documentation of
    individual API endpoints for details.

The client can authenticate itself by including an `X-Api-Key: <your-api-key>`
header in an HTTP request. Alternatively, for POST requests with a JSON request body,
the client can put an `api_key` field in the JSON document.
See the [Create a new check](#create-check) section for an example.

## API Requests

For POST requests, the SITE_NAME API expects the request body to be
a JSON document (*not* a `multipart/form-data` encoded form data).

## API Responses

SITE_NAME uses HTTP status codes wherever possible.
In general, 2xx class indicates success, 4xx indicates a client error,
and 5xx indicates a server error.

The response may contain a JSON document with additional data.

## List Existing Checks {: #list-checks .rule }

`GET SITE_ROOT/api/v3/checks/`

Returns a list of checks belonging to the user, optionally filtered by
one or more tags.

### Query Parameters

slug=&lt;value&gt;
:   Filters the checks and returns only the checks with the specified slug.
    If there are no matching checks, returns an empty list. If there are
    multiple matching checks, returns all of them.

    Example:

    `SITE_ROOT/api/v3/checks/?slug=backups`

tag=&lt;value&gt;
:   Filters the checks and returns only the checks that are tagged with the
    specified value.

    This parameter can be repeated multiple times.

    Example:

    `SITE_ROOT/api/v3/checks/?tag=foo&tag=bar`

### Response Codes

200 OK
:   The request succeeded.

401 Unauthorized
:   The API key is either missing or invalid.

### Example Request

```bash
curl --header "X-Api-Key: your-api-key" SITE_ROOT/api/v3/checks/
```

### Example Response

```json
{
  "checks": [
    {
      "name": "Filesystem Backup",
      "slug": "filesystem-backup",
      "tags": "backup fs",
      "desc": "Runs incremental backup every hour",
      "grace": 600,
      "n_pings": 1,
      "status": "up",
      "started": false,
      "last_ping": "2020-03-24T14:02:03+00:00",
      "next_ping": "2020-03-24T15:02:03+00:00",
      "manual_resume": false,
      "methods": "",
      "start_kw": "START",
      "success_kw": "SUCCESS",
      "failure_kw": "ERROR",
      "filter_subject": true,
      "filter_body": false,
      "ping_url": "PING_ENDPOINT31365bce-8da9-4729-8ff3-aaa71d56b712",
      "update_url": "SITE_ROOT/api/v3/checks/31365bce-8da9-4729-8ff3-aaa71d56b712",
      "pause_url": "SITE_ROOT/api/v3/checks/31365bce-8da9-4729-8ff3-aaa71d56b712/pause",
      "resume_url": "SITE_ROOT/api/v3/checks/31365bce-8da9-4729-8ff3-aaa71d56b712/resume",
      "channels": "1bdea468-03bf-47b8-ab27-29a9dd0e4b94,51c6eb2b-2ae1-456b-99fe-6f1e0a36cd3c",
      "timeout": 3600
    },
    {
      "name": "Database Backup",
      "slug": "database-backup",
      "tags": "production db",
      "desc": "Runs ~/db-backup.sh",
      "grace": 1200,
      "n_pings": 7,
      "status": "down",
      "started": false,
      "last_ping": "2020-03-23T10:19:32+00:00",
      "next_ping": null,
      "manual_resume": false,
      "methods": "",
      "start_kw": "",
      "success_kw": "",
      "failure_kw": "",
      "filter_subject": false,
      "filter_body": false,
      "ping_url": "PING_ENDPOINT803f680d-e89b-492b-82ef-2be7b774a92d",
      "update_url": "SITE_ROOT/api/v3/checks/803f680d-e89b-492b-82ef-2be7b774a92d",
      "pause_url": "SITE_ROOT/api/v3/checks/803f680d-e89b-492b-82ef-2be7b774a92d/pause",
      "resume_url": "SITE_ROOT/api/v3/checks/803f680d-e89b-492b-82ef-2be7b774a92d/resume",
      "channels": "1bdea468-03bf-47b8-ab27-29a9dd0e4b94,51c6eb2b-2ae1-456b-99fe-6f1e0a36cd3c",
      "schedule": "15 5 * * *",
      "tz": "UTC"
    }
  ]
}
```

The possible values for the `status` field are: `new`, `up`, `grace`, `down`,
and `paused`.

When using the read-only API key, SITE_NAME omits the following fields from responses:
`ping_url`, `update_url`, `pause_url`, `resume_url`, `channels`.  It adds an extra
`unique_key` field. The `unique_key` identifier is stable across API calls, and
you can use it in the [Get a single check](#get-check)
and [List check's status changes](#list-flips) API calls.

Example:

```json
{
  "checks": [
    {
      "name": "Filesystem Backup",
      "slug": "filesystem-backup",
      "tags": "backup fs",
      "desc": "Runs incremental backup every hour",
      "grace": 600,
      "n_pings": 1,
      "status": "up",
      "started": false,
      "last_ping": "2020-03-24T14:02:03+00:00",
      "next_ping": "2020-03-24T15:02:03+00:00",
      "manual_resume": false,
      "methods": "",
      "start_kw": "START",
      "success_kw": "SUCCESS",
      "failure_kw": "ERROR",
      "filter_subject": true,
      "filter_body": false,
      "unique_key": "a6c7b0a8a66bed0df66abfdab3c77736861703ee",
      "timeout": 3600
    },
    {
      "name": "Database Backup",
      "slug": "database-backup",
      "tags": "production db",
      "desc": "Runs ~/db-backup.sh",
      "grace": 1200,
      "n_pings": 7,
      "status": "down",
      "started": false,
      "last_ping": "2020-03-23T10:19:32+00:00",
      "next_ping": null,
      "manual_resume": false,
      "methods": "",
      "start_kw": "",
      "success_kw": "",
      "failure_kw": "",
      "filter_subject": false,
      "filter_body": false,
      "unique_key": "124f983e0e3dcaeba921cfcef46efd084576e783",
      "schedule": "15 5 * * *",
      "tz": "UTC"
    }
  ]
}
```

## Get a Single Check {: #get-check .rule }
`GET SITE_ROOT/api/v3/checks/<uuid>`<br>
`GET SITE_ROOT/api/v3/checks/<unique_key>`

Returns a JSON representation of a single check. Accepts either check's UUID or
the `unique_key` (a field derived from UUID and returned by API responses when
using the read-only API key) as an identifier.

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
curl --header "X-Api-Key: your-api-key" SITE_ROOT/api/v3/checks/<uuid>
```

### Example Response

```json
{
  "name": "Database Backup",
  "slug": "database-backup",
  "tags": "production db",
  "desc": "Runs ~/db-backup.sh",
  "grace": 1200,
  "n_pings": 7,
  "status": "down",
  "started": false,
  "last_ping": "2020-03-23T10:19:32+00:00",
  "next_ping": null,
  "manual_resume": false,
  "methods": "",
  "start_kw": "START",
  "success_kw": "SUCCESS",
  "failure_kw": "ERROR",
  "filter_subject": true,
  "filter_body": false,
  "ping_url": "PING_ENDPOINT803f680d-e89b-492b-82ef-2be7b774a92d",
  "update_url": "SITE_ROOT/api/v3/checks/803f680d-e89b-492b-82ef-2be7b774a92d",
  "pause_url": "SITE_ROOT/api/v3/checks/803f680d-e89b-492b-82ef-2be7b774a92d/pause",
  "resume_url": "SITE_ROOT/api/v3/checks/803f680d-e89b-492b-82ef-2be7b774a92d/resume",
  "channels": "1bdea468-03bf-47b8-ab27-29a9dd0e4b94,51c6eb2b-2ae1-456b-99fe-6f1e0a36cd3c",
  "schedule": "15 5 * * *",
  "tz": "UTC"
}
```

The possible values for the `status` field are: `new`, `up`, `grace`, `down`,
and `paused`.

### Example Read-Only Response

When using the read-only API key, SITE_NAME omits the following fields from responses:
`ping_url`, `update_url`, `pause_url`, `resume_url`, `channels`.  It adds an extra
`unique_key` field. This identifier is stable across API calls.

Note: although API omits the `*_url` fields in read-only API responses, the client can
easily construct these URLs themselves *if* they know the check's unique UUID.

```json
{
  "name": "Database Backup",
  "slug": "database-backup",
  "tags": "production db",
  "desc": "Runs ~/db-backup.sh",
  "grace": 1200,
  "n_pings": 7,
  "status": "down",
  "started": false,
  "last_ping": "2020-03-23T10:19:32+00:00",
  "next_ping": null,
  "manual_resume": false,
  "methods": "",
  "start_kw": "SUCCESS",
  "success_kw": "SUCCESS",
  "failure_kw": "ERROR",
  "filter_subject": true,
  "filter_body": false,
  "unique_key": "124f983e0e3dcaeba921cfcef46efd084576e783",
  "schedule": "15 5 * * *",
  "tz": "UTC"
}
```


## Create a Check {: #create-check .rule }
`POST SITE_ROOT/api/v3/checks/`

Creates a new check and returns its ping URL.
All request parameters are optional and will use their default
values if omitted.

With this API call, you can create both Simple and Cron checks:

* To create a Simple check, specify the `timeout` parameter.
* To create a Cron check, specify the `schedule` and `tz` parameters.

### Request Parameters

name
:   string, optional, default value: ""

    Name for the new check.

    Changed in API v3: the check's slug is no longer automatically generated
    from the check's name. Instead, the client can specify the slug explicitly
    via the `slug` field.

slug
:   string, optional, default value: ""

    Slug for the new check. The slug should only contain the following
    characters: `a-z`, `0-9`, hyphens, underscores. Example:

    <pre>{"slug": "my-custom-slug"}</pre>

tags
:   string, optional, default value: ""

    A space-delimited list of tags for the new check.
    Example:

    <pre>{"tags": "reports staging"}</pre>

desc
:   string, optional.

    Description of the check.

timeout
:   number, optional, default value: {{ default_timeout }}.

    The expected period of this check in seconds.

    Minimum: 60 (one minute), maximum: 31536000 (365 days).

    Example for a 5-minute timeout:

    <pre>{"timeout": 300}</pre>

grace
:   number, optional, default value: {{ default_grace }}.

    The grace period for this check in seconds.

    Minimum: 60 (one minute), maximum: 31536000 (365 days).

schedule
:   string, optional.

    A cron or systemd OnCalendar expression defining this check's schedule.
    SITE_NAME will detect the expression type (cron or OnCalendar) automatically.

    The `schedule` parameter takes precedence over the `timeout` field: if you specify
    both the `timeout` and the `schedule` parameters, SITE_NAME will save the
    `schedule` and ignore the `timeout`.

    Example using a cron expression ("run every half-hour"):

    <pre>{"schedule": "0,30 * * * *"}</pre>

    Example using an OnCalendar expression ("run at 12:00 of the last day of every
    month"):

    <pre>{"schedule": "\*-\*~1 12:00"}</pre>

tz
:   string, optional, default value: "UTC".

    Server's timezone. This setting only has an effect in combination with the
    `schedule` parameter.

    Example:

    <pre>{"tz": "Europe/Riga"}</pre>

manual_resume
:   boolean, optional, default value: false.

    Controls whether a paused check automatically resumes when pinged (the default)
    or not. If set to false, a paused check will leave the paused state when it receives
    a ping. If set to true, a paused check will ignore pings and stay paused until
    you manually resume it from the web dashboard.

methods
:   string, optional, default value: "".

    Specifies the allowed HTTP methods for making ping requests.
    Must be one of the two values: "" (an empty string) or "POST".

    Set this field to "" (an empty string) to allow HEAD, GET,
    and POST requests.

    Set this field to "POST" to allow only POST requests.

    Example:

    <pre>{"methods": "POST"}</pre>

channels
:   string, optional.

    By default, this API call assigns no integrations to the newly created
    check.

    Set this field to a special value "*" to automatically assign all existing
    integrations. Example:

    <pre>{"channels": "*"}</pre>

    To assign specific integrations, use a comma-separated list of integration
    UUIDs. You can look up integration UUIDs using the
    [List Existing Integrations](#list-channels) API call.

    Example:

    <pre>{"channels":
     "4ec5a071-2d08-4baa-898a-eb4eb3cd6941,746a083e-f542-4554-be1a-707ce16d3acc"}</pre>

    Alternatively, if you have named your integrations in SITE_NAME dashboard,
    you can specify integrations by their names. For this to work, your integrations
    need non-empty unique names, and they must not contain commas.
    The names must match exactly, whitespace is significant.

    Example:

    <pre>{"channels": "Email to Alice,SMS to Alice"}</pre>

unique
:   array of string values, optional, default value: [].

    Enables "upsert" functionality. Before creating a check, SITE_NAME looks for
    existing checks, filtered by fields listed in `unique`.

    If SITE_NAME does not find a matching check, it creates a new check and returns it
    with the HTTP status code 201.

    If SITE_NAME finds a matching check, it updates the existing check and
    returns it with HTTP status code 200.

    The accepted values for the `unique` field are
    `name`, `slug`, `tags`, `timeout`, and `grace`.

    Example:

    <pre>{"name": "Backups", unique: ["name"]}</pre>

    In this example, if a check named "Backups" exists, it will be returned.
    Otherwise, a new check will be created and returned.

start_kw
:   string, optional, default value: "".

    Specifies the keywords for classifying inbound email messages as "Start" signals.
    Separate multiple keywords using commas.

    Use this field in combination with the `filter_subject` and `filter_body` fields.
    Setting `filter_subject` to `true` enables filtering on the email subject line,
    `filter_body` enables filtering on the entire email body. SITE_NAME supports both
    plain text and HTML email messages.

    Example:

    <pre>{"filter_subject": true, "start_kw": "STARTED"}</pre>

    In this example, SITE_NAME classifies the email as a start signal if the Subject
    line contains the word "STARTED".

success_kw
:   string, optional, default value: "".

    Specifies the keywords for classifying inbound email messages as "Success" signals.
    Separate multiple keywords using commas.

    Use this field in combination with the `filter_subject` and `filter_body` fields.
    Setting `filter_subject` to `true` enables filtering on the email subject line,
    `filter_body` enables filtering on the entire email body. SITE_NAME supports both
    plain text and HTML email messages.

    Example:

    <pre>{"filter_subject": true, "success_kw": "SUCCESS,COMPLETED"}</pre>

    In this example, the email counts as success if the Subject line contains either
    the word "SUCCESS" or the word "COMPLETED".

failure_kw
:   string, optional, default value: "".

    Specifies the keywords for classifying inbound email messages as "Failure" signals.
    Separate multiple keywords using commas.

    Use this field in combination with the `filter_subject` and `filter_body` fields.
    Setting `filter_subject` to `true` enables filtering on the email subject line,
    `filter_body` enables filtering on the entire email body. SITE_NAME supports both
    plain text and HTML email messages.

    Example:

    <pre>{"filter_subject": true, "failure_kw": "FAILED, ERROR"}</pre>

    In this example, the email counts as failure if the Subject line contains either
    the word "FAILED" or the word "ERROR".

filter_subject
:   boolean, optional, default value: false.

    Enables filtering of inbound email messages by looking for keywords in their
    subject lines. See also the `success_kw` and `failure_kw` fields.

filter_body
:   boolean, optional, default value: false.

    Enables filtering of inbound email messages by looking for keywords in their
    message body. See also the `success_kw` and `failure_kw` fields.

subject
:   string, optional, default value: "".

    **Deprecated**. Use the `success_kw`, `filter_subject` and `filter_body` fields
    instead.

    Specifies the keywords for classifying inbound email messages as "Success" signals.
    Separate multiple keywords using commas. If any of the keywords is found in
    an email message's Subject line, the email message will count as "Success".

    Set this field to "" (an empty string) to consider all inbound email messages as
    "Success" (unless they match any keywords listed in `subject_fail` and are thus
    classified as "Failure").

    Example:

    <pre>SUCCESS,COMPLETED</pre>

    In this example, the email counts as success if the Subject line contains either
    the word "SUCCESS" or the word "COMPLETED".

subject_fail
:   string, optional, default value: "".

    **Deprecated**. Use the `failure_kw`, `filter_subject` and `filter_body` fields
    instead.

    Specifies the keywords for classifying inbound email messages as "Failure" signals.
    Separate multiple keywords using commas. If any of the keywords is found in
    an email message's Subject line, the email message will count as "Failure".

    Set this field to "" (an empty string) to perform no "Failure" classification.

    Example:

    <pre>FAILED,ERROR</pre>

    In this example, the email counts as failure if the Subject line contains either
    the word "FAILED" or the word "ERROR".

### Response Codes

201 Created
:   A new check was successfully created.

200 OK
:   An existing check was found and updated.

400 Bad Request
:   The request is not well-formed, violates schema, or uses invalid
    field values.

401 Unauthorized
:   The API key is either missing or invalid.

403 Forbidden
:   The account has hit its check limit. For free accounts,
    the limit is 20 checks per account.

### Example Request

```bash
curl SITE_ROOT/api/v3/checks/ \
    --header "X-Api-Key: your-api-key" \
    --data '{"name": "Backups", "tags": "prod www", "timeout": 3600, "grace": 60}'
```

Or, alternatively:

```bash
curl SITE_ROOT/api/v3/checks/ \
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
  "slug": "",
  "next_ping": null,
  "manual_resume": false,
  "methods": "",
  "start_kw": "",
  "success_kw": "",
  "failure_kw": "",
  "filter_subject": false,
  "filter_body": false,
  "pause_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "resume_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/resume",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "new",
  "started": false,
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc",
}
```

## Update an Existing Check {: #update-check .rule }

`POST SITE_ROOT/api/v3/checks/<uuid>`

Updates an existing check. All request parameters are optional. If you omit any
parameter, SITE_NAME will leave its value unchanged.

### Request Parameters

name
:   string, optional.

    Name for the check.

    Changed in API v3: the check's slug is no longer automatically generated
    from the check's name. Instead, the client can specify the slug explicitly
    via the `slug` field.

slug
:   string, optional

    Slug for the new check. The slug should only contain the following
    characters: `a-z`, `0-9`, hyphens, underscores. Example:

    <pre>{"slug": "my-custom-slug"}</pre>

tags
:   string, optional.

    A space-delimited list of tags for the check.

    Example:

    <pre>{"tags": "reports staging"}</pre>

desc
:   string, optional.

    Description of the check.

timeout
:   number, optional.

    The expected period of this check in seconds.

    Minimum: 60 (one minute), maximum: 31536000 (365 days).

    Example for a 5-minute timeout:

    <pre>{"timeout": 300}</pre>

grace
:   number, optional.

    The grace period for this check in seconds.

    Minimum: 60 (one minute), maximum: 31536000 (365 days).

schedule
:   string, optional.

    A cron or systemd OnCalendar expression defining this check's schedule.
    SITE_NAME will detect the expression type (cron or OnCalendar) automatically.

    The `schedule` parameter takes precedence over the `timeout` field: If you specify
    both the `timeout` and the `schedule` parameters, SITE_NAME will save the
    `schedule` and ignore the `timeout`.

    Example using a cron expression ("run every half-hour"):

    <pre>{"schedule": "0,30 * * * *"}</pre>

    Example using an OnCalendar expression ("run at 12:00 of the last day of every
    month"):

    <pre>{"schedule": "\*-\*~1 12:00"}</pre>

 tz
:   string, optional.

    Server's timezone. This setting only has an effect in combination with the
    "schedule" parameter.

    Example:

    <pre>{"tz": "Europe/Riga"}</pre>

manual_resume
:   boolean, optional, default value: false.

    Controls whether a paused ping automatically resumes when pinged (the default),
    or not. If set to false, a paused check will leave the paused state when it receives
    a ping. If set to true, a paused check will ignore pings and stay paused until
    you manually resume it from the web dashboard.

methods
:   string, optional, default value: "".

    Specifies the allowed HTTP methods for making ping requests.
    Must be one of the two values: "" (an empty string) or "POST".

    Set this field to "" (an empty string) to allow HEAD, GET,
    and POST requests.

    Set this field to "POST" to allow only POST requests.

    Example:

    <pre>{"methods": "POST"}</pre>

channels
:   string, optional.

    Set this field to a special value "*" to automatically assign all existing
    integrations. Example:

    <pre>{"channels": "*"}</pre>

    Set this field to a special value "" (empty string) to automatically *unassign*
    all existing integrations. Example:

    <pre>{"channels": ""}</pre>

    To assign specific integrations, use a comma-separated list of integration
    UUIDs. You can look up integration UUIDs using the
    [List Existing Integrations](#list-channels) API call.

    Example:

    <pre>{"channels":
     "4ec5a071-2d08-4baa-898a-eb4eb3cd6941,746a083e-f542-4554-be1a-707ce16d3acc"}</pre>

    Alternatively, if you have named your integrations in SITE_NAME dashboard,
    you can specify integrations by their names. For this to work, your integrations
    need non-empty and unique names, and they must not contain commas. The names
    must match exactly, whitespace is significant.

    Example:

    <pre>{"channels": "Email to Alice,SMS to Alice"}</pre>

start_kw
:   string, optional, default value: "".

    Specifies the keywords for classifying inbound email messages as "Start" signals.
    Separate multiple keywords using commas.

    Use this field in combination with the `filter_subject` and `filter_body` fields.
    Setting `filter_subject` to `true` enables filtering on the email subject line,
    `filter_body` enables filtering on the entire email body. SITE_NAME supports both
    plain text and HTML email messages.

    Example:

    <pre>{"filter_subject": true, "start_kw": "STARTED"}</pre>

    In this example, SITE_NAME classifies the email as a start signal if the Subject
    line contains the word "STARTED".

success_kw
:   string, optional, default value: "".

    Specifies the keywords for classifying inbound email messages as "Success" signals.
    Separate multiple keywords using commas.

    Use this field in combination with the `filter_subject` and `filter_body` fields.
    Setting `filter_subject` to `true` enables filtering on the email subject line,
    `filter_body` enables filtering on the entire email body. SITE_NAME supports both
    plain text and HTML email messages.

    Example:

    <pre>{"filter_subject": true, "success_kw": "SUCCESS,COMPLETED"}</pre>

    In this example, the email counts as success if the Subject line contains either
    the word "SUCCESS" or the word "COMPLETED".

failure_kw
:   string, optional, default value: "".

    Specifies the keywords for classifying inbound email messages as "Failure" signals.
    Separate multiple keywords using commas.

    Use this field in combination with the `filter_subject` and `filter_body` fields.
    Setting `filter_subject` to `true` enables filtering on the email subject line,
    `filter_body` enables filtering on the entire email body. SITE_NAME supports both
    plain text and HTML email messages.

    Example:

    <pre>{"filter_subject": true, "failure_kw": "FAILED, ERROR"}</pre>

    In this example, the email counts as failure if the Subject line contains either
    the word "FAILED" or the word "ERROR".

filter_subject
:   boolean, optional, default value: false.

    Enables filtering of inbound email messages by looking for keywords in their
    subject lines. See also the `success_kw` and `failure_kw` fields.

filter_body
:   boolean, optional, default value: false.

    Enables filtering of inbound email messages by looking for keywords in their
    message body. See also the `success_kw` and `failure_kw` fields.

subject
:   string, optional, default value: "".

    **Deprecated**. Use the `success_kw`, `filter_subject` and `filter_body` fields
    instead.

    Specifies the keywords for classifying inbound email messages as "Success" signals.
    Separate multiple keywords using commas. If any of the keywords is found in
    an email message's Subject line, the email message will count as "Success".

    Set this field to "" (an empty string) to consider all inbound email messages as
    "Success" (unless they match any keywords listed in `subject_fail` and are thus
    classified as "Failure").

    Example:

    <pre>SUCCESS,COMPLETED</pre>

    In this example, the email counts as success if the Subject line contains either
    the word "SUCCESS" or the word "COMPLETED".

subject_fail
:   string, optional, default value: "".

    **Deprecated**. Use the `failure_kw`, `filter_subject` and `filter_body` fields
    instead.

    Specifies the keywords for classifying inbound email messages as "Failure" signals.
    Separate multiple keywords using commas. If any of the keywords is found in
    an email message's Subject line, the email message will count as "Failure".

    Set this field to "" (an empty string) to perform no "Failure" classification.

    Example:

    <pre>FAILED,ERROR</pre>

    In this example, the email counts as failure if the Subject line contains either
    the word "FAILED" or the word "ERROR".

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
curl SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc \
    --header "X-Api-Key: your-api-key" \
    --data '{"name": "Backups", "tags": "prod www", "timeout": 3600, "grace": 60}'
```

Or, alternatively:

```bash
curl SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc \
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
  "slug": "",
  "next_ping": null,
  "manual_resume": false,
  "methods": "",
  "start_kw": "",
  "success_kw": "",
  "failure_kw": "",
  "filter_subject": false,
  "filter_body": false,
  "pause_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "resume_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/resume",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "new",
  "started": false,
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc",
}
```

## Pause Monitoring of a Check {: #pause-check .rule }

`POST SITE_ROOT/api/v3/checks/<uuid>/pause`

Disables monitoring for a check without removing it. The check goes into a "paused"
state. You can resume monitoring of the check by pinging it, or by running
the [Resume](#resume-check) API call (useful when check's `manual_resume=True`).

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
curl SITE_ROOT/api/v3/checks/0c8983c9-9d73-446f-adb5-0641fdacc9d4/pause \
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
  "next_ping": null,
  "n_pings": 0,
  "name": "Backups",
  "slug": "backups",
  "next_ping": null,
  "manual_resume": false,
  "methods": "",
  "start_kw": "",
  "success_kw": "",
  "failure_kw": "",
  "filter_subject": false,
  "filter_body": false,
  "pause_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "resume_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/resume",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "paused",
  "started": false,
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc"
}
```

## Resume Monitoring of a Check {: #resume-check .rule }

`POST SITE_ROOT/api/v3/checks/<uuid>/resume`

Resumes a check. The check goes into the "new" state. Use this API call to resume
the monitoring of checks that are in the paused state, and have the `manual_resume`
configuration parameter set to `True`.

This API call has no request parameters.

### Response Codes

200 OK
:   The operation was successful.

401 Unauthorized
:   The API key is either missing or invalid.

403 Forbidden
:   Access denied, wrong API key.

404 Not Found
:   The specified check does not exist.

409 Conflict
:   The specified check is currently not in a paused state.

### Example Request

```bash
curl SITE_ROOT/api/v3/checks/0c8983c9-9d73-446f-adb5-0641fdacc9d4/resume \
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
  "next_ping": null,
  "n_pings": 0,
  "name": "Backups",
  "slug": "backups",
  "next_ping": null,
  "manual_resume": false,
  "methods": "",
  "start_kw": "",
  "success_kw": "",
  "failure_kw": "",
  "filter_subject": false,
  "filter_body": false,
  "pause_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "resume_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/resume",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "new",
  "started": false,
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc"
}
```


## Delete Check {: #delete-check .rule }

`DELETE SITE_ROOT/api/v3/checks/<uuid>`

Permanently deletes the check from the user's account. Returns JSON representation of the
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
curl SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc \
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
  "slug": "backups",
  "next_ping": null,
  "manual_resume": false,
  "methods": "",
  "start_kw": "",
  "success_kw": "",
  "failure_kw": "",
  "filter_subject": false,
  "filter_body": false,
  "pause_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pause",
  "resume_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/resume",
  "ping_url": "PING_ENDPOINTf618072a-7bde-4eee-af63-71a77c5723bc",
  "status": "new",
  "started": false,
  "tags": "prod www",
  "timeout": 3600,
  "update_url": "SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc",
}
```

## List check's logged pings {: #list-pings .rule }

`GET SITE_ROOT/api/v3/checks/<uuid>/pings/`

Returns a list of pings this check has received.

This endpoint returns pings in reverse order (most recent first), and the total
number of returned pings depends on the account's billing plan: 100 for free accounts,
1000 for paid accounts.

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
curl SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pings/ \
    --header "X-Api-Key: your-api-key"
```

### Example Response

```json
{
  "pings": [
    {
      "type": "success",
      "date": "2020-06-09T14:51:06.113073+00:00",
      "n": 4,
      "scheme": "http",
      "remote_addr": "192.0.2.0",
      "method": "GET",
      "ua": "curl/7.68.0",
      "rid": "123e4567-e89b-12d3-a456-426614174000",
      "duration": 2.896736,
      "body_url": null
    },
    {
      "type": "start",
      "date": "2020-06-09T14:51:03.216337+00:00",
      "n": 3,
      "scheme": "http",
      "remote_addr": "192.0.2.0",
      "method": "GET",
      "ua": "curl/7.68.0",
      "rid": "123e4567-e89b-12d3-a456-426614174000",
      "body_url": null
    },
    {
      "type": "success",
      "date": "2020-06-09T14:50:59.633577+00:00",
      "n": 2,
      "scheme": "http",
      "remote_addr": "192.0.2.0",
      "method": "GET",
      "ua": "curl/7.68.0",
      "rid": null,
      "duration": 2.997976,
      "body_url": null
    },
    {
      "type": "start",
      "date": "2020-06-09T14:50:56.635601+00:00",
      "n": 1,
      "scheme": "http",
      "remote_addr": "192.0.2.0",
      "method": "GET",
      "ua": "curl/7.68.0",
      "rid": null,
      "body_url": null
    }
  ]
}
```


## Get a ping's logged body {: #ping-body .rule }

`GET SITE_ROOT/api/v3/checks/<uuid>/pings/<n>/body`

Returns a ping's logged body. The response always has the `Content-Type: text/plain`
response header and the ping body is returned verbatim in the response body.

### Response Codes

200 OK
:   The request succeeded and a body is present.

403 Forbidden
:   Access denied, wrong API key.

404 Not Found
:   The check does not exist, the ping does not exist, or the ping has no body data.

### Example Request

```bash
curl SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/pings/397/body \
    --header "X-Api-Key: your-api-key"
```

## List check's status changes {: #list-flips .rule }

`GET SITE_ROOT/api/v3/checks/<uuid>/flips/`<br>
`GET SITE_ROOT/api/v3/checks/<unique_key>/flips/`

Returns a list of "flips" this check has experienced. A flip is a change of status
(from "down" to "up," or from "up" to "down").

This API endpoint supports time filtering via the `seconds`, `start`, and `end` query
parameters. If no time filters are specified, the API returns all stored
flips for a given check.

Notes about flip retention: SITE_NAME stores historic flips for the current month
and for two full months prior to the current month. The cleanup of older flips is
[a manual administrative action](../self_hosted/#database-cleanup).
Therefore, SITE_NAME may return even older flips if the server administrator does not
perform regular database cleanups.

### Query Parameters

seconds=&lt;value&gt;
:   Returns the flips from the last `value` seconds

    Example:

    `SITE_ROOT/api/v3/checks/<uuid|unique_key>/flips/?seconds=3600`

start=&lt;value&gt;
:   Returns flips that are newer than the specified UNIX timestamp.

    Example:

    `SITE_ROOT/api/v3/checks/<uuid|unique_key>/flips/?start=1592214380`

end=&lt;value&gt;
:   Returns flips that are older than the specified UNIX timestamp.

    Example:

    `SITE_ROOT/api/v3/checks/<uuid|unique_key>/flips/?end=1592217980`


### Response Codes

200 OK
:   The request succeeded.

400 Bad Request
:   Invalid query parameters.

401 Unauthorized
:   The API key is either missing or invalid.

403 Forbidden
:   Access denied, wrong API key.

404 Not Found
:   The specified check does not exist.

### Example Request

```bash
curl SITE_ROOT/api/v3/checks/f618072a-7bde-4eee-af63-71a77c5723bc/flips/ \
    --header "X-Api-Key: your-api-key"
```

### Example Response

```json
[
    {
      "timestamp": "2020-03-23T10:18:23+00:00",
      "up": 1
    },
    {
      "timestamp": "2020-03-23T10:17:15+00:00",
      "up": 0
    },
    {
      "timestamp": "2020-03-23T10:16:18+00:00",
      "up": 1
    }
]
```

## List Existing Integrations {: #list-channels .rule }

`GET SITE_ROOT/api/v3/channels/`

Returns a list of integrations belonging to the project.

### Response Codes

200 OK
:   The request succeeded.

401 Unauthorized
:   The API key is either missing or invalid.

### Example Request

```bash
curl --header "X-Api-Key: your-api-key" SITE_ROOT/api/v3/channels/
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

## List Project's Badges {: #list-badges .rule }

`GET SITE_ROOT/api/v3/badges/`

Returns a map of all tags in the project, with badge URLs for each tag. SITE_NAME
provides badges in a few different formats:

* `svg`: returns the badge as an SVG document.
* `json`: returns a JSON document which you can use to generate a custom badge
    yourself.
* `shields`: returns JSON in a [Shields.io compatible format](https://shields.io/endpoint).

In addition, badges have 2-state and 3-state variations:

* `svg`, `json`, `shields`: reports two states: "up" and "down". It
    considers any checks in the grace period as still "up".
* `svg3`, `json3`, `shields3`: reports three states: "up", "late", and "down".

The response includes a special `*` entry: this pseudo-tag reports the overall status
of all checks in the project.

### Response Codes

200 OK
:   The request succeeded.

401 Unauthorized
:   The API key is either missing or invalid.

### Example Request

```bash
curl --header "X-Api-Key: your-api-key" SITE_ROOT/api/v3/badges/
```

### Example Response

```json
{
  "badges": {
    "backup": {
      "svg": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/LOegDs5M-2/backup.svg",
      "svg3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/LOegDs5M/backup.svg",
      "json": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/LOegDs5M-2/backup.json",
      "json3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/LOegDs5M/backup.json",
      "shields": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/LOegDs5M-2/backup.shields",
      "shields3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/LOegDs5M/backup.shields"
    },
    "db": {
      "svg": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/99MuQaKm-2/db.svg",
      "svg3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/99MuQaKm/db.svg",
      "json": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/99MuQaKm-2/db.json",
      "json3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/99MuQaKm/db.json",
      "shields": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/99MuQaKm-2/db.shields",
      "shields3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/99MuQaKm/db.shields"
    },
    "prod": {
      "svg": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/1TEhqie8-2/prod.svg",
      "svg3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/1TEhqie8/prod.svg",
      "json": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/1TEhqie8-2/prod.json",
      "json3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/1TEhqie8/prod.json",
      "shields": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/1TEhqie8-2/prod.shields",
      "shields3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/1TEhqie8/prod.shields"
    },
    "*": {
      "svg": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/9X7kcZoe-2.svg",
      "svg3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/9X7kcZoe.svg",
      "json": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/9X7kcZoe-2.json",
      "json3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/9X7kcZoe.json",
      "shields": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/9X7kcZoe-2.shields",
      "shields3": "SITE_ROOT/badge/67541b37-8b9c-4d17-b952-690eae/9X7kcZoe.shields"
    }
  }
}
```

## Check Database Connectivity {: #status .rule }

`GET SITE_ROOT/api/v3/status/`

Runs a test query and returns HTTP 200 if the query completes successfully.
Use this endpoint to monitor the uptime of your Healthchecks instance with an
external uptime monitoring system.

### Response Codes

200 OK
:   The request succeeded.

500 Internal Server Error
:   Test database query did not succeed.
