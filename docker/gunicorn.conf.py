from os import getenv

forwarded_allow_ips = "*"
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
# Disable control socket, will not be using it
control_socket = ""

# If $GUNICORN_WORKERS is set, use that.
# Next, if $UWSGI_PROCESSES is set, use that (for backwards compatibility).
# Otherwise, default to 4.
workers = int(getenv("GUNICORN_WORKERS") or getenv("UWSGI_PROCESSES") or "4")

_port = getenv("GUNICORN_PORT", "8000")
bind = f"[::]:{_port}" if getenv("LISTEN_IPV6") else f":{_port}"

# Enable access log to stdout if neither GUNICORN_DISABLE_LOGGING
# nor UWSGI_DISABLE_LOGGING is set
if not getenv("GUNICORN_DISABLE_LOGGING") and not getenv("UWSGI_DISABLE_LOGGING"):
    accesslog = "-"

