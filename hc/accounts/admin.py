from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count
from django.template.loader import render_to_string
from django.urls import reverse
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
    fields = ("email", "current_project", "reports_allowed",
              "next_report_date", "nag_period", "next_nag_date",
              "token", "sort")


class TeamFieldset(Fieldset):
    name = "Team"
    fields = ("team_limit", "check_limit", "ping_log_limit", "sms_limit",
              "sms_sent", "last_sms_date")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    class Media:
        css = {
            'all': ('css/admin/profiles.css',)
        }

    readonly_fields = ("user", "email")
    raw_id_fields = ("current_project", )
    list_select_related = ("user", )
    list_display = ("id", "email", "last_login", "projects", "checks", "invited",
                    "reports_allowed", "sms")
    search_fields = ["id", "user__email"]
    list_filter = ("team_limit", "reports_allowed",
                   "check_limit", "next_report_date")

    fieldsets = (ProfileFieldset.tuple(), TeamFieldset.tuple())

    def get_queryset(self, request):
        qs = super(ProfileAdmin, self).get_queryset(request)
        qs = qs.annotate(num_members=Count("user__project__member", distinct=True))
        qs = qs.annotate(num_checks=Count("user__project__check", distinct=True))
        return qs

    def email(self, obj):
            return obj.user.email

    def last_login(self, obj):
            return obj.user.last_login

    @mark_safe
    def projects(self, obj):
        return render_to_string("admin/profile_list_projects.html", {
            "profile": obj
        })

    @mark_safe
    def checks(self, obj):
        pct = 100 * obj.num_checks / max(obj.check_limit, 1)
        pct = min(100, int(pct))

        return """
            <span class="bar"><span style="width: %dpx"></span></span>
            &nbsp; %d of %d
        """ % (pct, obj.num_checks, obj.check_limit)

    def invited(self, obj):
        return "%d of %d" % (obj.num_members, obj.team_limit)

    def sms(self, obj):
        return "%d of %d" % (obj.sms_sent, obj.sms_limit)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_select_related = ("owner", )
    list_display = ("id", "name_", "users", "engagement", "switch")

    class Media:
        css = {
            'all': ('css/admin/projects.css',)
        }

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
            return render_to_string("admin/project_list_team.html", {
                "project": obj
            })

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
        url = reverse("hc-switch-project", args=[obj.code])
        return "<a href='%s'>Show Checks</a>" % url


class HcUserAdmin(UserAdmin):
    actions = ["send_report"]
    list_display = ('id', 'email', 'engagement', 'date_joined', 'last_login',
                    'is_staff')

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


admin.site.unregister(User)
admin.site.register(User, HcUserAdmin)
