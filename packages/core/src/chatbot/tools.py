"""OpenAI function-calling tool definitions for the chatbot.

Exposes a single ``execute_sql_query`` tool that lets the model run read-only
SQL queries against the location-tracking database.
"""

# Schema summary provided to the model so it knows what tables/columns exist.
# Use entities.external_id (e.g. badge_12, forklift_3) as the primary handle for questions.
_DB_SCHEMA_DESCRIPTION = """\
The SQLite database tracks in-store locations. Tables:

1. zones (id, name, zone_type, floor, department, polygon_coords, metadata, created_at)
   zone_type: lobby, loading_dock, aisle, floor_landing, department, other. Join to zones for floor (floor-jump checks).
2. entities (id, external_id, name, type['customer','employee','asset','device'], tags, first_seen, last_seen)
   external_id is the primary handle for questions (e.g. badge_12, forklift_3).
3. location_pings (id, entity_id FK->entities, zone_id FK->zones, timestamp, rssi, accuracy, source_device, raw_data)
   rssi: signal strength -100 to -30; low rssi (e.g. < -80) indicates weak signal / data quality.
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
