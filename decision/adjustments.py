from datetime import datetime, timezone
import sqlite3
import uuid
from typing import Optional


class AdjustmentError(Exception):
    """Base error for inventory adjustment failures."""
    pass


def propose_adjustment(
    case_id: str,
    sku: str,
    adjustment_type: str,
    quantity: int,
    reason: str,
    evidence_ids: list[str],
    conn: sqlite3.Connection
) -> str:
    """Create a proposed adjustment in PROPOSED status. Does NOT mutate inventory."""
    if quantity == 0:
        raise AdjustmentError("Adjustment quantity cannot be zero.")

    cursor = conn.cursor()
    cursor.execute("SELECT physical_quantity FROM inventory WHERE sku = ?", (sku,))
    if not cursor.fetchone():
        raise AdjustmentError(f"Cannot propose adjustment: SKU '{sku}' does not exist.")

    adj_id = f"ADJ-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    with conn:
        conn.execute("""
        INSERT INTO inventory_adjustments (
            adjustment_id, case_id, sku, adjustment_type, quantity,
            reason, status, before_quantity, after_quantity, approved_by,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'PROPOSED', NULL, NULL, NULL, ?, ?)
        """, (adj_id, case_id, sku, adjustment_type, quantity, reason, now, now))

    return adj_id


def approve_adjustment(adjustment_id: str, approver: str, conn: sqlite3.Connection) -> bool:
    """Mark a PROPOSED adjustment as APPROVED. Requires explicit approver name."""
    if not approver or not approver.strip():
        raise AdjustmentError("Approver name cannot be empty.")

    cursor = conn.cursor()
    cursor.execute("SELECT status FROM inventory_adjustments WHERE adjustment_id = ?", (adjustment_id,))
    row = cursor.fetchone()
    if not row:
        raise AdjustmentError(f"Adjustment '{adjustment_id}' not found.")

    current_status = row["status"] if isinstance(row, sqlite3.Row) else row[0]
    if current_status != "PROPOSED":
        raise AdjustmentError(f"Cannot approve adjustment in status '{current_status}' (must be 'PROPOSED').")

    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute("""
        UPDATE inventory_adjustments
        SET status = 'APPROVED', approved_by = ?, updated_at = ?
        WHERE adjustment_id = ?
        """, (approver.strip(), now, adjustment_id))

    return True


def apply_adjustment(adjustment_id: str, conn: sqlite3.Connection) -> dict:
    """
    Atomically apply an APPROVED adjustment to inventory.
    Enforces idempotency, optimistic locking, and transaction safety.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_adjustments WHERE adjustment_id = ?", (adjustment_id,))
    adj_row = cursor.fetchone()
    if not adj_row:
        raise AdjustmentError(f"Adjustment '{adjustment_id}' not found.")

    adj = dict(adj_row)
    status = adj["status"]
    if status == "APPLIED" or status == "VERIFIED":
        raise AdjustmentError(f"Idempotency violation: Adjustment '{adjustment_id}' has already been applied.")
    if status != "APPROVED":
        raise AdjustmentError(f"Cannot apply adjustment '{adjustment_id}': status is '{status}' (requires 'APPROVED').")

    sku = adj["sku"]
    delta = adj["quantity"]

    with conn:
        # Atomic read under transaction
        cursor.execute("SELECT physical_quantity, version FROM inventory WHERE sku = ?", (sku,))
        inv_row = cursor.fetchone()
        if not inv_row:
            raise AdjustmentError(f"Target SKU '{sku}' not found in inventory table.")

        before_qty = inv_row["physical_quantity"] if isinstance(inv_row, sqlite3.Row) else inv_row[0]
        version = inv_row["version"] if isinstance(inv_row, sqlite3.Row) else inv_row[1]

        after_qty = before_qty + delta
        if after_qty < 0:
            raise AdjustmentError(
                f"Stock shortage: cannot reduce stock from {before_qty} by {delta} (results in {after_qty})."
            )

        now = datetime.now(timezone.utc).isoformat()

        # Optimistic lock update
        cur = conn.execute("""
        UPDATE inventory
        SET physical_quantity = ?, version = version + 1, updated_at = ?
        WHERE sku = ? AND version = ?
        """, (after_qty, now, sku, version))

        if cur.rowcount == 0:
            raise AdjustmentError(f"Concurrency conflict: SKU '{sku}' version {version} was modified concurrently.")

        # Update adjustment record
        conn.execute("""
        UPDATE inventory_adjustments
        SET status = 'APPLIED', before_quantity = ?, after_quantity = ?, updated_at = ?
        WHERE adjustment_id = ?
        """, (before_qty, after_qty, now, adjustment_id))

    return {
        "adjustment_id": adjustment_id,
        "sku": sku,
        "status": "APPLIED",
        "before_quantity": before_qty,
        "after_quantity": after_qty,
        "quantity_delta": delta,
    }


def verify_adjustment(adjustment_id: str, conn: sqlite3.Connection) -> bool:
    """
    Independent verification: reads current persisted inventory from DB
    and confirms it strictly matches the adjustment record's after_quantity.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_adjustments WHERE adjustment_id = ?", (adjustment_id,))
    row = cursor.fetchone()
    if not row:
        raise AdjustmentError(f"Adjustment '{adjustment_id}' not found.")

    adj = dict(row)
    if adj["status"] not in ("APPLIED", "VERIFIED"):
        raise AdjustmentError(f"Cannot verify adjustment in status '{adj['status']}' (must be 'APPLIED').")

    sku = adj["sku"]
    expected_after = adj["after_quantity"]

    # Independent DB read
    cursor.execute("SELECT physical_quantity FROM inventory WHERE sku = ?", (sku,))
    inv_row = cursor.fetchone()
    if not inv_row:
        raise AdjustmentError(f"Verification failed: SKU '{sku}' not found in inventory table.")

    persisted_qty = inv_row["physical_quantity"] if isinstance(inv_row, sqlite3.Row) else inv_row[0]
    if persisted_qty != expected_after:
        raise AdjustmentError(
            f"Verification mismatch: DB physical_quantity is {persisted_qty}, expected {expected_after}."
        )

    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute("""
        UPDATE inventory_adjustments
        SET status = 'VERIFIED', updated_at = ?
        WHERE adjustment_id = ?
        """, (now, adjustment_id))

    return True

