from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.utils.timezone import now

from hc.accounts.models import Project
from hc.api.models import Channel, Check, Flip


# Needs to subclass from TransactionTestCase not BaseTestCase,
# otherwise test_it_handles_deleted_channel will not work properly.
class NotifyTestCase(TransactionTestCase):
    def _setup_data(self, kind: str, value: str, status: str = "down") -> None:
        self.alice = User.objects.create(username="alice")
        self.project = Project.objects.create(owner=self.alice)
        self.check = Check.objects.create(project=self.project)

        self.channel = Channel(project=self.project)
        self.channel.kind = kind
        self.channel.value = value
        self.channel.email_verified = True
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status

    def test_unexpected_channel_kind_raises_not_implemented(self) -> None:
        self._setup_data("invalid", "dummy data")

        with self.assertRaises(NotImplementedError):
            self.channel.notify(self.flip)

    def test_it_handles_deleted_channel(self) -> None:
        self._setup_data("email", "foo@example.org")

        # Change channel's id to a non-existent value.
        # notify() creates a Notification object, this will cause an IntegrityError.
        # We are testing if IntegrityError is handled.
        self.channel.id = -1
        e = self.channel.notify(self.flip)
        self.assertEqual(e, "Channel or check does not exist any more")
