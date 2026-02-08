"""
Lumo Ops Assistant — mock data generation.

Generates a SQLite database with in-store location data: zones, entities,
location_pings, zone_events. Target scale: ~10-20 zones, ~5-30 entities,
~20K-50K pings over one day.

Usage:
    uv run scripts/generate_mock_data.py [--output PATH] [--seed N]
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

from database.schema import SCHEMA_SQL # type: ignore


# Target scale: founder spec ~10-20 zones, ~5-30 entities, ~20K-80K pings/day
NUM_ZONES = 12
NUM_ENTITIES = 20
TARGET_PINGS = 30000
LOW_RSSI_FRACTION = 0.08


# Lumo-style zones with zone_type; spread across floors for movement/floor-jump queries
ZONE_DEFINITIONS = [
    {"name": "Lobby", "zone_type": "lobby", "floor": 1, "department": None},
    {"name": "Loading Dock", "zone_type": "loading_dock", "floor": 1, "department": None},
    {"name": "Aisle A", "zone_type": "aisle", "floor": 1, "department": "Grocery"},
    {"name": "Aisle B", "zone_type": "aisle", "floor": 1, "department": "Grocery"},
    {"name": "Floor 2 East", "zone_type": "floor_landing", "floor": 2, "department": None},
    {"name": "Floor 2 West", "zone_type": "floor_landing", "floor": 2, "department": None},
    {"name": "Electronics", "zone_type": "department", "floor": 2, "department": "Merchandise"},
    {"name": "Breakroom", "zone_type": "other", "floor": 2, "department": "HR"},
    {"name": "Floor 3 Landing", "zone_type": "floor_landing", "floor": 3, "department": None},
    {"name": "Storage", "zone_type": "other", "floor": 3, "department": "Inventory"},
    {"name": "Zone A", "zone_type": "department", "floor": 1, "department": "Sales"},
    {"name": "Office", "zone_type": "other", "floor": 2, "department": "Management"},
]

# Entity counts: badge_1..badge_N (employees), forklift_1..forklift_M (assets)
NUM_BADGES = 14
NUM_FORKLIFTS = 6


# =============================================================================
# CLI Argument Parsing (T003 scaffold)
# =============================================================================


def parse_args():
    """Parse command-line arguments for the mock data generator.

    Returns:
        argparse.Namespace with 'output' (Path) and 'seed' (int or None).
    """
    parser = argparse.ArgumentParser(
        description="Generate Lumo Ops Assistant mock in-store location data (SQLite).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/mock.db"),
        help="Output path for the SQLite database file (default: data/mock.db)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible data generation (default: random)",
    )
    return parser.parse_args()


def _timestamp_in_day(day_start, day_end, business_hour_fraction=0.8):
    """Random timestamp in [day_start, day_end], weighted toward 06:00-22:00."""
    delta = (day_end - day_start).total_seconds()
    ts = day_start + datetime.timedelta(seconds=random.uniform(0, delta))
    if random.random() < business_hour_fraction:
        hour = random.randint(6, 21)
    else:
        hour = random.choice(list(range(0, 6)) + list(range(22, 24)))
    return ts.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59), microsecond=0)


def _rssi(low_fraction):
    """RSSI: low_fraction of the time in [-95, -80], else normal around -65."""
    if random.random() < low_fraction:
        return random.randint(-95, -80)
    return max(-100, min(-30, int(random.gauss(-65, 12))))


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
    """Insert zones from ZONE_DEFINITIONS (name, zone_type, floor, department)."""
    zone_ids = []
    for i, zone_def in enumerate(ZONE_DEFINITIONS):
        polygon = generate_polygon_coords(i)
        cursor.execute(
            "INSERT INTO zones (name, zone_type, floor, department, polygon_coords, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                zone_def["name"],
                zone_def["zone_type"],
                zone_def["floor"],
                zone_def.get("department"),
                polygon,
                None,
            ),
        )
        zone_ids.append(cursor.lastrowid)

    return zone_ids


def generate_entities(cursor):
    """Insert entity records: badge_1..badge_N (employee), forklift_1..forklift_M (asset)."""
    entity_ids = []
    for i in range(1, NUM_BADGES + 1):
        cursor.execute(
            "INSERT INTO entities (external_id, name, type, tags) VALUES (?, ?, ?, ?)",
            (f"badge_{i}", f"Employee {i}", "employee", None),
        )
        entity_ids.append(cursor.lastrowid)
    for i in range(1, NUM_FORKLIFTS + 1):
        cursor.execute(
            "INSERT INTO entities (external_id, name, type, tags) VALUES (?, ?, ?, ?)",
            (f"forklift_{i}", f"Forklift {i}", "asset", None),
        )
        entity_ids.append(cursor.lastrowid)
    return entity_ids


def generate_location_pings(cursor, entity_ids, zone_ids, base_time):
    """Generate ~TARGET_PINGS pings over one day; random walk per entity; some low-RSSI and floor jumps."""
    day_end = base_time
    day_start = day_end - datetime.timedelta(days=1)
    zone_id_to_floor = {zone_ids[i]: ZONE_DEFINITIONS[i]["floor"] for i in range(len(zone_ids))}
    floors = list(set(zone_id_to_floor.values()))
    zones_by_floor = {f: [z for z in zone_ids if zone_id_to_floor[z] == f] for f in floors}

    # Allocate pings per entity (sum = TARGET_PINGS)
    n = len(entity_ids)
    base_per = TARGET_PINGS // n
    remainder = TARGET_PINGS % n
    counts = [base_per + (1 if i < remainder else 0) for i in range(n)]

    ping_count = 0
    for ei, entity_id in enumerate(entity_ids):
        num_pings = counts[ei]
        timestamps = sorted(
            [_timestamp_in_day(day_start, day_end) for _ in range(num_pings)]
        )
        # Random walk: 85% stay in same zone, 15% move; when moving, 20% pick different floor
        current_zone = random.choice(zone_ids)
        current_floor = zone_id_to_floor[current_zone]
        for ts in timestamps:
            if random.random() < 0.85:
                zone_id = current_zone
            else:
                if random.random() < 0.2 and len(floors) > 1:
                    other_floors = [f for f in floors if f != current_floor]
                    target_floor = random.choice(other_floors)
                    zone_id = random.choice(zones_by_floor[target_floor])
                    current_floor = target_floor
                else:
                    zone_id = random.choice(zone_ids)
                    current_floor = zone_id_to_floor[zone_id]
                current_zone = zone_id
            rssi = _rssi(LOW_RSSI_FRACTION)
            zone_index = zone_ids.index(zone_id)
            cursor.execute(
                "INSERT INTO location_pings "
                "(entity_id, zone_id, timestamp, rssi, accuracy, source_device, raw_data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    entity_id,
                    zone_id,
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    rssi,
                    round(random.uniform(0.5, 10.0), 1),
                    f"beacon-{zone_index + 1:02d}",
                    json.dumps({"signal_type": "ble", "channel": random.randint(37, 39)}),
                ),
            )
            ping_count += 1
    return ping_count


def derive_zone_events(cursor):
    """Derive enter/dwell/exit events from each entity's chronological pings. Single default confidence."""
    event_count = 0
    confidence = 0.9
    cursor.execute("SELECT DISTINCT entity_id FROM location_pings")
    entity_ids = [row[0] for row in cursor.fetchall()]

    for entity_id in entity_ids:
        cursor.execute(
            "SELECT zone_id, timestamp FROM location_pings WHERE entity_id = ? ORDER BY timestamp",
            (entity_id,),
        )
        pings = cursor.fetchall()
        if not pings:
            continue

        visits = []
        current_zone, visit_start = pings[0][0], pings[0][1]
        visit_pings = [pings[0][1]]
        for zone_id, ts in pings[1:]:
            if zone_id == current_zone:
                visit_pings.append(ts)
            else:
                visits.append(
                    {"zone_id": current_zone, "start": visit_start, "end": visit_pings[-1], "ping_count": len(visit_pings)}
                )
                current_zone, visit_start = zone_id, ts
                visit_pings = [ts]
        visits.append(
            {"zone_id": current_zone, "start": visit_start, "end": visit_pings[-1], "ping_count": len(visit_pings)}
        )

        for i, visit in enumerate(visits):
            cursor.execute(
                "INSERT INTO zone_events (entity_id, zone_id, event_type, start_time, end_time, duration_seconds, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entity_id, visit["zone_id"], "enter", visit["start"], visit["start"], 0, confidence),
            )
            event_count += 1
            if visit["ping_count"] >= 2:
                start_dt = datetime.datetime.strptime(visit["start"], "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.datetime.strptime(visit["end"], "%Y-%m-%d %H:%M:%S")
                duration = int((end_dt - start_dt).total_seconds())
                if duration > 0:
                    cursor.execute(
                        "INSERT INTO zone_events (entity_id, zone_id, event_type, start_time, end_time, duration_seconds, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (entity_id, visit["zone_id"], "dwell", visit["start"], visit["end"], duration, confidence),
                    )
                    event_count += 1
            if i < len(visits) - 1:
                cursor.execute(
                    "INSERT INTO zone_events (entity_id, zone_id, event_type, start_time, end_time, duration_seconds, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (entity_id, visit["zone_id"], "exit", visit["end"], visit["end"], 0, confidence),
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
    """Create DB from schema, then zones → entities → pings → zone_events → entity timestamps; print summary."""
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
