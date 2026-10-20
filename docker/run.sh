#!/bin/bash
set -e

cleanup() {
	echo "Parent (PGID: $$) received signal. Killing process group..."
	kill -SIGTERM -$$
	wait
	exit 0
}

# Install a SIGINT and SIGTERM handler (which sends SIGTERM to all processes)
trap cleanup SIGINT SIGTERM

# Run the database migrations
./manage.py migrate

# Start sendalerts and sendreports as background processes
./manage.py sendalerts --skip-checks &
./manage.py sendreports --loop --skip-checks &

# Start smtpd only if $SMTPD_PORT is set
if [ ! -z $SMTPD_PORT ]; then
	./manage.py smtpd --port $SMTPD_PORT &
fi

# Worker count:
# If $GUNICORN_WORKERS is set, use that.
# Otherwise, if $UWSGI_PROCESSES is set, use that (for backwards compatibility).
# Otherwise, default to 4.
GUNICORN_WORKERS="${GUNICORN_WORKERS:-${UWSGI_PROCESSES:-4}}"

# Listen on IPv4 only by default.
# If $LISTEN_IPV6 is set then listen on IPv4 and IPv6.
if [ -z $LISTEN_IPV6 ]; then
	GUNICORN_BIND=':8000'
else
	GUNICORN_BIND='[::]:8000'
fi

gunicorn hc.wsgi:application \
	--no-control-socket \
	--forwarded-allow-ips '*' \
	--bind $GUNICORN_BIND \
	--workers $GUNICORN_WORKERS \
	--access-logfile - &

# Wait for any process to exit, return its exit code
wait -n
exit $?