ARG BUILD_DATE


# First stage
FROM python:3.8-rc-alpine as builder

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
FROM python:3.8-rc-alpine

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

CMD ["uwsgi","uwsgi.ini"]
