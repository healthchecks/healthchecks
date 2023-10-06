from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import TypedDict

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth import login as auth_login
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, F, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django_stubs_ext import WithAnnotations

from hc.accounts.models import Credential, Profile, Project

Lookups = Iterable[tuple[str, str]]


def _format_usage(num_checks: int, num_channels: int) -> str:
    tmpl = ""

    if num_checks == 0:
        tmpl += "{} checks, "
    elif num_checks == 1:
        tmpl += "{} check, "
    else:
        tmpl += "<strong>{} checks</strong>, "

    if num_channels == 0:
        tmpl += "{} channels"
    elif num_channels == 1:
        tmpl += "{} channel"
    else:
        tmpl += "<strong>{} channels</strong>"

    return format_html(tmpl, num_checks, num_channels)


class NumChecksFilter(admin.SimpleListFilter):
    title = "check count"

    parameter_name = "num_checks"

    def lookups(self, r: HttpRequest, model_admin: ModelAdmin[Profile]) -> Lookups:
        return (
            ("10", "More than 10"),
            ("20", "More than 20"),
            ("50", "More than 50"),
            ("100", "More than 100"),
            ("500", "More than 500"),
            ("1000", "More than 1000"),
        )

    def queryset(self, r: HttpRequest, qs: QuerySet[Profile]) -> QuerySet[Profile]:
        value = self.value()
        if value:
            qs = qs.filter(num_checks__gt=int(value))

        return qs


class ProfileAnnotations(TypedDict):
    num_checks: int
    num_members: int
    plan: str


