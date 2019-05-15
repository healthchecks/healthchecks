check = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "maxLength": 100},
        "tags": {"type": "string", "maxLength": 500},
        "timeout": {"type": "number", "minimum": 60, "maximum": 2592000},
        "grace": {"type": "number", "minimum": 60, "maximum": 2592000},
        "schedule": {"type": "string", "format": "cron", "maxLength": 100},
        "tz": {"type": "string", "format": "timezone", "maxLength": 36},
        "channels": {"type": "string"},
        "unique": {
            "type": "array",
            "items": {"enum": ["name", "tags", "timeout", "grace"]},
        },
    },
}
