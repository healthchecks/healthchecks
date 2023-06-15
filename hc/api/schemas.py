from __future__ import annotations

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

telegram_migration = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "parameters": {
            "type": "object",
            "properties": {"migrate_to_chat_id": {"type": "number"}},
            "required": ["migrate_to_chat_id"],
        },
    },
    "required": ["description", "parameters"],
}
