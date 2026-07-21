import json
import unittest
from pathlib import Path


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "sentinel_x" / "knowledge"

EXPECTED_FILES = {
    "UN1090_acetone.json",
    "UN1203_gasoline.json",
    "UN1017_chlorine.json",
    "CLASS_3_FLAMMABLE.json",
    "CLASS_8_CORROSIVE.json",
    "UNKNOWN_HAZARD.json",
}

REQUIRED_FIELDS = {
    "name",
    "hazard_class",
    "immediate_actions",
    "forbidden_actions",
    "evacuation_guidance",
    "source_documents",
    "human_review_required",
}

FORBIDDEN_OPERATION_TERMS = {
    "sentinel-x may shut down",
    "sentinel-x can shut down",
    "sentinel-x may operate",
    "sentinel-x can operate",
    "open the valve",
    "close the valve",
    "handle the chemical",
}


def load_knowledge_records() -> dict[str, dict]:
    records = {}
    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as file:
            records[path.name] = json.load(file)
    return records


class KnowledgeFileTest(unittest.TestCase):
    def test_expected_files_exist(self) -> None:
        actual_files = {path.name for path in KNOWLEDGE_DIR.glob("*.json")}
        self.assertEqual(EXPECTED_FILES, actual_files)

    def test_records_load_with_required_schema(self) -> None:
        records = load_knowledge_records()

        for filename, record in records.items():
            with self.subTest(filename=filename):
                self.assertEqual(REQUIRED_FIELDS, set(record))
                self.assertIsInstance(record["name"], str)
                self.assertIsInstance(record["hazard_class"], str)
                self.assertIsInstance(record["immediate_actions"], list)
                self.assertIsInstance(record["forbidden_actions"], list)
                self.assertIsInstance(record["evacuation_guidance"], str)
                self.assertIsInstance(record["source_documents"], list)
                self.assertIs(record["human_review_required"], True)
                self.assertGreater(len(record["immediate_actions"]), 0)
                self.assertGreater(len(record["forbidden_actions"]), 0)
                self.assertGreater(len(record["source_documents"]), 0)

    def test_unknown_hazard_is_most_conservative(self) -> None:
        unknown = load_knowledge_records()["UNKNOWN_HAZARD.json"]
        combined_text = " ".join(
            [
                unknown["hazard_class"],
                *unknown["immediate_actions"],
                *unknown["forbidden_actions"],
                unknown["evacuation_guidance"],
            ]
        ).lower()

        self.assertIn("high risk", combined_text)
        self.assertIn("most conservative", combined_text)
        self.assertIn("human verification", combined_text)

    def test_records_do_not_authorize_dangerous_operations(self) -> None:
        records = load_knowledge_records()

        for filename, record in records.items():
            with self.subTest(filename=filename):
                combined_text = json.dumps(record, ensure_ascii=False).lower()
                for term in FORBIDDEN_OPERATION_TERMS:
                    self.assertNotIn(term, combined_text)
                self.assertIn("do not authorize equipment shutdown", combined_text)
                self.assertIn("do not operate valves", combined_text)


if __name__ == "__main__":
    unittest.main()
