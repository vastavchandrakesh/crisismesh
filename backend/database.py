"""
CrisisMesh — SQLite persistence layer.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "crisismesh.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS zones (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            lat         REAL NOT NULL,
            lon         REAL NOT NULL,
            radius_m    REAL DEFAULT 5000,
            active      INTEGER DEFAULT 1,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS device_consents (
            device_id    TEXT NOT NULL,
            zone_id      TEXT NOT NULL,
            consented_at TEXT NOT NULL,
            active       INTEGER DEFAULT 1,
            PRIMARY KEY (device_id, zone_id)
        );

        CREATE TABLE IF NOT EXISTS audio_events (
            id           TEXT PRIMARY KEY,
            device_id    TEXT NOT NULL,
            zone_id      TEXT NOT NULL,
            transcript   TEXT,
            event_type   TEXT,
            confidence   REAL DEFAULT 0,
            priority     TEXT DEFAULT 'LOW',
            keywords     TEXT,          -- JSON array
            lat          REAL,
            lon          REAL,
            timestamp    TEXT NOT NULL,
            is_distress  INTEGER DEFAULT 0,
            offline_flag INTEGER DEFAULT 0,
            synced       INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS incidents (
            id           TEXT PRIMARY KEY,
            zone_id      TEXT NOT NULL,
            sector       TEXT,
            status       TEXT DEFAULT 'NEEDS_VERIFICATION',
            confidence   REAL DEFAULT 0,
            priority     TEXT DEFAULT 'LOW',
            event_count  INTEGER DEFAULT 0,
            lat          REAL,
            lon          REAL,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS incident_events (
            incident_id  TEXT NOT NULL,
            event_id     TEXT NOT NULL,
            PRIMARY KEY (incident_id, event_id)
        );

        CREATE TABLE IF NOT EXISTS offline_queue (
            id           TEXT PRIMARY KEY,
            device_id    TEXT NOT NULL,
            payload      TEXT NOT NULL,
            queued_at    TEXT NOT NULL,
            synced       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id           TEXT PRIMARY KEY,
            action       TEXT NOT NULL,
            actor        TEXT DEFAULT 'system',
            entity_type  TEXT DEFAULT '',
            entity_id    TEXT DEFAULT '',
            detail       TEXT DEFAULT '',
            timestamp    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS incident_notes (
            id          TEXT PRIMARY KEY,
            incident_id TEXT NOT NULL,
            text        TEXT NOT NULL,
            author      TEXT DEFAULT 'responder',
            timestamp   TEXT NOT NULL
        );
    """)
    conn.commit()

    # Safely add columns that may not exist in older DBs
    for sql in [
        "ALTER TABLE audio_events ADD COLUMN battery_pct REAL DEFAULT NULL",
        "ALTER TABLE incidents    ADD COLUMN team         TEXT DEFAULT ''",
        "ALTER TABLE incidents ADD COLUMN triage TEXT DEFAULT ''",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass

    conn.close()
