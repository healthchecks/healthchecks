"""

Populate api_check.n_pings and api_ping.n fields.

 - api_ping.n stores ping's serial number, counted separately for
 each check. For example, if a particular check has received 100 pings,
 its first ping will have a n=1, and the 100th ping will have a n=100.

 - api_check.n_pings stores the last serial number assigned to a ping.
 It also is the total number of pings the check has ever received.

This command works by "replaying" stored pings in their primary
key order, and counting up their serial numbers. At the very end,
api_check.n_pings fields are updated as well.

Depending on the size of api_ping table, this command can potentially
take a long time to complete.

Note on ping pruning: when the prunepings command is run, some of the
pings with the lowest serial numbers get removed. This doesn't affect
the "n" field for remaining pings, or the "n_pings" value of checks.
The serial numbers keep going up.

"""

import gc
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from hc.api.models import Check, Ping


class Command(BaseCommand):
    help = 'Fill check.n_pings field and ping.n field'

    def handle(self, *args, **options):
        connection.use_debug_cursor = False
        chunksize = 2000

        # Reset all n_pings fields to zero
        Check.objects.update(n_pings=0)

        counts = Counter()

        pk = 0
        last_pk = Ping.objects.order_by('-pk')[0].pk
        queryset = Ping.objects.order_by('pk')

        while pk < last_pk:
            transaction.set_autocommit(False)
            while pk < last_pk:
                for ping in queryset.filter(pk__gt=pk)[:chunksize]:
                    pk = ping.pk
                    counts[ping.owner_id] += 1

                    ping.n = counts[ping.owner_id]
                    ping.save(update_fields=("n", ))

                gc.collect()
                progress = 100 * pk / last_pk
                self.stdout.write(
                    "Processed ping id %d (%.2f%%)" % (pk, progress))

                transaction.commit()

            transaction.set_autocommit(True)
            # last_pk might have increased because of influx of new pings:
            last_pk = Ping.objects.order_by('-pk')[0].pk

        self.stdout.write("Updating check.n_pings")
        for check_id, n_pings in counts.items():
            Check.objects.filter(pk=check_id).update(n_pings=n_pings)

        return "Done!"
