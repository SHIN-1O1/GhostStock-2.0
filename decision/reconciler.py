from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from .normalizer import NormalizedClaim


class ReconciliationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass
class ReconciliationResult:
    sku: str
    status: ReconciliationStatus
    discrepancy_detected: bool
    discrepancy_quantity: Optional[float]
    summary: str
    supporting_evidence_ids: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    action_justified: bool = False
    recommended_adjustment: Optional[dict] = None
    applied_guidance: list[str] = field(default_factory=list)


class Reconciler:
    """Epistemically grounded, deterministic inventory reconciliation engine."""

    def reconcile(
        self,
        sku: str,
        current_inventory: Optional[dict],
        claims: list[NormalizedClaim],
        past_feedback: Optional[list[dict]] = None
    ) -> ReconciliationResult:
        past_feedback = past_feedback or []
        applied_guidance = []

        # Extract contextual guidance from user feedback
        for fb in past_feedback:
            reason = fb.get("reason", "").lower()
            if "invoice proved delivery" in reason or "verify delivery" in reason:
                applied_guidance.append("Enforce strict receipt requirement: invoice alone cannot establish delivery.")
            elif "too aggressive" in reason or "conservative" in reason:
                applied_guidance.append("Conservative threshold: require explicit confirmation before stock changes.")

        # Unknown SKU check
        if not current_inventory:
            return ReconciliationResult(
                sku=sku,
                status=ReconciliationStatus.NEEDS_REVIEW,
                discrepancy_detected=False,
                discrepancy_quantity=None,
                summary=f"SKU '{sku}' was not found in authoritative inventory records. Action halted.",
                uncertainties=["Target SKU is not in inventory database; cannot establish stock baseline."],
                action_justified=False,
                applied_guidance=applied_guidance
            )

        invoiced_qty = None
        invoiced_unit = None
        received_qty = None
        received_unit = None
        damage_notes = []
        anomaly_notes = []
        evidence_ids = []
        uncertainties = []

        for claim in claims:
            evidence_ids.append(claim.evidence_id)

            if claim.category == "SHIPPED":
                if claim.numeric_value is not None:
                    invoiced_qty = claim.numeric_value
                    invoiced_unit = claim.unit
                else:
                    uncertainties.append(f"Non-numeric shipped quantity in evidence {claim.evidence_id}.")

            elif claim.category == "RECEIVED":
                if claim.numeric_value is not None:
                    received_qty = claim.numeric_value
                    received_unit = claim.unit
                else:
                    uncertainties.append(f"Non-numeric received quantity in evidence {claim.evidence_id}.")

            elif claim.category == "DAMAGED_OBSERVED":
                damage_notes.append(str(claim.raw_value))
                uncertainties.append(
                    f"Visual damage observed ({claim.raw_value}); exact affected unit count is unquantified."
                )

            elif claim.category == "ANOMALY_NOTE":
                anomaly_notes.append(str(claim.raw_value))
                uncertainties.append(
                    f"Warehouse voice/text anomaly report ({claim.raw_value}) requires corroboration."
                )

        # Incompatible units check
        if invoiced_unit and received_unit and invoiced_unit != received_unit:
            return ReconciliationResult(
                sku=sku,
                status=ReconciliationStatus.NEEDS_REVIEW,
                discrepancy_detected=False,
                discrepancy_quantity=None,
                summary=f"Unit mismatch detected: Invoice uses '{invoiced_unit}' while Receipt uses '{received_unit}'.",
                supporting_evidence_ids=evidence_ids,
                uncertainties=uncertainties + ["Unit conversion factor not verified; cannot compare raw quantities."],
                action_justified=False,
                applied_guidance=applied_guidance
            )

        # Epistemic Rule: Invoice alone != proof of delivery
        if invoiced_qty is not None and received_qty is None:
            return ReconciliationResult(
                sku=sku,
                status=ReconciliationStatus.INSUFFICIENT_EVIDENCE,
                discrepancy_detected=False,
                discrepancy_quantity=None,
                summary="Invoice claims goods were shipped, but no warehouse receipt or delivery confirmation exists.",
                supporting_evidence_ids=evidence_ids,
                uncertainties=uncertainties + ["Invoice alone does not establish physical delivery."],
                action_justified=False,
                applied_guidance=applied_guidance
            )

        # Epistemic Rule: Contradiction when invoice and receipt quantities differ
        if invoiced_qty is not None and received_qty is not None:
            discrepancy = invoiced_qty - received_qty
            if abs(discrepancy) > 1e-6:
                summary = (
                    f"Discrepancy detected: Supplier invoice claims {invoiced_qty} {invoiced_unit or 'units'} shipped, "
                    f"but warehouse receipt records {received_qty} {received_unit or 'units'} received "
                    f"(shortage of {discrepancy:g} units)."
                )
                if damage_notes:
                    summary += f" Packaging damage noted: {'; '.join(damage_notes)}."

                # Epistemic modesty: The 250 current balance in DB may or may not already reflect the receipt.
                # Propose a shortage adjustment if justified, but do NOT assume theft.
                recommended = {
                    "adjustment_type": "SHORTAGE_DISCREPANCY_FLAG",
                    "quantity": -int(discrepancy),
                    "reason": f"Discrepancy of {discrepancy:g} units between invoice and warehouse receipt."
                }

                return ReconciliationResult(
                    sku=sku,
                    status=ReconciliationStatus.CONTRADICTED,
                    discrepancy_detected=True,
                    discrepancy_quantity=discrepancy,
                    summary=summary,
                    supporting_evidence_ids=evidence_ids,
                    uncertainties=uncertainties,
                    action_justified=True,
                    recommended_adjustment=recommended,
                    applied_guidance=applied_guidance
                )

        # Supported case
        if invoiced_qty is not None and received_qty is not None and abs(invoiced_qty - received_qty) <= 1e-6:
            summary = f"Invoice and receipt quantities agree at {received_qty:g} units."
            if damage_notes:
                summary += f" However, package damage was observed: {'; '.join(damage_notes)}."

            return ReconciliationResult(
                sku=sku,
                status=ReconciliationStatus.SUPPORTED,
                discrepancy_detected=False,
                discrepancy_quantity=0.0,
                summary=summary,
                supporting_evidence_ids=evidence_ids,
                uncertainties=uncertainties,
                action_justified=False,
                recommended_adjustment=None,
                applied_guidance=applied_guidance
            )

        # Fallback if no relevant quantity claims present
        return ReconciliationResult(
            sku=sku,
            status=ReconciliationStatus.INSUFFICIENT_EVIDENCE,
            discrepancy_detected=False,
            discrepancy_quantity=None,
            summary="Insufficient quantitative evidence to establish receipt reconciliation.",
            supporting_evidence_ids=evidence_ids,
            uncertainties=uncertainties + ["No primary shipping or receiving quantities found."],
            action_justified=False,
            applied_guidance=applied_guidance
        )
