FROM python:3.8

RUN useradd --system hc
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/healthchecks

COPY requirements.txt /tmp
RUN \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install uwsgi

COPY . /opt/healthchecks/

RUN \
    rm -f /opt/healthchecks/hc/local_settings.py && \
    DEBUG=False SECRET_KEY=build-key ./manage.py collectstatic --noinput && \
    DEBUG=False SECRET_KEY=build-key ./manage.py compress

USER hc

CMD [ "uwsgi", "/opt/healthchecks/docker/uwsgi.ini"]

