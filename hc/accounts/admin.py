from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import login as auth_login
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, F
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.timezone import now

from hc.accounts.models import Credential, Profile, Project


@mark_safe
def _format_usage(num_checks, num_channels):
    result = ""

    if num_checks == 0:
        result += "0 checks, "
    elif num_checks == 1:
        result += "1 check, "
    else:
        result += f"<strong>{num_checks} checks</strong>, "

    if num_channels == 0:
        result += "0 channels"
    elif num_channels == 1:
        result += "1 channel"
    else:
        result += f"<strong>{num_channels} channels</strong>"

    return result


class Fieldset:
    name = "Group"
    fields: tuple[str, ...] = tuple()

    @classmethod
    def tuple(cls):
        return (cls.name, {"fields": cls.fields})


class ProfileFieldset(Fieldset):
    name = "User Profile"
    fields = (
        "email",
        "reports",
        "tz",
        "theme",
        "next_report_date",
        "nag_period",
        "next_nag_date",
        "deletion_notice_date",
        "token",
        "sort",
    )


class TeamFieldset(Fieldset):
    name = "Team"
    fields = (
        "team_limit",
        "check_limit",
        "ping_log_limit",
        "sms_limit",
        "sms_sent",
        "last_sms_date",
        "call_limit",
        "calls_sent",
        "last_call_date",
    )


class NumChecksFilter(admin.SimpleListFilter):
    title = "check count"

    parameter_name = "num_checks"

    def lookups(self, request, model_admin):
        return (
            ("10", "More than 10"),
            ("20", "More than 20"),
            ("50", "More than 50"),
            ("100", "More than 100"),
            ("500", "More than 500"),
            ("1000", "More than 1000"),
        )

    def queryset(self, request, queryset):
        if not self.value():
            return

        value = int(self.value())
        return queryset.filter(num_checks__gt=value)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("css/admin/profiles.css",)}

    readonly_fields = ("user", "email")
    search_fields = ["id", "user__email"]
    list_per_page = 30
    list_select_related = ("user",)
    list_display = (
        "id",
        "email",
        "checks",
        "date_joined",
        "last_active_date",
        "projects",
        "invited",
        "sms",
        "reports",
    )
    list_filter = (
        "user__date_joined",
        "last_active_date",
        "deletion_scheduled_date",
        "reports",
        "check_limit",
        NumChecksFilter,
        "theme",
    )
    actions = (
        "login",
        "send_report",
        "send_nag",
        "remove_totp",
        "mark_for_deletion",
        "unmark_for_deletion",
    )

    fieldsets = (ProfileFieldset.tuple(), TeamFieldset.tuple())

    def get_queryset(self, request):
        qs = super(ProfileAdmin, self).get_queryset(request)
        qs = qs.prefetch_related("user__project_set")
        qs = qs.annotate(num_members=Count("user__project__member", distinct=True))
        qs = qs.annotate(num_checks=Count("user__project__check", distinct=True))
        qs = qs.annotate(plan=F("user__subscription__plan_name"))
        return qs

    @mark_safe
    def email(self, obj):
        s = escape(obj.user.email)
        if obj.plan:
            s = "%s <span>%s</span>" % (s, obj.plan)

        return s

    def date_joined(self, obj):
        return obj.user.date_joined

    @mark_safe
    def projects(self, obj):
        return render_to_string("admin/profile_list_projects.html", {"profile": obj})

    @mark_safe
    def checks(self, obj):
        s = "%d of %d" % (obj.num_checks, obj.check_limit)
        if obj.num_checks > 1:
            s = "<b>%s</b>" % s
        return s

    def invited(self, obj):
        return "%d of %d" % (obj.num_members, obj.team_limit)

    def sms(self, obj):
        return "%d of %d" % (obj.sms_sent, obj.sms_limit)

    def login(self, request, qs):
        profile = qs.get()
        auth_login(request, profile.user, "hc.accounts.backends.EmailBackend")
        return redirect("hc-index")

    def send_report(self, request, qs):
        for profile in qs:
            profile.send_report()

        self.message_user(request, "%d email(s) sent" % qs.count())

    def send_nag(self, request, qs):
        for profile in qs:
            profile.send_report(nag=True)

        self.message_user(request, "%d email(s) sent" % qs.count())

    @admin.action(description="Remove TOTP")
    def remove_totp(self, request, qs):
        for profile in qs:
            profile.totp = None
            profile.totp_created = None
            profile.save()

        self.message_user(request, "Removed TOTP for %d profile(s)" % qs.count())

    def mark_for_deletion(self, request, qs):
        qs.update(deletion_scheduled_date=now())
        self.message_user(request, "%d user(s) marked for deletion" % qs.count())

    def unmark_for_deletion(self, request, qs):
        qs.update(deletion_scheduled_date=None)
        self.message_user(request, "%d user(s) unmarked for deletion" % qs.count())


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("code", "owner")
    list_select_related = ("owner",)
    list_display = ("id", "name_", "users", "usage", "switch")
    search_fields = ["id", "name", "owner__email"]

    class Media:
        css = {"all": ("css/admin/projects.css",)}

    def get_queryset(self, request):
        qs = super(ProjectAdmin, self).get_queryset(request)
        qs = qs.annotate(num_channels=Count("channel", distinct=True))
        qs = qs.annotate(num_checks=Count("check", distinct=True))
        qs = qs.annotate(num_members=Count("member", distinct=True))
        return qs

    def name_(self, obj):
        if obj.name:
            return obj.name

        return "Default Project for %s" % obj.owner.email

    @mark_safe
    def users(self, obj):
        if obj.num_members == 0:
            return obj.owner.email
        else:
            return render_to_string("admin/project_list_team.html", {"project": obj})

    def email(self, obj):
        return obj.owner.email

    def usage(self, obj):
        return _format_usage(obj.num_checks, obj.num_channels)

    @mark_safe
    def switch(self, obj):
        url = reverse("hc-checks", args=[obj.code])
        return "<a href='%s'>Show Checks</a>" % url


class HcUserAdmin(UserAdmin):
    list_display = (
        "id",
        "email",
        "usage",
        "date_joined",
        "last_login",
        "last_active",
        "is_staff",
    )

    list_display_links = ("id", "email")
    list_filter = ("last_login", "date_joined", "is_staff", "is_active")
    actions = ("activate", "deactivate")

    ordering = ["-id"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(num_checks=Count("project__check", distinct=True))
        qs = qs.annotate(num_channels=Count("project__channel", distinct=True))
        qs = qs.annotate(last_active_date=F("profile__last_active_date"))

        return qs

    def last_active(self, user):
        return user.last_active_date

    @mark_safe
    def usage(self, user):
        return _format_usage(user.num_checks, user.num_channels)

    def activate(self, request, qs):
        for user in qs:
            user.is_active = True
            user.save()

        self.message_user(request, "%d user(s) activated" % qs.count())

    def deactivate(self, request, qs):
        for user in qs:
            user.is_active = False
            user.set_unusable_password()
            user.save()

        self.message_user(request, "%d user(s) deactivated" % qs.count())


admin.site.unregister(User)
admin.site.register(User, HcUserAdmin)


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    list_display = ("id", "created", "email", "name")
    search_fields = ["id", "code", "name", "user__email"]
    list_filter = ["created"]
    readonly_fields = ("user",)

    def email(self, obj):
        return obj.user.email
