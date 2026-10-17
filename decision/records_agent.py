import json
import sqlite3
from typing import Optional
from contract import Evidence


class RecordsAgent:
    """Queries authoritative inventory records and persists evidence rows."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_inventory(self, sku: str) -> Optional[dict]:
        """Fetch current inventory row for a SKU."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE sku = ?", (sku,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def sku_exists(self, sku: str) -> bool:
        """Check if SKU exists in the authoritative inventory."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM inventory WHERE sku = ?", (sku,))
        return cursor.fetchone() is not None

    def get_adjustments_history(self, sku: str) -> list[dict]:
        """Retrieve adjustment audit history for a SKU."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM inventory_adjustments WHERE sku = ? ORDER BY created_at DESC",
            (sku,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def record_evidence(self, case_id: str, evidence: Evidence) -> None:
        """Persist a validated Evidence instance into evidence_records."""
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO evidence_records (
                evidence_id, case_id, source_type, agent, claim_type, sku,
                extracted_value, unit, confidence, raw_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evidence.evidence_id,
                case_id,
                evidence.source_type.value if hasattr(evidence.source_type, 'value') else str(evidence.source_type),
                evidence.agent_name,
                evidence.claim_type,
                evidence.sku,
                str(evidence.extracted_value),
                evidence.unit,
                float(evidence.confidence),
                json.dumps(evidence.metadata),
                evidence.timestamp
            ))