@admin.register(Profile)
class ProfileAdmin(ModelAdmin[Profile]):
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
        "projects",
        "date_joined",
        "last_active",
        "over_limit",
        "deletion",
        "invited",
        "sms",
        "reports",
    )
    list_filter = (
        "check_limit",
        NumChecksFilter,
        "last_active_date",
        "over_limit_date",
        "deletion_scheduled_date",
        "reports",
    )
    actions = (
        "login",
        "send_report",
        "send_nag",
        "remove_totp",
        "schedule_for_deletion",
        "unschedule_for_deletion",
    )

    _profile_fields = (
        "tz",
        "reports",
        "next_report_date",
        "nag_period",
        "next_nag_date",
        "token",
        "theme",
        "sort",
    )

    _limits_fields = (
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

    _deletion_fields = (
        "over_limit_date",
        "deletion_notice_date",
        "deletion_scheduled_date",
    )

    fieldsets = (
        ("User Profile", {"fields": _profile_fields}),
        ("Limits", {"fields": _limits_fields}),
        ("Deletion", {"fields": _deletion_fields}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Profile]:
        qs = super(ProfileAdmin, self).get_queryset(request)
        qs = qs.prefetch_related("user__project_set")
        qs = qs.annotate(num_members=Count("user__project__member", distinct=True))
        qs = qs.annotate(num_checks=Count("user__project__check", distinct=True))
        qs = qs.annotate(plan=F("user__subscription__plan_name"))
        return qs

    def email(self, obj: WithAnnotations[Profile, ProfileAnnotations]) -> str:
        if obj.plan:
            return format_html("{} <span>{}</span>", obj.user.email, obj.plan)

        return obj.user.email

    @admin.display(ordering="user__date_joined")
    def date_joined(self, obj: Profile) -> datetime:
        return obj.user.date_joined

    @admin.display(ordering="last_active_date")
    def last_active(self, obj: Profile) -> date | None:
        if obj.last_active_date:
            return obj.last_active_date.date()
        return None

    @admin.display(ordering="over_limit_date")
    def over_limit(self, obj: Profile) -> date | None:
        if obj.over_limit_date:
            return obj.over_limit_date.date()
        return None

    @admin.display(ordering="deletion_scheduled_date")
    def deletion(self, obj: Profile) -> date | None:
        if obj.deletion_scheduled_date:
            return obj.deletion_scheduled_date.date()
        return None

    def projects(self, obj: Profile) -> str:
        return render_to_string("admin/profile_list_projects.html", {"profile": obj})

    def checks(self, obj: WithAnnotations[Profile, ProfileAnnotations]) -> str:
        tmpl = "{} of {}"
        if obj.num_checks > 1:
            tmpl = "<b>%s</b>" % tmpl
        return format_html(tmpl, obj.num_checks, obj.check_limit)

    def invited(self, obj: WithAnnotations[Profile, ProfileAnnotations]) -> str:
        return f"{obj.num_members} of {obj.team_limit}"

    def sms(self, obj: Profile) -> str:
        return f"{obj.sms_sent} of {obj.sms_limit}"

    def login(self, r: HttpRequest, qs: QuerySet[Profile]) -> HttpResponseRedirect:
        profile = qs.get()
        auth_login(r, profile.user, "hc.accounts.backends.EmailBackend")
        return redirect("hc-index")

    def send_report(self, request: HttpRequest, qs: QuerySet[Profile]) -> None:
        for profile in qs:
            profile.send_report()

        self.message_user(request, f"{len(qs)} email(s) sent")

    def send_nag(self, request: HttpRequest, qs: QuerySet[Profile]) -> None:
        for profile in qs:
            profile.send_report(nag=True)

        self.message_user(request, f"{len(qs)} email(s) sent")

    @admin.action(description="Remove TOTP")
    def remove_totp(self, request: HttpRequest, qs: QuerySet[Profile]) -> None:
        for profile in qs:
            profile.totp = None
            profile.totp_created = None
            profile.save()

        self.message_user(request, f"Removed TOTP for {len(qs)} profile(s)")

    def schedule_for_deletion(self, r: HttpRequest, qs: QuerySet[Profile]) -> None:
        for profile in qs:
            profile.schedule_for_deletion()
        self.message_user(r, f"{len(qs)} user(s) scheduled for deletion")

    def unschedule_for_deletion(self, r: HttpRequest, qs: QuerySet[Profile]) -> None:
        num_unscheduled = qs.update(deletion_scheduled_date=None)
        self.message_user(r, f"{num_unscheduled} user(s) unscheduled for deletion")


class ProjectAnnotations(TypedDict):
    num_checks: int
    num_channels: int
    num_members: int


@admin.register(Project)
class ProjectAdmin(ModelAdmin[Project]):
    readonly_fields = ("code", "owner")
    list_select_related = ("owner",)
    list_display = ("id", "name_", "users", "usage", "switch")
    search_fields = ["id", "name", "owner__email"]

    class Media:
        css = {"all": ("css/admin/projects.css",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Project]:
        qs = super(ProjectAdmin, self).get_queryset(request)
        qs = qs.annotate(num_channels=Count("channel", distinct=True))
        # The Project model has a "num_checks" method, so use
        # a different name for the annotation to avoid type confusion:
        qs = qs.annotate(num_checks=Count("check", distinct=True))
        qs = qs.annotate(num_members=Count("member", distinct=True))
        return qs

    def name_(self, obj: Project) -> str:
        if obj.name:
            return obj.name

        return f"Default Project for {obj.owner.email}"

    def users(self, obj: WithAnnotations[Project, ProjectAnnotations]) -> str:
        if obj.num_members == 0:
            return obj.owner.email
        else:
            return render_to_string("admin/project_list_team.html", {"project": obj})

    def email(self, obj: Project) -> str:
        return obj.owner.email

    def usage(self, obj: WithAnnotations[Project, ProjectAnnotations]) -> str:
        return _format_usage(obj.num_checks, obj.num_channels)

    def switch(self, obj: Project) -> str:
        url = reverse("hc-checks", args=[obj.code])
        return format_html("<a href='{}'>Show Checks</a>", url)


class UserAnnotations(TypedDict):
    num_checks: int
    num_channels: int
    last_active_date: datetime | None


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

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        qs = super().get_queryset(request)
        qs = qs.annotate(num_checks=Count("project__check", distinct=True))
        qs = qs.annotate(num_channels=Count("project__channel", distinct=True))
        qs = qs.annotate(last_active_date=F("profile__last_active_date"))

        return qs

    def last_active(
        self, user: WithAnnotations[User, UserAnnotations]
    ) -> datetime | None:
        assert (
            isinstance(user.last_active_date, datetime) or user.last_active_date is None
        )
        return user.last_active_date

    def usage(self, user: WithAnnotations[User, UserAnnotations]) -> str:
        return _format_usage(user.num_checks, user.num_channels)

    def activate(self, request: HttpRequest, qs: QuerySet[User]) -> None:
        for user in qs:
            user.is_active = True
            user.save()

        self.message_user(request, f"{len(qs)} user(s) activated")

    def deactivate(self, request: HttpRequest, qs: QuerySet[User]) -> None:
        for user in qs:
            user.is_active = False
            user.set_unusable_password()
            user.save()

        self.message_user(request, f"{len(qs)} user(s) deactivated")


admin.site.unregister(User)
admin.site.register(User, HcUserAdmin)


@admin.register(Credential)
class CredentialAdmin(ModelAdmin[Credential]):
    list_display = ("id", "created", "email", "name")
    search_fields = ["id", "code", "name", "user__email"]
    list_filter = ["created"]
    readonly_fields = ("user",)

    def email(self, obj: Credential) -> str:
        return obj.user.email
