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
* Django 1.8
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

        $ git clone git@github.com:healthchecks/healthchecks.git

* install requirements (Django, ...) into virtualenv:

        $ pip install -r healthchecks/requirements.txt

* make sure PostgreSQL server is installed and running, create
  database "hc":

        $ psql --user postgres
        postgres=# create database hc;

* create database tables, triggers, superuser:

        $ cd ~/webapps/healthchecks
        $ ./manage.py migrate
        $ ./manage.py ensuretriggers
        $ ./manage.py createsuperuser

* run development server:

        $ ./manage.py runserver

