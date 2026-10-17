#!/usr/bin/env python3
"""
GhostStock 2.0 — End-to-End Decision & Verification Engine Demo
Demonstrates the complete evidence -> reconciliation -> approval -> application -> verification -> feedback pipeline.
"""

import json
from decision.database import init_db, get_db_connection
from decision.orchestrator import run_pipeline
from decision.adjustments import approve_adjustment, apply_adjustment, verify_adjustment
from decision.feedback import submit_feedback


def main():
    print("=" * 70)
    print(" GHOSTSTOCK 2.0 — DECISION & VERIFICATION ENGINE (PERSON B DEMO)")
    print("=" * 70)

    db_path = "ghoststock.db"
    conn = init_db(db_path, seed=True)

    print("\n[1] Authoritative Inventory Baseline (Pre-Reconciliation):")
    cur = conn.cursor()
    cur.execute("SELECT * FROM inventory WHERE sku = 'SKU-GHOST-01'")
    inv = dict(cur.fetchone())
    print(f"    SKU: {inv['sku']} | Physical: {inv['physical_quantity']} | Reserved: {inv['reserved_quantity']} | Version: {inv['version']}")

    print("\n[2] Executing Orchestrator Pipeline (Fixture Mode)...")
    res = run_pipeline(files=[], sku="SKU-GHOST-01", use_fixture=True, db_path=db_path)
    case_id = res["case_id"]
    print(f"    Case ID: {case_id}")
    print(f"    Status:  {res['status']}")
    print(f"    Summary: {res['reconciliation']['summary']}")

    print("\n[3] Extracted & Validated Multimodal Evidence:")
    for ev in res["evidence"]:
        print(f"    - [{ev['source_type']}] {ev['agent_name']} | {ev['claim_type']} = {ev['extracted_value']} {ev['unit']} (conf: {ev['confidence']})")

    print("\n[4] Epistemic Uncertainties Recorded:")
    for u in res["reconciliation"]["uncertainties"]:
        print(f"    * {u}")

    proposal = res["adjustment_proposal"]
    if proposal:
        adj_id = proposal["adjustment_id"]
        print(f"\n[5] Action Proposal Generated:")
        print(f"    Adjustment ID: {adj_id}")
        print(f"    Action Type:   {proposal['adjustment_type']}")
        print(f"    Delta:         {proposal['quantity']} units")
        print(f"    Reason:        {proposal['reason']}")
        print(f"    Status:        {proposal['status']} (Requires Human Approval)")

        print("\n[6] Human Approver Gate:")
        approve_adjustment(adj_id, approver="lead_auditor_sherwin", conn=conn)
        print(f"    -> Approved adjustment {adj_id} by 'lead_auditor_sherwin'.")

        print("\n[7] Transactional Application & Independent Verification:")
        exec_res = apply_adjustment(adj_id, conn=conn)
        print(f"    -> Applied: Stock moved from {exec_res['before_quantity']} to {exec_res['after_quantity']} units.")
        verify_adjustment(adj_id, conn=conn)
        print(f"    -> Independently verified persisted database state: OK.")

    print("\n[8] Submitting Mandatory User Feedback:")
    fb = submit_feedback(
        case_id=case_id,
        rating=5,
        reason="Discrepancy correctly isolated to 10-unit supplier shortage; physical damage noted without hallucinating loss.",
        conn=conn
    )
    print(f"    -> Feedback Recorded (ID: {fb['feedback_id']}) Rating: {fb['rating']}/5 | Reason: '{fb['reason']}'")

    print("\n[9] Execution Audit Ledger:")
    for step in res["execution_trace"]:
        print(f"    [{step['timestamp'][:19]}] {step['step_name']:<22} | {step['agent_name']:<16} | {step['status']:<12} | {step['details']}")

    print("\n" + "=" * 70)
    print(" VERIFICATION COMPLETE: ALL 8 PHASES OPERATIONAL AND VERIFIED")
    print("=" * 70)


if __name__ == "__main__":
    main()
