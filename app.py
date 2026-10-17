from dotenv import load_dotenv
load_dotenv()
"""CargoTruth / GhostStock 2.0 - Streamlit UI. Evidence side (Person A) owns this file."""
import html
import os
import tempfile

import streamlit as st

from feedback import load_feedback, save_feedback

try:
    from decision.orchestrator import run_pipeline
    STUB = False
except ImportError:
    from evidence.stub_pipeline import run_pipeline_stub as run_pipeline
    STUB = True

st.set_page_config(page_title="CargoTruth", layout="wide")
st.title("CargoTruth - claim-level evidence ledger")
if STUB:
    st.error("STUB MODE: decision side not connected (findings are placeholders, not reconciliation)")

AGENT_COLORS = {"document": "#dbeafe", "vision": "#dcfce7", "audio": "#fef9c3", "records": "#f3e8ff"}
STATUS_COLORS = {"supported": "green", "contradicted": "red", "insufficient": "orange"}

# ---- inputs ----
c1, c2, c3 = st.columns(3)
docs = c1.file_uploader("Invoice / receipt PDFs", type=["pdf"], accept_multiple_files=True)
photo = c2.file_uploader("Package photo", type=["jpg", "jpeg", "png"])
voice = c3.file_uploader("Voice note", type=["mp3", "wav"])
sku = st.text_input("SKU", "SKU-A")

has_files = bool(docs or photo or voice)
if not has_files:
    st.info("Upload at least one file to enable analysis.")
if st.button("Run analysis", type="primary", disabled=not has_files):
    tmp = tempfile.mkdtemp()

    def save(upload):
        path = os.path.join(tmp, os.path.basename(upload.name))
        with open(path, "wb") as f:
            f.write(upload.getbuffer())
        return path

    # Contract: ONE run_pipeline call per click; invoice and receipt go together in "document".
    files = {
        "document": [save(d) for d in docs],
        "vision": save(photo) if photo else None,
        "audio": save(voice) if voice else None,
    }
    with st.spinner("Agents extracting evidence..."):
        try:
            out = run_pipeline(files, sku)
            merged = {k: out.get(k, []) for k in ("evidence", "findings", "failures")}
        except Exception as e:  # never crash the UI
            merged = {"evidence": [], "findings": [], "failures": [f"pipeline: {e}"]}
    st.session_state["result"] = merged
    st.session_state.pop("saved_entry", None)

result = st.session_state.get("result")
if result:
    # a) failures
    for msg in result["failures"]:
        st.warning(msg)

    # b) evidence table
    st.subheader("Evidence (extracted independently by each agent)")
    if not result["evidence"]:
        st.info("No evidence extracted.")
    rows = "".join(
        f"<tr style='background:{AGENT_COLORS.get(e['agent'], '#fff')}'>"
        f"<td>{e['agent']}</td><td>{html.escape(e['claim'])}</td><td>{e['value'] if e['value'] is not None else ''}</td>"
        f"<td>{html.escape(e['source'])}</td><td><i>{html.escape(e['excerpt'])}</i></td>"
        f"<td>{e['model_confidence'] if e['model_confidence'] is not None else ''}</td></tr>"
        for e in sorted(result["evidence"], key=lambda e: e["agent"])
    )
    if rows:
        st.markdown(
            "<table style='width:100%;color:#111'><tr><th>agent</th><th>claim</th><th>value</th><th>source</th>"
            f"<th>excerpt</th><th>model-reported confidence (not calibrated)</th></tr>{rows}</table>",
            unsafe_allow_html=True,
        )

    # === LEDGER VIEW (shared with Person B) ===
    st.subheader("Ledger: findings")
    for f in result["findings"]:
        color = STATUS_COLORS.get(f["status"], "gray")
        st.markdown(f"**{f['claim']}** :{color}[{f['status'].upper()}]")
        st.caption(f["reasoning"])
        for e in f["evidence"]:
            st.markdown(f"- `{e['source']}` ({e['agent']}): _{e['excerpt']}_")
    # === END LEDGER VIEW ===

    # d) feedback
    st.subheader("Feedback (required)")
    rating = st.radio("Rating", [1, 2, 3, 4, 5], index=None, horizontal=True)
    reason = st.text_area("Reason")
    if st.button("Submit feedback"):
        if rating is None or not reason.strip():
            st.error("Both a rating and a reason are required.")
        else:
            summary = f"SKU {sku}: {len(result['evidence'])} evidence, {len(result['findings'])} findings, " \
                      f"{len(result['failures'])} failures" + (" (STUB)" if STUB else "")
            st.session_state["saved_entry"] = save_feedback(rating, reason, summary)
    if "saved_entry" in st.session_state:
        st.success("Feedback saved.")
        st.json(st.session_state["saved_entry"])

# e) history
with st.expander("Feedback history"):
    st.json(load_feedback())
