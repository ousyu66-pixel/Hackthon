from typing import Any

from sentinel_x.core.models import (
    AnalyzeIncidentRequest,
    ObservationResult,
    ResponsePlan,
    RiskAssessment,
    RiskLevel,
)


BENIGN_CLAIMS = (
    "contains water",
    "just water",
    "only water",
    "plain water",
    "not hazardous",
    "non hazardous",
    "non-hazardous",
)

HAZARDOUS_EVIDENCE_TERMS = (
    "flammable",
    "corrosive",
    "toxic",
    "flame",
    "fire",
    "un1090",
    "un1203",
    "un1017",
)


class ResponsePlanner:
    def plan(
        self,
        *,
        request: AnalyzeIncidentRequest,
        observation: ObservationResult,
        risk: RiskAssessment,
        sop_record: dict[str, Any],
    ) -> ResponsePlan:
        conflict_detected = self.detect_conflict(
            request=request,
            observation=observation,
            sop_record=sop_record,
        )

        if conflict_detected:
            observation.evidence.conflict_detected = True
            if "Text evidence conflicts with detected hazardous evidence." not in observation.evidence.notes:
                observation.evidence.notes.append(
                    "Text evidence conflicts with detected hazardous evidence."
                )
            return self._conflict_plan(sop_record)

        return self._standard_plan(risk=risk, sop_record=sop_record)

    def detect_conflict(
        self,
        *,
        request: AnalyzeIncidentRequest,
        observation: ObservationResult,
        sop_record: dict[str, Any],
    ) -> bool:
        text = self._request_text(request).lower()
        if not any(claim in text for claim in BENIGN_CLAIMS):
            return observation.evidence.conflict_detected

        detected_terms = self._hazard_evidence_text(observation, sop_record)
        has_hazardous_evidence = any(
            term in detected_terms for term in HAZARDOUS_EVIDENCE_TERMS
        )
        return observation.evidence.conflict_detected or has_hazardous_evidence

    def _standard_plan(
        self,
        *,
        risk: RiskAssessment,
        sop_record: dict[str, Any],
    ) -> ResponsePlan:
        risk_statement = self._risk_statement(risk, sop_record)
        immediate_actions = [risk_statement, *sop_record["immediate_actions"]]

        return ResponsePlan(
            status="planned",
            required_confirmation=risk.required_confirmation,
            immediate_actions=immediate_actions,
            forbidden_actions=sop_record["forbidden_actions"],
            evacuation_guidance=sop_record["evacuation_guidance"],
            source_documents=sop_record["source_documents"],
            human_review_required=(
                risk.required_confirmation or sop_record["human_review_required"]
            ),
        )

    def _conflict_plan(self, sop_record: dict[str, Any]) -> ResponsePlan:
        return ResponsePlan(
            status="conflict_detected",
            required_confirmation=True,
            immediate_actions=[
                "Evidence conflict detected; require human verification before using this recommendation.",
                "Treat the incident conservatively until authorized safety personnel resolve the conflict.",
                "Alert authorized site safety personnel and share both the text claim and detected hazardous evidence.",
            ],
            forbidden_actions=sop_record["forbidden_actions"],
            evacuation_guidance=sop_record["evacuation_guidance"],
            source_documents=sop_record["source_documents"],
            human_review_required=True,
        )

    def _risk_statement(self, risk: RiskAssessment, sop_record: dict[str, Any]) -> str:
        hazard_name = sop_record["name"]
        if risk.level == RiskLevel.high:
            return f"HIGH risk response for {hazard_name}; human approval is required before critical action."
        return f"{risk.level.value} risk response for {hazard_name}; follow site safety review procedures."

    def _request_text(self, request: AnalyzeIncidentRequest) -> str:
        return " ".join(
            value
            for value in (request.description, request.transcript, request.demo_case)
            if value
        )

    def _hazard_evidence_text(
        self,
        observation: ObservationResult,
        sop_record: dict[str, Any],
    ) -> str:
        evidence_parts = [
            *observation.detected_un_codes,
            *observation.detected_keywords,
            *observation.evidence.un_codes,
            *observation.evidence.hazard_keywords,
            *observation.evidence.hazard_symbols,
            sop_record["name"],
            sop_record["hazard_class"],
        ]
        return " ".join(evidence_parts).lower()
