# Running with Docker

In the Healthchecks source code, [/docker/ directory](https://github.com/healthchecks/healthchecks/tree/master/docker),
you can find a sample configuration for running the project with
[Docker](https://www.docker.com) and [Docker Compose](https://docs.docker.com/compose/).

Note: For the sake of simplicity, the sample configuration starts a single database
node and a single web server node, both on the same host. It does not handle TLS
termination.

## Getting Started

* Grab the Healthchecks source code
  [from the GitHub repository](https://github.com/healthchecks/healthchecks).
* Copy `docker/.env.example` to `docker/.env` and add your configuration in it.
  As a minimum, set the following fields:
    * `DEFAULT_FROM_EMAIL` – the "From:" address for outbound emails
    * `EMAIL_HOST` – the SMTP server
    * `EMAIL_HOST_PASSWORD` – the SMTP password
    * `EMAIL_HOST_USER` – the SMTP username
    * `SECRET_KEY` – secures HTTP sessions, set to a random value
* Create and start containers:

        $ cd docker
        $ docker-compose up

* Create a superuser:

        $ docker-compose run web /opt/healthchecks/manage.py createsuperuser

* Open [http://localhost:8000](http://localhost:8000) in your browser and log in with
  the credentials from the previous step.

## uWSGI Configuration

The reference Dockerfile uses [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)
as the WSGI server. You can configure uWSGI by setting `UWSGI_...` environment
variables in `docker/.env`. For example, to disable HTTP request logging, set:

    UWSGI_DISABLE_LOGGING=1

Read more about configuring uWSGI in [uWSGI documentation](https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html#environment-variables).

## TLS Termination

If you plan to expose your Healthchecks instance to the public internet, make sure you
put a TLS-terminating reverse proxy in front of it.

**Important:** This Dockerfile uses UWSGI, which relies on the [X-Forwarded-Proto](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-Proto)
header to determine if a request is secure or not. Make sure your TLS-terminating
reverse proxy:

* Discards the X-Forwarded-Proto header sent by the end user.
* Sets the X-Forwarded-Proto header value to match the protocol of the original request
  ("http" or "https").

For example, in NGINX you can use the `$scheme` variable like so:

```text
proxy_set_header X-Forwarded-Proto $scheme;
```
