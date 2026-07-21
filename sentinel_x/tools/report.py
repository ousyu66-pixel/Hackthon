from sentinel_x.core.models import AnalyzeIncidentResponse, AuditRecord


def audit_record_from_response(response: AnalyzeIncidentResponse) -> AuditRecord:
    return AuditRecord(
        incident_id=response.incident_id,
        timestamp=response.timestamp,
        observation=response.observation,
        evidence=response.evidence,
        risk=response.risk,
        sop_source=response.sop_source,
        response_plan=response.response_plan,
        approval_status=response.approval_status,
    )
