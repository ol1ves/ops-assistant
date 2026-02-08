"""
Schema DDL for the Lumo Ops Assistant in-store location tracking database.

Defines all table structures, constraints, and indexes as a single SQL
string constant. This module is imported by generate_mock_data.py to
create the database schema before populating it with mock data.

Target scale: ~10-20 zones, ~5-30 entities (people/assets), ~20K-80K pings/day.

Schema design philosophy:
    - Normalized but not overly complex
    - Timestamps on all temporal data
    - Indexes for common query patterns
    - Support both real-time (pings) and derived (events) data

Tables:
    zones            — Physical areas within the building (lobby, loading_dock, aisle, etc.)
    entities         — Trackable objects and people (external_id: badge_12, forklift_3)
    location_pings   — Real-time location readings (raw data; rssi for data quality)
    zone_events      — Derived enter/exit/dwell events (analytical data)
"""

# Complete schema DDL as a single SQL script.
SCHEMA_SQL = """
-- ============================================================================
-- ZONES: Physical areas within the building (in-store navigation)
-- ============================================================================

CREATE TABLE zones (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    zone_type TEXT,        -- lobby, loading_dock, aisle, floor_landing, department, other
    floor INTEGER NOT NULL,
    department TEXT,
    polygon_coords TEXT,   -- JSON string for simple boundary
    metadata TEXT,         -- JSON for extensibility
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Strategic indexes for common queries
CREATE INDEX idx_zones_floor ON zones(floor);
CREATE INDEX idx_zones_zone_type ON zones(zone_type);
CREATE INDEX idx_zones_department ON zones(department);

-- ============================================================================
-- ENTITIES: Trackable objects and people
-- ============================================================================

CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    external_id TEXT UNIQUE,  -- Could be device MAC, employee badge, etc.
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('customer', 'employee', 'asset', 'device')),
    tags TEXT,  -- JSON array for categorization
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

-- Essential for type filtering and time-window queries
CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_last_seen ON entities(last_seen);

-- ============================================================================
-- LOCATION PINGS: Real-time location readings from tracking hardware
-- ============================================================================

CREATE TABLE location_pings (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    rssi INTEGER,           -- Signal strength (-100 to -30)
    accuracy REAL,          -- Estimated accuracy in meters
    source_device TEXT,     -- Which receiver/beacon
    raw_data TEXT,          -- JSON for raw signal data
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE CASCADE
);

-- CRITICAL for performance - most queries filter by time
CREATE INDEX idx_pings_timestamp ON location_pings(timestamp);
CREATE INDEX idx_pings_entity_zone ON location_pings(entity_id, zone_id);
CREATE INDEX idx_pings_rssi ON location_pings(rssi) WHERE rssi < -80;

-- ============================================================================
-- ZONE EVENTS: Derived enter/exit/dwell events (analytical layer)
-- ============================================================================

CREATE TABLE zone_events (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    event_type TEXT CHECK(event_type IN ('enter', 'exit', 'dwell')),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    confidence REAL DEFAULT 1.0,
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);

-- Optimize for time-range and dwell time queries
CREATE INDEX idx_events_time_range ON zone_events(start_time, end_time);
CREATE INDEX idx_events_duration ON zone_events(duration_seconds);
"""
