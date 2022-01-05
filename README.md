# Healthchecks

![Build Status](https://github.com/healthchecks/healthchecks/workflows/Django%20CI/badge.svg)
[![Coverage Status](https://coveralls.io/repos/healthchecks/healthchecks/badge.svg?branch=master&service=github)](https://coveralls.io/github/healthchecks/healthchecks?branch=master)


![Screenshot of My Checks page](/static/img/my_checks.png?raw=true "My Checks Page")

![Screenshot of Period/Grace dialog](/static/img/period_grace.png?raw=true "Period/Grace Dialog")

![Screenshot of Cron dialog](/static/img/cron.png?raw=true "Cron Dialog")

![Screenshot of Check Details page](/static/img/check_details.png?raw=true "My Checks Page")

![Screenshot of Badges page](/static/img/badges.png?raw=true "Integrations Page")

Healthchecks is a cron job monitoring service. It listens for HTTP requests
and email messages ("pings") from your cron jobs and scheduled tasks ("checks").
When a ping does not arrive on time, Healthchecks sends out alerts.

Healthchecks comes with a web dashboard, API, 25+ integrations for
delivering notifications, monthly email reports, WebAuthn 2FA support,
team management features: projects, team members, read-only access.

The building blocks are:

* Python 3.8+
* Django 4
* PostgreSQL or MySQL

Healthchecks is licensed under the BSD 3-clause license.

Healthchecks is available as a hosted service
at [https://healthchecks.io/](https://healthchecks.io/).

## Setting Up for Development

To set up Healthchecks development environment:

* Install dependencies (Debian/Ubuntu):

        $ sudo apt-get update
        $ sudo apt-get install -y gcc python3-dev python3-venv libpq-dev

* Prepare directory for project code and virtualenv. Feel free to use a
  different location:

        $ mkdir -p ~/webapps
        $ cd ~/webapps

* Prepare virtual environment
  (with virtualenv you get pip, we'll use it soon to install requirements):

        $ python3 -m venv hc-venv
        $ source hc-venv/bin/activate
        $ pip3 install wheel # make sure wheel is installed in the venv

* Check out project code:

        $ git clone https://github.com/healthchecks/healthchecks.git

* Install requirements (Django, ...) into virtualenv:

        $ pip install -r healthchecks/requirements.txt


* Create database tables and a superuser account:

        $ cd ~/webapps/healthchecks
        $ ./manage.py migrate
        $ ./manage.py createsuperuser

  With the default configuration, Healthchecks stores data in a SQLite file
  `hc.sqlite` in the checkout directory (`~/webapps/healthchecks`).

  To use PostgreSQL or MySQL, see the section **Database Configuration** section
  below.

* Run tests:

        $ ./manage.py test

* Run development server:

        $ ./manage.py runserver

The site should now be running at `http://localhost:8000`.
To access Django administration site, log in as a superuser, then
visit `http://localhost:8000/admin/`

## Configuration

Healthchecks reads configuration from environment variables.

[Full list of configuration parameters](https://healthchecks.io/docs/self_hosted_configuration/).

## Accessing Administration Panel

Healthchecks comes with Django's administration panel where you can manually
view and modify user accounts, projects, checks, integrations etc. To access it,

 * if you haven't already, create a superuser account: `./manage.py createsuperuser`
 * log into the site using superuser credentials
 * in the top navigation, "Account" dropdown, select "Site Administration"


## Sending Emails

Healthchecks must be able to send email messages, so it can send out login
links and alerts to users. Specify your SMTP credentials using the following
environment variables:

```python
EMAIL_HOST = "your-smtp-server-here.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = "smtp-username"
EMAIL_HOST_PASSWORD = "smtp-password"
EMAIL_USE_TLS = True
```

For more information, have a look at Django documentation,
[Sending Email](https://docs.djangoproject.com/en/1.10/topics/email/) section.

## Receiving Emails

Healthchecks comes with a `smtpd` management command, which starts up a
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

Healthchecks deletes old entries from `api_ping` and `api_notification`
tables automatically. By default, Healthchecks keeps the 100 most recent
pings for every check. You can set the limit higher to keep a longer history:
go to the Administration Panel, look up user's **Profile** and modify its
"Ping log limit" field.

For each check, Healthchecks removes notifications that are older than the
oldest stored ping for same check.

Healthchecks also provides management commands for cleaning up
`auth_user`, `api_tokenbucket` and `api_flip` tables.

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

Healthchecks supports external authentication by means of HTTP headers set by
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

### Signal

Healthchecks uses [signal-cli](https://github.com/AsamK/signal-cli) to send Signal
notifications. Healthcecks interacts with signal-cli over DBus.

To enable the Signal integration:

* Set up and configure signal-cli to listen on DBus system bus ([instructions](https://github.com/AsamK/signal-cli/wiki/DBus-service)).
  Make sure you can send test messages from command line, using the `dbus-send`
  example given in the signal-cli instructions.
* Set the `SIGNAL_CLI_ENABLED` environment variable to `True`.


### Telegram

* Create a Telegram bot by talking to the
[BotFather](https://core.telegram.org/bots#6-botfather). Set the bot's name,
description, user picture, and add a "/start" command. To avoid user confusion,
please do not use the Healthchecks.io logo as your bot's user picture, use
your own logo.
* After creating the bot you will have the bot's name and token. Put them
in `TELEGRAM_BOT_NAME` and `TELEGRAM_TOKEN` environment variables.
* Run `settelegramwebhook` management command. This command tells Telegram
where to forward channel messages by invoking Telegram's
[setWebhook](https://core.telegram.org/bots/api#setwebhook) API call:

    ```
    $ ./manage.py settelegramwebhook
    Done, Telegram's webhook set to: https://my-monitoring-project.com/integrations/telegram/bot/
    ```

For this to work, your `SITE_ROOT` must be correct and must use the "https://"
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

### PagerDuty Simple Install Flow

To enable PagerDuty [Simple Install Flow](https://developer.pagerduty.com/docs/app-integration-development/events-integration/),

* Register a PagerDuty app at [PagerDuty](https://pagerduty.com/) › Developer Mode › My Apps
* In the newly created app, add the "Events Integration" functionality
* Specify a Redirect URL: `https://your-domain.com/integrations/add_pagerduty/`
* Copy the displayed app_id value (PXXXXX) and put it in the `PD_APP_ID` environment
  variable

## Running in Production

Here is a non-exhaustive list of pointers and things to check before launching a Healthchecks instance
in production.

* Environment variables, settings.py and local_settings.py.
  * [DEBUG](https://docs.djangoproject.com/en/2.2/ref/settings/#debug). Make sure it is
    set to `False`.
  * [ALLOWED_HOSTS](https://docs.djangoproject.com/en/2.2/ref/settings/#allowed-hosts).
    Make sure it contains the correct domain name you want to use.
  * Server Errors. When DEBUG=False, Django will not show detailed error pages, and
    will not print exception tracebacks to standard output. To receive exception
    tracebacks in email, review and edit the
    [ADMINS](https://docs.djangoproject.com/en/2.2/ref/settings/#admins) and
    [SERVER_EMAIL](https://docs.djangoproject.com/en/2.2/ref/settings/#server-email)
    settings. Consider setting up exception logging with [Sentry](https://sentry.io/for/django/).
* Management commands that need to be run during each deployment.
  * `manage.py compress` – creates combined JS and CSS bundles and
     places them in the `static-collected` directory.
  * `manage.py collectstatic` – collects static files in the `static-collected`
     directory.
  * `manage.py migrate` – applies any pending database schema changes
     and data migrations.
* Processes that need to be running constantly.
  * `manage.py runserver` is intended for development only.
     **Do not use it in production**, instead consider using
     [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) or
     [gunicorn](https://gunicorn.org/).
  *  `manage.py sendalerts` is the process that monitors checks and sends out
     monitoring alerts. It must be always running, it must be started on reboot, and it
     must be restarted if it itself crashes. On modern linux systems, a good option is
     to [define a systemd service](https://github.com/healthchecks/healthchecks/issues/273#issuecomment-520560304)
     for it.
* Static files. Healthchecks serves static files on its own, no configuration
  required. It uses the [Whitenoise library](http://whitenoise.evans.io/en/stable/index.html)
  for this.
* General
  * Make sure the database is secured well and is getting backed up regularly
  * Make sure the TLS certificates are secured well and are getting refreshed regularly
  * Have monitoring in place to be sure the Healthchecks instance itself is operational
    (is accepting pings, is sending out alerts, is not running out of resources).
