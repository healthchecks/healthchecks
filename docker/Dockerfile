FROM python:3.11-slim-bullseye as builder

COPY requirements.txt /tmp
RUN apt update && apt install -y build-essential curl git libpq-dev libmariadb-dev libffi-dev libssl-dev libcurl4-openssl-dev libpython3-dev pkg-config
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="${PATH}:/root/.cargo/bin"
ENV CARGO_NET_GIT_FETCH_WITH_CLI true
RUN \
    pip install --upgrade pip && \
    pip wheel --wheel-dir /wheels apprise uwsgi mysqlclient minio -r /tmp/requirements.txt

COPY . /opt/healthchecks/
RUN rm -rf /opt/healthchecks/.git

FROM python:3.11-slim-bullseye

RUN useradd --system hc
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/healthchecks

COPY --from=builder /wheels /wheels

RUN \
    apt update && \
    apt install -y libcurl4 libpq5 libmariadb3 && \
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

ENV USE_GZIP_MIDDLEWARE=True
CMD [ "uwsgi", "/opt/healthchecks/docker/uwsgi.ini"]
