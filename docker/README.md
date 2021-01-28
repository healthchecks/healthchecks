# Running with Docker

This is a sample configuration for running Healthchecks with
[Docker](https://www.docker.com) and [Docker Compose](https://docs.docker.com/compose/).

**Note: The Docker configuration is a recent addition, and, for the time being,
should be considered as highly experimental**.

Note: For the sake of simplicity, the sample configuration starts a single database
node and a single web server node, both on the same host. It also does not handle SSL
termination. If you plan to expose it to the public internet, make sure you put a
SSL-terminating load balancer or reverse proxy in front of it.

## Getting Started

* Add your configuration in the `/docker/.env` file.
  As a minimum, set the following fields:
    * `DEFAULT_FROM_EMAIL` – the "From:" address for outbound emails
    * `EMAIL_HOST` – the SMTP server
    * `EMAIL_HOST_PASSWORD` – the SMTP password
    * `EMAIL_HOST_USER` – the SMTP username
    * `SECRET_KEY` – secures HTTP sessions, set to a random value
* Create and start containers:

        $ docker-compose up

* Create a superuser:

        $ docker-compose run web /opt/healthchecks/manage.py createsuperuser

* Open [http://localhost:8000](http://localhost:8000) in your browser and log in with
  the credentials from the previous step.
