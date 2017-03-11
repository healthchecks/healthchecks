FROM python:3-alpine

# Caching layer with bash, tini, UWSGI and mysql / pg clients
RUN set -ex \
  && apk add --no-cache mariadb-libs mariadb-client-libs postgresql-libs tini bash \
  && apk add --no-cache --virtual .build-deps \
    gcc \
    # uwsgi needs linux headers
    linux-headers \
    # pip install needs py3 & musl dev
    python3-dev \
    musl-dev \
    mariadb-dev \
    postgresql-dev\
  && pip3 install --no-cache-dir uwsgi mysqlclient psycopg2==2.6.2 \
  && apk del .build-deps

# Add hc user
RUN adduser -D -u 1000 hc

# Install app requirements
COPY requirements.txt /usr/src/app/
WORKDIR /usr/src/app/
RUN set -ex \
  && apk add --no-cache --virtual .build-deps \
    gcc \
    python3-dev \
    musl-dev \
  && pip3 install braintree \
  && pip3 install --no-cache-dir -r requirements.txt \
  && apk del .build-deps


# Copy application source
COPY . /usr/src/app

# Read settings from env vars
RUN cp hc/local_settings.py.docker hc/local_settings.py

# Pre-compile assets
RUN set -ex \
  && ./manage.py collectstatic --no-input \
  && ./manage.py compress \
  && chown -R hc:hc /usr/src/app

EXPOSE 9090
ENTRYPOINT [ "/usr/bin/tini", "--" ]
CMD [ "/usr/src/app/bin/uwsgi-start.sh" ]
