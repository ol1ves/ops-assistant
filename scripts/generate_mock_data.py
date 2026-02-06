"""
Mock Data Generation Script for the Ops Chatbot MVP.

Generates a SQLite database populated with realistic indoor location
tracking data across four tables: zones, entities, location_pings,
and zone_events. Uses only Python standard library modules.

Usage:
    uv run scripts/generate_mock_data.py [--output PATH] [--seed N]

Examples:
    uv run scripts/generate_mock_data.py
    uv run scripts/generate_mock_data.py --seed 42
    uv run scripts/generate_mock_data.py --output /tmp/test.db --seed 42

See specs/001-mock-data-script/ for full specification and data model.
"""

import argparse
import datetime
import json
import random
import sqlite3
import sys
from pathlib import Path

# Add the project root to sys.path so we can import from the database package.
# This is needed because the script lives in scripts/ while the schema module
# lives in database/ — both are siblings under the project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from database.schema import SCHEMA_SQL


# =============================================================================
# Configuration — Default data volumes
# =============================================================================

NUM_ZONES = 8
NUM_ENTITIES = 25
NUM_PINGS = 550  # Target: 500+ pings
TIME_WINDOW_DAYS = 7


# =============================================================================
# Data Pools — Realistic values for mock data generation
# =============================================================================
# These pools ensure diversity across floors, departments, entity types,
# and naming conventions. See data-model.md for rationale.

# 8 zones across 3 floors and 4 departments (per spec acceptance scenario 2.1)
ZONE_DEFINITIONS = [
    # Floor 1 — Customer-facing, entrance, and produce
    {
        "name": "Entrance",
        "floor": 1,
        "department": "Customer Service",
        "metadata": {"capacity": 40, "type": "entryway"},
    },
    {
        "name": "Produce Section",
        "floor": 1,
        "department": "Grocery",
        "metadata": {"capacity": 60, "type": "fresh_food"},
    },
    {
        "name": "Bakery",
        "floor": 1,
        "department": "Grocery",
        "metadata": {"capacity": 10, "type": "in-store_bakery"},
    },
    # Floor 2 — General merchandise, offices, and breakroom
    {
        "name": "Home Goods",
        "floor": 2,
        "department": "Merchandise",
        "metadata": {"capacity": 35, "type": "retail_aisle"},
    },
    {
        "name": "Electronics",
        "floor": 2,
        "department": "Merchandise",
        "metadata": {"capacity": 25, "type": "retail_aisle"},
    },
    {
        "name": "Employee Breakroom",
        "floor": 2,
        "department": "Human Resources",
        "metadata": {"capacity": 15, "type": "breakroom"},
    },
    # Floor 3 — Storage, manager’s office
    {
        "name": "Frozen Storage",
        "floor": 3,
        "department": "Inventory",
        "metadata": {"capacity": 8, "type": "cold_storage"},
    },
    {
        "name": "Manager Office",
        "floor": 3,
        "department": "Management",
        "metadata": {"capacity": 4, "type": "office"},
    },
]

# Entity name pools by type
EMPLOYEE_NAMES = [
    "Laura Nguyen",
    "Mark Robinson",
    "Jose Ramirez",
    "Patricia Gomez",
    "Steve Adams",
    "Michelle Wang",
    "Heather Clark",
    "Brandon Lewis",
    "Natalie Patel",
    "Samuel Lee",
]

CUSTOMER_NAMES = [
    "Shopper: Adam Wright",
    "Shopper: Brenda Hall",
    "Shopper: Chloe Kelly",
    "Guest: Oscar Brooks",
    "Guest: Sophia Evans",
    "Family Member: Martinez",
]

ASSET_NAMES = [
    "Shopping Cart 101",
    "Pallet Jack B2",
    "Handheld Barcode Scanner 7",
    "Bakery Mixer X3",
    "Checkout Register 4",
]

DEVICE_NAMES = [
    "POS Terminal 14",
    "Security Camera C5",
    "Inventory Tablet 21",
    "Store WiFi Hub A",
]

# Weighted entity type distribution per data-model.md:
# ~40% employee, ~25% customer, ~20% asset, ~15% device
# For 25 entities: 10 employees, 6 customers, 5 assets, 4 devices
ENTITY_TYPE_COUNTS = {
    "employee": 10,
    "customer": 6,
    "asset": 5,
    "device": 4,
}

