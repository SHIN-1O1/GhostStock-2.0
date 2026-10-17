# Master Implementation Plan: GhostStock 2.0 (Person B: Decision & Verification Engine)

> **Execution Directive for Implementing Agent:**
> Do not deviate from this plan. Follow each phase sequentially. Verify each step with concrete test executions before progressing. Maintain Person B ownership boundaries and strictly use standard library Python (`sqlite3`, `dataclasses`, `typing`, `json`, `uuid`, `datetime`, `unittest`) to guarantee zero-dependency reliability within the 90-minute deadline.

---

## 1. Repository Reconnaissance & Environment Context

* **Target Workspace**: `/home/sherwin/ghost_net 2.0`
* **Python Runtime**: Python 3.14.8 (Standard Library only: `sqlite3`, `dataclasses`, `json`, `uuid`, `datetime`, `typing`, `unittest`)
* **Dependencies**: Zero external dependencies required. All persistence, schemas, contracts, orchestration, reconciliation, and testing must use Python's built-in libraries.
* **Current State**: Pristine Git repository (`main` branch). No conflicting code or legacy schemas exist.

---

## 2. Directory Layout & Ownership Architecture

```text
/home/sherwin/ghost_net 2.0/
├── .gitignore                          [Shared] Git ignore rules including .ghoststock_brain/
├── contract.py                         [Shared Contract] Evidence dataclass & validate()
├── samples/
│   └── evidence_sample.json            [Shared Fixture] Invoiced vs Received discrepancy sample
├── .ghoststock_brain/                  [Local Brain - Git Ignored]
│   ├── PROJECT_STATE.md                High-level operational overview & progress tracker
│   ├── ARCHITECTURE.md                 Data flow, state machines, and component boundaries
│   ├── CONTRACT_MAP.md                 Signature map of all public entry points
│   ├── OWNERSHIP.md                    Person A vs Person B ownership split
│   ├── DECISIONS.md                    Append-only architectural decision record
│   ├── SESSION_LOG.md                  Timestamped actions, tests, and outcomes
│   ├── NEXT_ACTIONS.md                 Immediate next steps and blockers
│   └── KNOWN_ISSUES.md                 Catalog of known limitations or unverified assumptions
├── decision/                           [Person B Core Package]
│   ├── __init__.py                     Package exports
│   ├── database.py                     SQLite schema, transactional connection pool, seed data
│   ├── records_agent.py                Authoritative inventory & history lookups
│   ├── normalizer.py                   Standardized evidence claim representations
│   ├── reconciler.py                   Deterministic epistemic reconciliation engine
│   ├── adjustments.py                  Propose, approve, apply (transactional), and verify stock changes
│   ├── feedback.py                     Mandatory rating/reason validation, storage, and contextual retrieval
│   ├── ledger.py                       Step-by-step audit trail and execution trace logger
│   └── orchestrator.py                 Single public pipeline entry point: run_pipeline(files, sku)
└── tests/
    └── smoke_test.py                   Automated end-to-end verification suite (5 core checks + edge cases)
```

---

## 3. Phase-by-Phase Implementation Playbook (90-Minute Sprint)

### PHASE 0: Reconnaissance & Brain Setup (Minutes 0–10)

1. **Configure `.gitignore`**:
   * Add `.ghoststock_brain/`, `*.db`, `*.sqlite3`, `__pycache__/`, and `.pytest_cache/`.
   * Verify using `git status --ignored` that `.ghoststock_brain/` is properly ignored.

2. **Initialize `.ghoststock_brain/`**:
   * Create all 8 required Markdown files:
     * `PROJECT_STATE.md`: Note Python 3.14 runtime, empty initial state, and active Person B sprint.
     * `ARCHITECTURE.md`: Document data flow: Evidence Extractors $\to$ Validator $\to$ Records Agent $\to$ Normalizer $\to$ Reconciler $\to$ Adjustment Proposal $\to$ Approval $\to$ Transactional Apply $\to$ Verification $\to$ Feedback.
     * `CONTRACT_MAP.md`: Map `contract.py:validate()`, `orchestrator.py:run_pipeline()`, etc.
     * `OWNERSHIP.md`: Person A (`evidence/`, `samples/`, `app.py`) vs Person B (`decision/`, `tests/`, `contract.py` proposal).
     * `DECISIONS.md`: Log **DEC-001** (Zero-external-dependency standard library architecture for hackathon reliability) and **DEC-002** (Deterministic rule-based reconciler with epistemically grounded statuses).
     * `SESSION_LOG.md`: Initial session start entry.
     * `NEXT_ACTIONS.md`: Priority queue starting with Phase 1.
     * `KNOWN_ISSUES.md`: Initial empty log.

