ARG BUILD_DATE=""
ARG ARCH=amd64
ARG PYTHON_VERSION=3


# First stage
FROM docker.io/${ARCH}/python:${PYTHON_VERSION}-alpine3.8 as builder

# Install deps
COPY requirements.txt /tmp

RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    linux-headers

RUN pip install --prefix="/install" --no-warn-script-location -r /tmp/requirements.txt \
    braintree \
    uWSGI


## Second stage
FROM docker.io/${ARCH}/python:${PYTHON_VERSION}-alpine3.8

ENV DEBUG False
ENV DB_NAME /data/hc.sqlite

RUN apk add --no-cache libpq \
    mailcap

RUN addgroup -g 900 -S healthchecks && \
    adduser -u 900 -S healthchecks -G healthchecks

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN ./manage.py collectstatic --noinput && \
    ./manage.py compress

RUN mkdir /data && chown healthchecks:healthchecks /data

VOLUME /data

USER healthchecks 

EXPOSE 8000/tcp

ARG SYNAPSE_VERSION
ARG PYTHON_VERSION
ARG BUILD_DATE

CMD ["uwsgi", "--enable-threads", "uwsgi.ini"]
