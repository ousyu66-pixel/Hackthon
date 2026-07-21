from fastapi import FastAPI

from datetime import datetime, timezone
from uuid import uuid4

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
