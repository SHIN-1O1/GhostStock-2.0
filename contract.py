from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EvidenceSourceType(str, Enum):
    DOCUMENT = "DOCUMENT"
    VISION = "VISION"
    AUDIO = "AUDIO"
    RECORD = "RECORD"


class EvidenceStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    SUSPECT = "SUSPECT"


@dataclass
class Evidence:
    evidence_id: str
    source_file: str
    source_type: EvidenceSourceType
    agent_name: str
    sku: str
    claim_type: str        # e.g., "SHIPPED_QUANTITY", "RECEIVED_QUANTITY", "DAMAGE_OBSERVED"
    extracted_value: Any   # Numeric quantity (int/float), description string, or bool
    unit: str              # e.g., "units", "boxes", "n/a"
    confidence: float      # 0.0 - 1.0 (uncalibrated model score)
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())



def validate(evidence: Evidence) -> tuple[bool, list[str]]:
    """Validate an Evidence object against schema requirements."""
    errors = []
    if not evidence.evidence_id or not isinstance(evidence.evidence_id, str):
        errors.append("evidence_id must be a non-empty string")
    if not evidence.sku or not isinstance(evidence.sku, str):
        errors.append("sku must be a non-empty string")
    if not (0.0 <= float(evidence.confidence) <= 1.0):
        errors.append(f"confidence must be in [0.0, 1.0], got {evidence.confidence}")
    if evidence.claim_type in ("SHIPPED_QUANTITY", "RECEIVED_QUANTITY"):
        try:
            val = float(evidence.extracted_value)
            if val < 0:
                errors.append(f"quantity value cannot be negative: {val}")
        except (ValueError, TypeError):
            errors.append(f"claim {evidence.claim_type} requires numeric extracted_value, got {evidence.extracted_value}")
    return (len(errors) == 0, errors)
