import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentinel_x.core.config import get_settings
from sentinel_x.retrieval.knowledge_base import KnowledgeBase


UN_CODE_TO_FILE = {
    "UN1090": "UN1090_acetone.json",
    "UN1203": "UN1203_gasoline.json",
    "UN1017": "UN1017_chlorine.json",
}

HAZARD_SYMBOL_TO_FILE = {
    "flame": "CLASS_3_FLAMMABLE.json",
    "corrosive": "CLASS_8_CORROSIVE.json",
}

UNKNOWN_HAZARD_FILE = "UNKNOWN_HAZARD.json"


@dataclass(frozen=True)
class RetrievalResult:
    match_type: str
    matched_key: str
    filename: str
    record: dict[str, Any]


class KnowledgeRetriever:
    def __init__(self, knowledge_base: KnowledgeBase | None = None) -> None:
        settings = get_settings()
        self.knowledge_base = knowledge_base or KnowledgeBase(Path(settings.knowledge_dir))

    def retrieve(
        self,
        *,
        un_codes: list[str] | None = None,
        hazard_symbols: list[str] | None = None,
        text: str = "",
    ) -> RetrievalResult:
        normalized_un_codes = self._extract_un_codes(un_codes or [], text)
        for un_code in normalized_un_codes:
            filename = UN_CODE_TO_FILE.get(un_code)
            if filename:
                return self._result("un_code", un_code, filename)

        normalized_symbols = self._extract_hazard_symbols(hazard_symbols or [], text)
        for symbol in normalized_symbols:
            filename = HAZARD_SYMBOL_TO_FILE.get(symbol)
            if filename:
                return self._result("hazard_symbol", symbol, filename)

        return self._result("unknown_fallback", "UNKNOWN_HAZARD", UNKNOWN_HAZARD_FILE)

    def _result(self, match_type: str, matched_key: str, filename: str) -> RetrievalResult:
        return RetrievalResult(
            match_type=match_type,
            matched_key=matched_key,
            filename=filename,
            record=self.knowledge_base.load(filename),
        )

    def _extract_un_codes(self, un_codes: list[str], text: str) -> list[str]:
        detected = [self._normalize_un_code(un_code) for un_code in un_codes]
        detected.extend(match.upper() for match in re.findall(r"\bUN\s?\d{4}\b", text, re.IGNORECASE))
        return self._unique([un_code for un_code in detected if un_code])

    def _extract_hazard_symbols(self, hazard_symbols: list[str], text: str) -> list[str]:
        candidates = [symbol.lower().strip() for symbol in hazard_symbols]
        text_lower = text.lower()
        candidates.extend(
            symbol for symbol in HAZARD_SYMBOL_TO_FILE if re.search(rf"\b{re.escape(symbol)}\b", text_lower)
        )
        return self._unique([symbol for symbol in candidates if symbol])

    def _normalize_un_code(self, value: str) -> str | None:
        match = re.search(r"\bUN\s?(\d{4})\b", value, re.IGNORECASE)
        if not match:
            return None
        return f"UN{match.group(1)}"

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        unique_values = []
        for value in values:
            if value not in seen:
                seen.add(value)
                unique_values.append(value)
        return unique_values
