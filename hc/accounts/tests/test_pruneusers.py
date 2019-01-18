from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from hc.accounts.management.commands.pruneusers import Command
from hc.accounts.models import Project
from hc.api.models import Check
from hc.test import BaseTestCase


class PruneUsersTestCase(BaseTestCase):
    year_ago = timezone.now() - timedelta(days=365)

    def test_it_removes_old_never_logged_in_users(self):
        self.charlie.date_joined = self.year_ago
        self.charlie.save()

        # Charlie has one demo check
        charlies_project = Project.objects.create(owner=self.charlie)
        Check(project=charlies_project).save()

        Command().handle()

        self.assertEqual(User.objects.filter(username="charlie").count(), 0)
        self.assertEqual(Check.objects.count(), 0)

    def test_it_leaves_team_members_alone(self):
        self.bob.date_joined = self.year_ago
        self.bob.last_login = self.year_ago
        self.bob.save()

        Command().handle()
        # Bob belongs to a team so should not get removed
        self.assertEqual(User.objects.filter(username="bob").count(), 1)
