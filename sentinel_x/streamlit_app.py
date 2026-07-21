import json
import urllib.error
import urllib.request
from typing import Any
from uuid import uuid4

import streamlit as st
from audio_recorder_streamlit import audio_recorder

from sentinel_x.core.memory import AuditMemory
from sentinel_x.core.models import AnalyzeIncidentRequest, AnalyzeIncidentResponse
from sentinel_x.main import analyze_incident


TRANSCRIBE_URL = "http://127.0.0.1:8000/api/transcribe"

SCENARIOS = {
    "UN1090 leaking container": {
        "description": "There is a leaking container marked UN1090 near the solvent storage area.",
        "transcript": "Operator reports a strong solvent odor. No one has entered the immediate area.",
        "demo_case": "UN1090 demo",
    },
    "Flame symbol on unknown container": {
        "description": "An unlabeled container has a flame symbol and appears damaged.",
        "transcript": "Floor team is keeping distance and waiting for safety personnel.",
        "demo_case": "flammable symbol demo",
    },
    "Possible corrosive spill": {
        "description": "A container marked corrosive is leaking near a maintenance aisle.",
        "transcript": "Worker reports irritation and the area has been cleared.",
        "demo_case": "corrosive symbol demo",
    },
    "Evidence conflict": {
        "description": "The container contains water, but a flammable chemical label is visible.",
        "transcript": "The team is unsure whether the label or verbal report is correct.",
        "demo_case": "conflict demo",
    },
    "Unknown odor": {
        "description": "I smell something strange near an unknown container.",
        "transcript": "No label is visible from the safe observation point.",
        "demo_case": "unknown hazard demo",
    },
}


