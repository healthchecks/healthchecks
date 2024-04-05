FROM python:3.12-slim-bookworm as builder

COPY requirements.txt /tmp
RUN \
    apt-get update && \
    apt-get install -y build-essential git libpq-dev libmariadb-dev libffi-dev libssl-dev libcurl4-openssl-dev libpython3-dev rustc pkg-config
ENV CARGO_NET_GIT_FETCH_WITH_CLI true
RUN \
    pip install --upgrade pip && \
    pip wheel --wheel-dir /wheels apprise uwsgi mysqlclient minio -r /tmp/requirements.txt

COPY . /opt/healthchecks/
RUN \
    rm -rf /opt/healthchecks/.git && \
    rm -rf /opt/healthchecks/stuff

FROM python:3.12-slim-bookworm

RUN useradd --system hc
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/healthchecks

RUN \
    apt-get update && \
    apt-get install -y libcurl4 libpq5 libmariadb3 libxml2 && \
    rm -rf /var/apt/cache && \
    rm -rf /var/lib/apt/lists


RUN --mount=type=bind,target=/wheels,source=/wheels,from=builder \
    pip install --upgrade pip && \
    pip install --no-cache /wheels/*

COPY --from=builder /opt/healthchecks/ /opt/healthchecks/

RUN \
    rm -f /opt/healthchecks/hc/local_settings.py && \
    DEBUG=False SECRET_KEY=build-key ./manage.py collectstatic --noinput && \
    DEBUG=False SECRET_KEY=build-key ./manage.py compress

RUN mkdir /data && chown hc /data

USER hc

ENV USE_GZIP_MIDDLEWARE=True
CMD [ "uwsgi", "/opt/healthchecks/docker/uwsgi.ini"]
