from dotenv import load_dotenv
load_dotenv()
from dotenv import load_dotenv
load_dotenv()

"""Shared Gemini extraction helper used by the document, vision and audio agents."""
import os
from typing import Literal, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from contract import validate

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")


class EvidenceItem(BaseModel):
    claim: str
    sku: Optional[str] = None
    metric: Literal["shipped_qty", "received_qty", "damage", "stock_qty", "other"]
    value: Optional[float] = None
    excerpt: str
    model_confidence: Optional[float] = None  # model-reported, not calibrated


def run_extraction(file_path: str, mime: str, prompt: str, agent: str) -> list:
    """Send one file + prompt to Gemini, return validated Evidence dicts."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        client = genai.Client()  # reads GOOGLE_API_KEY from the environment
        resp = client.models.generate_content(
            model=MODEL,
            contents=[types.Part.from_bytes(data=data, mime_type=mime), prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[EvidenceItem],
                temperature=0,
            ),
        )
    except Exception as e:
        raise RuntimeError(f"{agent} agent failed ({MODEL}): {type(e).__name__}: {e}") from e

    items = resp.parsed or []
    source = os.path.basename(file_path)
    records = []
    for item in items:
        rec = item.model_dump()
        rec["agent"] = agent
        rec["source"] = source
        records.append(rec)
    return validate(records)