# Tag pools by entity type — optional JSON arrays for categorization
TAG_POOLS = {
    "employee": [
        ["staff", "full-time"],
        ["staff", "part-time"],
        ["cashier"],
        ["manager"],
        None,
    ],
    "customer": [
        ["member", "loyalty"],
        ["guest"],
        ["family_shopper"],
        None,
    ],
    "asset": [
        ["store_owned", "mobile"],
        ["shared"],
        ["checkout_equipment"],
        None,
    ],
    "device": [
        ["iot", "pos"],
        ["iot", "security"],
        ["wifi_access"],
        None,
    ],
}


# =============================================================================
# CLI Argument Parsing (T003 scaffold)
# =============================================================================


def parse_args():
    """Parse command-line arguments for the mock data generator.

    Returns:
        argparse.Namespace with 'output' (Path) and 'seed' (int or None).
    """
    parser = argparse.ArgumentParser(
        description="Generate mock indoor location tracking data in a SQLite database.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("database/mock.db"),
        help="Output path for the SQLite database file (default: database/mock.db)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible data generation (default: random)",
    )
    return parser.parse_args()


# =============================================================================
# Timestamp Generation — Business-hour weighted (T006, T010)
# =============================================================================


def generate_weighted_timestamp(base_time, window_days):
    """Generate a single timestamp within the time window, weighted toward
    business hours (8am–6pm).

    Approximately 70%% of generated timestamps fall during business hours
    and 30%% during off-hours, producing realistic daily activity patterns
    for indoor location tracking queries.

    Args:
        base_time: The end of the time window (typically datetime.now()).
        window_days: Number of days the window spans (typically 7).

    Returns:
        A datetime object within [base_time - window_days, base_time].
    """
    # Pick a random day within the window
    day_offset = random.randint(0, window_days - 1)
    target_date = base_time - datetime.timedelta(days=day_offset)

    # Pick hour with business-hour weighting (~70% during 8am-6pm)
    if random.random() < 0.70:
        hour = random.randint(8, 17)  # Business hours
    else:
        # Off-hours: 0-7 or 18-23
        hour = random.choice(list(range(0, 8)) + list(range(18, 24)))

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return target_date.replace(hour=hour, minute=minute, second=second, microsecond=0)


# =============================================================================
# Signal Strength Generation — Normal distribution (T006, T010)
# =============================================================================


def generate_rssi():
    """Generate an RSSI value with normal distribution centered at -65 dBm.

    Real BLE signal strengths follow a roughly normal distribution.
    Values are clamped to the valid range [-100, -30] per schema constraints.
    The standard deviation of 12 produces realistic spread across the range.

    Returns:
        Integer RSSI value in range [-100, -30].
    """
    rssi = int(random.gauss(-65, 12))
    return max(-100, min(-30, rssi))


# =============================================================================
# Polygon Coordinate Generation (T004)
# =============================================================================


def generate_polygon_coords(zone_index):
    """Generate a simple rectangular polygon as a JSON string.

    Each zone gets a unique position based on its index, simulating
    a floor plan layout. Coordinates are in arbitrary units (meters
    from building origin).

    Args:
        zone_index: Integer index of the zone (0-based) for positioning.

    Returns:
        JSON string containing an array of [x, y] coordinate pairs.
    """
    # Position zones in a grid layout: 2 columns per floor
    col = zone_index % 2
    row = zone_index // 2
    base_x = col * 15.0 + random.uniform(0, 2)
    base_y = row * 12.0 + random.uniform(0, 2)
    width = random.uniform(8.0, 12.0)
    height = random.uniform(6.0, 10.0)

    coords = [
        [round(base_x, 1), round(base_y, 1)],
        [round(base_x + width, 1), round(base_y, 1)],
        [round(base_x + width, 1), round(base_y + height, 1)],
        [round(base_x, 1), round(base_y + height, 1)],
    ]
    return json.dumps(coords)


# =============================================================================
# Data Generation Functions (T004–T008)
# =============================================================================


def generate_zones(cursor):
    """Insert zone records into the database.

    Creates 8 zones from ZONE_DEFINITIONS with realistic names, floor
    assignments across 3 floors, department assignments across 4 departments,
    valid polygon_coords JSON, and optional metadata JSON.

    All INSERTs use parameterized queries (Constitution I: Safety First).

    Args:
        cursor: sqlite3.Cursor connected to the target database.

    Returns:
        List of zone IDs (integers) for use by downstream generators.
    """
    zone_ids = []
    for i, zone_def in enumerate(ZONE_DEFINITIONS):
        polygon = generate_polygon_coords(i)
        metadata = json.dumps(zone_def["metadata"]) if zone_def.get("metadata") else None

        cursor.execute(
            "INSERT INTO zones (name, floor, department, polygon_coords, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                zone_def["name"],
                zone_def["floor"],
                zone_def["department"],
                polygon,
                metadata,
            ),
        )
        zone_ids.append(cursor.lastrowid)

    return zone_ids


