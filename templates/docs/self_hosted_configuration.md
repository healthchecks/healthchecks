# Server Configuration

Healthchecks prepares its configuration in `hc/settings.py`. It reads configuration
from environment variables. Below is a list of variables it reads and uses.

<ul class="self-hosted-configuration-toc">
<li><a href="#ADMINS">ADMINS</a></li>
<li><a href="#ALLOWED_HOSTS">ALLOWED_HOSTS</a></li>
<li><a href="#APPRISE_ENABLED">APPRISE_ENABLED</a></li>
<li><a href="#DB">DB</a></li>
<li><a href="#DB_CONN_MAX_AGE">DB_CONN_MAX_AGE</a></li>
<li><a href="#DB_HOST">DB_HOST</a></li>
<li><a href="#DB_NAME">DB_NAME</a></li>
<li><a href="#DB_PASSWORD">DB_PASSWORD</a></li>
<li><a href="#DB_PORT">DB_PORT</a></li>
<li><a href="#DB_SSLMODE">DB_SSLMODE</a></li>
<li><a href="#DB_TARGET_SESSION_ATTRS">DB_TARGET_SESSION_ATTRS</a></li>
<li><a href="#DB_USER">DB_USER</a></li>
<li><a href="#DEBUG">DEBUG</a></li>
<li><a href="#DEFAULT_FROM_EMAIL">DEFAULT_FROM_EMAIL</a></li>
<li><a href="#DISCORD_CLIENT_ID">DISCORD_CLIENT_ID</a></li>
<li><a href="#DISCORD_CLIENT_SECRET">DISCORD_CLIENT_SECRET</a></li>
<li><a href="#EMAIL_HOST">EMAIL_HOST</a></li>
<li><a href="#EMAIL_HOST_PASSWORD">EMAIL_HOST_PASSWORD</a></li>
<li><a href="#EMAIL_HOST_USER">EMAIL_HOST_USER</a></li>
<li><a href="#EMAIL_PORT">EMAIL_PORT</a></li>
<li><a href="#EMAIL_USE_TLS">EMAIL_USE_TLS</a></li>
<li><a href="#EMAIL_USE_SSL">EMAIL_USE_SSL</a></li>
<li><a href="#EMAIL_USE_VERIFICATION">EMAIL_USE_VERIFICATION</a></li>
<li><a href="#http_proxy">http_proxy and https_proxy</a></li>
<li><a href="#INTEGRATIONS_ALLOW_PRIVATE_IPS">INTEGRATIONS_ALLOW_PRIVATE_IPS</a></li>
<li><a href="#LINENOTIFY_CLIENT_ID">LINENOTIFY_CLIENT_ID</a></li>
<li><a href="#LINENOTIFY_CLIENT_SECRET">LINENOTIFY_CLIENT_SECRET</a></li>
<li><a href="#MASTER_BADGE_URL">MASTER_BADGE_LABEL</a></li>
<li><a href="#MATRIX_ACCESS_TOKEN">MATRIX_ACCESS_TOKEN</a></li>
<li><a href="#MATRIX_HOMESERVER">MATRIX_HOMESERVER</a></li>
<li><a href="#MATRIX_USER_ID">MATRIX_USER_ID</a></li>
<li><a href="#MATTERMOST_ENABLED">MATTERMOST_ENABLED</a></li>
<li><a href="#MSTEAMS_ENABLED">MSTEAMS_ENABLED</a></li>
<li><a href="#OPSGENIE_ENABLED">OPSGENIE_ENABLED</a></li>
<li><a href="#PAGERTREE_ENABLED">PAGERTREE_ENABLED</a></li>
<li><a href="#PD_APP_ID">PD_APP_ID</a></li>
<li><a href="#PD_ENABLED">PD_ENABLED</a></li>
<li><a href="#PING_BODY_LIMIT">PING_BODY_LIMIT</a></li>
<li><a href="#PING_EMAIL_DOMAIN">PING_EMAIL_DOMAIN</a></li>
<li><a href="#PING_ENDPOINT">PING_ENDPOINT</a></li>
<li><a href="#PROMETHEUS_ENABLED">PROMETHEUS_ENABLED</a></li>
<li><a href="#PUSHBULLET_CLIENT_ID">PUSHBULLET_CLIENT_ID</a></li>
<li><a href="#PUSHBULLET_CLIENT_SECRET">PUSHBULLET_CLIENT_SECRET</a></li>
<li><a href="#PUSHOVER_API_TOKEN">PUSHOVER_API_TOKEN</a></li>
<li><a href="#PUSHOVER_EMERGENCY_EXPIRATION">PUSHOVER_EMERGENCY_EXPIRATION</a></li>
<li><a href="#PUSHOVER_EMERGENCY_RETRY_DELAY">PUSHOVER_EMERGENCY_RETRY_DELAY</a></li>
<li><a href="#PUSHOVER_SUBSCRIPTION_URL">PUSHOVER_SUBSCRIPTION_URL</a></li>
<li><a href="#REGISTRATION_OPEN">REGISTRATION_OPEN</a></li>
<li><a href="#REMOTE_USER_HEADER">REMOTE_USER_HEADER</a></li>
<li><a href="#ROCKETCHAT_ENABLED">ROCKETCHAT_ENABLED</a></li>
<li><a href="#RP_ID">RP_ID</a></li>
<li><a href="#S3_ACCESS_KEY">S3_ACCESS_KEY</a></li>
<li><a href="#S3_BUCKET">S3_BUCKET</a></li>
<li><a href="#S3_ENDPOINT">S3_ENDPOINT</a></li>
<li><a href="#S3_REGION">S3_REGION</a></li>
<li><a href="#S3_SECRET_KEY">S3_SECRET_KEY</a></li>
<li><a href="#S3_TIMEOUT">S3_TIMEOUT</a></li>
<li><a href="#S3_SECURE">S3_SECURE</a></li>
<li><a href="#SECRET_KEY">SECRET_KEY</a></li>
<li><a href="#SHELL_ENABLED">SHELL_ENABLED</a></li>
<li><a href="#SIGNAL_CLI_SOCKET">SIGNAL_CLI_SOCKET</a></li>
<li><a href="#SITE_LOGO_URL">SITE_LOGO_URL</a></li>
<li><a href="#SITE_NAME">SITE_NAME</a></li>
<li><a href="#SITE_ROOT">SITE_ROOT</a></li>
<li><a href="#SLACK_CLIENT_ID">SLACK_CLIENT_ID</a></li>
<li><a href="#SLACK_CLIENT_SECRET">SLACK_CLIENT_SECRET</a></li>
<li><a href="#SLACK_ENABLED">SLACK_ENABLED</a></li>
<li><a href="#SPIKE_ENABLED">SPIKE_ENABLED</a></li>
<li><a href="#TELEGRAM_BOT_NAME">TELEGRAM_BOT_NAME</a></li>
<li><a href="#TELEGRAM_TOKEN">TELEGRAM_TOKEN</a></li>
<li><a href="#TRELLO_APP_KEY">TRELLO_APP_KEY</a></li>
<li><a href="#TWILIO_ACCOUNT">TWILIO_ACCOUNT</a></li>
<li><a href="#TWILIO_AUTH">TWILIO_AUTH</a></li>
<li><a href="#TWILIO_FROM">TWILIO_FROM</a></li>
<li><a href="#TWILIO_MESSAGING_SERVICE_SID">TWILIO_MESSAGING_SERVICE_SID</a></li>
<li><a href="#TWILIO_USE_WHATSAPP">TWILIO_USE_WHATSAPP</a></li>
<li><a href="#USE_PAYMENTS">USE_PAYMENTS</a></li>
<li><a href="#VICTOROPS_ENABLED">VICTOROPS_ENABLED</a></li>
<li><a href="#WEBHOOKS_ENABLED">WEBHOOKS_ENABLED</a></li>
<li><a href="#WHATSAPP_DOWN_CONTENT_SID">WHATSAPP_DOWN_CONTENT_SID</a></li>
<li><a href="#WHATSAPP_UP_CONTENT_SID">WHATSAPP_UP_CONTENT_SID</a></li>
<li><a href="#ZULIP_ENABLED">ZULIP_ENABLED</a></li>
</ul>