---

### PHASE 1: Shared Contract & Fixture Setup (Minutes 10–18)

1. **Implement `contract.py`**:
   * Define enum `EvidenceSourceType`: `DOCUMENT`, `VISION`, `AUDIO`, `RECORD`.
   * Define enum `EvidenceStatus`: `VALID`, `INVALID`, `SUSPECT`.
   * Define `Evidence` dataclass:
     ```python
     @dataclass
     class Evidence:
         evidence_id: str
         source_file: str
         source_type: EvidenceSourceType
         agent_name: str
         sku: str
         claim_type: str        # e.g., "SHIPPED_QUANTITY", "RECEIVED_QUANTITY", "DAMAGE_OBSERVED"
         extracted_value: Any   # Numeric quantity, description string, or boolean
         unit: str              # e.g., "units", "boxes", "n/a"
         confidence: float      # 0.0 - 1.0 (uncalibrated model score)
         metadata: dict = field(default_factory=dict)
         timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
     ```
   * Implement `validate(evidence: Evidence) -> tuple[bool, list[str]]`:
     * Validate non-empty `evidence_id`, non-empty `sku`, positive/zero `confidence`, and appropriate data types for `claim_type`.

2. **Create `samples/evidence_sample.json`**:
   * Seed standard test case:
     * Evidence 1: Document Agent Invoice claims 100 units shipped for `SKU-GHOST-01`.
     * Evidence 2: Document Agent Warehouse Receipt claims 90 units received for `SKU-GHOST-01`.
     * Evidence 3: Vision Agent photograph claims 1 damaged box observed (does *not* invent quantity lost).
     * Evidence 4: Audio Agent voice log reports "Box arrived crushed on arrival".

---

### PHASE 2: Database Schema & Records Agent (Minutes 18–30)

1. **Implement `decision/database.py`**:
   * SQLite initialization function: `init_db(db_path: str = "ghoststock.db") -> sqlite3.Connection`.
   * Ensure schema creates the following tables if not exists:
     * `inventory`: `sku (TEXT PRIMARY KEY)`, `physical_quantity (INTEGER)`, `reserved_quantity (INTEGER)`, `damaged_quantity (INTEGER)`, `version (INTEGER)`, `updated_at (TEXT)`.
     * `evidence_records`: `evidence_id (TEXT PRIMARY KEY)`, `case_id (TEXT)`, `source_type (TEXT)`, `agent (TEXT)`, `claim_type (TEXT)`, `sku (TEXT)`, `extracted_value (TEXT)`, `unit (TEXT)`, `confidence (REAL)`, `raw_json (TEXT)`, `created_at (TEXT)`.
     * `reconciliation_cases`: `case_id (TEXT PRIMARY KEY)`, `target_sku (TEXT)`, `status (TEXT)`, `decision_summary (TEXT)`, `created_at (TEXT)`, `updated_at (TEXT)`.
     * `inventory_adjustments`: `adjustment_id (TEXT PRIMARY KEY)`, `case_id (TEXT)`, `sku (TEXT)`, `adjustment_type (TEXT)`, `quantity (INTEGER)`, `reason (TEXT)`, `status (TEXT)`, `before_quantity (INTEGER)`, `after_quantity (INTEGER)`, `approved_by (TEXT)`, `created_at (TEXT)`, `updated_at (TEXT)`.
     * `feedback`: `feedback_id (TEXT PRIMARY KEY)`, `case_id (TEXT)`, `rating (INTEGER)`, `reason (TEXT)`, `created_at (TEXT)`.
     * `execution_events`: `event_id (TEXT PRIMARY KEY)`, `case_id (TEXT)`, `step_name (TEXT)`, `agent_name (TEXT)`, `status (TEXT)`, `details (TEXT)`, `timestamp (TEXT)`.
   * **Deterministic Seeding Function**:
     * Insert seed record for `SKU-GHOST-01`: Physical Quantity = `250`, Reserved = `10`, Damaged = `0`, Version = `1`.

2. **Implement `decision/records_agent.py`**:
   * `class RecordsAgent`:
     * `get_inventory(sku: str) -> Optional[dict]`: Parameterized query returning dictionary representation of inventory row.
     * `get_inventory_history(sku: str) -> list[dict]`: Queries adjustments for the SKU.
     * `sku_exists(sku: str) -> bool`: Safe existence check.

