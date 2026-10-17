"""Run: python test_contract.py"""
import json
import os

import feedback
from contract import validate

ROOT = os.path.dirname(os.path.abspath(__file__))
results = []


def check(name, fn):
    try:
        fn()
        results.append((name, "PASS", ""))
    except Exception as e:
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"[:150]))


GOOD = {"agent": "document", "claim": "c", "sku": "sku a", "metric": "shipped_qty",
        "value": "100", "source": "s", "excerpt": "e", "model_confidence": None}


def rejects(**change):
    def run():
        rec = {**GOOD, **change}
        rec = {k: v for k, v in rec.items() if v is not ...}
        try:
            validate([rec])
        except ValueError:
            return
        raise AssertionError("validate() accepted bad input")
    return run


def fixture_ok():
    with open(os.path.join(ROOT, "fixtures", "evidence_sample.json")) as f:
        assert len(validate(json.load(f))) == 4


def sku_norm():
    assert validate([GOOD])[0]["sku"] == "SKU-A" and validate([GOOD])[0]["value"] == 100.0


def feedback_roundtrip():
    backup = feedback.PATH + ".bak"
    had = os.path.exists(feedback.PATH)
    if had:
        os.replace(feedback.PATH, backup)
    try:
        feedback.save_feedback(2, "ledger missed the damage", "test-case")
        assert "ledger missed the damage" in feedback.get_lessons()
        os.remove(feedback.PATH)
        feedback.save_feedback(5, "great", "ok-case")
        assert feedback.get_lessons() == ""
        with open(feedback.PATH, "w") as f:
            f.write("{corrupt")
        assert feedback.load_feedback() == []
    finally:
        if os.path.exists(feedback.PATH):
            os.remove(feedback.PATH)
        if had:
            os.replace(backup, feedback.PATH)


check("fixture passes validate", fixture_ok)
check("rejects missing field", rejects(claim=...))
check("rejects bad metric", rejects(metric="theft"))
check("rejects non-numeric value", rejects(value="lots"))
check("rejects unknown agent", rejects(agent="oracle"))
check("sku normalization", sku_norm)
check("feedback round-trip", feedback_roundtrip)

from evidence import audio_agent, document_agent, vision_agent  # noqa: E402

# ---- no-key tests for the stub pipeline: extractors are faked HERE ONLY ----
from evidence import stub_pipeline  # noqa: E402


def fake_ev(source):
    return {"agent": "document", "claim": f"from {source}", "sku": "SKU-A", "metric": "other",
            "value": 1.0, "source": source, "excerpt": "x", "model_confidence": None}


def with_fake_docs(fn_extract, body):
    orig = document_agent.extract
    document_agent.extract = fn_extract
    try:
        body()
    finally:
        document_agent.extract = orig


def t_two_docs():
    def body():
        out = stub_pipeline.run_pipeline_stub({"document": ["/t/invoice.pdf", "/t/receipt.pdf"]}, "SKU-A")
        assert [e["source"] for e in out["evidence"]] == ["invoice.pdf", "receipt.pdf"], out
        assert out["failures"] == [] and out["is_stub"] is True
    with_fake_docs(lambda p: [fake_ev(os.path.basename(p))], body)


def t_str_doc():
    def body():
        out = stub_pipeline.run_pipeline_stub({"document": "/t/invoice.pdf"}, "SKU-A")
        assert len(out["evidence"]) == 1 and out["evidence"][0]["source"] == "invoice.pdf"
    with_fake_docs(lambda p: [fake_ev(os.path.basename(p))], body)


def t_empty():
    for files in ({}, {"document": [], "vision": None, "audio": None}):
        out = stub_pipeline.run_pipeline_stub(files, "SKU-A")
        assert out["evidence"] == [] and out["findings"] == [] and out["failures"] == []


def t_one_fails():
    def fake(p):
        if p.endswith("bad.pdf"):
            raise RuntimeError("boom")
        return [fake_ev(os.path.basename(p))]

    def body():
        out = stub_pipeline.run_pipeline_stub({"document": ["/t/bad.pdf", "/t/good.pdf"]}, "SKU-A")
        assert [e["source"] for e in out["evidence"]] == ["good.pdf"]
        assert len(out["failures"]) == 1 and out["failures"][0].startswith("document (bad.pdf): ")
    with_fake_docs(fake, body)


check("stub: two docs in one call", t_two_docs)
check("stub: single str doc", t_str_doc)
check("stub: empty files dict", t_empty)
check("stub: one doc fails, other kept", t_one_fails)

REAL = [("invoice.pdf", document_agent), ("receipt.pdf", document_agent),
        ("package.jpg", vision_agent), ("note.mp3", audio_agent)]
for fname, mod in REAL:
    path = os.path.join(ROOT, "samples", fname)
    if not os.path.exists(path):
        results.append((f"extract {fname}", "SKIP", "file missing"))
        continue

    def run(path=path, mod=mod):
        recs = mod.extract(path)
        for r in recs:
            print(f"  [{fname}]", r)
        validate(recs)
    check(f"extract {fname}", run)

for fname, mod in [("blank.pdf", document_agent), ("garbage.jpg", vision_agent)]:
    path = os.path.join(ROOT, "samples", fname)

    def neg(path=path, mod=mod):
        recs = mod.extract(path)
        print(f"  [{os.path.basename(path)}] -> {recs}")
        assert not [r for r in recs if r["metric"] == "damage"], "invented damage"
    check(f"negative {fname}", neg)

print("\n{:<32}{:<6} {}".format("TEST", "RESULT", "DETAIL"))
for n, r, d in results:
    print("{:<32}{:<6} {}".format(n, r, d))
print("\nFAILED" if any(r == "FAIL" for _, r, _ in results) else "\nALL OK (skips excluded)")
