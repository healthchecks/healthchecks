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

# Start the HTTP server
gunicorn hc.wsgi:application &

# Wait for any process to exit, return its exit code
wait -n
exit $?