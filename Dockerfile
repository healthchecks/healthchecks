FROM python:3

MAINTAINER keller.eric@gmail.com
ARG my_mail_host
ENV MY_MAIL_HOST=$my_mail_host
ARG my_admin_user
ENV MY_ADMIN_USER=$my_admin_user
ARG my_admin_email
ENV MY_ADMIN_EMAIL=$my_admin_email

EXPOSE 8000

COPY requirements.txt /tmp
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN groupadd -g 999 appuser && \
    useradd -r -u 999 --home /opt/healthchecks -g appuser appuser
WORKDIR /opt/healthchecks

COPY . .
RUN chown -R appuser:appuser /opt/healthchecks
USER appuser
RUN mv hc/local_settings.py.example hc/local_settings.py
RUN sed -i "s/# EMAIL_HOST = \"your-smtp-server-here.com\"/EMAIL_HOST = \"$MY_MAIL_HOST\"/g" hc/local_settings.py

RUN ./manage.py migrate
RUN ./manage.py createsuperuser --email $MY_ADMIN_EMAIL --username $MY_ADMIN_USER --noinput

CMD [ "python3", "/opt/healthchecks/manage.py", "runserver", "0.0.0.0:8000"]