---

### PHASE 3: Evidence Normalization & Reconciliation Engine (Minutes 30–45)

1. **Implement `decision/normalizer.py`**:
   * `class NormalizedClaim`:
     * Stores normalized quantity (if applicable), standard unit conversion, source certainty classification (`DIRECT_OBSERVATION`, `DOCUMENTED_REPORT`, `HEARSAY_AUDIO`).
   * Normalization logic:
     * Map claims into standardized buckets: `SHIPPED`, `RECEIVED`, `DAMAGED_OBSERVED`, `ANOMALY_NOTE`.
     * Prevent conversion across incompatible units (e.g., boxes to units without a validated conversion factor).

2. **Implement `decision/reconciler.py`**:
   * Epistemic statuses: `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`, `NEEDS_REVIEW`.
   * Core Reconcile Logic:
     * Input: `sku: str`, `inventory_record: dict`, `normalized_claims: list[NormalizedClaim]`, `past_feedback: list[dict]`.
     * **Epistemic Invariants**:
       1. If Invoiced Quantity ($Q_{inv}$) and Received Quantity ($Q_{rec}$) are both present and $Q_{inv} \neq Q_{rec}$: mark as `CONTRADICTED`. Discrepancy $= |Q_{inv} - Q_{rec}|$.
       2. Do **not** infer theft or assume warehouse stock should automatically decrease by $10$ units. Current inventory balance ($250$) may already reflect the received shipment.
       3. If Vision evidence reports physical package damage without explicit piece counts: mark damaged item count as *Unquantified* (`NEEDS_REVIEW`). Do not invent a damaged unit count.
       4. If Invoice exists without any corresponding receipt: return `INSUFFICIENT_EVIDENCE` (invoice alone $\neq$ proof of delivery).
       5. Incorporate past feedback: If past feedback mentions "prioritize receipt over invoice", prioritize receipt evidence and flag invoice discrepancy as vendor billing issue rather than stock shortage.
     * Output: `ReconciliationResult` dataclass with status, discrepancy details, supporting evidence IDs, uncertainties, and proposed action recommendations.

---

### PHASE 4: Adjustment Proposal & Controlled Execution (Minutes 45–58)

1. **Implement `decision/adjustments.py`**:
   * State Machine: `PROPOSED` $\to$ `APPROVED` $\to$ `APPLIED` $\to$ `VERIFIED` (also `REJECTED`, `FAILED`).
   * `propose_adjustment(case_id, sku, adjustment_type, quantity, reason, supporting_evidence_ids, conn) -> str`:
     * Validates that quantity is non-zero and sku exists.
     * Saves record with status `PROPOSED`. Returns `adjustment_id`.
   * `approve_adjustment(adjustment_id, approver_name, conn) -> bool`:
     * Checks status is `PROPOSED`. Updates status to `APPROVED` and records `approved_by`.
   * `apply_adjustment(adjustment_id, conn) -> dict`:
     * **Atomic Transaction**:
       * Check status is `APPROVED` (reject if already `APPLIED` $\to$ Idempotency).
       * Read current stock with `SELECT physical_quantity, version FROM inventory WHERE sku = ?`.
       * Compute target stock: `after_quantity = before_quantity + delta`.
       * Verify `after_quantity >= 0`.
       * Update inventory with optimistic locking:
         `UPDATE inventory SET physical_quantity = ?, version = version + 1 WHERE sku = ? AND version = ?`.
       * If update count == 0: Raise concurrency conflict.
       * Update adjustment record: `status = 'APPLIED'`, `before_quantity = ?`, `after_quantity = ?`.
       * Commit transaction.
   * `verify_adjustment(adjustment_id, conn) -> bool`:
     * Independent fresh read from `inventory` table.
     * Confirms that the persisted `physical_quantity` strictly matches `after_quantity` recorded in the adjustment.
     * Updates adjustment record status to `VERIFIED`.

---

### PHASE 5: Feedback Loop & Execution Ledger (Minutes 58–68)

1. **Implement `decision/feedback.py`**:
   * `submit_feedback(case_id: str, rating: int, reason: str, conn) -> dict`:
     * Enforce rating $\in [1, 5]$. Reject if outside range.
     * Enforce `reason.strip()` is non-empty. Reject empty reasons.
     * Persist to `feedback` table.
   * `get_relevant_feedback(limit: int = 5, conn) -> list[dict]`:
     * Retrieve recent feedback entries to pass into subsequent orchestrator runs as decision guidance.

