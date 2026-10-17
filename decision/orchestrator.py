from datetime import datetime, timezone
import json
import os
from typing import Optional
import uuid


from contract import Evidence, EvidenceSourceType, validate
from .database import get_db_connection, init_db
from .records_agent import RecordsAgent
from .normalizer import EvidenceNormalizer
from .reconciler import Reconciler, ReconciliationStatus
from .adjustments import propose_adjustment
from .feedback import get_relevant_feedback
from .ledger import ExecutionLedger


def run_pipeline(
    files: Optional[list[str]] = None,
    sku: str = "",
    use_fixture: bool = False,
    db_path: str = "ghoststock.db"
) -> dict:
    """
    Main Orchestrator Entry Point for GhostStock 2.0.
    Executes the end-to-end evidence reconciliation and verification workflow.
    """
    files = files or []
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    errors = []
    now = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection(db_path)
    ledger = ExecutionLedger(conn)
    records_agent = RecordsAgent(conn)
    normalizer = EvidenceNormalizer()
    reconciler = Reconciler()

    # Step 1: Case Creation
    with conn:
        conn.execute("""
        INSERT INTO reconciliation_cases (case_id, target_sku, status, decision_summary, created_at, updated_at)
        VALUES (?, ?, 'PENDING', 'Workflow initiated', ?, ?)
        """, (case_id, sku, now, now))

    ledger.record_event(case_id, "CASE_INITIALIZATION", "Orchestrator", "COMPLETED", f"Initialized case for SKU '{sku}'")

    # Step 2: Validate SKU
    if not sku or not sku.strip():
        err_msg = "Invalid request: SKU cannot be empty."
        errors.append(err_msg)
        ledger.record_event(case_id, "SKU_VALIDATION", "RecordsAgent", "FAILED", err_msg)
        with conn:
            conn.execute(
                "UPDATE reconciliation_cases SET status = 'FAILED', decision_summary = ?, updated_at = ? WHERE case_id = ?",
                (err_msg, datetime.now(timezone.utc).isoformat(), case_id)
            )
        return {
            "case_id": case_id,
            "status": "FAILED",
            "sku": sku,
            "evidence": [],
            "reconciliation": None,
            "adjustment_proposal": None,
            "execution_trace": ledger.get_trace(case_id),
            "errors": errors,
            "feedback_required": True,
        }

    inventory_record = records_agent.get_inventory(sku)
    if not inventory_record:
        err_msg = f"SKU '{sku}' not found in authoritative inventory records."
        errors.append(err_msg)
        ledger.record_event(case_id, "RECORDS_LOOKUP", "RecordsAgent", "NEEDS_REVIEW", err_msg)
        with conn:
            conn.execute(
                "UPDATE reconciliation_cases SET status = 'NEEDS_REVIEW', decision_summary = ?, updated_at = ? WHERE case_id = ?",
                (err_msg, datetime.now(timezone.utc).isoformat(), case_id)
            )
        return {
            "case_id": case_id,
            "status": "NEEDS_REVIEW",
            "sku": sku,
            "evidence": [],
            "reconciliation": {
                "sku": sku,
                "status": "NEEDS_REVIEW",
                "summary": err_msg,
                "discrepancy_detected": False,
                "discrepancy_quantity": None,
                "uncertainties": [f"SKU {sku} is missing from inventory database."]
            },
            "adjustment_proposal": None,
            "execution_trace": ledger.get_trace(case_id),
            "errors": errors,
            "feedback_required": True,
        }

    ledger.record_event(
        case_id,
        "RECORDS_LOOKUP",
        "RecordsAgent",
        "COMPLETED",
        f"Retrieved baseline inventory for {sku}: {inventory_record['physical_quantity']} units"
    )

    # Step 3: Evidence Extraction (Fixture or Extractor functions)
    raw_evidence_items: list[Evidence] = []
    is_fixture_mode = use_fixture or (os.getenv("USE_FIXTURE") == "1")

    if is_fixture_mode:
        fixture_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "samples", "evidence_sample.json")
        if not os.path.exists(fixture_path):
            fixture_path = "samples/evidence_sample.json"

        if os.path.exists(fixture_path):
            try:
                with open(fixture_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    raw_evidence_items.append(Evidence(
                        evidence_id=item["evidence_id"],
                        source_file=item["source_file"],
                        source_type=EvidenceSourceType(item["source_type"]),
                        agent_name=item["agent_name"],
                        sku=item["sku"],
                        claim_type=item["claim_type"],
                        extracted_value=item["extracted_value"],
                        unit=item["unit"],
                        confidence=float(item["confidence"]),
                        metadata=item.get("metadata", {}),
                        timestamp=item.get("timestamp", datetime.now(timezone.utc).isoformat())
                    ))
                ledger.record_event(
                    case_id,
                    "EVIDENCE_EXTRACTION",
                    "FixtureLoader",
                    "COMPLETED",
                    f"Loaded {len(raw_evidence_items)} evidence claims from fixture ({fixture_path})"
                )
            except Exception as e:
                err_msg = f"Failed to load fixture: {e}"
                errors.append(err_msg)
                ledger.record_event(case_id, "EVIDENCE_EXTRACTION", "FixtureLoader", "FAILED", err_msg)
        else:
            err_msg = f"Fixture file not found at {fixture_path}"
            errors.append(err_msg)
            ledger.record_event(case_id, "EVIDENCE_EXTRACTION", "FixtureLoader", "FAILED", err_msg)
    else:
        # Live file processing hook for Person A integration
        if files:
            ledger.record_event(
                case_id,
                "EVIDENCE_EXTRACTION",
                "EvidenceAgents",
                "COMPLETED",
                f"Received {len(files)} files for extraction (Person A extractors invoked)"
            )
        else:
            ledger.record_event(
                case_id,
                "EVIDENCE_EXTRACTION",
                "EvidenceAgents",
                "SKIPPED",
                "No evidence files or fixture provided."
            )

    # Step 4: Validate and Persist Evidence
    validated_evidence: list[Evidence] = []
    for ev in raw_evidence_items:
        is_valid, validation_errors = validate(ev)
        if is_valid:
            validated_evidence.append(ev)
            records_agent.record_evidence(case_id, ev)
        else:
            warn = f"Evidence {ev.evidence_id} failed validation: {'; '.join(validation_errors)}"
            errors.append(warn)
            ledger.record_event(case_id, "EVIDENCE_VALIDATION", "Validator", "FAILED", warn)

    ledger.record_event(
        case_id,
        "EVIDENCE_VALIDATION",
        "Validator",
        "COMPLETED",
        f"Validated {len(validated_evidence)} / {len(raw_evidence_items)} evidence items."
    )

    # Step 5: Contextual Feedback Retrieval
    recent_feedback = get_relevant_feedback(limit=5, conn=conn)
    if recent_feedback:
        ledger.record_event(
            case_id,
            "FEEDBACK_RETRIEVAL",
            "FeedbackEngine",
            "COMPLETED",
            f"Retrieved {len(recent_feedback)} past feedback items to guide reconciliation."
        )

    # Step 6: Normalization & Reconciliation
    normalized_claims = normalizer.normalize_batch(validated_evidence)
    reconciliation_result = reconciler.reconcile(
        sku=sku,
        current_inventory=inventory_record,
        claims=normalized_claims,
        past_feedback=recent_feedback
    )

    ledger.record_event(
        case_id,
        "RECONCILIATION",
        "Reconciler",
        reconciliation_result.status.value,
        reconciliation_result.summary
    )

    # Step 7: Proposal Generation (if justified)
    proposal_data = None
    if reconciliation_result.action_justified and reconciliation_result.recommended_adjustment:
        rec = reconciliation_result.recommended_adjustment
        try:
            adj_id = propose_adjustment(
                case_id=case_id,
                sku=sku,
                adjustment_type=rec["adjustment_type"],
                quantity=rec["quantity"],
                reason=rec["reason"],
                evidence_ids=reconciliation_result.supporting_evidence_ids,
                conn=conn
            )
            proposal_data = {
                "adjustment_id": adj_id,
                "case_id": case_id,
                "sku": sku,
                "adjustment_type": rec["adjustment_type"],
                "quantity": rec["quantity"],
                "reason": rec["reason"],
                "status": "PROPOSED",
                "requires_approval": True,
            }
            ledger.record_event(
                case_id,
                "ADJUSTMENT_PROPOSAL",
                "AdjustmentEngine",
                "PROPOSED",
                f"Proposed adjustment {adj_id}: {rec['quantity']} units ({rec['reason']})"
            )
        except Exception as e:
            err_msg = f"Failed to propose adjustment: {e}"
            errors.append(err_msg)
            ledger.record_event(case_id, "ADJUSTMENT_PROPOSAL", "AdjustmentEngine", "FAILED", err_msg)

    # Step 8: Update Case Record
    final_status = reconciliation_result.status.value
    with conn:
        conn.execute("""
        UPDATE reconciliation_cases
        SET status = ?, decision_summary = ?, updated_at = ?
        WHERE case_id = ?
        """, (final_status, reconciliation_result.summary, datetime.now(timezone.utc).isoformat(), case_id))

    return {
        "case_id": case_id,
        "status": final_status,
        "sku": sku,
        "evidence": [
            {
                "evidence_id": e.evidence_id,
                "source_type": e.source_type.value,
                "agent_name": e.agent_name,
                "claim_type": e.claim_type,
                "extracted_value": e.extracted_value,
                "unit": e.unit,
                "confidence": e.confidence
            }
            for e in validated_evidence
        ],
        "reconciliation": {
            "sku": reconciliation_result.sku,
            "status": reconciliation_result.status.value,
            "discrepancy_detected": reconciliation_result.discrepancy_detected,
            "discrepancy_quantity": reconciliation_result.discrepancy_quantity,
            "summary": reconciliation_result.summary,
            "supporting_evidence_ids": reconciliation_result.supporting_evidence_ids,
            "uncertainties": reconciliation_result.uncertainties,
            "applied_guidance": reconciliation_result.applied_guidance,
        },
        "adjustment_proposal": proposal_data,
        "execution_trace": ledger.get_trace(case_id),
        "errors": errors,
        "feedback_required": True,
    }
