"""OpenAI function-calling tool definitions for the chatbot.

Exposes a single ``execute_sql_query`` tool that lets the model run read-only
SQL queries against the location-tracking database.
"""

# Schema summary provided to the model so it knows what tables/columns exist.
_DB_SCHEMA_DESCRIPTION = """\
The SQLite database tracks indoor locations. Tables:

1. zones (id, name, floor, department, polygon_coords, metadata, created_at)
2. entities (id, external_id, name, type['customer','employee','asset','device'], tags, first_seen, last_seen)
3. location_pings (id, entity_id FK->entities, zone_id FK->zones, timestamp, rssi, accuracy, source_device, raw_data)
4. zone_events (id, entity_id FK->entities, zone_id FK->zones, event_type['enter','exit','dwell'], start_time, end_time, duration_seconds, confidence)
"""

# OpenAI function-calling tool definitions.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description": (
                "Execute a read-only SQL SELECT query against the database "
                "and return the results. Only SELECT statements are allowed. "
                "Here is the database schema:\n" + _DB_SCHEMA_DESCRIPTION
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A SQL SELECT statement to execute.",
                    },
                },
                "required": ["query"],
            },
        },
    }
]
