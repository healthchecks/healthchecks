from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
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
              "next_report_date", "nag_period", "next_nag_date",
              "token", "sort")


class TeamFieldset(Fieldset):
    name = "Team"
    fields = ("team_name", "team_limit", "check_limit",
              "ping_log_limit", "sms_limit", "sms_sent", "last_sms_date",
              "bill_to")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    class Media:
        css = {
            'all': ('css/admin/profiles.css',)
        }

    readonly_fields = ("user", "email")
    raw_id_fields = ("current_team", )
    list_select_related = ("user", )
    list_display = ("id", "users", "checks", "invited",
                    "reports_allowed", "ping_log_limit", "sms")
    search_fields = ["id", "user__email"]
    list_filter = ("team_limit", "reports_allowed",
                   "check_limit", "next_report_date")

    fieldsets = (ProfileFieldset.tuple(), TeamFieldset.tuple())

    def get_queryset(self, request):
        qs = super(ProfileAdmin, self).get_queryset(request)
        qs = qs.annotate(Count("member", distinct=True))
        qs = qs.annotate(Count("user__check", distinct=True))
        return qs

    @mark_safe
    def users(self, obj):
        if obj.member__count == 0:
            return obj.user.email
        else:
            return render_to_string("admin/profile_list_team.html", {
                "profile": obj
            })

    @mark_safe
    def checks(self, obj):
        num_checks = obj.user__check__count
        pct = 100 * num_checks / max(obj.check_limit, 1)
        pct = min(100, int(pct))

        return """
            <span class="bar"><span style="width: %dpx"></span></span>
            &nbsp; %d of %d
        """ % (pct, num_checks, obj.check_limit)

    def invited(self, obj):
        return "%d of %d" % (obj.member__count, obj.team_limit)

    def sms(self, obj):
        return "%d of %d" % (obj.sms_sent, obj.sms_limit)

    def email(self, obj):
        return obj.user.email


class HcUserAdmin(UserAdmin):
    actions = ["send_report"]
    list_display = ('id', 'email', 'date_joined', 'engagement',
                    'is_staff', 'checks')

    list_filter = ("last_login", "date_joined", "is_staff", "is_active")

    ordering = ["-id"]

    def engagement(self, user):
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

    engagement.allow_tags = True

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
