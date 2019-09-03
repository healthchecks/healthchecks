from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, F
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from hc.accounts.models import Profile, Project


class Fieldset:
    name = None
    fields = []

    @classmethod
    def tuple(cls):
        return (cls.name, {"fields": cls.fields})


class ProfileFieldset(Fieldset):
    name = "User Profile"
    fields = (
        "email",
        "current_project",
        "reports_allowed",
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
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("css/admin/profiles.css",)}

    readonly_fields = ("user", "email")
    raw_id_fields = ("current_project",)
    search_fields = ["id", "user__email"]
    list_per_page = 50
    list_select_related = ("user",)
    list_display = (
        "id",
        "email",
        "engagement",
        "date_joined",
        "last_login",
        "projects",
        "invited",
        "sms",
        "reports_allowed",
    )
    list_filter = (
        "user__date_joined",
        "user__last_login",
        "reports_allowed",
        "check_limit",
    )

    fieldsets = (ProfileFieldset.tuple(), TeamFieldset.tuple())

    def get_queryset(self, request):
        qs = super(ProfileAdmin, self).get_queryset(request)
        qs = qs.prefetch_related("user__project_set")
        qs = qs.annotate(num_members=Count("user__project__member", distinct=True))
        qs = qs.annotate(num_checks=Count("user__project__check", distinct=True))
        qs = qs.annotate(num_channels=Count("user__project__channel", distinct=True))
        qs = qs.annotate(plan=F("user__subscription__plan_name"))
        return qs

    @mark_safe
    def engagement(self, obj):
        result = ""

        if obj.num_checks == 0:
            result += "0 checks, "
        elif obj.num_checks == 1:
            result += "1 check, "
        else:
            result += "<strong>%d checks</strong>, " % obj.num_checks

        if obj.num_channels == 0:
            result += "0 channels"
        elif obj.num_channels == 1:
            result += "1 channel, "
        else:
            result += "<strong>%d channels</strong>, " % obj.num_channels

        return result

    @mark_safe
    def email(self, obj):
        s = escape(obj.user.email)
        if obj.plan:
            return "<span title='%s'>%s</span>" % (obj.plan, s)

        return s

    def last_login(self, obj):
        return obj.user.last_login

    def date_joined(self, obj):
        return obj.user.date_joined

    @mark_safe
    def projects(self, obj):
        return render_to_string("admin/profile_list_projects.html", {"profile": obj})

    def invited(self, obj):
        return "%d of %d" % (obj.num_members, obj.team_limit)

    def sms(self, obj):
        return "%d of %d" % (obj.sms_sent, obj.sms_limit)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("code", "owner")
    list_select_related = ("owner",)
    list_display = ("id", "name_", "users", "engagement", "switch")
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

    @mark_safe
    def engagement(self, obj):
        result = ""

        if obj.num_checks == 0:
            result += "0 checks, "
        elif obj.num_checks == 1:
            result += "1 check, "
        else:
            result += "<strong>%d checks</strong>, " % obj.num_checks

        if obj.num_channels == 0:
            result += "0 channels"
        elif obj.num_channels == 1:
            result += "1 channel, "
        else:
            result += "<strong>%d channels</strong>, " % obj.num_channels

        return result

    @mark_safe
    def switch(self, obj):
        url = reverse("hc-checks", args=[obj.code])
        return "<a href='%s'>Show Checks</a>" % url


class HcUserAdmin(UserAdmin):
    actions = ["send_report", "send_nag"]
    list_display = (
        "id",
        "email",
        "engagement",
        "date_joined",
        "last_login",
        "is_staff",
    )

    list_display_links = ("id", "email")
    list_filter = ("last_login", "date_joined", "is_staff", "is_active")

    ordering = ["-id"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(num_checks=Count("project__check", distinct=True))
        qs = qs.annotate(num_channels=Count("project__channel", distinct=True))

        return qs

    @mark_safe
    def engagement(self, user):
        result = ""

        if user.num_checks == 0:
            result += "0 checks, "
        elif user.num_checks == 1:
            result += "1 check, "
        else:
            result += "<strong>%d checks</strong>, " % user.num_checks

        if user.num_channels == 0:
            result += "0 channels"
        elif user.num_channels == 1:
            result += "1 channel, "
        else:
            result += "<strong>%d channels</strong>, " % user.num_channels

        return result

    def send_report(self, request, qs):
        for user in qs:
            user.profile.send_report()

        self.message_user(request, "%d email(s) sent" % qs.count())

    def send_nag(self, request, qs):
        for user in qs:
            user.profile.send_report(nag=True)

        self.message_user(request, "%d email(s) sent" % qs.count())


admin.site.unregister(User)
admin.site.register(User, HcUserAdmin)
