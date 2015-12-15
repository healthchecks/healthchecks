from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core import signing
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from hc.lib import emails
import uuid


class ProfileManager(models.Manager):

    def for_user(self, user):
        try:
            profile = self.get(user_id=user.id)
        except Profile.DoesNotExist:
            profile = Profile(user=user)
            profile.save()

        return profile


class Profile(models.Model):
    user = models.OneToOneField(User, blank=True, null=True)
    next_report_date = models.DateTimeField(null=True, blank=True)
    reports_allowed = models.BooleanField(default=True)

    objects = ProfileManager()

    def send_report(self):
        # reset next report date first:
        now = timezone.now()
        self.next_report_date = now + timedelta(days=30)
        self.save()

        token = signing.Signer().sign(uuid.uuid4())
        path = reverse("hc-unsubscribe-reports", args=[self.user.username])
        unsub_link = "%s%s?token=%s" % (settings.SITE_ROOT, path, token)

        ctx = {
            "checks": self.user.check_set.order_by("created"),
            "now": now,
            "unsub_link": unsub_link
        }

        emails.report(self.user.email, ctx)
