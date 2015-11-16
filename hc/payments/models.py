from django.contrib.auth.models import User
from django.db import models


class Subscription(models.Model):
    user = models.OneToOneField(User, blank=True, null=True)
    customer_id = models.CharField(max_length=36, blank=True)
    payment_method_token = models.CharField(max_length=35, blank=True)
    subscription_id = models.CharField(max_length=10, blank=True)
