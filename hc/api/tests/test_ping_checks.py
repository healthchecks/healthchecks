from django.test import TestCase
from django.urls import reverse
from hc.api.models import Check, Project
from django.contrib.auth.models import User
from uuid import uuid4


class PingTestCase(TestCase):
    def setUp(self):
        # Create a User object
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password")

        # Create a Project object associated with the user
        self.project = Project.objects.create(name="Test Project", owner=self.user)

        # Create a Check object associated with the project
        self.check = Check.objects.create(
            code=uuid4(),
            project=self.project,  # Associate with the project
            filter_body=True,  # Enable filtering by message body
        )
        self.ping_url = reverse("hc-ping", args=[self.check.code])

    def test_ping_success(self):
        """
        Test that a request with success keywords sets the status to 'up'
        """
        # Set success keywords
        self.check.success_kw = "ok,success"
        self.check.save()

        # Send a POST request with a success keyword
        response = self.client.post(self.ping_url, data="status=success", content_type="text/plain")

        # Refresh from the database and assert the status
        self.check.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Success")  # Response matches the action
        self.assertEqual(self.check.status, "up")  # Status of the Check is updated to 'up'

    def test_ping_failure(self):
        """
        Test that a request with failure keywords sets the status to 'down'
        """
        # Set failure keywords
        self.check.failure_kw = "fail,error"
        self.check.save()

        # Send a POST request with a failure keyword
        response = self.client.post(self.ping_url, data="status=fail", content_type="text/plain")

        # Refresh from the database and assert the status
        self.check.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Fail")  # Response matches the action
        self.assertEqual(self.check.status, "down")  # Status of the Check is updated to 'down'

    def test_ping_start(self):
        """
        Test that a request with start keywords does not change the status
        """
        # Set start keywords
        self.check.start_kw = "start,init"
        self.check.save()

        # Send a POST request with a start keyword
        response = self.client.post(self.ping_url, data="status=start", content_type="text/plain")

        # Refresh from the database and assert the status
        self.check.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Start")  # Response matches the action
        self.assertIsNone(self.check.last_ping)  # Status does not change for 'start'

    def test_ping_unknown(self):
        """
        Test that a request with no matching keywords does not change the status
        """
        # Do not set any keywords
        self.check.save()

        # Send a POST request with an unknown keyword
        response = self.client.post(self.ping_url, data="status=unknown", content_type="text/plain")

        # Refresh from the database and assert the status
        self.check.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Unknown")  # Response matches the action
        self.assertIsNone(self.check.last_ping)  # Status does not change for unknown keywords

    def test_ping_with_no_body(self):
        """
        Test that an empty request body is treated as an unknown action
        """
        # Send a POST request with an empty body
        response = self.client.post(self.ping_url, data="", content_type="text/plain")

        # Refresh from the database and assert the status
        self.check.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Unknown")  # Response matches the action
        self.assertIsNone(self.check.last_ping)  # Status does not change for empty body