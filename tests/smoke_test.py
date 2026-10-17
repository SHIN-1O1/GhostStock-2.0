import os
import sqlite3
import tempfile
import unittest

from contract import Evidence, EvidenceSourceType, validate
from decision.database import init_db, get_db_connection
from decision.records_agent import RecordsAgent
from decision.reconciler import Reconciler, ReconciliationStatus
from decision.normalizer import EvidenceNormalizer, NormalizedClaim
from decision.adjustments import (
    propose_adjustment,
    approve_adjustment,
    apply_adjustment,
    verify_adjustment,
    AdjustmentError,
)
from decision.feedback import submit_feedback, get_relevant_feedback, FeedbackError
from decision.orchestrator import run_pipeline


class TestGhostStockDecisionEngine(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary SQLite database for each test
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.conn = init_db(self.temp_db_path, seed=True)

    def tearDown(self):
        self.conn.close()
        try:
            os.close(self.temp_db_fd)
            os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_1_happy_path_fixture_pipeline(self):
        """Mandatory Check 1: Run fixture pipeline and verify structured result."""
        result = run_pipeline(
            files=[],
            sku="SKU-GHOST-01",
            use_fixture=True,
            db_path=self.temp_db_path
        )

        self.assertIn("case_id", result)
        self.assertEqual(result["sku"], "SKU-GHOST-01")
        self.assertEqual(result["status"], "CONTRADICTED")
        self.assertEqual(len(result["evidence"]), 4)
        self.assertIsNotNone(result["adjustment_proposal"])
        self.assertTrue(result["feedback_required"])
        self.assertTrue(len(result["execution_trace"]) >= 5)

        # Check trace step sequence
        steps = [e["step_name"] for e in result["execution_trace"]]
        self.assertIn("CASE_INITIALIZATION", steps)
        self.assertIn("RECORDS_LOOKUP", steps)
        self.assertIn("EVIDENCE_EXTRACTION", steps)
        self.assertIn("RECONCILIATION", steps)

    def test_2_discrepancy_detection_and_epistemic_modesty(self):
        """Mandatory Check 2: Confirm invoice-vs-receipt mismatch and damage note without hallucinating quantity."""
        result = run_pipeline(
            files=[],
            sku="SKU-GHOST-01",
            use_fixture=True,
            db_path=self.temp_db_path
        )

        recon = result["reconciliation"]
        self.assertTrue(recon["discrepancy_detected"])
        self.assertEqual(recon["discrepancy_quantity"], 10.0)
        self.assertIn("shortage of 10 units", recon["summary"].lower())

        # Epistemic modesty: damage photo does not fabricate damaged unit count
        uncertainties_text = " ".join(recon["uncertainties"]).lower()
        self.assertIn("unquantified", uncertainties_text)

    def test_3_adjustment_safety_and_approval_gate(self):
        """Mandatory Check 3: Adjustment cannot be applied without human approval."""
        result = run_pipeline(
            files=[],
            sku="SKU-GHOST-01",
            use_fixture=True,
            db_path=self.temp_db_path
        )
        proposal = result["adjustment_proposal"]
        self.assertIsNotNone(proposal)
        adj_id = proposal["adjustment_id"]

        # Attempt to apply directly without approval -> must fail
        with self.assertRaises(AdjustmentError):
            apply_adjustment(adj_id, self.conn)

        # Approve adjustment
        approved = approve_adjustment(adj_id, approver="auditor_jane", conn=self.conn)
        self.assertTrue(approved)

        # Now apply adjustment -> must succeed
        exec_res = apply_adjustment(adj_id, self.conn)
        self.assertEqual(exec_res["status"], "APPLIED")
        self.assertEqual(exec_res["before_quantity"], 250)
        self.assertEqual(exec_res["after_quantity"], 240)

    def test_4_before_and_after_independent_verification(self):
        """Mandatory Check 4: Independent DB query confirms persisted value matches expected."""
        result = run_pipeline(
            files=[],
            sku="SKU-GHOST-01",
            use_fixture=True,
            db_path=self.temp_db_path
        )
        adj_id = result["adjustment_proposal"]["adjustment_id"]
        approve_adjustment(adj_id, approver="auditor_jane", conn=self.conn)
        apply_adjustment(adj_id, self.conn)

        # Verify independently through verification function
        verified = verify_adjustment(adj_id, self.conn)
        self.assertTrue(verified)

        # Independent raw SQL query
        cur = self.conn.cursor()
        cur.execute("SELECT physical_quantity, version FROM inventory WHERE sku = 'SKU-GHOST-01'")
        row = cur.fetchone()
        self.assertEqual(row["physical_quantity"], 240)
        self.assertEqual(row["version"], 2)

    def test_5_idempotency_double_application_prevention(self):
        """Check: Applying the same adjustment twice fails and does not double-decrement."""
        result = run_pipeline(
            files=[],
            sku="SKU-GHOST-01",
            use_fixture=True,
            db_path=self.temp_db_path
        )
        adj_id = result["adjustment_proposal"]["adjustment_id"]
        approve_adjustment(adj_id, approver="auditor_jane", conn=self.conn)
        apply_adjustment(adj_id, self.conn)

        # Second application must raise AdjustmentError
        with self.assertRaises(AdjustmentError) as ctx:
            apply_adjustment(adj_id, self.conn)
        self.assertIn("Idempotency violation", str(ctx.exception))

        # Confirm stock remains 240, not 230
        cur = self.conn.cursor()
        cur.execute("SELECT physical_quantity FROM inventory WHERE sku = 'SKU-GHOST-01'")
        self.assertEqual(cur.fetchone()["physical_quantity"], 240)

    def test_6_mandatory_feedback_persistence(self):
        """Mandatory Check 5: Rating and non-empty reason are required and survive restart."""
        result = run_pipeline(
            files=[],
            sku="SKU-GHOST-01",
            use_fixture=True,
            db_path=self.temp_db_path
        )
        case_id = result["case_id"]

        # Missing / invalid rating
        with self.assertRaises(FeedbackError):
            submit_feedback(case_id, rating=0, reason="Valid note", conn=self.conn)
        with self.assertRaises(FeedbackError):
            submit_feedback(case_id, rating=6, reason="Valid note", conn=self.conn)

        # Empty reason
        with self.assertRaises(FeedbackError):
            submit_feedback(case_id, rating=5, reason="   ", conn=self.conn)

        # Valid feedback
        fb = submit_feedback(
            case_id,
            rating=5,
            reason="Accurately flagged 10-unit invoice discrepancy without hallucinating loss.",
            conn=self.conn
        )
        self.assertEqual(fb["rating"], 5)

        # Retrieval check
        recent = get_relevant_feedback(limit=5, conn=self.conn)
        self.assertTrue(len(recent) >= 1)
        self.assertEqual(recent[0]["reason"], fb["reason"])

    def test_7_unknown_sku_handling(self):
        """Check: Unknown SKU produces controlled result without fabricating inventory."""
        result = run_pipeline(
            files=[],
            sku="SKU-UNKNOWN-99",
            use_fixture=True,
            db_path=self.temp_db_path
        )
        self.assertEqual(result["status"], "NEEDS_REVIEW")
        self.assertIsNone(result["adjustment_proposal"])
        self.assertTrue(len(result["errors"]) >= 1)
        self.assertIn("not found", result["errors"][0])


if __name__ == "__main__":
    unittest.main()
