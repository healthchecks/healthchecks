check = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "maxLength": 100},
        "tags": {"type": "string", "maxLength": 500},
        "timeout": {"type": "number", "minimum": 60, "maximum": 604800},
        "grace": {"type": "number", "minimum": 60, "maximum": 604800},
        "channels": {"type": "string"},
        "unique": {
            "type": "array",
            "items": {"enum": ["name", "tags", "timeout", "grace"]}
        }
    }
}
