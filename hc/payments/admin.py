from __future__ import annotations

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from hc.accounts.models import Profile
from hc.payments.models import Subscription


@admin.register(Subscription)
class SubsAdmin(admin.ModelAdmin):

    readonly_fields = ("email",)
    search_fields = (
        "customer_id",
        "payment_method_token",
        "subscription_id",
        "user__email",
    )
    list_display = (
        "id",
        "email",
        "customer_id",
        "address_id",
        "payment_method_token",
        "subscription_id",
        "plan_id",
        "plan_name",
        "profile",
    )

    list_filter = ("plan_id",)
    raw_id_fields = ("user",)
    actions = ("cancel",)

    def email(self, obj):
        return obj.user.email if obj.user else None

    @mark_safe
    def profile(self, obj):
        if obj.user.profile:
            url = reverse("admin:accounts_profile_change", args=[obj.user.profile.id])
            return "<a href='%s'>View Profile</a>" % url

        return ""

    def cancel(self, request, qs):
        for sub in qs.all():
            sub.cancel()

        profile = Profile.objects.for_user(sub.user)
        profile.check_limit = 20
        profile.team_limit = 2
        profile.sms_limit = 5
        profile.save()

        self.message_user(request, "%d subscriptions cancelled" % qs.count())
