import re

from sentinel_x.core.models import AnalyzeIncidentRequest, Evidence, ObservationResult


KNOWN_UN_CODES = ("UN1090", "UN1203", "UN1017")

KEYWORDS = (
    "strange odor",
    "unknown container",
    "unlabeled",
    "corrosive",
    "flame",
    "fire",
    "smell",
)

UNKNOWN_HAZARD_KEYWORDS = {
    "smell",
    "strange odor",
    "unknown container",
    "unlabeled",
}


class ObserverAgent:
    def observe(self, request: AnalyzeIncidentRequest) -> ObservationResult:
        text = self._combine_text(request)
        detected_un_codes = self._detect_un_codes(text)
        detected_keywords = self._detect_keywords(text)
        unknown_hazard_evidence = any(
            keyword in UNKNOWN_HAZARD_KEYWORDS for keyword in detected_keywords
        )

        possible_un_code = detected_un_codes[0] if len(detected_un_codes) == 1 else None
        confidence = self._confidence(detected_un_codes, detected_keywords)

        notes = []
        if not detected_un_codes:
            notes.append("No supported UN code detected.")
        if unknown_hazard_evidence:
            notes.append("Unknown hazard evidence detected; identity remains unknown.")
        if len(detected_un_codes) > 1:
            notes.append("Multiple supported UN codes detected; human verification required.")

        return ObservationResult(
            possible_un_code=possible_un_code,
            detected_un_codes=detected_un_codes,
            detected_keywords=detected_keywords,
            unknown_hazard_evidence=unknown_hazard_evidence,
            confidence=confidence,
            evidence=Evidence(
                un_codes=detected_un_codes,
                hazard_keywords=detected_keywords,
                hazard_symbols=[
                    keyword
                    for keyword in detected_keywords
                    if keyword in {"flame", "corrosive"}
                ],
                notes=notes,
            ),
        )

    def _combine_text(self, request: AnalyzeIncidentRequest) -> str:
        return " ".join(
            value
            for value in (request.description, request.transcript, request.demo_case)
            if value
        )

    def _detect_un_codes(self, text: str) -> list[str]:
        detected = []
        for un_code in KNOWN_UN_CODES:
            pattern = rf"\b{un_code[:2]}\s?{un_code[2:]}\b"
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(un_code)
        return detected

    def _detect_keywords(self, text: str) -> list[str]:
        text_lower = text.lower()
        detected = []
        for keyword in KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                detected.append(keyword)
        return detected

    def _confidence(self, detected_un_codes: list[str], detected_keywords: list[str]) -> float:
        if len(detected_un_codes) == 1:
            return 0.9
        if len(detected_un_codes) > 1:
            return 0.7
        if detected_keywords:
            return 0.6
        return 0.2
