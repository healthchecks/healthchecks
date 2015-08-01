import json

from django.test import TestCase

from hc.api.models import Check, Ping


class EmailTestCase(TestCase):

    def test_it_works(self):
        check = Check()
        check.save()

        payload = [{
            "event": "inbound",
            "msg": {
                "raw_msg": "This is raw message",
                "to": ["somewhere@example.com", "%s@example.com" % check.code]
            }
        }]

        data = {"mandrill_events": json.dumps(payload)}
        r = self.client.post("/handle_email/", data=data)
        assert r.status_code == 200

        same_check = Check.objects.get(code=check.code)
        assert same_check.status == "up"

        pings = list(Ping.objects.all())
        assert pings[0].scheme == "email"
        assert pings[0].body == "This is raw message"