def generate_entities(cursor):
    """Insert entity records into the database.

    Creates 25 entities with weighted type distribution (~40% employee,
    ~25% customer, ~20% asset, ~15% device). Each entity gets a unique
    external_id in a type-specific format and optional tags.

    Note: first_seen and last_seen are left NULL here and updated later
    by update_entity_timestamps() after pings are generated.

    Args:
        cursor: sqlite3.Cursor connected to the target database.

    Returns:
        List of entity IDs (integers) for use by downstream generators.
    """
    entity_ids = []

    # Build the entity list with weighted type distribution
    entities_to_create = []
    for entity_type, count in ENTITY_TYPE_COUNTS.items():
        for i in range(count):
            entities_to_create.append((entity_type, i))

    # Shuffle to mix types rather than inserting all of one type sequentially
    random.shuffle(entities_to_create)

    for entity_type, index in entities_to_create:
        # Generate type-specific external_id (per data-model.md)
        if entity_type == "employee":
            external_id = f"EMP-{index + 1:04d}"
            name = EMPLOYEE_NAMES[index % len(EMPLOYEE_NAMES)]
        elif entity_type == "customer":
            external_id = f"CUST-{index + 1:04d}"
            name = CUSTOMER_NAMES[index % len(CUSTOMER_NAMES)]
        elif entity_type == "asset":
            external_id = f"ASSET-{index + 1:04d}"
            name = ASSET_NAMES[index % len(ASSET_NAMES)]
        else:  # device
            # MAC-style external_id for devices
            mac_bytes = [random.randint(0, 255) for _ in range(6)]
            external_id = ":".join(f"{b:02X}" for b in mac_bytes)
            name = DEVICE_NAMES[index % len(DEVICE_NAMES)]

        # Pick random tags from the pool for this type (may be None)
        tags_list = random.choice(TAG_POOLS[entity_type])
        tags = json.dumps(tags_list) if tags_list else None

        cursor.execute(
            "INSERT INTO entities (external_id, name, type, tags) "
            "VALUES (?, ?, ?, ?)",
            (external_id, name, entity_type, tags),
        )
        entity_ids.append(cursor.lastrowid)

    return entity_ids


def generate_location_pings(cursor, entity_ids, zone_ids, base_time):
    """Insert location ping records into the database.

    Generates 500+ pings distributed across all entities and zones over
    a 7-day window. Timestamps are business-hour weighted (~70% during
    8am-6pm). RSSI values follow a normal distribution centered at -65 dBm.

    Each entity gets a roughly proportional share of total pings, with
    some random variance to avoid perfectly uniform distribution.

    Args:
        cursor: sqlite3.Cursor connected to the target database.
        entity_ids: List of valid entity IDs to reference.
        zone_ids: List of valid zone IDs to reference.
        base_time: End of the 7-day time window (datetime).

    Returns:
        Total number of pings inserted.
    """
    ping_count = 0

    # Distribute pings across entities — each gets a base allocation
    # plus random variance for realistic distribution
    base_pings_per_entity = NUM_PINGS // len(entity_ids)

    for entity_id in entity_ids:
        # Vary the number of pings per entity (±30%) for realism
        entity_ping_count = max(
            5, int(base_pings_per_entity * random.uniform(0.7, 1.3))
        )

        # Each entity tends to frequent a few zones more than others.
        # Pick 2-3 "home" zones with higher probability.
        home_zones = random.sample(zone_ids, k=min(3, len(zone_ids)))

        for _ in range(entity_ping_count):
            # 70% chance of being in a home zone, 30% in any zone
            if random.random() < 0.70:
                zone_id = random.choice(home_zones)
            else:
                zone_id = random.choice(zone_ids)

            timestamp = generate_weighted_timestamp(base_time, TIME_WINDOW_DAYS)
            rssi = generate_rssi()
            accuracy = round(random.uniform(0.5, 10.0), 1)

            # Source device corresponds to the zone's beacon
            zone_index = zone_ids.index(zone_id)
            source_device = f"beacon-{zone_index + 1:02d}"

            # Raw data with BLE signal metadata
            raw_data = json.dumps(
                {"signal_type": "ble", "channel": random.randint(37, 39)}
            )

            cursor.execute(
                "INSERT INTO location_pings "
                "(entity_id, zone_id, timestamp, rssi, accuracy, source_device, raw_data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    entity_id,
                    zone_id,
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    rssi,
                    accuracy,
                    source_device,
                    raw_data,
                ),
            )
            ping_count += 1

    return ping_count


