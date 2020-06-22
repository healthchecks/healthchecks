import requests
from datetime import datetime, timedelta as td

from django.core.management.base import BaseCommand
from hc.api.models import Check, DEFAULT_TIMEOUT


PROJECT_ID_TO_API_KEY_MAP = {}

PROJECT_ID_TO_INTEGRATION_ID_MAP = {}

API_CHECKS_URL = 'https://healthchecks.io/api/v1/checks/'


class Command(BaseCommand):
    help = "Migrates healthchecks from healthchecks.io to healthchecks.squadplatform.com"

    def handle(self, *args, **options):
        self.stdout.write("migration started\n")

        for project_id, api_key in PROJECT_ID_TO_API_KEY_MAP.items():
            self.stdout.write('migrating Project ' + str(project_id))
            checks = self.fetch_checks_from_api(api_key)
            self.stdout.write('Checks fetched')

            self.create_checks_in_db(checks, project_id)
            self.stdout.write('Created checks in DB')

    def fetch_checks_from_api(self, api_key: str):
        response = requests.get(API_CHECKS_URL, headers={'X-Api-Key': api_key})

        if response.ok:
            return response.json()['checks']

        raise Exception('API request failed for api-key', api_key)

    def create_checks_in_db(self, checks: [dict], project_id: int):
        checks_to_create = []

        for check in checks:
            checks_to_create.append(Check(
                name=check['name'],
                tags=check['tags'],
                desc=check['desc'],
                grace=td(seconds=check['grace']),
                n_pings=check['n_pings'],
                last_ping=check['last_ping'],
                timeout=td(seconds=check['timeout']) if 'timeout' in check else DEFAULT_TIMEOUT,
                tz=check['tz'] if 'tz' in check else 'UTC',
                schedule=check['schedule'] if 'schedule' in check else "* * * * *",
                code=check['ping_url'][check['ping_url'].find('.com/')+5:],
                kind='simple' if 'timeout' in check else 'cron',
                project_id=project_id,
            ))

        Check.objects.bulk_create(checks_to_create)




