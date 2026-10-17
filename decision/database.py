import sqlite3
from datetime import datetime, timezone


DEFAULT_DB_PATH = "ghoststock.db"



def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH, seed: bool = True) -> sqlite3.Connection:
    """Initialize SQLite database with all required tables and optional deterministic seed."""
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            physical_quantity INTEGER NOT NULL,
            reserved_quantity INTEGER NOT NULL DEFAULT 0,
            damaged_quantity INTEGER NOT NULL DEFAULT 0,
            version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS evidence_records (
            evidence_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            agent TEXT NOT NULL,
            claim_type TEXT NOT NULL,
            sku TEXT NOT NULL,
            extracted_value TEXT NOT NULL,
            unit TEXT NOT NULL,
            confidence REAL NOT NULL,
            raw_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_cases (
            case_id TEXT PRIMARY KEY,
            target_sku TEXT NOT NULL,
            status TEXT NOT NULL,
            decision_summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_adjustments (
            adjustment_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            adjustment_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            before_quantity INTEGER,
            after_quantity INTEGER,
            approved_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES reconciliation_cases(case_id)
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES reconciliation_cases(case_id)
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            step_name TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """)

        if seed:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
            INSERT OR IGNORE INTO inventory (sku, physical_quantity, reserved_quantity, damaged_quantity, version, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("SKU-GHOST-01", 250, 10, 0, 1, now))

    return conn
