import json

import pytest
from fastapi.testclient import TestClient

import sentinel_x.main as main
from sentinel_x.agents.response_planner import ResponsePlanner
from sentinel_x.agents.risk_agent import RiskAgent
from sentinel_x.core.memory import AuditMemory
from sentinel_x.core.models import AnalyzeIncidentRequest, Evidence, ObservationResult
from sentinel_x.retrieval.retriever import KnowledgeRetriever


@pytest.fixture
def retriever() -> KnowledgeRetriever:
    return KnowledgeRetriever()


@pytest.fixture
def planner_stack() -> tuple[ResponsePlanner, RiskAgent, KnowledgeRetriever]:
    return ResponsePlanner(), RiskAgent(), KnowledgeRetriever()


@pytest.fixture
def isolated_audit_log(tmp_path, monkeypatch):
    log_path = tmp_path / "logs" / "incidents.json"
    monkeypatch.setattr(main, "audit_memory", AuditMemory(log_path))
    return log_path


def test_un1090_retrieval_priority_1(retriever):
    result = retriever.retrieve(text="Leaking container marked UN1090.")
    assert (result.match_type, result.filename, result.record["name"]) == (
        "un_code",
        "UN1090_acetone.json",
        "Acetone",
    )


def test_flame_symbol_retrieval_priority_2(retriever):
    result = retriever.retrieve(text="A flame symbol is visible.")
    assert (result.match_type, result.filename, result.record["name"]) == (
        "hazard_symbol",
        "CLASS_3_FLAMMABLE.json",
        "Class 3 Flammable Liquid",
    )


def test_unknown_hazard_fallback_priority_3(retriever):
    result = retriever.retrieve(text="Unclear residue near storage.")
    assert (result.match_type, result.filename, result.record["name"]) == (
        "unknown_fallback",
        "UNKNOWN_HAZARD.json",
        "Unknown Hazard",
    )


def test_evidence_conflict_detection(planner_stack):
    planner, risk_agent, retriever = planner_stack
    request = AnalyzeIncidentRequest(description="The container contains water")
    observation = ObservationResult(
        detected_keywords=["flame"],
        confidence=0.9,
        evidence=Evidence(
            hazard_keywords=["flammable chemical label"],
            hazard_symbols=["flame"],
        ),
    )
    plan = planner.plan(
        request=request,
        observation=observation,
        risk=risk_agent.assess(observation),
        sop_record=retriever.retrieve(hazard_symbols=["flame"]).record,
    )
    assert plan.status == "conflict_detected"
    assert plan.required_confirmation is True
    assert observation.evidence.conflict_detected is True


def test_audit_log_creation(isolated_audit_log):
    response = TestClient(main.app).post(
        "/analyze_incident",
        json={"description": "There is a leaking container marked UN1090"},
    )
    records = json.loads(isolated_audit_log.read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert isolated_audit_log.exists()
    assert len(records) == 1
    assert records[0]["incident_id"] == response.json()["incident_id"]
    assert records[0]["evidence"]["un_codes"] == ["UN1090"]
    assert records[0]["risk"]["level"] == "HIGH"
    assert records[0]["response_plan"]["status"] == "planned"
