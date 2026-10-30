from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from feagent.config import OLLAMA_MODEL
from feagent.data_loader import load_ground_truth, load_observable
from feagent.investigator import ollama_status
from feagent.llm import OllamaClient
from feagent.qa import DEMO_QUESTIONS, answer_question
from feagent.schema import InvestigationRequest
from feagent.store import briefing_request, default_request

st.set_page_config(page_title="Forecast-Explanation Agent", layout="wide")

DRIVER_LABELS = {
    "payer_access": "Payer access",
    "competitor_activity": "Competitor activity",
}
METHOD_LABELS = {
    "difference_in_differences_vs_named_controls": "Exposed vs control (DiD)",
    "forecast_error_difference_vs_named_controls": "Forecast error vs controls",
    "variance − explained drivers": "Residual",
}

st.markdown(
    """
    <style>
      .block-container {max-width: 1180px; padding-top: 1.2rem;}
      h1 {letter-spacing: -0.03em;}
      .kpi {background: #f4f1ea; border: 1px solid #ddd4c4; padding: 0.9rem 1rem; border-radius: 10px;}
      .kpi .label {font-size: 0.78rem; color: #6b6256; text-transform: uppercase; letter-spacing: 0.04em;}
      .kpi .value {font-size: 1.55rem; font-weight: 650; color: #1f1b16; line-height: 1.2;}
      .miss {background: #f8e7e2;}
    </style>
    """,
    unsafe_allow_html=True,
)

obs = load_observable("week18")
flagged = next(r for r in obs["weekly_national"] if r["week"] == obs["flagged_week"])

if "messages" not in st.session_state:
    st.session_state.messages = []
if "request_payload" not in st.session_state:
    st.session_state.request_payload = default_request()
if "report" not in st.session_state:
    st.session_state.report = None
if "report_key" not in st.session_state:
    st.session_state.report_key = None

st.title("Forecast-Explanation Agent")
st.caption(
    f"{obs['brand']} · {obs['metric']} · Week {obs['flagged_week']} ending {flagged['week_ending']} · "
    "Sienna & Alvin · DuckDB + Q&A demo"
)

with st.sidebar:
    st.subheader("Investigation")
    mode = st.selectbox(
        "Investigator",
        options=["stub", "auto", "ollama"],
        index=0,
        help="stub = deterministic playbook (use this for the live demo). auto = Ollama if pulled, else stub.",
    )
    probe = ollama_status(OLLAMA_MODEL)
    if "ollama_model" not in st.session_state:
        installed = probe.get("installed") or []
        st.session_state["ollama_model"] = (
            OLLAMA_MODEL
            if probe["ok"]
            else (installed[0] if installed else OLLAMA_MODEL)
        )
    model_name = st.text_input("Ollama model", key="ollama_model")
    status = ollama_status(model_name)
    if status["ok"]:
        st.success(status["detail"])
    else:
        st.warning(status["detail"])

    show_truth = st.toggle("Show evaluator ground truth", value=False)
    st.divider()
    st.markdown("**Briefing handoff**")
    st.caption("Simulates Michael/Meghna's Brand-Performance Briefing Agent posting an InvestigationRequest.")
    if st.button("Load briefing request", use_container_width=True):
        payload = briefing_request()
        st.session_state.request_payload = payload
        st.session_state.report = None
        st.session_state.report_key = None
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "Briefing Agent handed off a material TRx miss.\n\n"
                    f"**{payload['brand']} · week {payload['week']} · {payload['metric']}**\n\n"
                    f"{payload['notes']}"
                ),
                "handoff": True,
            }
        )
        st.session_state.pending_question = DEMO_QUESTIONS[0]
        st.rerun()
    st.json(st.session_state.request_payload, expanded=False)
    st.caption("Data layer: DuckDB `weekly_performance`, `commercial_events`, `investigation_requests`.")

