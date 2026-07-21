import unittest

from sentinel_x.agents.response_planner import ResponsePlanner
from sentinel_x.agents.risk_agent import RiskAgent
from sentinel_x.core.models import AnalyzeIncidentRequest, Evidence, ObservationResult, RiskLevel
from sentinel_x.retrieval.retriever import KnowledgeRetriever


class ResponsePlannerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = ResponsePlanner()
        self.risk_agent = RiskAgent()
        self.retriever = KnowledgeRetriever()

    def test_normal_high_risk_response(self) -> None:
        request = AnalyzeIncidentRequest(description="Container marked UN1090 is leaking.")
        observation = ObservationResult(
            possible_un_code="UN1090",
            detected_un_codes=["UN1090"],
            confidence=0.9,
            evidence=Evidence(un_codes=["UN1090"]),
        )
        risk = self.risk_agent.assess(observation)
        retrieval = self.retriever.retrieve(un_codes=observation.detected_un_codes)

        plan = self.planner.plan(
            request=request,
            observation=observation,
            risk=risk,
            sop_record=retrieval.record,
        )

        self.assertEqual("planned", plan.status)
        self.assertEqual(RiskLevel.high, risk.level)
        self.assertTrue(plan.required_confirmation)
        self.assertTrue(plan.human_review_required)
        self.assertIn("HIGH risk response", plan.immediate_actions[0])
        self.assertIn("ERG 2024 Guide 127: Flammable Liquids", plan.source_documents)

    def test_conflict_response(self) -> None:
        request = AnalyzeIncidentRequest(description="The container contains water")
        observation = ObservationResult(
            detected_keywords=["flame"],
            confidence=0.9,
            evidence=Evidence(
                hazard_keywords=["flammable chemical label"],
                hazard_symbols=["flame"],
            ),
        )
        risk = self.risk_agent.assess(observation)
        retrieval = self.retriever.retrieve(hazard_symbols=observation.evidence.hazard_symbols)

        plan = self.planner.plan(
            request=request,
            observation=observation,
            risk=risk,
            sop_record=retrieval.record,
        )

        self.assertEqual("conflict_detected", plan.status)
        self.assertTrue(observation.evidence.conflict_detected)
        self.assertTrue(plan.required_confirmation)
        self.assertTrue(plan.human_review_required)
        self.assertIn("Evidence conflict detected", plan.immediate_actions[0])


if __name__ == "__main__":
    unittest.main()
