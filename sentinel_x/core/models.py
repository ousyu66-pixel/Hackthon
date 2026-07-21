from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ApprovalStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    not_required = "not_required"


class RiskLevel(StrEnum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    unknown = "UNKNOWN"


class AnalyzeIncidentRequest(BaseModel):
    description: str = Field(..., min_length=1)
    transcript: str = ""
    demo_case: str | None = None


class Evidence(BaseModel):
    un_codes: list[str] = Field(default_factory=list)
    hazard_keywords: list[str] = Field(default_factory=list)
    hazard_symbols: list[str] = Field(default_factory=list)
    conflict_detected: bool = False
    notes: list[str] = Field(default_factory=list)


class ObservationResult(BaseModel):
    possible_un_code: str | None = None
    detected_un_codes: list[str] = Field(default_factory=list)
    detected_keywords: list[str] = Field(default_factory=list)
    unknown_hazard_evidence: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: Evidence = Field(default_factory=Evidence)


class RiskAssessment(BaseModel):
    level: RiskLevel = RiskLevel.unknown
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    required_confirmation: bool = True
    human_confirmation_required: bool = True
    reasons: list[str] = Field(default_factory=list)


class SafetyGateResult(BaseModel):
    approval_required: bool = True
    authorized_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ResponsePlan(BaseModel):
    status: str = "planned"
    required_confirmation: bool = True
    immediate_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    evacuation_guidance: str | None = None
    source_documents: list[str] = Field(default_factory=list)
    human_review_required: bool = True


class AnalyzeIncidentResponse(BaseModel):
    incident_id: str
    timestamp: datetime
    observation: AnalyzeIncidentRequest
    evidence: Evidence
    risk: RiskAssessment
    sop_source: list[str] = Field(default_factory=list)
    response_plan: ResponsePlan
    approval_status: ApprovalStatus = ApprovalStatus.pending
    status: str

    @classmethod
    def phase_one_placeholder(
        cls, observation: AnalyzeIncidentRequest
    ) -> "AnalyzeIncidentResponse":
        return cls(
            incident_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            observation=observation,
            evidence=Evidence(notes=["Phase 1 skeleton only; analysis deferred."]),
            risk=RiskAssessment(reasons=["Risk assessment deferred to Phase 5."]),
            response_plan=ResponsePlan(
                immediate_actions=[
                    "No automated recommendation generated in Phase 1.",
                    "Escalate to authorized human safety personnel.",
                ],
                forbidden_actions=[
                    "Do not perform equipment shutdown through Sentinel-X.",
                    "Do not operate valves through Sentinel-X.",
                    "Do not perform chemical handling based on this placeholder.",
                ],
            ),
            status="phase_1_placeholder",
        )


class AuditRecord(BaseModel):
    incident_id: str
    timestamp: datetime
    observation: AnalyzeIncidentRequest
    evidence: Evidence
    risk: RiskAssessment
    sop_source: list[str]
    response_plan: ResponsePlan
    approval_status: ApprovalStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
