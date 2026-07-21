import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "name",
    "hazard_class",
    "immediate_actions",
    "forbidden_actions",
    "evacuation_guidance",
    "source_documents",
    "human_review_required",
}


class KnowledgeBaseError(RuntimeError):
    """Raised when a knowledge file is missing or malformed."""


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path) -> None:
        self.knowledge_dir = knowledge_dir

    def load(self, filename: str) -> dict[str, Any]:
        path = self.knowledge_dir / filename
        if not path.is_file():
            raise KnowledgeBaseError(f"Knowledge file not found: {filename}")

        with path.open(encoding="utf-8") as file:
            record = json.load(file)

        self._validate_record(filename, record)
        return record

    def _validate_record(self, filename: str, record: object) -> None:
        if not isinstance(record, dict):
            raise KnowledgeBaseError(f"Knowledge file must contain an object: {filename}")

        missing_fields = REQUIRED_FIELDS - set(record)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise KnowledgeBaseError(f"Knowledge file {filename} missing fields: {missing}")
