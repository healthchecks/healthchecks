# Server Configuration

Healthchecks prepares its configuration in `hc/settings.py`. It reads configuration
from environment variables. Below is a list of variables it reads and uses:

## `ALLOWED_HOSTS` {: #ALLOWED_HOSTS }

Default: `*`

A list of strings representing the host/domain names that this site can serve.
You can specify multiple domain names by separating them with commas:

```ini
ALLOWED_HOSTS=my-hc.example.org,alternative-name.example.org
```

Aside from the comma-separated syntax, this is a standard Django setting.
Read more about it in the
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts).

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

The database enginge to use. Possible values: `sqlite`, `postgres`, `mysql`.

## `DB_CONN_MAX_AGE` {: #DB_CONN_MAX_AGE }

Default: `0`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#conn-max-age).

## `DB_HOST` {: #DB_HOST }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#host).

## `DB_NAME` {: #DB_NAME }

Default: `hc` (PostgreSQL, MySQL) or `/path/to/projectdir/hc.sqlite` (SQLite)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#name).

## `DB_PASSWORD` {: #DB_PASSWORD }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#password).

## `DB_PORT` {: #DB_PORT }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#port).

## `DB_SSLMODE` {: #DB_SSLMODE }

Default: `prefer`

PostgreSQL-specific, [details](https://www.postgresql.org/docs/10/libpq-connect.html#LIBPQ-CONNECT-SSLMODE)

## `DB_TARGET_SESSION_ATTRS` {: #DB_TARGET_SESSION_ATTRS }

Default: `read-write`

PostgreSQL-specific, [details](https://www.postgresql.org/docs/10/libpq-connect.html#LIBPQ-CONNECT-TARGET-SESSION-ATTRS)

## `DB_USER` {: #DB_USER }

Default: `postgres` (PostgreSQL) or `root` (MySQL)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#user).

## `DEBUG` {: #DEBUG }

Default: `True`

A boolean that turns on/off debug mode.

_Never run a Healthchecks instance in production with the debug mode turned on!_

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#debug).

## `DEFAULT_FROM_EMAIL` {: #DEFAULT_FROM_EMAIL }

Default: `healthchecks@example.org`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#default-from-email).

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
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#email-host).

## `EMAIL_HOST_PASSWORD` {: #EMAIL_HOST_PASSWORD }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#email-host-password).

## `EMAIL_HOST_USER` {: #EMAIL_HOST_USER }

Default: `""` (empty string)

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#email-host-user).

## `EMAIL_PORT` {: #EMAIL_PORT }

Default: `587`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#email-port).

## `EMAIL_USE_TLS` {: #EMAIL_USE_TLS }

Default: `True`

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#email-use-tls).

## `EMAIL_USE_VERIFICATION` {: #EMAIL_USE_VERIFICATION }

Default: `True`

A boolean that turns on/off a verification step when adding an email integration.

If enabled, whenever an user adds an email integration, Healthchecks emails a
verification link to the new address. The new integration becomes active only
after user clicks the verification link.

If you are setting up a private healthchecks instance where
you trust your users, you can opt to disable the verification step. In that case,
set `EMAIL_USE_VERIFICATION` to `False`.

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
  using curl in command shell.
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

## `PD_VENDOR_KEY` {: #PD_VENDOR_KEY }

Default: `None`

[PagerDuty](https://www.pagerduty.com/) vendor key,
required by the PagerDuty integration.

## `PING_BODY_LIMIT` {: #PING_BODY_LIMIT }

Default: `10000`

The upper size limit in bytes for logged ping request bodies.
The default value is 10000 (10 kilobytes). You can adjust the limit or you can remove
the it altogether by setting this value to `None`.

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

The base URL to use for generating ping URLs. Example:

```ini
PING_ENDPOINT=https://ping.my-hc.example.org
```

In this example, Healthchecks would generate ping URLs similar
to `https://ping.my-hc.example.org/3f1a7317-8e96-437c-a17d-b0d550b51e86`.

## `PUSHBULLET_CLIENT_ID` {: #PUSHBULLET_CLIENT_ID }

Default: `None`

## `PUSHBULLET_CLIENT_SECRET` {: #PUSHBULLET_CLIENT_SECRET }

Default: `None`

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

Specifies how many seconds an emergency Pushoover notification
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

Specifies the request header to use for external authentication.

Healthchecks supports external authentication by means of HTTP headers set by
reverse proxies or the WSGI server. This allows you to integrate it into your
existing authentication system (e.g., LDAP or OAuth) via an authenticating proxy. When this option is enabled, **Healtchecks will trust the header's value implicitly**, so it is **very important** to ensure that attackers cannot set the value themselves (and thus impersonate any user). How to do this varies by your chosen proxy, but generally involves configuring it to strip out headers that normalize to the same name as the chosen identity header.

To enable this feature, set the `REMOTE_USER_HEADER` value to a header you wish to authenticate with. HTTP headers will be prefixed with `HTTP_` and have any dashes converted to underscores. Headers without that prefix can be set by the WSGI server itself only, which is more secure.

When `REMOTE_USER_HEADER` is set, Healthchecks will:
 - assume the header contains user's email address
 - look up and automatically log in the user with a matching email address
 - automatically create an user account if it does not exist
 - disable the default authentication methods (login link to email, password)

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

## `SECRET_KEY` {: #SECRET_KEY }

Default: `---`

A secret key used for cryptographic signing, and should be set to a unique,
unpredictable value.

This is a standard Django setting, read more in
[Django documentation](https://docs.djangoproject.com/en/3.1/ref/settings/#secret-key).

## `SHELL_ENABLED` {: #SHELL_ENABLED }

Default: `False`

A boolean that turns on/off the "Shell Commands" integration.

The "Shell Commands" integration runs user-defined local shell commands when checks
go up or down. This integration is disabled by default, and can be enabled by setting
the `SHELL_ENABLED` environment variable to `True`.

Note: be careful when using "Shell Commands" integration, and only enable it when
you fully trust the users of your Healthchecks instance. The commands will be executed
by the `manage.py sendalerts` process, and will run with its system permissions.

## `SIGNAL_CLI_ENABLED` {: #SIGNAL_CLI_ENABLED }

Default: `False`

A boolean that turns on/off the [Signal](https://signal.org/) integration.

Healthchecks uses [signal-cli](https://github.com/AsamK/signal-cli) to send Signal
notifications. Healthcecks interacts with signal-cli over DBus.

To enable the Signal integration:

* Set up and configure signal-cli to listen on DBus system bus
  ([instructions](https://github.com/AsamK/signal-cli/wiki/DBus-service)).
  Make sure you can send test messages from command line, using the `dbus-send`
  example given in the signal-cli instructions.
* Set the `SIGNAL_CLI_ENABLED` environment variable to `True`.

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

The Slack Client ID, used by the Slack integration.

The Slack integration can work with or without the Slack Client ID. If
the Slack Client ID is not set, in the "Integrations - Add Slack" page,
Healthchecks will ask the user to provide a webhook URL for posting notifications.

If the Slack Client _is_ set, Healthchecks will use the OAuth2 flow
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

A boolean that turns on/off the Slack integration. Enabled by default.

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

For this to work, your `SITE_ROOT` must be publicy accessible and use the "https://"
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

## `TWILIO_AUTH` {: #TWILIO_AUTH }

Default: `None`

## `TWILIO_FROM` {: #TWILIO_FROM }

Default: `None`

## `TWILIO_USE_WHATSAPP` {: #TWILIO_USE_WHATSAPP }

Default: `False`

## `USE_PAYMENTS` {: #USE_PAYMENTS }

Default: `False`

A boolean that turns on/off billing features.

## `WEBHOOKS_ENABLED` {: #WEBHOOKS_ENABLED }

Default: `True`

A boolean that turns on/off the Webhooks integration. Enabled by default.
