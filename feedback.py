"""Feedback loop: persist ratings and turn low-rated cases into lessons."""
import json
import os
from datetime import datetime, timezone

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback.json")


def load_feedback() -> list:
    """Return saved entries; a missing or corrupt file yields []."""
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_feedback(rating: int, reason: str, case_summary: str) -> dict:
    if not 1 <= int(rating) <= 5:
        raise ValueError("rating must be 1-5")
    if not reason.strip():
        raise ValueError("reason is required")
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rating": int(rating),
        "reason": reason.strip(),
        "case_summary": case_summary,
    }
    entries = load_feedback()  # recovers from a corrupt file by starting fresh
    entries.append(entry)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    return entry


def get_lessons(n: int = 5) -> str:
    """Last n entries rated <= 3, formatted for injection into agent instructions."""
    low = [e for e in load_feedback() if e.get("rating", 5) <= 3][-n:]
    if not low:
        return ""
    lines = ["LESSONS FROM LOW-RATED CASES:"]
    for e in low:
        lines.append(f"- (rated {e['rating']}/5) {e['reason']} [case: {e['case_summary']}]")
    return "\n".join(lines)
