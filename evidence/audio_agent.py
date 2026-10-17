"""Audio Agent: extracts claims from warehouse voice notes."""
import os

from evidence.common import run_extraction

PROMPT = """You are the Audio Agent in a logistics evidence ledger.
Extract ONLY what the speaker actually says about quantities, SKUs or package condition.
- Spoken counts -> metric "shipped_qty" / "received_qty" only if the speaker says shipped / received;
  otherwise "other". Spoken damage (torn, crushed, wet) -> metric "damage", value null.
- Put the exact transcript line in `excerpt`.
- NEVER infer cause. Damage or a shortfall is an observation, not an explanation.
  Never claim theft or tampering unless the speaker says so, and then record it as
  "speaker states ..." with metric "other".
- If the audio is silent, unintelligible or irrelevant, return an empty list.
- model_confidence: your own 0-1 estimate (it is not calibrated)."""

MIMES = {".wav": "audio/wav", ".mp3": "audio/mpeg"}


def extract(file_path: str) -> list:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in MIMES:
        raise ValueError(f"audio agent: unsupported file type {ext!r}")
    return run_extraction(file_path, MIMES[ext], PROMPT, "audio")
