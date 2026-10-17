"""STUB pipeline: lets the UI work before the decision side (Person B) is connected.

Real extractors run on the provided files. Findings are a placeholder built locally
and are NOT reconciliation. The return value carries is_stub=True.
"""
import os

from evidence import audio_agent, document_agent, vision_agent

AGENTS = {"document": document_agent, "vision": vision_agent, "audio": audio_agent}


def run_pipeline_stub(files: dict, sku: str) -> dict:
    evidence, failures = [], []
    docs = files.get("document") or []
    if isinstance(docs, str):
        docs = [docs]
    for path in docs:  # one try/except per document file
        try:
            evidence.extend(document_agent.extract(path))
        except Exception as e:
            failures.append(f"document ({os.path.basename(path)}): {e}")
    for name in ("vision", "audio"):
        path = files.get(name)
        if not path:
            continue
        try:
            evidence.extend(AGENTS[name].extract(path))
        except Exception as e:  # each agent isolated: one failure must not stop the rest
            failures.append(f"{name}: {e}")
    findings = [
        {
            "claim": ev["claim"],
            "status": "insufficient",
            "evidence": [ev],
            "reasoning": "STUB: reconciliation not connected",
        }
        for ev in evidence
    ]
    return {"evidence": evidence, "findings": findings, "failures": failures, "is_stub": True}
