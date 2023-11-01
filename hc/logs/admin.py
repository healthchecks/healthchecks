from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.http import HttpRequest
from django.utils.html import format_html

from hc.logs.models import Record


@admin.register(Record)
class RecordsAdmin(ModelAdmin[Record]):
    class Media:
        css = {"all": ("css/admin/records.css",)}

    search_fields = ["name", "message"]
    readonly_fields = ("message",)
    list_display = ("when", "logger", "message_traceback")
    list_filter = (
        "created",
        "level",
    )

    def when(self, obj: Record) -> str:
        return obj.created.strftime("%b %-d, %H:%M")

    def logger(self, obj: Record) -> str:
        level_name = obj.get_level_display()
        level_letter = level_name[0].upper()
        return format_html(
            """<span class="{}">{}</span> {}""",
            level_letter,
            level_letter,
            obj.name,
        )

    @admin.display(description="Message")
    def message_traceback(self, obj: Record) -> str:
        if not obj.traceback:
            return obj.message

        return format_html(
            """{}<details><summary>Show traceback</summary><pre>{}</pre></details>


            """,
            obj.message,
            obj.traceback,
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Record | None = None
    ) -> bool:
        return False
