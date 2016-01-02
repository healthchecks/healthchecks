from django.test import TestCase
from hc.api.models import Check, Ping


class CheckModelTestCase(TestCase):

    def test_prune_pings(self):
        check = Check()
        check.save()

        for i in range(0, 6):
            p = Ping(pk=100 + i, owner=check, ua="UA%d" % i)
            p.save()

        check.prune_pings(keep_limit=3)

        self.assertEqual(check.n_pings, 3)

        ua_set = set(Ping.objects.values_list("ua", flat=True))
        # UA0, UA1, UA2 should have been pruned--
        self.assertEqual(ua_set, set(["UA3", "UA4", "UA5"]))