## `ADMINS` {: #ADMINS }

Default: `""` (empty string)

A comma-sepparated list of email addresses to send code error notifications to.
When `DEBUG=False`, Healthchecks will send the details of exceptions raised in the
request/response cycle to the listed addresses. Example:

```ini
ADMINS=alice@example.org,bob@example.org
```

Note: for error notifications to work, make sure you have also specified working
SMTP credentials in the `EMAIL_...` environment variables.

## `ALLOWED_HOSTS` {: #ALLOWED_HOSTS }

Default: `*`

The host/domain names that this site can serve. You can specify multiple domain names
by separating them with commas:

```ini
ALLOWED_HOSTS=my-hc.example.org,alternative-name.example.org
```

Apart from the comma-separated syntax, this is a standard Django setting.
Read more about it in the
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#allowed-hosts).

## `APPRISE_ENABLED` {: #APPRISE_ENABLED }

Default: `False`

A boolean that turns on/off the [Apprise](https://github.com/caronc/apprise)
integration.

Before enabling the Apprise integration, make sure the `apprise` package is installed:

```bash
pip install apprise
```

## `DB` {: #DB }

Default: `sqlite`

The database engine to use. Possible values: `sqlite`, `postgres`, `mysql`.

## `DB_CONN_MAX_AGE` {: #DB_CONN_MAX_AGE }

Default: `0`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#conn-max-age).

## `DB_HOST` {: #DB_HOST }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#host).

## `DB_NAME` {: #DB_NAME }

Default: `hc` (PostgreSQL, MySQL) or `/path/to/projectdir/hc.sqlite` (SQLite)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#name).

## `DB_PASSWORD` {: #DB_PASSWORD }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#password).

## `DB_PORT` {: #DB_PORT }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#port).

## `DB_SSLMODE` {: #DB_SSLMODE }

Default: `prefer`

PostgreSQL-specific, [details](https://www.postgresql.org/docs/10/libpq-connect.html#LIBPQ-CONNECT-SSLMODE)

## `DB_TARGET_SESSION_ATTRS` {: #DB_TARGET_SESSION_ATTRS }

Default: `read-write`

PostgreSQL-specific, [details](https://www.postgresql.org/docs/10/libpq-connect.html#LIBPQ-CONNECT-TARGET-SESSION-ATTRS)

## `DB_USER` {: #DB_USER }

Default: `postgres` (PostgreSQL) or `root` (MySQL)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#user).

## `DEBUG` {: #DEBUG }

Default: `True`

A boolean that turns on/off debug mode.

_Never run a Healthchecks instance in production with the debug mode turned on!_

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#debug).

## `DEFAULT_FROM_EMAIL` {: #DEFAULT_FROM_EMAIL }

Default: `healthchecks@example.org`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#default-from-email).

## `DISCORD_CLIENT_ID` {: #DISCORD_CLIENT_ID }

Default: `None`

The Discord Client ID, required by the Discord integration.

To set up the Discord integration:

* Register a new application at
  [https://discordapp.com/developers/applications/me](https://discordapp.com/developers/applications/me)
* Add a Redirect URI to your Discord application. The URI format is
  `SITE_ROOT/integrations/add_discord/`. For example, if `your SITE_ROOT`
  is `https://my-hc.example.org` then the Redirect URI would be
  `https://my-hc.example.org/integrations/add_discord/`
* Look up your Discord app's _Client ID_ and _Client Secret_. Put them
  in the `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET` environment
  variables.

## `DISCORD_CLIENT_SECRET` {: #DISCORD_CLIENT_SECRET }

Default: `None`

The Discord Client Secret, required by the Discord integration. Look it up at
[https://discordapp.com/developers/applications/me](https://discordapp.com/developers/applications/me).

## `EMAIL_HOST` {: #EMAIL_HOST }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#email-host).

## `EMAIL_HOST_PASSWORD` {: #EMAIL_HOST_PASSWORD }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#email-host-password).

## `EMAIL_HOST_USER` {: #EMAIL_HOST_USER }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#email-host-user).

## `EMAIL_PORT` {: #EMAIL_PORT }

Default: `587`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#email-port).

## `EMAIL_USE_TLS` {: #EMAIL_USE_TLS }

Default: `True`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#email-use-tls).

## `EMAIL_USE_SSL` {: #EMAIL_USE_SSL}

Default: `False`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#email-use-ssl).

## `EMAIL_USE_VERIFICATION` {: #EMAIL_USE_VERIFICATION }

Default: `True`

A boolean that turns on/off a verification step when adding an email integration.

If enabled, whenever a user adds an email integration, Healthchecks emails a
verification link to the new address. The new integration becomes active only
after the user clicks the verification link.

If you are setting up a private healthchecks instance where
you trust your users, you can opt to disable the verification step. In that case,
set `EMAIL_USE_VERIFICATION` to `False`.

## `http_proxy` and `https_proxy` {: #http_proxy}

Default: `""` (empty string)

Specifies the proxy server to use for outgoing HTTP and HTTPS requests.
Supports different proxy server types. Examples:

```ini
https_proxy=http://example.org:1234
https_proxy=https://example.org:1234
https_proxy=socks4://example.org:1234
https_proxy=socks5://example.org:1234
```

Healthchecks uses libcurl as the HTTP client library for making HTTP(S) requests.
For more information about the proxy functionality, please see
[libcurl documentation](https://curl.se/libcurl/c/CURLOPT_PROXY.html).

Note: If your proxy server has a private IP address, you will also need to
set the `INTEGRATIONS_ALLOW_PRIVATE_IPS` setting to `True` to use it.

## `INTEGRATIONS_ALLOW_PRIVATE_IPS` {: #INTEGRATIONS_ALLOW_PRIVATE_IPS }

Default: `False`

A boolean that controls whether the integrations are allowed to make
HTTP(S) requests to private IP addresses (127.0.0.1, 192.168.x.x, ...). This setting
is set to `False` by default, because allowing users to define webhooks that probe
internal addresses is a security risk.

Only enable this setting if you run your Healthchecks instance in a trusted
environment, and need to integrate with services running in your internal network.

This setting affects all integration types, not just webhooks. For example,
if you run a Gotify instance on `localhost`, you will need to enable
`INTEGRATIONS_ALLOW_PRIVATE_IPS` to be able to use it via the Gotify integration.

This setting affects all outbound HTTP requests, including those made
while setting up new integrations (e.g. during the OAuth2 authorization flow).

This setting also affects connections to the proxy server when the `http_proxy` or
`https_proxy` environment variables are set. If your proxy server has a private
IP address, you will need to enable `INTEGRATIONS_ALLOW_PRIVATE_IPS` to use it.

## `LINENOTIFY_CLIENT_ID` {: #LINENOTIFY_CLIENT_ID }

Default: `None`

## `LINENOTIFY_CLIENT_SECRET` {: #LINENOTIFY_CLIENT_SECRET }

Default: `None`

## `MASTER_BADGE_LABEL` {: #MASTER_BADGE_URL }

Default: same as `SITE_NAME`

The label for the "Overall Status" status badge.

## `MATRIX_ACCESS_TOKEN` {: #MATRIX_ACCESS_TOKEN }

Default: `None`

The [Matrix](https://matrix.org/) bot user's access token, required by the Matrix
integration.

To set up the Matrix integration:

* Register a bot user (for posting notifications) in your preferred Matrix homeserver.
* Use the [Login API call](https://www.matrix.org/docs/guides/client-server-api#login)
  to retrieve bot user's access token. You can run it as shown in the documentation,
  using curl in the command shell.
* Set the `MATRIX_` environment variables. Example:

```ini
MATRIX_ACCESS_TOKEN=[a long string of characters returned by the login call]
MATRIX_HOMESERVER=https://matrix.org
MATRIX_USER_ID=@mychecks:matrix.org
```

## `MATRIX_HOMESERVER` {: #MATRIX_HOMESERVER }

Default: `None`

The Matrix bot's homeserver address, required by the Matrix integration.

## `MATRIX_USER_ID` {: #MATRIX_USER_ID }

Default: `None`

The Matrix bot's user identifier, required by the Matrix integration.

## `MATTERMOST_ENABLED` {: #MATTERMOST_ENABLED }

Default: `True`

A boolean that turns on/off the Mattermost integration. Enabled by default.

## `MSTEAMS_ENABLED` {: #MSTEAMS_ENABLED }

Default: `True`

A boolean that turns on/off the MS Teams integration. Enabled by default.

## `OPSGENIE_ENABLED` {: #OPSGENIE_ENABLED }

Default: `True`

A boolean that turns on/off the Opsgenie integration. Enabled by default.

## `PAGERTREE_ENABLED` {: #PAGERTREE_ENABLED }

Default: `True`

A boolean that turns on/off the PagerTree integration. Enabled by default.

## `PD_APP_ID` {: #PD_APP_ID }

Default: `None`

PagerDuty application ID. If set, enables the PagerDuty
[Simple Install Flow](https://developer.pagerduty.com/docs/app-integration-development/events-integration/).
If `None`, Healthchecks will fall back to the even simpler flow where users manually
copy integration keys from PagerDuty and paste them in Healthchecks.

To set up:

* Register a PagerDuty app at [PagerDuty](https://pagerduty.com/) › Developer Mode › My Apps
* In the newly created app, add the "Events Integration" functionality
* Specify a Redirect URL: `https://your-domain.com/integrations/add_pagerduty/`
* Copy the displayed app_id value (PXXXXX) and put it in the `PD_APP_ID` environment
  variable

## `PD_ENABLED` {: #PD_ENABLED }

Default: `True`

A boolean that turns on/off the PagerDuty integration. Enabled by default.

## `PING_BODY_LIMIT` {: #PING_BODY_LIMIT }

Default: `10000`

The upper size limit in bytes for logged ping request bodies.
The default value is 10000 (10 kilobytes). You can adjust the limit or you can remove
it altogether by setting this value to `None`.

## `PING_EMAIL_DOMAIN` {: #PING_EMAIL_DOMAIN }

Default: `localhost`

The domain to use for generating ping email addresses. Example:

```ini
PING_EMAIL_DOMAIN=ping.my-hc.example.org
```

In this example, Healthchecks would generate ping email addresses similar
to `3f1a7317-8e96-437c-a17d-b0d550b51e86@ping.my-hc.example.org`.

## `PING_ENDPOINT` {: #PING_ENDPOINT }

Default: `SITE_ROOT` + `/ping/`

The base URL to use for constructing ping URLs for display. Healthchecks constructs ping
URLs by appending either an UUID value or `<ping-key>/<slug>` value to `PING_ENDPOINT`.

Notes:

* Make sure the `PING_ENDPOINT` value ends with a trailing slash. If a trailing slash
  is missing, Healthchecks will *not* add it implicitly.
* Healthchecks uses `PING_ENDPOINT` for formatting ping URLs for display.
  The `PING_ENDPOINT` value does not influence the routing of incoming HTTP requests.
  If you change the `PING_ENDPOINT` value, you will likely also need to add matching
  URL rewriting rules in your reverse proxy configuration.

Example:

```ini
PING_ENDPOINT=https://ping.my-hc.example.org/
```

With this setting, Healthchecks will generate ping URLs similar to:

```
https://ping.my-hc.example.org/3f1a7317-8e96-437c-a17d-b0d550b51e86
https://ping.my-hc.example.org/1fj9XWM6Ns8vLGTmnPGk9g/dummy-slug
```

## `PROMETHEUS_ENABLED` {: #PROMETHEUS_ENABLED }

Default: `True`

A boolean that turns on/off the Prometheus integration. Enabled by default.

## `PUSHBULLET_CLIENT_ID` {: #PUSHBULLET_CLIENT_ID }

Default: `None`

The Pushbullet Client ID, required by the Pushbullet integration.

To set up the Pushbullet integration:

* Add a new OAuth client at
  [https://www.pushbullet.com/#settings/clients](https://www.pushbullet.com/#settings/clients)
* Add a `redirect_uri` to your OAuth client. The URI format is
  `SITE_ROOT/integrations/add_pushbullet/`. For example, if `your SITE_ROOT`
  is `https://my-hc.example.org` then the `redirect_uri` would be
  `https://my-hc.example.org/integrations/add_pushbullet/`
* Look up your OAuth client's `client_id` and `client_secret` values. Put them
  in the `PUSHBULLET_CLIENT_ID` and `PUSHBULLET_CLIENT_SECRET` environment
  variables.

Read more about setting up a Pushbullet OAuth client in the
[Pushbullet OAuth2 guide](https://docs.pushbullet.com/#oauth2).

## `PUSHBULLET_CLIENT_SECRET` {: #PUSHBULLET_CLIENT_SECRET }

Default: `None`

The Pushbullet Client Secret, required by the Pushbullet integration. Look it up at
[https://www.pushbullet.com/#settings/clients](https://www.pushbullet.com/#settings/clients).

## `PUSHOVER_API_TOKEN` {: #PUSHOVER_API_TOKEN }

Default: `None`

The [Pushover](https://pushover.net/) API token, required by the Pushover integration.

To enable the Pushover integration:

* Register a new Pushover application at
  [https://pushover.net/apps/build](https://pushover.net/apps/build).
* Within the Pushover application configuration, enable subscriptions.
  Make sure the subscription type is set to "URL". Also make sure the redirect
  URL is configured to point back to the root of the Healthchecks instance
  (e.g., `https://my-hc.example.org/`).
* Put the Pushover application's _API Token_ and the _Subscription URL_ in
  `PUSHOVER_API_TOKEN` and `PUSHOVER_SUBSCRIPTION_URL` environment
  variables. The Pushover subscription URL should look similar to
  `https://pushover.net/subscribe/yourAppName-randomAlphaNumericData`.

## `PUSHOVER_EMERGENCY_EXPIRATION` {: #PUSHOVER_EMERGENCY_EXPIRATION }

Default: `86400` (24 hours)

Specifies how many seconds an emergency Pushover notification
will continue to be retried for.

More information in [Pushover API documentation](https://pushover.net/api#priority).

## `PUSHOVER_EMERGENCY_RETRY_DELAY` {: #PUSHOVER_EMERGENCY_RETRY_DELAY }

Default: `300` (5 minutes)

Specifies how often (in seconds) the Pushover servers will send the same notification
to the user.

More information in [Pushover API documentation](https://pushover.net/api#priority).

## `PUSHOVER_SUBSCRIPTION_URL` {: #PUSHOVER_SUBSCRIPTION_URL }

Default: `None`

The Pushover Subscription URL, required by the Pushover integration.

## `REGISTRATION_OPEN` {: #REGISTRATION_OPEN }

Default: `True`

A boolean that controls whether site visitors can create new accounts.
Set it to `False` if you are setting up a private Healthchecks instance, but
it needs to be publicly accessible (so, for example, your cloud services
can send pings to it).

If you close new user registration, you can still selectively invite users
to your team account.

## `REMOTE_USER_HEADER` {: #REMOTE_USER_HEADER }

Default: `None`

Specifies the request header to use for external authentication. If you use
a reverse proxy that handles user authentication, and the reverse proxy can pass
the authenticated user's email address in an HTTP request header, you can use this
setting to integrate Healthchecks with it.

When `REMOTE_USER_HEADER` is set, Healthchecks will:

 - in views that require authentication, look up the request header
   specified in `REMOTE_USER_HEADER`
 - assume the header contains the user's email address
 - automatically log in the user with a matching email address
 - automatically create a user account if it does not exist
 - disable the default authentication methods (login link to email, password)

 The header name in `REMOTE_USER_HEADER` must be specified in upper-case,
 with any dashes replaced with underscores, and prefixed with `HTTP_`. For
 example, if your authentication proxy sets a `X-Authenticated-User` request
 header, you should set `REMOTE_USER_HEADER=HTTP_X_AUTHENTICATED_USER`.

**Important:** When this option is enabled, **Healthchecks will trust the header's
value implicitly**, so it is **very important** to ensure that attackers cannot
set the value themselves (and thus impersonate any user). How to do this varies by
your chosen proxy, but generally involves configuring it to strip out headers that
normalize to the same name as the chosen identity header.

## `ROCKETCHAT_ENABLED` {: #ROCKETCHAT_ENABLED }

Default: `True`

A boolean that turns on/off the Rocket.Chat integration. Enabled by default.

## `RP_ID` {: #RP_ID }

Default: `None`

The [Relying Party identifier](https://www.w3.org/TR/webauthn-2/#relying-party-identifier),
required by the WebAuthn second-factor authentication feature.

Healthchecks optionally supports two-factor authentication using the WebAuthn
standard. To enable WebAuthn support, set the `RP_ID` setting to a non-null value.
Set its value to your site's domain without scheme and without port. For example,
if your site runs on `https://my-hc.example.org`, set `RP_ID` to `my-hc.example.org`.

Note that WebAuthn requires HTTPS, even if running on localhost. To test WebAuthn
locally with a self-signed certificate, you can use the `runsslserver` command
from the `django-sslserver` package.

## `S3_ACCESS_KEY` {: #S3_ACCESS_KEY }

Default: `None`

Access key of an account in S3 service.

Healthchecks can optionally upload ping request body data to S3-compatible object
storage instead of storing it in the database. To use this feature, provide valid
credentials to an S3-compatible service by setting the following environment variables:

* `S3_ACCESS_KEY` (example: `AKIAFIXMEFIXME`)
* `S3_BUCKET` (example: `my-bucket`)
* `S3_ENDPOINT` (example: `s3.eu-central-1.amazonaws.com`)
* `S3_REGION` (example: `eu-central-1`)
* `S3_SECRET_KEY`

## `S3_BUCKET` {: #S3_BUCKET }

Default: `None`

Name of the bucket in S3 service for storing ping request body data.

## `S3_ENDPOINT` {: #S3_ENDPOINT }

Default: `None`

URL to the S3-compatible service.

## `S3_REGION` {: #S3_REGION }

Default: `None`

Region name of buckets in S3 service.

## `S3_SECRET_KEY` {: #S3_SECRET_KEY }

Default: `None`

The secret key of an account in S3 service.

## `S3_TIMEOUT` {: #S3_TIMEOUT }

Default: `60`

Timeout for individual S3 operations, in seconds.

## `S3_SECURE` {: #S3_SECURE }

Default: `True`

Whether to use secure (TLS) connection to S3 or not. To
use unencrypted HTTP requests, set this value to `False`.

## `SECRET_KEY` {: #SECRET_KEY }

Default: `---`

A secret key used for cryptographic signing. Should be set to a unique,
unpredictable value.

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#secret-key).

## `SHELL_ENABLED` {: #SHELL_ENABLED }

Default: `False`

A boolean that turns on/off the "Shell Commands" integration.

The "Shell Commands" integration runs user-defined local shell commands when checks
go up or down. This integration is disabled by default and can be enabled by setting
the `SHELL_ENABLED` environment variable to `True`.

Note: be careful when using "Shell Commands" integration, and only enable it when
you fully trust the users of your Healthchecks instance. The commands will be executed
by the `manage.py sendalerts` process and will run with its system permissions.

## `SIGNAL_CLI_SOCKET` {: #SIGNAL_CLI_SOCKET }

Default: `None`

The path to the signal-cli UNIX socket, or the hostname:port of the signal-cli
TCP socket.

Example (UNIX socket):

```ini
SIGNAL_CLI_SOCKET=/tmp/signal-cli.socket
```

Example (TCP socket):

```ini
SIGNAL_CLI_SOCKET=example.org:7583
```

Healthchecks uses [signal-cli](https://github.com/AsamK/signal-cli) to send Signal
notifications. Healthcecks interacts with signal-cli over UNIX or TCP socket (requires
signal-cli 0.10.0 or later).

To enable the Signal integration:

* Set up and configure signal-cli to expose JSON RPC on an UNIX or TCP socket
  ([instructions](https://github.com/AsamK/signal-cli/wiki/JSON-RPC-service)).
  Example: `signal-cli -a +xxxxxx daemon --socket /tmp/signal-cli-socket`
* Put the socket's location in the `SIGNAL_CLI_SOCKET` environment variable.

## `SITE_LOGO_URL` {: #SITE_LOGO_URL }

Default: `None`

An URL pointing to the image you want to use as the site logo. If not set,
Healthchecks will use a fallback image: `/static/img/logo.png`.

You can place a custom logo in `/static/img/`, run `manage.py collectstatic`, and
point `SITE_LOGO_URL` to it like so:

```ini
SITE_LOGO_URL=/static/img/my-custom-logo.png
```

Or you can serve the logo from another server, and point to it using an absolute URL:

```ini
SITE_LOGO_URL=https://example.org/cdn/my-custom-logo.png
```

Either way, Healthchecks will use the provided `SITE_LOGO_URL` value as-is in HTML
pages, and you should use an URL that **the end user's browser will be able to
access directly**. The logo image can use any image format supported by browsers
(PNG, SVG, JPG are all fine).

**Docker note.** You can build a custom Docker image with your logo "baked in". To
do so, use a Dockerfile with the following contents, and with your logo.png placed next
to it:

```docker
FROM healthchecks/healthchecks
COPY logo.png /opt/healthchecks/static-collected/img/
```

This overwrites the default placeholder logo, so, in this case, you do not need to
specify `SITE_LOGO_URL`. Notice that the logo must be placed in `static-collected`, not
`static`. This is because `manage.py collectstatic` has already been run in the base
image's build time, and the web server will not recognize any new files placed in the
`static` directory.

Please do not use the Healthchecks.io logo (the one with the dark green background) on
self-hosted instances. This logo is not part of the Healthchecks open-source project.

## `SITE_NAME` {: #SITE_NAME }

Default: `Mychecks`

The display name of this Healthchecks instance. Healthchecks uses it throughout
its web UI and documentation.

## `SITE_ROOT` {: #SITE_ROOT }

Default: `http://localhost:8000`

The base URL of this Healthchecks instance. Healthchecks uses `SITE_ROOT` whenever
it needs to construct absolute URLs.

## `SLACK_CLIENT_ID` {: #SLACK_CLIENT_ID }

Default: `None`

The Slack Client ID, used by the Healthchecks integration for Slack.

The integration can work with or without the Slack Client ID. If
the Slack Client ID is not set, in the "Integrations - Add Slack" page,
Healthchecks will ask the user to provide a webhook URL for posting notifications.

If the Slack Client ID _is_ set, Healthchecks will use the OAuth2 flow
to get the webhook URL from Slack. The OAuth2 flow is more user-friendly.
To set it up, go to [https://api.slack.com/apps/](https://api.slack.com/apps/)
and create a _Slack app_. When setting up the Slack app, make sure to:

* Add the [incoming-webhook](https://api.slack.com/scopes/incoming-webhook)
  scope to the Bot Token Scopes.
* Add a _Redirect URL_ in the format `SITE_ROOT/integrations/add_slack_btn/`.
  For example, if your `SITE_ROOT` is `https://my-hc.example.org` then the
  Redirect URL would be `https://my-hc.example.org/integrations/add_slack_btn/`.

## `SLACK_CLIENT_SECRET` {: #SLACK_CLIENT_SECRET }

Default: `None`

The Slack Client Secret. Required if `SLACK_CLIENT_ID` is set.
Look it up at [https://api.slack.com/apps/](https://api.slack.com/apps/).

## `SLACK_ENABLED` {: #SLACK_ENABLED }

Default: `True`

A boolean that turns on/off the Healthchecks integration for Slack. Enabled by default.

## `SPIKE_ENABLED` {: #SPIKE_ENABLED }

Default: `True`

A boolean that turns on/off the Spike.sh integration. Enabled by default.

## `TELEGRAM_BOT_NAME` {: #TELEGRAM_BOT_NAME }

Default: `ExampleBot`

The [Telegram](https://telegram.org/) bot name, required by the Telegram integration.

To set up the Telegram integration:

* Create a Telegram bot by talking to the
[BotFather](https://core.telegram.org/bots#6-botfather). Set the bot's name,
description, user picture, and add a "/start" command.
* After creating the bot you will have the bot's name and token. Put them
in `TELEGRAM_BOT_NAME` and `TELEGRAM_TOKEN` environment variables.
* Run the `settelegramwebhook` management command. This command tells Telegram
where to forward channel messages by invoking Telegram's
[setWebhook](https://core.telegram.org/bots/api#setwebhook) API call:

```bash
$ ./manage.py settelegramwebhook
Done, Telegram's webhook set to: https://my-monitoring-project.com/integrations/telegram/bot/
```

For this to work, your `SITE_ROOT` must be publicly accessible and use the "https://"
scheme.

## `TELEGRAM_TOKEN` {: #TELEGRAM_TOKEN }

Default: `None`

The Telegram bot user's authentication token, required by the Telegram integration.

## `TRELLO_APP_KEY` {: #TRELLO_APP_KEY }

Default: `None`

The [Trello](https://trello.com/) app key, required by the Trello integration.

To set up the Trello integration, get a developer API key from
[https://trello.com/app-key](https://trello.com/app-key) and put it in the
`TRELLO_APP_KEY` environment variable.

## `TWILIO_ACCOUNT` {: #TWILIO_ACCOUNT }

Default: `None`

Twilio Account SID, required by the SMS, Call, and WhatsApp integrations.

## `TWILIO_AUTH` {: #TWILIO_AUTH }

Default: `None`

Twilio Auth token, required by the SMS, Call, and WhatsApp integrations.

## `TWILIO_FROM` {: #TWILIO_FROM }

Default: `None`

The Twilio phone number to use as the sender for SMS and WhatsApp notifications,
and as the caller for Call integrations.

Example:

```ini
TWILIO_FROM=+15017122661
```

## `TWILIO_MESSAGING_SERVICE_SID` {: #TWILIO_MESSAGING_SERVICE_SID }

Default: `None`

The Twilio Messaging Service SID for sending SMS and WhatsApp notifications.

`TWILIO_MESSAGING_SERVICE_SID` is **required** for sending WhatsApp notifications.

`TWILIO_MESSAGING_SERVICE_SID` is **optional** for sending SMS notifications. If specified,
Healthchecks will pass it in the "MessagingServiceSid" field to Twilio API. This will
result in Twilio using a Messaging Service instead of a plain sender number to deliver
the SMS messages. If not specified, Healthchecks will fall back to using
the "From" field with the value configured in [TWILIO_FROM](#TWILIO_FROM).

Example:

```ini
TWILIO_MESSAGING_SERVICE_SID=MGe56e622d540e6badc52ae0ac4af028c6
```

## `TWILIO_USE_WHATSAPP` {: #TWILIO_USE_WHATSAPP }

Default: `False`

A boolean that turns on/off the WhatsApp integration. For the WhatsApp integration
to work, you will also need to specify:

* [TWILIO_ACCOUNT](#TWILIO_ACCOUNT)
* [TWILIO_AUTH](#TWILIO_AUTH)
* [TWILIO_FROM](#TWILIO_FROM)
* [TWILIO_MESSAGING_SERVICE_SID](#TWILIO_MESSAGING_SERVICE_SID)
* [WHATSAPP_DOWN_CONTENT_SID](#WHATSAPP_DOWN_CONTENT_SID)
* [WHATSAPP_UP_CONTENT_SID](#WHATSAPP_UP_CONTENT_SID).

## `USE_PAYMENTS` {: #USE_PAYMENTS }

Default: `False`

A boolean that turns on/off billing features.

## `VICTOROPS_ENABLED` {: #VICTOROPS_ENABLED }

Default: `True`

A boolean that turns on/off the Splunk On-Call (VictorOps) integration.
Enabled by default.

## `WEBHOOKS_ENABLED` {: #WEBHOOKS_ENABLED }

Default: `True`

A boolean that turns on/off the Webhooks integration. Enabled by default.

## `WHATSAPP_DOWN_CONTENT_SID` {: #WHATSAPP_DOWN_CONTENT_SID }

Default: `None`

Identifier of the Twilio content template to use for WhatsApp "down" notifications.
Required by the WhatsApp integration.

Meta requires WhatsApp message templates to be pre-registered and approved.
Create a content template in your Twilio account with the following contents:

````
The check “{{1}}” is DOWN.
````

You can tweak the message contents as needed, but make sure it has a single placeholder
similar to the above example.

## `WHATSAPP_UP_CONTENT_SID` {: #WHATSAPP_UP_CONTENT_SID }

Default: `None`

Identifier of the Twilio content template to use for WhatsApp "up" notifications.
Required by the WhatsApp integration.

Meta requires WhatsApp message templates to be pre-registered and approved.
Create a content template in your Twilio account with the following contents:

````
The check “{{1}}” is now UP.
````

You can tweak the message contents as needed, but make sure it has a single placeholder
similar to the above example.

## `ZULIP_ENABLED` {: #ZULIP_ENABLED }

Default: `True`

A boolean that turns on/off the Zulip integration. Enabled by default.
