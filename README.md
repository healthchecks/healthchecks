# healthchecks

[![Build Status](https://travis-ci.org/healthchecks/healthchecks.svg?branch=master)](https://travis-ci.org/healthchecks/healthchecks)
[![Coverage Status](https://coveralls.io/repos/healthchecks/healthchecks/badge.svg?branch=master&service=github)](https://coveralls.io/github/healthchecks/healthchecks?branch=master)


![Screenshot of Welcome page](/stuff/screenshots/welcome.png?raw=true "Welcome Page")

![Screenshot of My Checks page](/stuff/screenshots/my_checks.png?raw=true "My Checks Page")

![Screenshot of Period/Grace dialog](/stuff/screenshots/period_grace.png?raw=true "Period/Grace Dialog")

![Screenshot of Channels page](/stuff/screenshots/channels.png?raw=true "Channels Page")

healthchecks is a watchdog for your cron jobs. It's a web server that listens for pings from your cron jobs, plus a web interface.

It is live here: [http://healthchecks.io/](http://healthchecks.io/)

The building blocks are:

* Python 2 or Python 3
* Django 1.9
* PostgreSQL or MySQL

## Setting Up for Development

These are instructions for setting up HealthChecks Django app
in development environment.

* prepare directory for project code and virtualenv:

        $ mkdir -p ~/webapps
        $ cd ~/webapps

* prepare virtual environment
  (with virtualenv you get pip, we'll use it soon to install requirements):

        $ virtualenv --python=python3 hc-venv
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

The site should now be running at `http://localhost:8080`
To log into Django administration site as a super user,
visit `http://localhost:8080/admin`

## Configuration

Site configuration is kept in `hc/settings.py`. Additional configuration
is loaded from `hc/local_settings.py` file, if it exists. You
can create this file (should be right next to `settings.py` in the filesystem)
and override settings as needed.

Some useful settings keys to override are:

`SITE_ROOT` is used to build fully qualified URLs for pings, and for use in
emails and notifications. Example:

    SITE_ROOT = "https://my-monitoring-project.com"

`SITE_NAME` has the default value of "healthchecks.io" and is used throughout
the templates. Replace it with your own name to personalize your installation.
Example:

    SITE_NAME = "My Monitoring Project"

`REGISTRATION_OPEN` controls whether site visitors can create new accounts.
Set it to `False` if you are setting up a private healthchecks instance, but
it needs to be publicly accessible (so, for example, your cloud services
can send pings).

If you close new user registration, you can still selectively invite users
to your team account.


## Database Configuration

Database configuration is stored in `hc/settings.py` and can be overriden
in `hc/local_settings.py`. The default database engine is SQLite. To use
PostgreSQL, create `hc/local_settings.py` if it does not exist, and put the
following in it, changing it as neccessary:

    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     'your-database-name-here',
            'USER':     'your-database-user-here',
            'PASSWORD': 'your-database-password-here',
            'TEST': {'CHARSET': 'UTF8'}
        }
    }

For MySQL:

    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.mysql',
            'NAME':     'your-database-name-here',
            'USER':     'your-database-user-here',
            'PASSWORD': 'your-database-password-here',
            'TEST': {'CHARSET': 'UTF8'}
        }
    }

You can also use `hc/local_settings.py` to read database
configuration from environment variables like so:

    import os

    DATABASES = {
        'default': {
            'ENGINE':   os.environ['DB_ENGINE'],
            'NAME':     os.environ['DB_NAME'],
            'USER':     os.environ['DB_USER'],
            'PASSWORD': os.environ['DB_PASSWORD'],
            'TEST': {'CHARSET': 'UTF8'}
        }
    }


## Sending Emails

healthchecks must be able to send email messages, so it can send out login
links and alerts to users. Put your SMTP server configuration in
`hc/local_settings.py` like so:

    EMAIL_HOST = "your-smtp-server-here.com"
    EMAIL_PORT = 587
    EMAIL_HOST_USER = "username"
    EMAIL_HOST_PASSWORD = "password"
    EMAIL_USE_TLS = True

For more information, have a look at Django documentation,
[Sending Email](https://docs.djangoproject.com/en/1.10/topics/email/) section.

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

    ````
    $ ./manage.py prunepings
    ````

* Remove checks older than 2 hours that are not assigned to users. Such
  checks are by-products of random visitors and robots loading the welcome
  page and never setting up an account:

    ```
    $ ./manage.py prunechecks
    ```

* Remove records of sent email messages older than 7 days.

    ````
    $ ./manage.py pruneemails
    ````

* Remove old records of sent notifications. For each check, remove
  notifications that are older than the oldest stored ping for same check.

    ````
    $ ./manage.py prunenotifications
    ````

* Remove user accounts that match either of these conditions:
 * Account was created more than 6 months ago, and user has never logged in.
   These can happen when user enters invalid email address when signing up.
 * Last login was more than 6 months ago, and the account has no checks.
   Assume the user doesn't intend to use the account any more and would
   probably *want* it removed.

    ```
    $ ./manage.py pruneusers
    ```

When you first try these commands on your data, it is a good idea to
test them on a copy of your database, not on the live database right away.
In a production setup, you should also have regular, automated database
backups set up.

## Integrations

### Pushover

To enable Pushover integration, you will need to:

* register a new application on https://pushover.net/apps/build
* enable subscriptions in your application and make sure to enable the URL
  subscription type
* add the application token and subscription URL to `hc/local_settings.py`, as
  `PUSHOVER_API_TOKEN` and `PUSHOVER_SUBSCRIPTION_URL`

### Telegram

* Create a Telegram bot by talking to the
[BotFather](https://core.telegram.org/bots#6-botfather). Set the bot's name,
description, user picture, and add a "/start" command.
* After creating the bot you will have the bot's name and token. Add them
to your `hc/local_settings.py` file as `TELEGRAM_BOT_NAME` and
`TELEGRAM_TOKEN` fields.
* Now the tricky part: when a Telegram user talks to your bot,
Telegram will use a webhook to forward received messages to your healthchecks
instance. For this to work, your healthchecks instance needs to be publicly
accessible over HTTPS. Using the
[setWebhook](https://core.telegram.org/bots/api#setwebhook) API call
set the bot's webhook to `https://yourdomain.com/integrations/telegram/bot/`.





