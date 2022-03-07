FROM python:3.10-slim-buster as builder

COPY requirements.txt /tmp
RUN apt update && apt install -y build-essential libpq-dev libmariadb-dev libffi-dev libssl-dev rustc
RUN \
    pip install --upgrade pip && \
    pip wheel --wheel-dir /wheels apprise uwsgi mysqlclient -r /tmp/requirements.txt

COPY . /opt/healthchecks/
RUN rm -rf /opt/healthchecks/.git

FROM python:3.10-slim-buster

RUN useradd --system hc
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/healthchecks

COPY --from=builder /wheels /wheels

RUN \
    apt update && \
    apt install -y libpq5 libmariadb3 && \
    rm -rf /var/apt/cache

RUN \
    pip install --upgrade pip && \
    pip install --no-cache /wheels/*

COPY --from=builder /opt/healthchecks/ /opt/healthchecks/

RUN \
    rm -f /opt/healthchecks/hc/local_settings.py && \
    DEBUG=False SECRET_KEY=build-key ./manage.py collectstatic --noinput && \
    DEBUG=False SECRET_KEY=build-key ./manage.py compress

USER hc

CMD [ "uwsgi", "/opt/healthchecks/docker/uwsgi.ini"]