def derive_zone_events(cursor):
    """Derive zone events from location ping sequences.

    For each entity, analyzes their chronological ping history to detect
    zone transitions. Generates three event types:
        - 'enter': When an entity first appears in a zone
        - 'dwell': When an entity has multiple consecutive pings in the
                    same zone (duration > 0)
        - 'exit':  When an entity leaves a zone (transitions to another)

    This derivation approach guarantees temporal consistency between
    pings and events (research.md R2).

    Confidence scoring:
        - 1 ping in visit:  0.70 (low — single observation)
        - 2-3 pings:        0.85 (moderate)
        - 4+ pings:         0.95 (high — well-supported)

    Args:
        cursor: sqlite3.Cursor connected to the target database.

    Returns:
        Total number of events inserted.
    """
    event_count = 0

    # Get all distinct entities that have pings
    cursor.execute("SELECT DISTINCT entity_id FROM location_pings")
    entity_ids = [row[0] for row in cursor.fetchall()]

    for entity_id in entity_ids:
        # Fetch this entity's pings in chronological order
        cursor.execute(
            "SELECT zone_id, timestamp FROM location_pings "
            "WHERE entity_id = ? ORDER BY timestamp",
            (entity_id,),
        )
        pings = cursor.fetchall()

        if not pings:
            continue

        # Group consecutive pings into "visits" (same zone streaks)
        visits = []
        current_zone = pings[0][0]
        visit_start = pings[0][1]
        visit_pings = [pings[0][1]]

        for zone_id, ts in pings[1:]:
            if zone_id == current_zone:
                # Same zone — extend current visit
                visit_pings.append(ts)
            else:
                # Zone changed — close current visit, start new one
                visits.append(
                    {
                        "zone_id": current_zone,
                        "start": visit_start,
                        "end": visit_pings[-1],
                        "ping_count": len(visit_pings),
                    }
                )
                current_zone = zone_id
                visit_start = ts
                visit_pings = [ts]

        # Don't forget the last visit
        visits.append(
            {
                "zone_id": current_zone,
                "start": visit_start,
                "end": visit_pings[-1],
                "ping_count": len(visit_pings),
            }
        )

        # Generate events from visits
        for i, visit in enumerate(visits):
            ping_count = visit["ping_count"]

            # Confidence based on number of supporting pings
            if ping_count >= 4:
                confidence = round(random.uniform(0.93, 1.0), 2)
            elif ping_count >= 2:
                confidence = round(random.uniform(0.80, 0.90), 2)
            else:
                confidence = round(random.uniform(0.65, 0.75), 2)

            # 'enter' event — entity arrives in this zone
            cursor.execute(
                "INSERT INTO zone_events "
                "(entity_id, zone_id, event_type, start_time, end_time, "
                "duration_seconds, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    entity_id,
                    visit["zone_id"],
                    "enter",
                    visit["start"],
                    visit["start"],  # Point-in-time event
                    0,
                    confidence,
                ),
            )
            event_count += 1

            # 'dwell' event — entity stays in zone (only if 2+ pings)
            if ping_count >= 2:
                start_dt = datetime.datetime.strptime(visit["start"], "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.datetime.strptime(visit["end"], "%Y-%m-%d %H:%M:%S")
                duration = int((end_dt - start_dt).total_seconds())

                # Only emit dwell if there's actual duration
                if duration > 0:
                    cursor.execute(
                        "INSERT INTO zone_events "
                        "(entity_id, zone_id, event_type, start_time, end_time, "
                        "duration_seconds, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            entity_id,
                            visit["zone_id"],
                            "dwell",
                            visit["start"],
                            visit["end"],
                            duration,
                            confidence,
                        ),
                    )
                    event_count += 1

            # 'exit' event — entity leaves this zone (not for the last visit,
            # which represents where the entity currently is)
            if i < len(visits) - 1:
                cursor.execute(
                    "INSERT INTO zone_events "
                    "(entity_id, zone_id, event_type, start_time, end_time, "
                    "duration_seconds, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        entity_id,
                        visit["zone_id"],
                        "exit",
                        visit["end"],
                        visit["end"],  # Point-in-time event
                        0,
                        confidence,
                    ),
                )
                event_count += 1

    return event_count


