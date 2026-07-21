import unittest

from sentinel_x.agents.observer import ObserverAgent
from sentinel_x.core.models import AnalyzeIncidentRequest


class ObserverAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.observer = ObserverAgent()

    def test_detects_un1090(self) -> None:
        result = self.observer.observe(
            AnalyzeIncidentRequest(
                description="There is a leaking container marked UN1090"
            )
        )

        self.assertEqual("UN1090", result.possible_un_code)
        self.assertIn("UN1090", result.detected_un_codes)
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_strange_smell_is_unknown_hazard_evidence(self) -> None:
        result = self.observer.observe(
            AnalyzeIncidentRequest(description="I smell something strange")
        )

        self.assertIsNone(result.possible_un_code)
        self.assertTrue(result.unknown_hazard_evidence)
        self.assertIn("smell", result.detected_keywords)
        self.assertLess(result.confidence, 0.85)


if __name__ == "__main__":
    unittest.main()
