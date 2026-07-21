import json
from pathlib import Path

from sentinel_x.core.config import get_settings
from sentinel_x.core.models import AuditRecord


class AuditMemory:
    def __init__(self, log_path: Path | None = None) -> None:
        settings = get_settings()
        self.log_path = log_path or Path(settings.audit_log_path)

    def append(self, record: AuditRecord) -> None:
        records = self.load_all()
        records.append(record)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("w", encoding="utf-8") as file:
            json.dump(
                [item.model_dump(mode="json") for item in records],
                file,
                indent=2,
            )

    def load_all(self) -> list[AuditRecord]:
        if not self.log_path.exists():
            return []

        with self.log_path.open(encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("Audit log must contain a JSON array.")

        return [AuditRecord.model_validate(item) for item in data]
