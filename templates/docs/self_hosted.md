# Self-Hosted Healthchecks

Healthchecks is open-source, and is licensed under the BSD 3-clause license.

Rather than using the hosted service at
[https://healthchecks.io](https://healthchecks.io), you have the option to host an
instance yourself.

The building blocks are:

* Python 3.6+
* Django 3
* PostgreSQL or MySQL

## Setting Up for Development


You can set up a development environment in a Python
[virtual environment](https://docs.python.org/3/tutorial/venv.html)
on your local system to develop a new feature, write a new integration
or test a bugfix.

The following instructions assume you are using a Debian-based OS.

* Install dependencies:

        $ sudo apt-get update
        $ sudo apt-get install -y gcc python3-dev python3-venv

* Prepare directory for project code and virtualenv. Feel free to use a
  different location:

        $ mkdir -p ~/webapps
        $ cd ~/webapps

* Prepare virtual environment
  (with virtualenv you get pip, we'll use it soon to install requirements):

        $ python3 -m venv hc-venv
        $ source hc-venv/bin/activate

* Check out project code:

        $ git clone https://github.com/healthchecks/healthchecks.git

* Install requirements (Django, ...) into virtualenv:

        $ pip install wheel
        $ pip install -r healthchecks/requirements.txt


* Create database tables and a superuser account:

        $ cd ~/webapps/healthchecks
        $ ./manage.py migrate
        $ ./manage.py createsuperuser

  With the default configuration, Healthchecks stores data in a SQLite file
  `hc.sqlite` in the checkout directory (`~/webapps/healthchecks`).

* Run tests:

        $ ./manage.py test

* Run development server:

        $ ./manage.py runserver

At this point, the site should now be running at `http://localhost:8000`.

To access Django administration site, log in as a superuser, then
visit `http://localhost:8000/admin/`.

FIXME note about no email configuration, no sendalerts, and the devserver

## Next Steps

Get the [source code](https://github.com/healthchecks/healthchecks).

See [Configuration](../self_hosted_configuration/) for a list of configuration options.

