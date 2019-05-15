from hc.test import BaseTestCase
from hc.accounts.models import Project
from hc.api.models import Check


class ProjectModelTestCase(BaseTestCase):
    def test_num_checks_available_handles_multiple_projects(self):
        # One check in Alice's primary project:
        Check.objects.create(project=self.project)

        # One check in Alice's secondary project:
        p2 = Project.objects.create(owner=self.alice)
        Check.objects.create(project=p2)

        self.assertEqual(self.project.num_checks_available(), 18)
