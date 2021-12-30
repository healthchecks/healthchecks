check = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "maxLength": 100},
        "desc": {"type": "string"},
        "tags": {"type": "string", "maxLength": 500},
        "timeout": {"type": "number", "minimum": 60, "maximum": 31536000},
        "grace": {"type": "number", "minimum": 60, "maximum": 31536000},
        "schedule": {"type": "string", "format": "cron", "maxLength": 100},
        "tz": {"type": "string", "format": "timezone", "maxLength": 36},
        "channels": {"type": "string"},
        "manual_resume": {"type": "boolean"},
        "methods": {"enum": ["", "POST"]},
        "unique": {
            "type": "array",
            "items": {"enum": ["name", "tags", "timeout", "grace"]},
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
