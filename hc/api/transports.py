from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import json
import requests

from hc.lib import emails


def tmpl(template_name, **ctx):
    template_path = "integrations/%s" % template_name
    return render_to_string(template_path, ctx).strip()


class Transport(object):
    def __init__(self, channel):
        self.channel = channel

    def notify(self, check):
        """ Send notification about current status of the check.

        This method returns None on success, and error message
        on error.

        """

        raise NotImplementedError()

    def test(self):
        """ Send test message.

        This method returns None on success, and error message
        on error.

        """

        raise NotImplementedError()

    def checks(self):
        return self.channel.user.check_set.order_by("created")


class Email(Transport):
    def notify(self, check):
        if not self.channel.email_verified:
            return "Email not verified"

        ctx = {
            "check": check,
            "checks": self.checks(),
            "now": timezone.now()
        }
        emails.alert(self.channel.value, ctx)


class Webhook(Transport):
    def notify(self, check):
        # Webhook integration only fires when check goes down.
        if check.status != "down":
            return "no-op"

        # Webhook transport sends no arguments, so the
        # notify and test actions are the same
        return self.test()

    def test(self):
        headers = {"User-Agent": "healthchecks.io"}
        try:
            r = requests.get(self.channel.value, timeout=5, headers=headers)
            if r.status_code not in (200, 201):
                return "Received status code %d" % r.status_code
        except requests.exceptions.Timeout:
            # Well, we tried
            return "Connection timed out"
        except requests.exceptions.ConnectionError:
            return "A connection to %s failed" % self.channel.value


class JsonTransport(Transport):
    def post(self, url, payload):
        headers = {"User-Agent": "healthchecks.io"}
        try:
            r = requests.post(url, json=payload, timeout=5, headers=headers)
            if r.status_code not in (200, 201):
                return "Received status code %d" % r.status_code
        except requests.exceptions.Timeout:
            # Well, we tried
            return "Connection timed out"
        except requests.exceptions.ConnectionError:
            return "A connection to %s failed" % url


class Slack(JsonTransport):
    def notify(self, check):
        text = tmpl("slack_message.json", check=check)
        payload = json.loads(text)
        return self.post(self.channel.value, payload)


class HipChat(JsonTransport):
    def notify(self, check):
        text = tmpl("hipchat_message.html", check=check)
        payload = {
            "message": text,
            "color": "green" if check.status == "up" else "red",
        }
        return self.post(self.channel.value, payload)


class PagerDuty(JsonTransport):
    URL = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"

    def notify(self, check):
        description = tmpl("pd_description.html", check=check)
        payload = {
            "service_key": self.channel.value,
            "incident_key": str(check.code),
            "event_type": "trigger" if check.status == "down" else "resolve",
            "description": description,
            "client": "healthchecks.io",
            "client_url": settings.SITE_ROOT
        }

        return self.post(self.URL, payload)


class Pushover(JsonTransport):
    URL = "https://api.pushover.net/1/messages.json"

    def notify(self, check):
        others = self.checks().filter(status="down").exclude(code=check.code)
        ctx = {
            "check": check,
            "down_checks":  others,
        }
        text = tmpl("pushover_message.html", **ctx)
        title = tmpl("pushover_title.html", **ctx)
        user_key, prio = self.channel.value.split("|")
        payload = {
            "token": settings.PUSHOVER_API_TOKEN,
            "user": user_key,
            "message": text,
            "title": title,
            "html": 1,
            "priority": int(prio),
        }

        # Emergency notification
        if prio == "2":
            payload["retry"] = settings.PUSHOVER_EMERGENCY_RETRY_DELAY
            payload["expire"] = settings.PUSHOVER_EMERGENCY_EXPIRATION

        return self.post(self.URL, payload)
