"""Vision Agent: reports visible condition of packages from a photo."""
import os

from evidence.common import run_extraction

PROMPT = """You are the Vision Agent in a logistics evidence ledger.
Report ONLY what is visible in this photo: package damage, labels, visible text, counts.
- Visible damage (crushed, torn, wet, open) -> metric "damage", value null.
- Legible label text or SKU -> metric "other"; set sku only if it is legible in the image.
- Put a short description of exactly what you see in `excerpt` (include legible label text verbatim).
- NEVER infer cause. Damage is an observation, not an explanation. Never claim theft or tampering.
- If the image is noise, blank, unreadable or not a package, return an empty list.
- model_confidence: your own 0-1 estimate (it is not calibrated)."""

MIMES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def extract(file_path: str) -> list:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in MIMES:
        raise ValueError(f"vision agent: unsupported file type {ext!r}")
    return run_extraction(file_path, MIMES[ext], PROMPT, "vision")
