import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import sentinel_x.main as main
from sentinel_x.core.memory import AuditMemory


class AuditMemoryTest(unittest.TestCase):
    def test_analyze_incident_creates_log_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "logs" / "incidents.json"
            original_memory = main.audit_memory
            main.audit_memory = AuditMemory(log_path)

            try:
                client = TestClient(main.app)
                response = client.post(
                    "/analyze_incident",
                    json={
                        "description": "There is a leaking container marked UN1090",
                        "transcript": "",
                        "demo_case": None,
                    },
                )
            finally:
                main.audit_memory = original_memory

            self.assertEqual(200, response.status_code)
            self.assertTrue(log_path.exists())

            with log_path.open(encoding="utf-8") as file:
                records = json.load(file)

            self.assertEqual(1, len(records))
            record = records[0]
            self.assertEqual(response.json()["incident_id"], record["incident_id"])
            self.assertIn("timestamp", record)
            self.assertEqual("There is a leaking container marked UN1090", record["observation"]["description"])
            self.assertEqual(["UN1090"], record["evidence"]["un_codes"])
            self.assertEqual("HIGH", record["risk"]["level"])
            self.assertIn("ERG 2024 Guide 127: Flammable Liquids", record["SOP source"] if "SOP source" in record else record["sop_source"])
            self.assertEqual("planned", record["response_plan"]["status"])
            self.assertEqual("pending", record["approval_status"])


if __name__ == "__main__":
    unittest.main()