def update_entity_timestamps(cursor):
    """Update first_seen and last_seen on entities from their ping history.

    After all pings are generated, this function sets each entity's
    first_seen to their earliest ping timestamp and last_seen to their
    latest. This ensures temporal consistency (FR-005).

    Args:
        cursor: sqlite3.Cursor connected to the target database.
    """
    cursor.execute(
        "UPDATE entities SET "
        "first_seen = (SELECT MIN(timestamp) FROM location_pings WHERE location_pings.entity_id = entities.id), "
        "last_seen = (SELECT MAX(timestamp) FROM location_pings WHERE location_pings.entity_id = entities.id) "
        "WHERE id IN (SELECT DISTINCT entity_id FROM location_pings)"
    )


# =============================================================================
# Summary Output (T008, per CLI contract)
# =============================================================================


def print_summary(output_path, seed, counts):
    """Print a summary of the generated data to stdout.

    Format follows the CLI contract in contracts/cli.md.

    Args:
        output_path: Path to the generated database file.
        seed: The random seed used (int).
        counts: Dict with keys 'zones', 'entities', 'pings', 'events'.
    """
    print("Mock data generated successfully.")
    print(f"  Output:   {output_path}")
    print(f"  Seed:     {seed}")
    print(f"  Zones:    {counts['zones']}")
    print(f"  Entities: {counts['entities']}")
    print(f"  Pings:    {counts['pings']}")
    print(f"  Events:   {counts['events']}")


# =============================================================================
# Main Entry Point (T003 scaffold + T008 wiring + T011 seed + T012 errors)
# =============================================================================


def main():
    """Main entry point for the mock data generation script.

    Execution flow:
        1. Parse CLI arguments
        2. Initialize random seed (for reproducibility)
        3. Delete existing database file (clean state per FR-008)
        4. Create database with schema
        5. Generate data in dependency order:
           zones → entities → pings → events → entity timestamps
        6. Commit and print summary
    """
    args = parse_args()
    output_path = args.output

    # --- Seed initialization (T011: US3 reproducibility) ---
    # If no seed provided, auto-generate one and print it so the user
    # can reproduce this run later if needed.
    if args.seed is not None:
        seed = args.seed
    else:
        seed = random.randint(0, 2**31 - 1)

    random.seed(seed)

    # --- File setup (T003 scaffold + T012 error handling) ---
    try:
        # Create parent directories if they don't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Delete existing database file for clean state (FR-008, research R4)
        if output_path.exists():
            output_path.unlink()

    except PermissionError:
        print(
            f"Error: Cannot write to {output_path} — Permission denied",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as e:
        print(f"Error: Cannot prepare output path {output_path} — {e}", file=sys.stderr)
        sys.exit(1)

    # --- Database creation and data generation ---
    conn = None
    try:
        conn = sqlite3.connect(str(output_path))
        cursor = conn.cursor()

        # Enable foreign key enforcement (per constitution and spec assumptions)
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create schema — all tables and indexes (T003)
        cursor.executescript(SCHEMA_SQL)

        # Begin explicit transaction for atomicity (research R4)
        cursor.execute("BEGIN TRANSACTION")

        # Generate data in dependency order (T008 wiring):
        # 1. Zones first — no dependencies
        zone_ids = generate_zones(cursor)

        # 2. Entities second — no dependencies on zones
        entity_ids = generate_entities(cursor)

        # 3. Location pings — references zones and entities
        base_time = datetime.datetime.now().replace(microsecond=0)
        ping_count = generate_location_pings(cursor, entity_ids, zone_ids, base_time)

        # 4. Zone events — derived from ping sequences
        event_count = derive_zone_events(cursor)

        # 5. Update entity first_seen/last_seen from ping history
        update_entity_timestamps(cursor)

        # Commit the transaction
        conn.commit()

        # Print summary per CLI contract
        counts = {
            "zones": len(zone_ids),
            "entities": len(entity_ids),
            "pings": ping_count,
            "events": event_count,
        }
        print_summary(output_path, seed, counts)

    except sqlite3.Error as e:
        print(f"Error: Database operation failed — {e}", file=sys.stderr)
        # Clean up incomplete database file
        if conn:
            conn.close()
            conn = None
        if output_path.exists():
            output_path.unlink()
        sys.exit(1)

    except (PermissionError, OSError) as e:
        print(f"Error: I/O failure — {e}", file=sys.stderr)
        if conn:
            conn.close()
            conn = None
        if output_path.exists():
            output_path.unlink()
        sys.exit(1)

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
