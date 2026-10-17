"""Frozen shared contract between the evidence side and the decision side."""
from typing import Optional, TypedDict

METRICS = {"shipped_qty", "received_qty", "damage", "stock_qty", "other"}
AGENTS = {"document", "vision", "audio", "records"}
STATUSES = {"supported", "contradicted", "insufficient"}
# Pipeline interface (decision side implements it, UI calls it ONCE per analysis):
#   run_pipeline(files: dict, sku: str) -> {"evidence": [...], "findings": [...], "failures": [...]}
#   files = {
#     "document": [paths]  # invoice AND receipt in the same call; a plain str = one-item list
#     "vision":   path | None
#     "audio":    path | None
#   }   any key may be missing or empty
REQUIRED = ("agent", "claim", "sku", "metric", "value", "source", "excerpt", "model_confidence")


class Evidence(TypedDict):
    agent: str
    claim: str
    sku: Optional[str]
    metric: str
    value: Optional[float]
    source: str
    excerpt: str
    model_confidence: Optional[float]  # model-reported, NOT calibrated


class Finding(TypedDict):
    claim: str
    status: str  # "supported" | "contradicted" | "insufficient"
    evidence: list  # list[Evidence]
    reasoning: str


def validate(evidence: list) -> list:
    """Check every record against the contract and return cleaned copies."""
    cleaned = []
    for i, ev in enumerate(evidence):
        missing = [k for k in REQUIRED if k not in ev]
        if missing:
            raise ValueError(f"evidence[{i}] missing fields: {missing}")
        if ev["agent"] not in AGENTS:
            raise ValueError(f"evidence[{i}] unknown agent: {ev['agent']!r}")
        if ev["metric"] not in METRICS:
            raise ValueError(f"evidence[{i}] unknown metric: {ev['metric']!r}")
        ev = dict(ev)
        if ev["value"] is not None:
            try:
                ev["value"] = float(ev["value"])
            except (TypeError, ValueError):
                raise ValueError(f"evidence[{i}] value not numeric: {ev['value']!r}")
        if ev["sku"] is not None:
            ev["sku"] = str(ev["sku"]).strip().upper().replace(" ", "-")
        cleaned.append(ev)
    return cleaned
