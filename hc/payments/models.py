from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models


class Subscription(models.Model):
    user = models.OneToOneField(User, models.CASCADE)
    customer_id = models.CharField(max_length=36, blank=True)
    payment_method_token = models.CharField(max_length=35, blank=True)
    subscription_id = models.CharField(max_length=10, blank=True)
    plan_id = models.CharField(max_length=10, blank=True)
    plan_name = models.CharField(max_length=50, blank=True)
    address_id = models.CharField(max_length=2, blank=True)
    send_invoices = models.BooleanField(default=True)
    invoice_email = models.EmailField(blank=True)
    next_billing_date = models.DateField(null=True, blank=True)
    renew_notice_date = models.DateField(null=True, blank=True)
    setup_date = models.DateField(null=True, blank=True)

    def cancel(self) -> None:
        # FIXME
        pass