2. **Implement `decision/ledger.py`**:
   * `class ExecutionLedger`:
     * Records structured events: `record_event(case_id, step_name, agent_name, status, details)`.
     * Statuses: `COMPLETED`, `FAILED`, `SKIPPED`, `PENDING`, `NEEDS_REVIEW`.
     * `get_trace(case_id) -> list[dict]`: Returns chronologically ordered audit trail for UI or API inspection.

---

### PHASE 6: Orchestrator Pipeline Integration (Minutes 68–78)

1. **Implement `decision/orchestrator.py`**:
   * Public interface: `run_pipeline(files: list[str], sku: str, use_fixture: bool = False, db_path: str = "ghoststock.db") -> dict`.
   * **Execution Pipeline Flow**:
     1. Generate unique `case_id = str(uuid.uuid4())`.
     2. Initialize case in `reconciliation_cases` and start execution trace in `ExecutionLedger`.
     3. Validate SKU input; verify existence via `RecordsAgent`.
     4. **Evidence Retrieval**:
        * If `use_fixture` or `os.getenv("USE_FIXTURE") == "1"`:
          * Read `samples/evidence_sample.json`.
          * Log trace: `step='EVIDENCE_EXTRACTION'`, `status='COMPLETED'`, `details='Loaded from fixture'`.
        * Else:
          * Call Person A extractors (with fallback / controlled error if extractors are missing).
     5. Validate each piece of evidence using `contract.validate()`. Record failures to trace.
     6. Persist validated evidence to `evidence_records` table.
     7. Fetch authoritative inventory via `RecordsAgent`.
     8. Retrieve recent feedback guidance via `get_relevant_feedback()`.
     9. Normalize evidence via `normalizer.py`.
     10. Run reconciliation via `reconciler.py`.
     11. If justified, create adjustment proposal via `adjustments.propose_adjustment()` in `PROPOSED` state (do *not* apply without explicit approval).
     12. Return structured dictionary containing:
         * `case_id`: UUID
         * `status`: Reconciler status (`CONTRADICTED`, `SUPPORTED`, etc.)
         * `sku`: Target SKU
         * `evidence`: List of validated evidence summaries
         * `reconciliation`: Full reconciliation report
         * `adjustment_proposal`: Proposed adjustment details (or `None`)
         * `execution_trace`: List of all logged audit events
         * `errors`: List of non-fatal errors or warnings
         * `feedback_required`: `True`

---

### PHASE 7: Minimal Testing & Smoke Test Suite (Minutes 78–85)

1. **Implement `tests/smoke_test.py`**:
   * Uses an isolated in-memory or temporary SQLite database (`:memory:` or `/tmp/test_ghoststock.db`).
   * Test 1: **Happy Path & Fixture Pipeline**:
     * Run `run_pipeline([], 'SKU-GHOST-01', use_fixture=True)`.
     * Assert returned dictionary contains `case_id`, `reconciliation`, and `execution_trace`.
   * Test 2: **Discrepancy Detection**:
     * Assert reconciler flags discrepancy between 100 invoiced and 90 received as `CONTRADICTED`.
     * Assert discrepancy amount is exactly 10 units.
     * Assert reconciler notes damage observation without fabricating quantity lost.
   * Test 3: **Adjustment Safety & Approval Gate**:
     * Verify that an unapproved proposal cannot be applied.
     * Approve proposal and apply it.
     * Verify inventory quantity changes from 250 to 240 (or according to adjustment logic).
   * Test 4: **Before-and-After Independent Verification**:
     * Query `inventory` directly using raw SQL; assert physical quantity equals the adjustment's `after_quantity`.
   * Test 5: **Idempotency**:
     * Attempt to apply the already applied adjustment again; assert rejection and verify stock does not double-decrement.
   * Test 6: **Mandatory Feedback Persistence**:
     * Assert submission with empty reason fails with `ValueError`.
     * Assert submission with rating `6` fails with `ValueError`.
     * Submit valid feedback (rating 4, "Verified receipt mismatch"); assert stored and retrievable.
   * Test 7: **Unknown SKU Handling**:
     * Run pipeline for `SKU-UNKNOWN-99`; verify clean error handling without fabricating stock.

---

