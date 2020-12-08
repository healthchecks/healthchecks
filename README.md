# Healthchecks

![Build Status](https://github.com/healthchecks/healthchecks/workflows/Django%20CI/badge.svg)
[![Coverage Status](https://coveralls.io/repos/healthchecks/healthchecks/badge.svg?branch=master&service=github)](https://coveralls.io/github/healthchecks/healthchecks?branch=master)


![Screenshot of Welcome page](/static/img/welcome.png?raw=true "Welcome Page")

![Screenshot of My Checks page](/static/img/my_checks.png?raw=true "My Checks Page")

![Screenshot of Period/Grace dialog](/static/img/period_grace.png?raw=true "Period/Grace Dialog")

![Screenshot of Cron dialog](/static/img/cron.png?raw=true "Cron Dialog")

![Screenshot of Integrations page](/static/img/channels.png?raw=true "Integrations Page")

healthchecks is a watchdog for your cron jobs. It's a web server that listens for pings from your cron jobs, plus a web interface.

It is live here: [http://healthchecks.io/](http://healthchecks.io/)

The building blocks are:

* Python 3.6+
* Django 3
* PostgreSQL or MySQL

## Setting Up for Development

These are instructions for setting up healthchecks Django app
in development environment.

* install dependencies (Debian/Ubuntu)

        $ sudo apt-get update
        $ sudo apt-get install -y gcc python3-dev python3-venv

* prepare directory for project code and virtualenv:

        $ mkdir -p ~/webapps
        $ cd ~/webapps

* prepare virtual environment
  (with virtualenv you get pip, we'll use it soon to install requirements):

        $ python3 -m venv hc-venv
        $ source hc-venv/bin/activate

* check out project code:

        $ git clone https://github.com/healthchecks/healthchecks.git

* install requirements (Django, ...) into virtualenv:

        $ pip install -r healthchecks/requirements.txt

* healthchecks is configured to use a SQLite database by default. To use
  PostgreSQL or MySQL database, create and edit `hc/local_settings.py` file.
  There is a template you can copy and edit as needed:

        $ cd ~/webapps/healthchecks
        $ cp hc/local_settings.py.example hc/local_settings.py

* create database tables and the superuser account:

        $ cd ~/webapps/healthchecks
        $ ./manage.py migrate
        $ ./manage.py createsuperuser

* run development server:

        $ ./manage.py runserver

The site should now be running at `http://localhost:8000`.
To access Django administration site, log in as a super user, then
visit `http://localhost:8000/admin`

## Configuration

Healthchecks prepares its configuration in `hc/settings.py`. It reads configuration
from two places:

 * environment variables (see the variable names in the table below)
 * it imports configuration for `hc/local_settings.py` file, if it exists

You can use either mechanism, depending on what is more convenient. Using
`hc/local_settings.py` allows more flexibility: you can set
each and every [Django setting](https://docs.djangoproject.com/en/3.1/ref/settings/),
you can run Python code to load configuration from an external source.

Healthchecks reads configuration from the following environment variables:

| Environment variable | Default value | Notes
| -------------------- | ------------- | ----- |
| [SECRET_KEY](https://docs.djangoproject.com/en/3.1/ref/settings/#secret-key) | `"---"`
| [DEBUG](https://docs.djangoproject.com/en/3.1/ref/settings/#debug) | `True` | Set to `False` for production
| [ALLOWED_HOSTS](https://docs.djangoproject.com/en/3.1/ref/settings/#allowed-hosts) | `*` | Separate multiple hosts with commas
| [DEFAULT_FROM_EMAIL](https://docs.djangoproject.com/en/3.1/ref/settings/#default-from-email) | `"healthchecks@example.org"`
| USE_PAYMENTS | `False`
| REGISTRATION_OPEN | `True`
| DB | `"sqlite"` | Set to `"postgres"` or `"mysql"`
| [DB_HOST](https://docs.djangoproject.com/en/3.1/ref/settings/#host) | `""` *(empty string)*
| [DB_PORT](https://docs.djangoproject.com/en/3.1/ref/settings/#port) | `""` *(empty string)*
| [DB_NAME](https://docs.djangoproject.com/en/3.1/ref/settings/#name) | `"hc"` (PostgreSQL, MySQL) or `"/path/to/project/hc.sqlite"` (SQLite) | For SQLite, specify the full path to the database file.
| [DB_USER](https://docs.djangoproject.com/en/3.1/ref/settings/#user) | `"postgres"` or `"root"`
| [DB_PASSWORD](https://docs.djangoproject.com/en/3.1/ref/settings/#password) | `""` *(empty string)*
| [DB_CONN_MAX_AGE](https://docs.djangoproject.com/en/3.1/ref/settings/#conn-max-age) | `0`
| DB_SSLMODE | `"prefer"` | PostgreSQL-specific, [details](https://blog.github.com/2018-10-21-october21-incident-report/)
| DB_TARGET_SESSION_ATTRS | `"read-write"` | PostgreSQL-specific, [details](https://www.postgresql.org/docs/10/static/libpq-connect.html#LIBPQ-CONNECT-TARGET-SESSION-ATTRS)
| [EMAIL_HOST](https://docs.djangoproject.com/en/3.1/ref/settings/#email-host) | `""` *(empty string)*
| [EMAIL_PORT](https://docs.djangoproject.com/en/3.1/ref/settings/#email-port) | `"587"`
| [EMAIL_HOST_USER](https://docs.djangoproject.com/en/3.1/ref/settings/#email-host-user) | `""` *(empty string)*
| [EMAIL_HOST_PASSWORD](https://docs.djangoproject.com/en/3.1/ref/settings/#email-host-password) | `""` *(empty string)*
| [EMAIL_USE_TLS](https://docs.djangoproject.com/en/3.1/ref/settings/#email-use-tls) | `"True"`
| EMAIL_USE_VERIFICATION | `"True"` | Whether to send confirmation links when adding email integrations
| SITE_ROOT | `"http://localhost:8000"`
| SITE_NAME | `"Mychecks"`
| RP_ID | `None` | Enables WebAuthn support
| MASTER_BADGE_LABEL | `"Mychecks"`
| PING_ENDPOINT | `"http://localhost:8000/ping/"`
| PING_EMAIL_DOMAIN | `"localhost"`
| PING_BODY_LIMIT | 10000 | In bytes. Set to `None` to always log full request body
| APPRISE_ENABLED | `"False"`
| DISCORD_CLIENT_ID | `None`
| DISCORD_CLIENT_SECRET | `None`
| LINENOTIFY_CLIENT_ID | `None`
| LINENOTIFY_CLIENT_SECRET | `None`
| MATRIX_ACCESS_TOKEN | `None`
| MATRIX_HOMESERVER | `None`
| MATRIX_USER_ID | `None`
| PD_VENDOR_KEY | `None`
| PUSHBULLET_CLIENT_ID | `None`
| PUSHBULLET_CLIENT_SECRET | `None`
| PUSHOVER_API_TOKEN | `None`
| PUSHOVER_EMERGENCY_EXPIRATION | `86400`
| PUSHOVER_EMERGENCY_RETRY_DELAY | `300`
| PUSHOVER_SUBSCRIPTION_URL | `None`
| REMOTE_USER_HEADER | `None` | See [External Authentication](#external-authentication) for details.
| SHELL_ENABLED | `"False"`
| SLACK_CLIENT_ID | `None`
| SLACK_CLIENT_SECRET | `None`
| TELEGRAM_BOT_NAME | `"ExampleBot"`
| TELEGRAM_TOKEN | `None`
| TRELLO_APP_KEY | `None`
| TWILIO_ACCOUNT | `None`
| TWILIO_AUTH | `None`
| TWILIO_FROM | `None`
| TWILIO_USE_WHATSAPP | `"False"`


Some useful settings keys to override are:

`SITE_ROOT` is used to build fully qualified URLs for pings, and for use in
emails and notifications. Example:

```python
SITE_ROOT = "https://my-monitoring-project.com"
```

`SITE_NAME` has the default value of "Mychecks" and is used throughout
the templates. Replace it with your own name to personalize your installation.
Example:

```python
SITE_NAME = "My Monitoring Project"
```

`REGISTRATION_OPEN` controls whether site visitors can create new accounts.
Set it to `False` if you are setting up a private healthchecks instance, but
it needs to be publicly accessible (so, for example, your cloud services
can send pings).

If you close new user registration, you can still selectively invite users
to your team account.

`EMAIL_USE_VERIFICATION` enables/disables the sending of a verification
link when an email address is added to the list of notification methods.
Set it to `False` if you are setting up a private healthchecks instance where
you trust your users and want to avoid the extra verification step.


`PING_BODY_LIMIT` sets the size limit in bytes for logged ping request bodies.
The default value is 10000 (10 kilobytes). You can remove the limit altogether by
setting this value to `None`.

## Database Configuration

Database configuration is loaded from environment variables. If you
need to use a non-standard configuration, you can override the
database configuration in `hc/local_settings.py` like so:

```python
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     'your-database-name-here',
        'USER':     'your-database-user-here',
        'PASSWORD': 'your-database-password-here',
        'TEST': {'CHARSET': 'UTF8'},
        'OPTIONS': {
            ... your custom options here ...
        }
    }
}
```

## Accessing Administration Panel

healthchecks comes with Django's administration panel where you can manually
view and modify user accounts, projects, checks, integrations etc. To access it,

 * if you haven't already, create a superuser account: `./manage.py createsuperuser`
 * log into the site using superuser credentials
 * in the top navigation, "Account" dropdown, select "Site Administration"


## Sending Emails

healthchecks must be able to send email messages, so it can send out login
links and alerts to users. Environment variables can be used to configure
SMTP settings, or your may put your SMTP server configuration in
`hc/local_settings.py` like so:

```python
EMAIL_HOST = "your-smtp-server-here.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = "username"
EMAIL_HOST_PASSWORD = "password"
EMAIL_USE_TLS = True
```

For more information, have a look at Django documentation,
[Sending Email](https://docs.djangoproject.com/en/1.10/topics/email/) section.

## Receiving Emails

healthchecks comes with a `smtpd` management command, which starts up a
SMTP listener service. With the command running, you can ping your
checks by sending email messages
to `your-uuid-here@my-monitoring-project.com` email addresses.

Start the SMTP listener on port 2525:

    $ ./manage.py smtpd --port 2525

Send a test email:

    $ curl --url 'smtp://127.0.0.1:2525' \
        --mail-from 'foo@example.org' \
        --mail-rcpt '11111111-1111-1111-1111-111111111111@my-monitoring-project.com' \
        -F '='



## Sending Status Notifications

healtchecks comes with a `sendalerts` management command, which continuously
polls database for any checks changing state, and sends out notifications as
needed. Within an activated virtualenv, you can manually run
the `sendalerts` command like so:

    $ ./manage.py sendalerts

In a production setup, you will want to run this command from a process
manager like [supervisor](http://supervisord.org/) or systemd.

## Database Cleanup

With time and use the healthchecks database will grow in size. You may
decide to prune old data: inactive user accounts, old checks not assigned
to users, records of outgoing email messages and records of received pings.
There are separate Django management commands for each task:

* Remove old records from `api_ping` table. For each check, keep 100 most
  recent pings:

    ```
    $ ./manage.py prunepings
    ```

* Remove old records of sent notifications. For each check, remove
  notifications that are older than the oldest stored ping for same check.

    ```
    $ ./manage.py prunenotifications
    ```

* Remove user accounts that match either of these conditions:
  * Account was created more than 6 months ago, and user has never logged in.
   These can happen when user enters invalid email address when signing up.
  * Last login was more than 6 months ago, and the account has no checks.
   Assume the user doesn't intend to use the account any more and would
   probably *want* it removed.

    ```
    $ ./manage.py pruneusers
    ```

* Remove old records from the `api_tokenbucket` table. The TokenBucket
  model is used for rate-limiting login attempts and similar operations.
  Any records older than one day can be safely removed.

    ```
    $ ./manage.py prunetokenbucket
    ```

* Remove old records from the `api_flip` table. The Flip
  objects are used to track status changes of checks, and to calculate
  downtime statistics month by month. Flip objects from more than 3 months
  ago are not used and can be safely removed.

    ```
    $ ./manage.py pruneflips
    ```

When you first try these commands on your data, it is a good idea to
test them on a copy of your database, not on the live database right away.
In a production setup, you should also have regular, automated database
backups set up.

## Two-factor Authentication

Healthchecks optionally supports two-factor authentication using the WebAuthn
standard. To enable WebAuthn support, set the `RP_ID` (relying party identifier )
setting to a non-null value. Set its value to your site's domain without scheme
and without port. For example, if your site runs on `https://my-hc.example.org`,
set `RP_ID` to `my-hc.example.org`.

Note that WebAuthn requires HTTPS, even if running on localhost. To test WebAuthn
locally with a self-signed certificate, you can use the `runsslserver` command
from the `django-sslserver` package.

## External Authentication

HealthChecks supports external authentication by means of HTTP headers set by
reverse proxies or the WSGI server. This allows you to integrate it into your
existing authentication system (e.g., LDAP or OAuth) via an authenticating proxy.
When this option is enabled, **healtchecks will trust the header's value implicitly**,
so it is **very important** to ensure that attackers cannot set the value themselves
(and thus impersonate any user). How to do this varies by your chosen proxy,
but generally involves configuring it to strip out headers that normalize to the
same name as the chosen identity header.

To enable this feature, set the `REMOTE_USER_HEADER` value to a header you wish to
authenticate with. HTTP headers will be prefixed with `HTTP_` and have any dashes
converted to underscores. Headers without that prefix can be set by the WSGI server
itself only, which is more secure.

When `REMOTE_USER_HEADER` is set, Healthchecks will:
 - assume the header contains user's email address
 - look up and automatically log in the user with a matching email address
 - automatically create an user account if it does not exist
 - disable the default authentication methods (login link to email, password)

## Integrations

### Slack

To enable the Slack "self-service" integration, you will need to create a "Slack App".

To do so:
* Create a _new Slack app_ on https://api.slack.com/apps/
* Add at least _one scope_ in the permissions section to be able to deploy the app in your workspace (By example `incoming-webhook` for the `Bot Token Scopes`
https://api.slack.com/apps/APP_ID/oauth?).
* Add a _redirect url_ in the format `SITE_ROOT/integrations/add_slack_btn/`.
  For example, if your SITE_ROOT is `https://my-hc.example.org` then the redirect URL would be
  `https://my-hc.example.org/integrations/add_slack_btn/`.
* Look up your Slack app for the Client ID and Client Secret at https://api.slack.com/apps/APP_ID/general? . Put them
  in `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` environment
  variables.


### Discord

To enable Discord integration, you will need to:

* register a new application on https://discordapp.com/developers/applications/me
* add a redirect URI to your Discord application. The URI format is
  `SITE_ROOT/integrations/add_discord/`. For example, if you are running a
  development server on `localhost:8000` then the redirect URI would be
  `http://localhost:8000/integrations/add_discord/`
* Look up your Discord app's Client ID and Client Secret. Put them
  in `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET` environment
  variables.


### Pushover

Pushover integration works by creating an application on Pushover.net which
is then subscribed to by Healthchecks users. The registration workflow is as follows:

* On Healthchecks, the user adds a "Pushover" integration to a project
* Healthchecks redirects user's browser to a Pushover.net subscription page
* User approves adding the Healthchecks subscription to their Pushover account
* Pushover.net HTTP redirects back to Healthchecks with a subscription token
* Healthchecks saves the subscription token and uses it for sending Pushover
  notifications

To enable the Pushover integration, you will need to:

* Register a new application on Pushover via https://pushover.net/apps/build.
* Within the Pushover 'application' configuration, enable subscriptions.
  Make sure the subscription type is set to "URL". Also make sure the redirect
  URL is configured to point back to the root of the Healthchecks instance
  (e.g., `http://healthchecks.example.com/`).
* Put the Pushover application API Token and the Pushover subscription URL in
  `PUSHOVER_API_TOKEN` and `PUSHOVER_SUBSCRIPTION_URL` environment
  variables. The Pushover subscription URL should look similar to
  `https://pushover.net/subscribe/yourAppName-randomAlphaNumericData`.

### Telegram

* Create a Telegram bot by talking to the
[BotFather](https://core.telegram.org/bots#6-botfather). Set the bot's name,
description, user picture, and add a "/start" command.
* After creating the bot you will have the bot's name and token. Put them
in `TELEGRAM_BOT_NAME` and `TELEGRAM_TOKEN` environment variables.
* Run `settelegramwebhook` management command. This command tells Telegram
where to forward channel messages by invoking Telegram's
[setWebhook](https://core.telegram.org/bots/api#setwebhook) API call:

    ```
    $ ./manage.py settelegramwebhook
    Done, Telegram's webhook set to: https://my-monitoring-project.com/integrations/telegram/bot/
    ```

For this to work, your `SITE_ROOT` needs to be correct and use "https://"
scheme.

### Apprise

To enable Apprise integration, you will need to:

* ensure you have apprise installed in your local environment:
```bash
pip install apprise
```
* enable the apprise functionality by setting the `APPRISE_ENABLED` environment variable.

### Shell Commands

The "Shell Commands" integration runs user-defined local shell commands when checks
go up or down. This integration is disabled by default, and can be enabled by setting
the `SHELL_ENABLED` environment variable to `True`.

Note: be careful when using "Shell Commands" integration, and only enable it when
you fully trust the users of your Healthchecks instance. The commands will be executed
by the `manage.py sendalerts` process, and will run with the same system permissions as
the `sendalerts` process.

### Matrix

To enable the Matrix integration you will need to:

* Register a bot user (for posting notifications) in your preferred homeserver.
* Use the [Login API call](https://www.matrix.org/docs/guides/client-server-api#login)
  to retrieve bot user's access token. You can run it as shown in the documentation,
  using curl in command shell.
* Set the `MATRIX_` environment variables. Example:

```
MATRIX_HOMESERVER=https://matrix.org
MATRIX_USER_ID=@mychecks:matrix.org
MATRIX_ACCESS_TOKEN=[a long string of characters returned by the login call]
```

## Running in Production

Here is a non-exhaustive list of pointers and things to check before launching a Healthchecks instance
in production.

* Environment variables, settings.py and local_settings.py.
  * [DEBUG](https://docs.djangoproject.com/en/2.2/ref/settings/#debug). Make sure it is set to `False`.
  * [ALLOWED_HOSTS](https://docs.djangoproject.com/en/2.2/ref/settings/#allowed-hosts). Make sure it
    contains the correct domain name you want to use.
  * Server Errors. When DEBUG=False, Django will not show detailed error pages, and will not print exception
    tracebacks to standard output. To receive exception tracebacks in email,
    review and edit the [ADMINS](https://docs.djangoproject.com/en/2.2/ref/settings/#admins) and
    [SERVER_EMAIL](https://docs.djangoproject.com/en/2.2/ref/settings/#server-email) settings.
    Another good option for receiving exception tracebacks is to use [Sentry](https://sentry.io/for/django/).
* Management commands that need to be run during each deployment.
  * This project uses [Django Compressor](https://django-compressor.readthedocs.io/en/stable/)
    to combine the CSS and JS files. It is configured for offline compression – run the
    `manage.py compress` command whenever files in the `/static/` directory change.
  * This project uses Django's [staticfiles app](https://docs.djangoproject.com/en/2.2/ref/contrib/staticfiles/).
    Run the `manage.py collectstatic` command whenever files in the `/static/`
    directory change. This command collects all the static files inside the `static-collected` directory.
    Configure your web server to serve files from this directory under the `/static/` prefix.
  * Database migration should be run after each update to make sure the database schemas are up to date. You can do that with `./manage.py migrate`.
* Processes that need to be running constantly.
  * `manage.py runserver` is intended for development only. Do not use it in production,
    instead consider using [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) or
    [gunicorn](https://gunicorn.org/).
  * Make sure the `manage.py sendalerts` command is running and can survive server restarts.
    On modern linux systems, a good option is to
    [define a systemd service](https://github.com/healthchecks/healthchecks/issues/273#issuecomment-520560304) for it.
* General
  * Make sure the database is secured well and is getting backed up regularly
  * Make sure the TLS certificates are secured well and are getting refreshed regularly
  * Have monitoring in place to be sure the Healthchecks instance itself is operational
    (is accepting pings, is sending out alerts, is not running out of resources).
