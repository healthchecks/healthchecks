FROM python:3

RUN mkdir /app

COPY hc /app/hc
COPY static /app/static
COPY stuff /app/stuff
COPY templates /app/templates
COPY manage.py /app/manage.py
COPY requirements.txt /app/requirements.txt

COPY entrypoint /app/entrypoint
RUN chmod +x /app/entrypoint

WORKDIR /app

RUN  ["pip", "install", "-r", "requirements.txt"]
