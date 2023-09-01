from __future__ import annotations

from pydantic import BaseModel

check = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "maxLength": 100},
        "slug": {"type": "string", "pattern": "^[a-z0-9-_]*$"},
        "desc": {"type": "string"},
        "tags": {"type": "string", "maxLength": 500},
        "timeout": {"type": "number", "minimum": 60, "maximum": 31536000},
        "grace": {"type": "number", "minimum": 60, "maximum": 31536000},
        "schedule": {"type": "string", "format": "cron", "maxLength": 100},
        "tz": {"type": "string", "format": "timezone", "maxLength": 36},
        "channels": {"type": "string"},
        "manual_resume": {"type": "boolean"},
        "methods": {"enum": ["", "POST"]},
        "subject": {"type": "string", "maxLength": 200},
        "subject_fail": {"type": "string", "maxLength": 200},
        "start_kw": {"type": "string", "maxLength": 200},
        "success_kw": {"type": "string", "maxLength": 200},
        "failure_kw": {"type": "string", "maxLength": 200},
        "filter_subject": {"type": "boolean"},
        "filter_body": {"type": "boolean"},
        "unique": {
            "type": "array",
            "items": {"enum": ["name", "slug", "tags", "timeout", "grace"]},
        },
    },
}


class TelegramFailure(BaseModel):
    description: str


class TelegramMigrationParameters(BaseModel):
    migrate_to_chat_id: int


class TelegramMigration(BaseModel):
    description: str
    parameters: TelegramMigrationParameters

    @property
    def new_chat_id(self) -> int:
        return self.parameters.migrate_to_chat_id
