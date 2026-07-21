import unittest

from sentinel_x.agents.risk_agent import RiskAgent
from sentinel_x.core.models import Evidence, ObservationResult, RiskLevel
from sentinel_x.core.policy import HumanSafetyGate


class RiskPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.risk_agent = RiskAgent()

    def test_low_confidence_requires_confirmation(self) -> None:
        risk = self.risk_agent.assess(
            ObservationResult(confidence=0.6, evidence=Evidence())
        )

        self.assertTrue(risk.required_confirmation)
        self.assertTrue(risk.human_confirmation_required)
        self.assertIn("Confidence below threshold", " ".join(risk.reasons))

    def test_unknown_hazard_is_high_risk(self) -> None:
        risk = self.risk_agent.assess(
            ObservationResult(
                unknown_hazard_evidence=True,
                confidence=0.6,
                evidence=Evidence(hazard_keywords=["smell"]),
            )
        )

        self.assertEqual(RiskLevel.high, risk.level)
        self.assertTrue(risk.required_confirmation)

    def test_un1017_is_high_risk(self) -> None:
        risk = self.risk_agent.assess(
            ObservationResult(
                possible_un_code="UN1017",
                detected_un_codes=["UN1017"],
                confidence=0.9,
                evidence=Evidence(un_codes=["UN1017"]),
            )
        )

        self.assertEqual(RiskLevel.high, risk.level)
        self.assertTrue(risk.required_confirmation)

    def test_un1090_and_un1203_are_high_risk(self) -> None:
        for un_code in ("UN1090", "UN1203"):
            with self.subTest(un_code=un_code):
                risk = self.risk_agent.assess(
                    ObservationResult(
                        possible_un_code=un_code,
                        detected_un_codes=[un_code],
                        confidence=0.9,
                        evidence=Evidence(un_codes=[un_code]),
                    )
                )

                self.assertEqual(RiskLevel.high, risk.level)
                self.assertTrue(risk.required_confirmation)

    def test_flame_and_corrosive_symbols_are_high_risk(self) -> None:
        for symbol in ("flame", "corrosive"):
            with self.subTest(symbol=symbol):
                risk = self.risk_agent.assess(
                    ObservationResult(
                        detected_keywords=[symbol],
                        confidence=0.9,
                        evidence=Evidence(
                            hazard_keywords=[symbol],
                            hazard_symbols=[symbol],
                        ),
                    )
                )

                self.assertEqual(RiskLevel.high, risk.level)
                self.assertTrue(risk.required_confirmation)

    def test_human_safety_gate_blocks_forbidden_actions(self) -> None:
        risk = self.risk_agent.assess(
            ObservationResult(confidence=0.9, evidence=Evidence())
        )
        gate = HumanSafetyGate()

        result = gate.review(
            risk=risk,
            proposed_actions=[
                "Alert authorized safety personnel.",
                "Perform equipment shutdown.",
                "Open valve 12.",
                "Start physical intervention.",
                "Handle the chemical.",
            ],
        )

        self.assertEqual(["Alert authorized safety personnel."], result.authorized_actions)
        self.assertEqual(4, len(result.blocked_actions))
        self.assertTrue(result.approval_required)


if __name__ == "__main__":
    unittest.main()
