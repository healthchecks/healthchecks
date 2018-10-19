FROM python:3

MAINTAINER keller.eric@gmail.com
ARG my_mail_host
ENV MY_MAIL_HOST=$my_mail_host
ARG my_admin_user
ENV MY_ADMIN_USER=$my_admin_user
ARG my_admin_email
ENV MY_ADMIN_EMAIL=$my_admin_email
EXPOSE 8000
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mv hc/local_settings.py.example hc/local_settings.py
RUN sed -i "s/# EMAIL_HOST = \"your-smtp-server-here.com\"/EMAIL_HOST = \"$MY_MAIL_HOST\"/g" hc/local_settings.py
RUN ./manage.py migrate
RUN ./manage.py createsuperuser --email $MY_ADMIN_EMAIL --username $MY_ADMIN_USER --noinput

CMD [ "python3", "/usr/src/app/manage.py", "runserver", "0.0.0.0:8000"]

