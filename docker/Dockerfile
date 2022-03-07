FROM python:3.9-slim-buster as builder

COPY requirements.txt /tmp
RUN apt update && apt install -y build-essential libpq-dev libmariadb-dev

RUN \
    if [ `dpkg --print-architecture` = "armhf" ]; then \
    printf "[global]\nextra-index-url=https://www.piwheels.org/simple\n" > /etc/pip.conf ; \
    fi
RUN pip wheel --wheel-dir /wheels apprise uwsgi mysqlclient -r /tmp/requirements.txt

FROM python:3.9-slim-buster

RUN useradd --system hc
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/healthchecks

COPY requirements.txt /tmp
COPY --from=builder /wheels /wheels

RUN \
    apt update && \
    apt install -y libpq5 libmariadb3 && \
    rm -rf /var/apt/cache

RUN pip install --no-cache /wheels/*

COPY . /opt/healthchecks/

RUN \
    rm -f /opt/healthchecks/hc/local_settings.py && \
    DEBUG=False SECRET_KEY=build-key ./manage.py collectstatic --noinput && \
    DEBUG=False SECRET_KEY=build-key ./manage.py compress

USER hc

CMD [ "uwsgi", "/opt/healthchecks/docker/uwsgi.ini"]