### PHASE 8: Final Polish, Brain Sync & Handoff Report (Minutes 85–90)

1. **Update Project Brain**:
   * Update `PROJECT_STATE.md`: Document all implemented modules and the passing test command.
   * Update `SESSION_LOG.md`: Record test command output and timestamps.
   * Update `CONTRACT_MAP.md`: Confirm actual file paths and signatures.
   * Update `KNOWN_ISSUES.md`: Document any mocked or simulated aspects (e.g. live vision/audio models defaulted to fixture when offline).

2. **Prepare Final Report (Section 13 Format)**:
   * Formulate the required final report detailing implemented components, files created, test output, end-to-end verification description, and handoff instructions for Person A.

---

## 4. Component Technical Specifications & Signatures

### 4.1 SQLite DDL (`decision/database.py`)

```sql
CREATE TABLE IF NOT EXISTS inventory (
    sku TEXT PRIMARY KEY,
    physical_quantity INTEGER NOT NULL,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,
    damaged_quantity INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    agent TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    sku TEXT NOT NULL,
    extracted_value TEXT NOT NULL,
    unit TEXT NOT NULL,
    confidence REAL NOT NULL,
    raw_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reconciliation_cases (
    case_id TEXT PRIMARY KEY,
    target_sku TEXT NOT NULL,
    status TEXT NOT NULL,
    decision_summary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_adjustments (
    adjustment_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    adjustment_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    before_quantity INTEGER,
    after_quantity INTEGER,
    approved_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES reconciliation_cases(case_id)
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    rating INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES reconciliation_cases(case_id)
);

CREATE TABLE IF NOT EXISTS execution_events (
    event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

### 4.2 Key Python Interfaces

```python
# contract.py
def validate(evidence: Evidence) -> tuple[bool, list[str]]: ...

# decision/records_agent.py
class RecordsAgent:
    def __init__(self, conn: sqlite3.Connection): ...
    def get_inventory(self, sku: str) -> Optional[dict]: ...
    def sku_exists(self, sku: str) -> bool: ...

# decision/reconciler.py
class Reconciler:
    def reconcile(
        self,
        sku: str,
        current_inventory: dict,
        normalized_evidence: list[NormalizedClaim],
        contextual_feedback: list[dict]
    ) -> ReconciliationResult: ...

# decision/adjustments.py
def propose_adjustment(case_id: str, sku: str, adj_type: str, qty: int, reason: str, evidence_ids: list[str], conn: sqlite3.Connection) -> str: ...
def approve_adjustment(adjustment_id: str, approver: str, conn: sqlite3.Connection) -> bool: ...
def apply_adjustment(adjustment_id: str, conn: sqlite3.Connection) -> dict: ...
def verify_adjustment(adjustment_id: str, conn: sqlite3.Connection) -> bool: ...

# decision/feedback.py
def submit_feedback(case_id: str, rating: int, reason: str, conn: sqlite3.Connection) -> dict: ...
def get_relevant_feedback(limit: int, conn: sqlite3.Connection) -> list[dict]: ...

# decision/orchestrator.py
def run_pipeline(files: list[str], sku: str, use_fixture: bool = False, db_path: str = "ghoststock.db") -> dict: ...
```

---

## 5. Critical Invariants & Guardrails for the Agent

1. **Epistemic Modesty**:
   * Invoices specify what was billed/shipped; receipts record what was logged into receiving.
   * If Invoice ($100$) $\neq$ Receipt ($90$), do **not** jump to conclusions about theft.
   * If Vision evidence spots crushed cardboard, record damaged packaging observed, but do **not** invent a number of lost pieces unless clearly indicated.
2. **Transaction & Idempotency Rules**:
   * Never execute an adjustment without `APPROVED` status.
   * Stock updates must use optimistic locking (`version` check).
   * Double execution must fail without modifying inventory.
3. **Mandatory Feedback Rules**:
   * Reject ratings $<1$ or $>5$.
   * Reject empty or whitespace-only written explanations.
4. **Zero Hallucination**:
   * If a SKU is not found in the `inventory` table, return a controlled error (`SKU_NOT_FOUND`). Do not insert a mock inventory row silently.

---

## 6. How Person A Integrates With This Engine

Provide Person A with the following integration code snippet:

```python
from decision.orchestrator import run_pipeline
from decision.adjustments import approve_adjustment, apply_adjustment
from decision.feedback import submit_feedback
import sqlite3

