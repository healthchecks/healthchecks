from __future__ import annotations

from typing import TYPE_CHECKING, ParamSpec, TypeVar

from django.contrib.auth.models import User
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.core.signing import TimestampSigner
from django.test import Client, TestCase

from hc.accounts.models import Member, Profile, Project

if TYPE_CHECKING:
    # _MonkeyPatchedWSGIResponse is defined in django-stubs,
    # we import with a "TestHttpResponse" alias.
    # We list it in __all__ so subclasses can import and use it.
    from django.test.client import _MonkeyPatchedWSGIResponse as TestHttpResponse
else:
    from django.http import HttpResponse as TestHttpResponse

__all__ = ["BaseTestCase", "TestHttpResponse"]

P = ParamSpec("P")
T = TypeVar("T")


class BaseTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.csrf_client = Client(enforce_csrf_checks=True)

        # Alice is a normal user for tests. Alice has team access enabled.
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

        self.project = Project(owner=self.alice, api_key="X" * 32)
        self.project.name = "Alices Project"
        self.project.badge_key = self.alice.username
        self.project.ping_key = "p" * 22
        self.project.save()

        self.profile = Profile(user=self.alice)
        self.profile.sms_limit = 50
        self.profile.save()

        # Bob is on Alice's team and should have access to her stuff
        self.bob = User(username="bob", email="bob@example.org")
        self.bob.set_password("password")
        self.bob.save()

        self.bobs_project = Project(owner=self.bob)
        self.bobs_project.badge_key = self.bob.username
        self.bobs_project.save()

        self.bobs_profile = Profile(user=self.bob)
        self.bobs_profile.save()

        self.bobs_membership = Member.objects.create(
            user=self.bob, project=self.project, role=Member.Role.REGULAR
        )

        # Charlie should have no access to Alice's stuff
        self.charlie = User(username="charlie", email="charlie@example.org")
        self.charlie.set_password("password")
        self.charlie.save()

        self.charlies_project = Project(owner=self.charlie)
        self.charlies_project.badge_key = self.charlie.username
        self.charlies_project.save()

        self.charlies_profile = Profile(user=self.charlie)
        self.charlies_profile.save()

        self.channels_url = f"/projects/{self.project.code}/integrations/"

    def set_sudo_flag(self) -> None:
        session = self.client.session
        session["sudo"] = TimestampSigner().sign("active")
        session.save()

    def assertEmailContainsText(self, fragment: str) -> None:
        """Test if fragment appears in email body."""

        self.assertIn(fragment, mail.outbox[0].body)

    def assertEmailContainsHtml(self, fragment: str) -> None:
        """Test if fragment appears in email's HTML content."""

        email = mail.outbox[0]
        assert isinstance(email, EmailMultiAlternatives)
        html_content, _ = email.alternatives[0]
        assert isinstance(html_content, str)
        self.assertIn(fragment, html_content)

    def assertEmailContains(self, fragment: str) -> None:
        """Test if fragment appears in email's plain text *and* HTML content."""

        self.assertEmailContainsText(fragment)
        self.assertEmailContainsHtml(fragment)

    def assertEmailNotContains(self, fragment: str) -> None:
        """Test if fragment is absent from both plain text *and* HTML content."""

        email = mail.outbox[0]
        self.assertNotIn(fragment, email.body)

        assert isinstance(email, EmailMultiAlternatives)
        html_content, _ = email.alternatives[0]
        assert isinstance(html_content, str)
        self.assertNotIn(fragment, html_content)
