#!/bin/sh
set -ex

# wait for database connection to run migration
while ! ./manage.py migrate 2>&1; do
    sleep 5
done

#replace bash with uwsgi
exec uwsgi --master \
    --uid hc \
    --gid hc \
    --http-socket 0.0.0.0:9090 \
    --processes 2 \
    --threads 2 \
    --chdir /usr/src/app \
    --module hc.wsgi:application \
    --enable-threads \
    --thunder-lock \
    --static-map /static=/usr/src/app/static-collected \
    --attach-daemon "./manage.py sendalerts"
