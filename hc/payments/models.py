from django.contrib.auth.models import User
from django.db import models


class SubscriptionManager(models.Manager):

    def for_user(self, user):
        sub, created = Subscription.objects.get_or_create(user_id=user.id)
        return sub


class Subscription(models.Model):
    user = models.OneToOneField(User, blank=True, null=True)
    customer_id = models.CharField(max_length=36, blank=True)
    payment_method_token = models.CharField(max_length=35, blank=True)
    subscription_id = models.CharField(max_length=10, blank=True)
    plan_id = models.CharField(max_length=10, blank=True)

    objects = SubscriptionManager()

    def price(self):
        if self.plan_id == "P5":
            return 5
        elif self.plan_id == "P20":
            return 20

        return 0