st.set_page_config(page_title="Sentinel-X", page_icon="SX", layout="wide")


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f4f7f9;
            color: #162027;
        }
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d8e0e6;
            border-radius: 6px;
            padding: 0.85rem 1rem;
            min-height: 104px;
        }
        .section {
            background: #ffffff;
            border: 1px solid #d8e0e6;
            border-left: 5px solid #536d79;
            border-radius: 6px;
            padding: 1rem 1.1rem;
            margin: 0.75rem 0;
        }
        .section h3 {
            margin: 0 0 0.5rem;
            font-size: 1rem;
            color: #20313a;
        }
        .gate {
            border-left-color: #b05b00;
        }
        .risk-high {
            border-left-color: #b42318;
        }
        .ok {
            border-left-color: #28715d;
        }
        .muted {
            color: #5d6b73;
            font-size: 0.92rem;
        }
        .pill {
            display: inline-block;
            background: #e8eef2;
            border: 1px solid #cbd6dd;
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            margin: 0.1rem 0.25rem 0.1rem 0;
            font-size: 0.86rem;
            color: #263941;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_list(items: list[str]) -> None:
    if not items:
        st.caption("None detected.")
        return
    for item in items:
        st.markdown(f"- {item}")


def render_pills(items: list[str]) -> None:
    if not items:
        st.markdown('<span class="muted">None detected</span>', unsafe_allow_html=True)
        return
    pills = "".join(f'<span class="pill">{item}</span>' for item in items)
    st.markdown(pills, unsafe_allow_html=True)


def render_json(data: Any) -> None:
    st.code(json.dumps(data, indent=2, ensure_ascii=False), language="json")


def post_audio_for_transcription(audio_bytes: bytes) -> str:
    boundary = f"sentinelx-{uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="voice_input.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8")
    body += audio_bytes
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    request = urllib.request.Request(
        TRANSCRIBE_URL,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("text", "")


def render_response(response: AnalyzeIncidentResponse) -> None:
    risk_class = "risk-high" if response.risk.level == "HIGH" else "ok"
    gate_status = "Requires approval" if response.risk.required_confirmation else "No approval required"

    metric_cols = st.columns(4)
    metric_cols[0].metric("Risk Level", response.risk.level)
    metric_cols[1].metric("Confidence", f"{response.risk.confidence:.2f}")
    metric_cols[2].metric("Plan Status", response.response_plan.status)
    metric_cols[3].metric("Human Gate", gate_status)

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown('<div class="section"><h3>Observation Result</h3>', unsafe_allow_html=True)
        st.write(f"Possible UN code: `{response.evidence.un_codes[0] if response.evidence.un_codes else 'unknown'}`")
        st.write(f"Conflict detected: `{response.evidence.conflict_detected}`")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><h3>Detected Evidence</h3>', unsafe_allow_html=True)
        st.caption("UN codes")
        render_pills(response.evidence.un_codes)
        st.caption("Keywords")
        render_pills(response.evidence.hazard_keywords)
        st.caption("Hazard symbols")
        render_pills(response.evidence.hazard_symbols)
        if response.evidence.notes:
            st.caption("Notes")
            render_list(response.evidence.notes)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><h3>Knowledge Source</h3>', unsafe_allow_html=True)
        render_list(response.sop_source)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f'<div class="section {risk_class}"><h3>Risk Level</h3>', unsafe_allow_html=True)
        render_list(response.risk.reasons)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section gate"><h3>Human Approval Gate</h3>', unsafe_allow_html=True)
        st.write(f"Approval status: `{response.approval_status}`")
        st.write(f"Required confirmation: `{response.risk.required_confirmation}`")
        st.write(f"Human review required: `{response.response_plan.human_review_required}`")
        st.caption("Sentinel-X never authorizes equipment shutdown, valve operation, physical intervention, or chemical handling.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><h3>Response Plan</h3>', unsafe_allow_html=True)
        st.caption("Immediate actions")
        render_list(response.response_plan.immediate_actions)
        st.caption("Forbidden actions")
        render_list(response.response_plan.forbidden_actions)
        st.caption("Evacuation guidance")
        st.write(response.response_plan.evacuation_guidance)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><h3>Audit Record</h3>', unsafe_allow_html=True)
        audit_records = AuditMemory().load_all()
        latest = audit_records[-1].model_dump(mode="json") if audit_records else {}
        render_json(latest)
        st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    apply_styles()

    st.title("Sentinel-X")
    st.caption("Agentic safety copilot MVP | Recommendations only | Human approval required for critical actions")

    scenario_name = st.selectbox("Scenario selector", list(SCENARIOS))
    scenario = SCENARIOS[scenario_name]

    if st.session_state.get("scenario_name") != scenario_name:
        st.session_state["scenario_name"] = scenario_name
        st.session_state["description_text"] = scenario["description"]
        st.session_state["transcript_text"] = scenario["transcript"]

    st.markdown('<div class="section"><h3>Voice Input</h3>', unsafe_allow_html=True)
    audio_bytes = audio_recorder(
        text="Record incident voice note",
        recording_color="#b42318",
        neutral_color="#536d79",
        icon_name="microphone",
        icon_size="2x",
    )
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")
        if st.button("Transcribe voice to incident description", use_container_width=True):
            try:
                transcript_text = post_audio_for_transcription(audio_bytes)
                st.session_state["description_text"] = transcript_text
                st.success("Voice transcription added to incident description.")
            except (urllib.error.URLError, TimeoutError) as exc:
                st.error(f"Transcription service unavailable: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("incident_form"):
        description = st.text_area(
            "Incident description",
            key="description_text",
            height=110,
        )
        transcript = st.text_area(
            "Transcript input",
            key="transcript_text",
            height=110,
        )
        analyze = st.form_submit_button("Analyze", type="primary", use_container_width=True)

    if analyze:
        request = AnalyzeIncidentRequest(
            description=description,
            transcript=transcript,
            demo_case=scenario["demo_case"],
        )
        response = analyze_incident(request)
        st.session_state["latest_response"] = response

    response = st.session_state.get("latest_response")
    if response is None:
        st.info("Select a scenario or edit the incident inputs, then run Analyze.")
        return

    render_response(response)


if __name__ == "__main__":
    main()
