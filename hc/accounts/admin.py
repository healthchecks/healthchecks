from django.contrib import admin

# Register your models here.
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from hc.api.models import Check


class HcUserAdmin(UserAdmin):
    list_display = ('id', 'username', 'email', 'date_joined', 'num_checks',
                    'is_staff')

    ordering = ["-id"]

    def num_checks(self, user):
        return Check.objects.filter(user=user).count()

admin.site.unregister(User)
admin.site.register(User, HcUserAdmin)
