from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from hc.api.models import Channel, Check


class HcUserAdmin(UserAdmin):
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


admin.site.unregister(User)
admin.site.register(User, HcUserAdmin)
