from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubsAdmin(admin.ModelAdmin):

    list_display = ("id", "user")