# 1. Trigger the workflow
result = run_pipeline(
    files=["uploads/invoice.pdf", "uploads/receipt.png"],
    sku="SKU-GHOST-01",
    use_fixture=True  # or False once Person A's extractors are wired
)

case_id = result["case_id"]
proposal = result["adjustment_proposal"]

# 2. If an adjustment is proposed, approve and apply via UI button
if proposal:
    conn = sqlite3.connect("ghoststock.db")
    approve_adjustment(proposal["adjustment_id"], approver="sherwin", conn=conn)
    execution_result = apply_adjustment(proposal["adjustment_id"], conn=conn)
    print(f"Verified stock changed from {execution_result['before']} to {execution_result['after']}")

# 3. Mandatory feedback collection at case conclusion
submit_feedback(
    case_id=case_id,
    rating=5,
    reason="Identified 10-unit supplier shortage correctly."
)
```

---

## 7. Concrete File Templates & Reference Implementations

The implementing agent should use the following reference templates as the canonical blueprint when creating each file.

### 7.1 `contract.py`
```python
from dataclasses import dataclass, field
from datetime import datetime
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
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


def validate(evidence: Evidence) -> tuple[bool, list[str]]:
    """Validate an Evidence object against schema requirements."""
    errors = []
    if not evidence.evidence_id or not isinstance(evidence.evidence_id, str):
        errors.append("evidence_id must be a non-empty string")
    if not evidence.sku or not isinstance(evidence.sku, str):
        errors.append("sku must be a non-empty string")
    if not (0.0 <= evidence.confidence <= 1.0):
        errors.append(f"confidence must be in [0.0, 1.0], got {evidence.confidence}")
    if evidence.claim_type in ("SHIPPED_QUANTITY", "RECEIVED_QUANTITY"):
        try:
            val = float(evidence.extracted_value)
            if val < 0:
                errors.append(f"quantity value cannot be negative: {val}")
        except (ValueError, TypeError):
            errors.append(f"claim {evidence.claim_type} requires numeric extracted_value, got {evidence.extracted_value}")
    return (len(errors) == 0, errors)
```

### 7.2 `samples/evidence_sample.json`
```json
[
  {
    "evidence_id": "EV-DOC-INV-001",
    "source_file": "samples/supplier_invoice.pdf",
    "source_type": "DOCUMENT",
    "agent_name": "DocumentAgent",
    "sku": "SKU-GHOST-01",
    "claim_type": "SHIPPED_QUANTITY",
    "extracted_value": 100,
    "unit": "units",
    "confidence": 0.95,
    "metadata": {"invoice_number": "INV-2026-8812", "vendor": "Apex Logistics"}
  },
  {
    "evidence_id": "EV-DOC-REC-002",
    "source_file": "samples/warehouse_receipt.pdf",
    "source_type": "DOCUMENT",
    "agent_name": "DocumentAgent",
    "sku": "SKU-GHOST-01",
    "claim_type": "RECEIVED_QUANTITY",
    "extracted_value": 90,
    "unit": "units",
    "confidence": 0.92,
    "metadata": {"receipt_number": "REC-9941", "receiver": "Dock Door 4"}
  },
  {
    "evidence_id": "EV-VIS-DMG-003",
    "source_file": "samples/pallet_damage.jpg",
    "source_type": "VISION",
    "agent_name": "VisionAgent",
    "sku": "SKU-GHOST-01",
    "claim_type": "DAMAGE_OBSERVED",
    "extracted_value": "Outer cardboard puncture on pallet 1",
    "unit": "n/a",
    "confidence": 0.85,
    "metadata": {"box_count_unverified": true}
  },
  {
    "evidence_id": "EV-AUD-REP-004",
    "source_file": "samples/dock_voice_note.wav",
    "source_type": "AUDIO",
    "agent_name": "AudioAgent",
    "sku": "SKU-GHOST-01",
    "claim_type": "ANOMALY_NOTE",
    "extracted_value": "Supervisor mentions 1 box appeared crushed and short-shipped",
    "unit": "n/a",
    "confidence": 0.78,
    "metadata": {"speaker": "Warehouse Shift Lead"}
  }
]
```

### 7.3 `decision/database.py`
```python
import sqlite3
from datetime import datetime


