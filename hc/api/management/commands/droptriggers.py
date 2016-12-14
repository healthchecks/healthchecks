from django.core.management.base import BaseCommand
from django.db import connection


def _pg(cursor):
    cursor.execute("""
    DROP TRIGGER IF EXISTS update_alert_after ON api_check;
    """)


def _mysql(cursor):
    cursor.execute("""
    DROP TRIGGER IF EXISTS update_alert_after;
    """)


def _sqlite(cursor):
    cursor.execute("""
    DROP TRIGGER IF EXISTS update_alert_after;
    """)


class Command(BaseCommand):
    help = 'Drops the `update_alert_after` trigger'
    requires_system_checks = False

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                _pg(cursor)
                return "Dropped PostgreSQL trigger"
            if connection.vendor == "mysql":
                _mysql(cursor)
                return "Dropped MySQL trigger"
            if connection.vendor == "sqlite":
                _sqlite(cursor)
                return "Dropped SQLite trigger"
