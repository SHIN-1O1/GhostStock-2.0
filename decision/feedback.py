from datetime import datetime, timezone
import sqlite3
from typing import Optional
import uuid


class FeedbackError(Exception):
    """Raised when user feedback is invalid or missing."""
    pass


def submit_feedback(
    case_id: str,
    rating: int,
    reason: str,
    conn: sqlite3.Connection
) -> dict:
    """
    Submit mandatory user feedback for a case.
    Validates that rating is in [1, 5] and reason is non-empty.
    Persists feedback to SQLite and returns the created record.
    """
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise FeedbackError(f"Feedback rating must be an integer between 1 and 5, got {rating}.")

    if not reason or not reason.strip():
        raise FeedbackError("Feedback reason cannot be empty.")

    # Confirm case exists
    cursor = conn.cursor()
    cursor.execute("SELECT case_id FROM reconciliation_cases WHERE case_id = ?", (case_id,))
    if not cursor.fetchone():
        raise FeedbackError(f"Case '{case_id}' does not exist in reconciliation_cases.")

    fb_id = f"FB-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    clean_reason = reason.strip()


    with conn:
        conn.execute("""
        INSERT INTO feedback (feedback_id, case_id, rating, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (fb_id, case_id, rating, clean_reason, now))

    return {
        "feedback_id": fb_id,
        "case_id": case_id,
        "rating": rating,
        "reason": clean_reason,
        "created_at": now
    }


def get_relevant_feedback(limit: int = 5, conn: Optional[sqlite3.Connection] = None) -> list[dict]:
    """Retrieve recent feedback entries to pass into subsequent orchestrator runs."""
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("""
    SELECT feedback_id, case_id, rating, reason, created_at
    FROM feedback
    ORDER BY created_at DESC
    LIMIT ?
    """, (limit,))
    return [dict(row) for row in cursor.fetchall()]