DEFAULT_DB_PATH = "ghoststock.db"


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH, seed: bool = True) -> sqlite3.Connection:
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            physical_quantity INTEGER NOT NULL,
            reserved_quantity INTEGER NOT NULL DEFAULT 0,
            damaged_quantity INTEGER NOT NULL DEFAULT 0,
            version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS evidence_records (
            evidence_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            agent TEXT NOT NULL,
            claim_type TEXT NOT NULL,
            sku TEXT NOT NULL,
            extracted_value TEXT NOT NULL,
            unit TEXT NOT NULL,
            confidence REAL NOT NULL,
            raw_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_cases (
            case_id TEXT PRIMARY KEY,
            target_sku TEXT NOT NULL,
            status TEXT NOT NULL,
            decision_summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_adjustments (
            adjustment_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            adjustment_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            before_quantity INTEGER,
            after_quantity INTEGER,
            approved_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES reconciliation_cases(case_id)
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES reconciliation_cases(case_id)
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            step_name TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """)

        if seed:
            now = datetime.utcnow().isoformat()
            conn.execute("""
            INSERT OR IGNORE INTO inventory (sku, physical_quantity, reserved_quantity, damaged_quantity, version, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("SKU-GHOST-01", 250, 10, 0, 1, now))

    return conn
```

### 7.4 `decision/records_agent.py`
```python
import sqlite3
from typing import Optional


class RecordsAgent:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_inventory(self, sku: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE sku = ?", (sku,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def sku_exists(self, sku: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM inventory WHERE sku = ?", (sku,))
        return cursor.fetchone() is not None

    def get_adjustments_history(self, sku: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory_adjustments WHERE sku = ? ORDER BY created_at DESC", (sku,))
        return [dict(row) for row in cursor.fetchall()]
```

### 7.5 `decision/reconciler.py`
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


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


class Reconciler:
    def reconcile(
        self,
        sku: str,
        current_inventory: Optional[dict],
        claims: list[dict],
        past_feedback: list[dict]
    ) -> ReconciliationResult:
        if not current_inventory:
            return ReconciliationResult(
                sku=sku,
                status=ReconciliationStatus.NEEDS_REVIEW,
                discrepancy_detected=False,
                discrepancy_quantity=None,
                summary=f"SKU {sku} not found in authoritative inventory records.",
                uncertainties=["Unknown SKU; no baseline inventory exists."]
            )

        invoiced_qty = None
        received_qty = None
        evidence_ids = []
        uncertainties = []
        damage_notes = []

        for c in claims:
            cid = c.get("evidence_id")
            if cid:
                evidence_ids.append(cid)
            ctype = c.get("claim_type")
            cval = c.get("extracted_value")

            if ctype == "SHIPPED_QUANTITY":
                try:
                    invoiced_qty = float(cval)
                except (ValueError, TypeError):
                    uncertainties.append(f"Non-numeric invoice quantity: {cval}")
            elif ctype == "RECEIVED_QUANTITY":
                try:
                    received_qty = float(cval)
                except (ValueError, TypeError):
                    uncertainties.append(f"Non-numeric receipt quantity: {cval}")
            elif ctype == "DAMAGE_OBSERVED":
                damage_notes.append(str(cval))
                uncertainties.append("Visual damage observed but exact lost unit count is unquantified.")
            elif ctype == "ANOMALY_NOTE":
                uncertainties.append(f"Audio/voice note reported: {cval} (requires corroboration).")

        # Evaluate Epistemic Invariants
        if invoiced_qty is not None and received_qty is None:
            return ReconciliationResult(
                sku=sku,
                status=ReconciliationStatus.INSUFFICIENT_EVIDENCE,
                discrepancy_detected=False,
                discrepancy_quantity=None,
                summary="Invoice exists without corresponding warehouse receipt. Invoice alone does not prove delivery.",
                supporting_evidence_ids=evidence_ids,
                uncertainties=uncertainties + ["Missing delivery confirmation."]
            )

        if invoiced_qty is not None and received_qty is not None:
            discrepancy = invoiced_qty - received_qty
            if abs(discrepancy) > 1e-6:
                summary = (
                    f"Discrepancy detected: Invoice claims {invoiced_qty} units shipped, "
                    f"but warehouse receipt records {received_qty} units received (mismatch of {discrepancy} units)."
                )
                if damage_notes:
                    summary += f" Damage note recorded: {'; '.join(damage_notes)}."

                # Rule: Do not infer theft or automatically deduct from existing warehouse balance
                return ReconciliationResult(
                    sku=sku,
                    status=ReconciliationStatus.CONTRADICTED,
                    discrepancy_detected=True,
                    discrepancy_quantity=discrepancy,
                    summary=summary,
                    supporting_evidence_ids=evidence_ids,
                    uncertainties=uncertainties,
                    action_justified=True,
                    recommended_adjustment={
                        "adjustment_type": "SHORTAGE_DISCREPANCY_FLAG",
                        "quantity": -int(discrepancy),
                        "reason": f"Discrepancy of {discrepancy} units between invoice and receipt."
                    }
                )

        return ReconciliationResult(
            sku=sku,
            status=ReconciliationStatus.SUPPORTED,
            discrepancy_detected=False,
            discrepancy_quantity=0.0,
            summary="Evidence claims are consistent with received inventory.",
            supporting_evidence_ids=evidence_ids,
            uncertainties=uncertainties
        )
```

---

## 8. Final Report Checklist & Template (Person B Section 13)

When the implementing agent concludes the session, it must output a structured markdown report following this format:

```markdown
# GHOSTSTOCK 2.0 (PERSON B) — FINAL EXECUTION REPORT

## A. Implemented
- SQLite Database & Deterministic Seeding (`decision/database.py`)
- Authoritative Records Agent (`decision/records_agent.py`)
- Shared Evidence Contract & Validation Function (`contract.py`)
- Standard Multimodal Fixture (`samples/evidence_sample.json`)
- Epistemic Rule-Based Reconciler (`decision/reconciler.py`)
- Transactional & Idempotent Adjustment Engine (`decision/adjustments.py`)
- Mandatory Feedback Collection & Persistence (`decision/feedback.py`)
- Audit Execution Ledger (`decision/ledger.py`)
- High-level Workflow Entry Point: `run_pipeline(files, sku)` (`decision/orchestrator.py`)
- Automated Smoke Verification Suite (`tests/smoke_test.py`)

## B. Files Changed
- `.gitignore`: Added `.ghoststock_brain/`, `*.db`, `__pycache__/`
- `contract.py`: Shared evidence dataclass and validation rules
- `samples/evidence_sample.json`: Multimodal 4-agent discrepancy fixture
- `decision/database.py`: Schema DDL and connection helpers
- `decision/records_agent.py`: Authoritative inventory queries
- `decision/normalizer.py`: Claim normalization logic
- `decision/reconciler.py`: Epistemic discrepancy detection
- `decision/adjustments.py`: Safe propose, approve, apply, verify lifecycle
- `decision/feedback.py`: Rating/reason storage and contextual recall
- `decision/ledger.py`: Audit trail recorder
- `decision/orchestrator.py`: Main `run_pipeline` workflow
- `tests/smoke_test.py`: Complete sanity checks suite
- `.ghoststock_brain/*`: All 8 operational project state tracking documents

## C. Tests Executed
- Command: `python3 -m unittest tests/smoke_test.py`
- Result: Ran 7 tests in 0.04s — OK (All passed)

## D. End-to-End Verification
- **Scenario**: Invoiced 100 units vs Received 90 units with damaged packaging observation.
- **Evidence**: `samples/evidence_sample.json` loaded in fixture mode.
- **Reconciliation Result**: Detected 10-unit shortage; flagged as `CONTRADICTED`; preserved visual damage without inventing lost piece counts.
- **Database Action**: Proposal created in `PROPOSED` status; approved by human; applied transactionally with optimistic version check; stock adjusted from 250 to 240.
- **Verification**: Direct independent re-read from SQLite confirmed persisted balance of 240; double execution rejected idempotently.
- **Feedback**: Successfully validated rating 5 and written reason, persisting for subsequent runs.

## E. Integration Contract
- Pipeline invocation: `from decision.orchestrator import run_pipeline; res = run_pipeline(files, sku, use_fixture=True)`
- Schema: Returns dict with `case_id`, `status`, `sku`, `evidence`, `reconciliation`, `adjustment_proposal`, `execution_trace`, `errors`, `feedback_required`.

## F. Known Issues
- Vision and Audio models are simulated via fixture data pending Person A live extraction functions.

## G. Project Brain Status
- `.ghoststock_brain/` populated with all 8 files and verified ignored by Git.

## H. Next Actions
- Person A: Connect Streamlit/FastAPI UI file uploader to `run_pipeline(files, sku)`.
- Person B: Support multi-line item purchase orders and vendor-specific dispute formatting.

## I. Git Status
- Active branch: `main`
- No unauthorized commits created.
```

---

*This specification represents the complete, frozen architecture and execution blueprint for Person B.*
