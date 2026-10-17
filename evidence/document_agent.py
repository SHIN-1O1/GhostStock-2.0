"""Document Agent: extracts quantities from invoices, packing lists and receipts (PDF)."""
import os

from evidence.common import run_extraction

PROMPT = """You are the Document Agent in a logistics evidence ledger.
Extract ONLY what is explicitly written in this document.
- Invoice or packing list quantity -> metric "shipped_qty".
- Goods receipt / received quantity -> metric "received_qty".
- Any other explicit number or note -> metric "other" (or "damage" only if damage is written).
- Set sku to the SKU printed in the document, value to the number.
- Put the exact supporting text copied from the document in `excerpt`.
- NEVER infer a cause. A shortfall or discrepancy is an observation, not an explanation.
  Never claim theft, loss or tampering.
- If the document is blank, unreadable or irrelevant, return an empty list.
- model_confidence: your own 0-1 estimate (it is not calibrated)."""

MIMES = {".pdf": "application/pdf"}


def extract(file_path: str) -> list:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in MIMES:
        raise ValueError(f"document agent: unsupported file type {ext!r}")
    return run_extraction(file_path, MIMES[ext], PROMPT, "document")