k1, k2, k3, k4 = st.columns(4)
kpis = [
    (k1, "Forecast TRx", f"{flagged['forecast']:,.0f}", "kpi"),
    (k2, "Actual TRx", f"{flagged['actual']:,.0f}", "kpi"),
    (k3, "Variance", f"{flagged['actual'] - flagged['forecast']:+,.0f}", "kpi miss"),
    (
        k4,
        "Variance %",
        f"{(flagged['actual'] - flagged['forecast']) / flagged['forecast']:.0%}",
        "kpi miss",
    ),
]
for col, label, value, css in kpis:
    col.markdown(
        f'<div class="{css}"><div class="label">{label}</div><div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")
weekly = pd.DataFrame(obs["weekly_national"])
st.line_chart(weekly.set_index("week")[["forecast", "actual"]], height=180)

chat_col, result_col = st.columns((1.15, 1))


def _answer(question: str):
    if mode == "ollama" and not status["ok"]:
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.messages.append({"role": "assistant", "content": status["detail"]})
        return
    request = InvestigationRequest.from_dict(st.session_state.request_payload)
    client = OllamaClient(model=model_name) if mode in {"auto", "ollama"} else None
    cache_key = (mode, request.request_id, model_name)
    cached = st.session_state.report if st.session_state.report_key == cache_key else None
    result = answer_question(
        question, request, mode=mode, client=client, report=cached
    )
    st.session_state.report = result.report
    st.session_state.report_key = cache_key
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.markdown,
            "evidence": [rec.__dict__ for rec in result.evidence],
        }
    )


with chat_col:
    st.subheader("Ask the investigator")
    st.caption("Tonight's three questions:")
    for i, question in enumerate(DEMO_QUESTIONS):
        if st.button(question, key=f"demo_{i}", use_container_width=True):
            st.session_state.pending_question = question
            st.rerun()

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            evidence = message.get("evidence")
            if evidence:
                with st.expander("Tool evidence"):
                    for rec in evidence:
                        st.markdown(f"`{rec['tool_id']}` **{rec['name']}**")
                        st.json(rec["payload"], expanded=False)

    pending = st.session_state.pop("pending_question", None)
    typed = st.chat_input("Ask why the brand missed, how much is payer vs competitor, or what to check next")
    question = pending or typed
    if question:
        _answer(question)
        st.rerun()

with result_col:
    report = st.session_state.report
    if report is None:
        st.info("Ask a question to fill attribution, residual, and what to check.")
    else:
        st.markdown("**Attribution**")
        attr = pd.DataFrame(
            [
                {
                    "Driver": DRIVER_LABELS.get(d.driver, d.driver),
                    "Impact TRx": d.impact_trx,
                    "Confidence": d.confidence,
                    "Method": METHOD_LABELS.get(d.method, d.method),
                }
                for d in report.drivers
            ]
            + [
                {
                    "Driver": "Unexplained residual",
                    "Impact TRx": report.residual_trx,
                    "Confidence": "low",
                    "Method": METHOD_LABELS["variance − explained drivers"],
                }
            ]
        )
        st.dataframe(attr, hide_index=True, width="stretch")
        st.bar_chart(attr.set_index("Driver")["Impact TRx"], horizontal=True)
        st.caption(
            f"Mode: {report.investigator_mode}"
            + (f" · {report.model}" if report.model else "")
            + f" · source {st.session_state.request_payload.get('source')}"
        )

if show_truth:
    truth = load_ground_truth("week18")
    st.subheader("Evaluator ground truth")
    st.caption("Hidden from Investigator tools. Table: eval_ground_truth.")
    truth_rows = [
        {"Driver": DRIVER_LABELS.get(d["driver"], d["driver"]), "Injected TRx": d["impact_trx"]}
        for d in truth["injected_drivers"]
    ]
    truth_rows.append({"Driver": "Unexplained residual", "Injected TRx": truth["residual_trx"]})
    st.dataframe(pd.DataFrame(truth_rows), hide_index=True, width="stretch")
