from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from contract import Evidence, EvidenceSourceType


class SourceCertainty(str, Enum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"      # e.g., Vision model scan
    DOCUMENTED_REPORT = "DOCUMENTED_REPORT"        # e.g., Invoice, Receipt
    HEARSAY_AUDIO = "HEARSAY_AUDIO"                # e.g., Voice note / radio report
    RECORD = "RECORD"                              # e.g., Database state


@dataclass
class NormalizedClaim:
    evidence_id: str
    source_file: str
    source_type: EvidenceSourceType
    agent_name: str
    sku: str
    category: str                   # "SHIPPED", "RECEIVED", "DAMAGED_OBSERVED", "ANOMALY_NOTE"
    original_claim_type: str
    raw_value: Any
    numeric_value: Optional[float]  # Parsed numeric quantity if applicable
    unit: str
    certainty: SourceCertainty
    confidence: float
    metadata: dict = field(default_factory=dict)
    timestamp: str = ""


class EvidenceNormalizer:
    """Normalizes validated multimodal Evidence into comparable claims."""

    CATEGORY_MAP = {
        "SHIPPED_QUANTITY": "SHIPPED",
        "RECEIVED_QUANTITY": "RECEIVED",
        "DAMAGE_OBSERVED": "DAMAGED_OBSERVED",
        "ANOMALY_NOTE": "ANOMALY_NOTE",
    }

    CERTAINTY_MAP = {
        EvidenceSourceType.DOCUMENT: SourceCertainty.DOCUMENTED_REPORT,
        EvidenceSourceType.VISION: SourceCertainty.DIRECT_OBSERVATION,
        EvidenceSourceType.AUDIO: SourceCertainty.HEARSAY_AUDIO,
        EvidenceSourceType.RECORD: SourceCertainty.RECORD,
    }

    def normalize(self, evidence: Evidence) -> NormalizedClaim:
        category = self.CATEGORY_MAP.get(evidence.claim_type, "OTHER")
        certainty = self.CERTAINTY_MAP.get(evidence.source_type, SourceCertainty.DOCUMENTED_REPORT)

        numeric_val = None
        if category in ("SHIPPED", "RECEIVED"):
            try:
                numeric_val = float(evidence.extracted_value)
            except (ValueError, TypeError):
                numeric_val = None

        return NormalizedClaim(
            evidence_id=evidence.evidence_id,
            source_file=evidence.source_file,
            source_type=evidence.source_type,
            agent_name=evidence.agent_name,
            sku=evidence.sku,
            category=category,
            original_claim_type=evidence.claim_type,
            raw_value=evidence.extracted_value,
            numeric_value=numeric_val,
            unit=evidence.unit.lower().strip(),
            certainty=certainty,
            confidence=evidence.confidence,
            metadata=dict(evidence.metadata) if evidence.metadata else {},
            timestamp=evidence.timestamp,
        )

    def normalize_batch(self, evidence_list: list[Evidence]) -> list[NormalizedClaim]:
        return [self.normalize(e) for e in evidence_list]
