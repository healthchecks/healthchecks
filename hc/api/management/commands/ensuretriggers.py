from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Ensures triggers exist in database'

    def handle(self, *args, **options):
        cursor = connection.cursor()

        cursor.execute("""
CREATE OR REPLACE FUNCTION update_alert_after()
RETURNS trigger AS $update_alert_after$
    BEGIN
        IF NEW.last_ping IS NOT NULL THEN
            NEW.alert_after := NEW.last_ping + NEW.timeout + '1 hour';
        END IF;
        RETURN NEW;
    END;
$update_alert_after$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_alert_after ON api_check;

CREATE TRIGGER update_alert_after
BEFORE INSERT OR UPDATE OF last_ping, timeout  ON api_check
FOR EACH ROW EXECUTE PROCEDURE update_alert_after();
        """)
