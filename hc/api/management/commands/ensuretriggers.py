from django.core.management.base import BaseCommand
from django.db import connection


def _pg(cursor):
    cursor.execute("""
    CREATE OR REPLACE FUNCTION update_alert_after()
    RETURNS trigger AS $update_alert_after$
        BEGIN
            IF NEW.last_ping IS NOT NULL THEN
                NEW.alert_after := NEW.last_ping + NEW.timeout + NEW.grace;
            END IF;
            RETURN NEW;
        END;
    $update_alert_after$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS update_alert_after ON api_check;

    CREATE TRIGGER update_alert_after
    BEFORE INSERT OR UPDATE OF last_ping, timeout, grace  ON api_check
    FOR EACH ROW EXECUTE PROCEDURE update_alert_after();
    """)


def _mysql(cursor):
    cursor.execute("""
    DROP TRIGGER IF EXISTS update_alert_after;
    """)

    cursor.execute("""
    CREATE TRIGGER update_alert_after
    BEFORE UPDATE ON api_check
    FOR EACH ROW SET
        NEW.alert_after =
            NEW.last_ping + INTERVAL (NEW.timeout + NEW.grace) MICROSECOND;
    """)


def _sqlite(cursor):
    cursor.execute("""
    DROP TRIGGER IF EXISTS update_alert_after;
    """)

    cursor.execute("""
    CREATE TRIGGER update_alert_after
    AFTER UPDATE OF last_ping, timeout, grace ON api_check
    FOR EACH ROW BEGIN
        UPDATE api_check
        SET alert_after =
            datetime(strftime('%s', last_ping) +
            timeout/1000000 + grace/1000000, 'unixepoch')
        WHERE id = OLD.id;
    END;
    """)


class Command(BaseCommand):
    help = 'Ensures triggers exist in database'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                _pg(cursor)
                return "Created PostgreSQL trigger"
            if connection.vendor == "mysql":
                _mysql(cursor)
                return "Created MySQL trigger"
            if connection.vendor == "sqlite":
                _sqlite(cursor)
                return "Created SQLite trigger"
