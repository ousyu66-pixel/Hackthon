from datetime import datetime, timezone
from functools import lru_cache
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from sentinel_x.agents.observer import ObserverAgent
from sentinel_x.agents.response_planner import ResponsePlanner
from sentinel_x.agents.risk_agent import RiskAgent
from sentinel_x.core.config import get_settings
from sentinel_x.core.memory import AuditMemory
from sentinel_x.core.models import AnalyzeIncidentRequest, AnalyzeIncidentResponse
from sentinel_x.retrieval.retriever import KnowledgeRetriever
from sentinel_x.tools.report import audit_record_from_response

settings = get_settings()
observer_agent = ObserverAgent()
risk_agent = RiskAgent()
knowledge_retriever = KnowledgeRetriever()
response_planner = ResponsePlanner()
audit_memory = AuditMemory()

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_WHISPER_MODEL_PATH = PROJECT_DIR / "models" / "faster-whisper-tiny.en"
WHISPER_MODEL_PATH = Path(
    os.environ.get("SENTINEL_X_STT_MODEL_PATH", DEFAULT_WHISPER_MODEL_PATH)
).expanduser().resolve()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Human-in-the-loop hazardous material emergency decision-support MVP.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "phase": "1",
    }


@lru_cache
def get_whisper_model():
    from faster_whisper import WhisperModel

    if not WHISPER_MODEL_PATH.exists():
        raise RuntimeError(
            "Local STT model not found. Place faster-whisper tiny.en model files in "
            f"{DEFAULT_WHISPER_MODEL_PATH} or set SENTINEL_X_STT_MODEL_PATH. "
            f"Resolved path: {WHISPER_MODEL_PATH}"
        )
    return WhisperModel(str(WHISPER_MODEL_PATH), device="cpu", compute_type="int8")


@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict[str, str]:
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    try:
        audio_bytes = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = Path(temp_audio.name)

        segments, _ = get_whisper_model().transcribe(
            str(temp_audio_path),
            language="en",
            beam_size=1,
            temperature=0.0,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return {"text": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"STT transcription failed: {exc}") from exc
    finally:
        if "temp_audio_path" in locals():
            temp_audio_path.unlink(missing_ok=True)


@app.post("/analyze_incident", response_model=AnalyzeIncidentResponse)
def analyze_incident(request: AnalyzeIncidentRequest) -> AnalyzeIncidentResponse:
    observation = observer_agent.observe(request)
    retrieval = knowledge_retriever.retrieve(
        un_codes=observation.detected_un_codes,
        hazard_symbols=observation.evidence.hazard_symbols,
        text=" ".join(
            value
            for value in (request.description, request.transcript, request.demo_case)
            if value
        ),
    )
    risk = risk_agent.assess(observation)
    response_plan = response_planner.plan(
        request=request,
        observation=observation,
        risk=risk,
        sop_record=retrieval.record,
    )

    response = AnalyzeIncidentResponse(
        incident_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        observation=request,
        evidence=observation.evidence,
        risk=risk,
        sop_source=retrieval.record["source_documents"],
        response_plan=response_plan,
        status=response_plan.status,
    )
    audit_memory.append(audit_record_from_response(response))
    return response
