from datetime import datetime, timezone
import json
import sqlite3
import uuid


class ExecutionLedger:
    """Records audit trail events for every step in the decision lifecycle."""

    VALID_STATUSES = {
        "COMPLETED", "FAILED", "SKIPPED", "PENDING", "NEEDS_REVIEW",
        "SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE",
        "PROPOSED", "APPROVED", "APPLIED", "VERIFIED"
    }


    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def record_event(
        self,
        case_id: str,
        step_name: str,
        agent_name: str,
        status: str,
        details: str
    ) -> str:
        """Log a structured audit event into execution_events table."""
        if status not in self.VALID_STATUSES:
            status = "PENDING"

        event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()


        with self.conn:
            self.conn.execute("""
            INSERT INTO execution_events (
                event_id, case_id, step_name, agent_name, status, details, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_id, case_id, step_name, agent_name, status, details, now))

        return event_id

    def get_trace(self, case_id: str) -> list[dict]:
        """Retrieve chronological execution trace for a given case."""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT event_id, case_id, step_name, agent_name, status, details, timestamp
        FROM execution_events
        WHERE case_id = ?
        ORDER BY timestamp ASC
        """, (case_id,))
        return [dict(row) for row in cursor.fetchall()]
