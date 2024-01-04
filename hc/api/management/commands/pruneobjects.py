from __future__ import annotations

from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand
from minio.deleteobjects import DeleteObject

from hc.api.models import Check
from hc.lib.s3 import client


class Command(BaseCommand):
    help = "Prune ping bodies of deleted checks from object store."

    def handle(self, **options: Any) -> str:
        if not settings.S3_BUCKET:
            return "Object storage is not configured"

        existing = set(map(str, Check.objects.values_list("code", flat=True)))

        c = client()
        delete_list = []
        for obj in c.list_objects(settings.S3_BUCKET):
            try:
                UUID(obj.object_name[:-1])
            except ValueError:
                continue

            if obj.object_name[:-1] not in existing:
                delete_list.append(obj.object_name)

        print("Staged for deletion: %d" % len(delete_list))
        for prefix in delete_list:
            print("Deleting %s" % prefix)
            q = c.list_objects(settings.S3_BUCKET, prefix)
            delete_objs = [DeleteObject(obj.object_name) for obj in q]
            if delete_objs:
                errors = c.remove_objects(settings.S3_BUCKET, delete_objs)
                for e in errors:
                    print("remove_objects error: ", e)

        return "Done!"
