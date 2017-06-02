from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.urls import reverse
from hc.accounts.models import Profile
from hc.api.models import Channel, Check


class Fieldset:
    name = None
    fields = []

    @classmethod
    def tuple(cls):
        return (cls.name, {"fields": cls.fields})


class ProfileFieldset(Fieldset):
    name = "User Profile"
    fields = ("email", "api_key", "current_team", "reports_allowed",
              "next_report_date", "token")


class TeamFieldset(Fieldset):
    name = "Team"
    fields = ("team_name", "team_access_allowed", "check_limit",
              "ping_log_limit")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    class Media:
        css = {
            'all': ('css/admin/profiles.css',)
        }

    readonly_fields = ("user", "email")
    raw_id_fields = ("current_team", )
    list_select_related = ("user", )
    list_display = ("id", "users", "checks", "team_access_allowed",
                    "reports_allowed", "ping_log_limit")
    search_fields = ["id", "user__email"]
    list_filter = ("team_access_allowed", "reports_allowed",
                   "check_limit", "next_report_date")

    fieldsets = (ProfileFieldset.tuple(), TeamFieldset.tuple())

    def users(self, obj):
        if obj.member_set.count() == 0:
            return obj.user.email
        else:
            return render_to_string("admin/profile_list_team.html", {
                "profile": obj
            })

    def checks(self, obj):
        current = Check.objects.filter(user=obj.user).count()
        text = "%d of %d" % (current, obj.check_limit)
        url = reverse("hc-switch-team", args=[obj.user.username])
        return "<a href='%s'>%s</a>" % (url, text)

    def email(self, obj):
        return obj.user.email

    users.allow_tags = True
    checks.allow_tags = True


class HcUserAdmin(UserAdmin):
    actions = ["send_report"]
    list_display = ('id', 'email', 'date_joined', 'involvement',
                    'is_staff', 'checks')

    list_filter = ("last_login", "date_joined", "is_staff", "is_active")

    ordering = ["-id"]

    def involvement(self, user):
        result = ""
        num_checks = Check.objects.filter(user=user).count()
        num_channels = Channel.objects.filter(user=user).count()

        if num_checks == 0:
            result += "0 checks, "
        elif num_checks == 1:
            result += "1 check, "
        else:
            result += "<strong>%d checks</strong>, " % num_checks

        if num_channels == 0:
            result += "0 channels"
        elif num_channels == 1:
            result += "1 channel, "
        else:
            result += "<strong>%d channels</strong>, " % num_channels

        return result

    involvement.allow_tags = True

    def checks(self, user):
        url = reverse("hc-switch-team", args=[user.username])
        return "<a href='%s'>Checks</a>" % url

    checks.allow_tags = True

    def send_report(self, request, qs):
        for user in qs:
            user.profile.send_report()

        self.message_user(request, "%d email(s) sent" % qs.count())


admin.site.unregister(User)
admin.site.register(User, HcUserAdmin)
