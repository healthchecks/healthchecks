from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from hc.accounts.models import Profile
from hc.api.models import Channel, Check


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    list_display = ("id", "email", "reports_allowed", "next_report_date",
                    "ping_log_limit")
    search_fields = ["user__email"]

    def email(self, obj):
        return obj.user.email


class HcUserAdmin(UserAdmin):
    actions = ["send_report"]
    list_display = ('id', 'username', 'email', 'date_joined', 'involvement',
                    'is_staff')

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

    def send_report(self, request, qs):
        for user in qs:
            profile = Profile.objects.for_user(user)
            profile.send_report()

        self.message_user(request, "%d email(s) sent" % qs.count())


admin.site.unregister(User)
admin.site.register(User, HcUserAdmin)
