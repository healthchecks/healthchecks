from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubsAdmin(admin.ModelAdmin):

    list_display = ("id", "email", "customer_id",
                    "payment_method_token", "subscription_id", "plan_id")

    list_filter = ("plan_id", )
    actions = ("cancel", )

    def email(self, obj):
        return obj.user.email if obj.user else None

    def cancel(self, request, qs):
        for sub in qs.all():
            sub.cancel()

        self.message_user(request, "%d subscriptions cancelled" % qs.count())
