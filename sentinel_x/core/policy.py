from sentinel_x.core.config import get_settings
from sentinel_x.core.models import ObservationResult, RiskAssessment, RiskLevel, SafetyGateResult


HIGH_RISK_UN_CODES = {"UN1017", "UN1090", "UN1203"}
HIGH_RISK_SYMBOLS = {"flame", "corrosive"}

FORBIDDEN_ACTION_TERMS = {
    "equipment shutdown": "Equipment shutdown cannot be authorized by Sentinel-X.",
    "shutdown equipment": "Equipment shutdown cannot be authorized by Sentinel-X.",
    "shut down equipment": "Equipment shutdown cannot be authorized by Sentinel-X.",
    "valve operation": "Valve operation cannot be authorized by Sentinel-X.",
    "operate valve": "Valve operation cannot be authorized by Sentinel-X.",
    "open valve": "Valve operation cannot be authorized by Sentinel-X.",
    "close valve": "Valve operation cannot be authorized by Sentinel-X.",
    "physical intervention": "Physical intervention cannot be authorized by Sentinel-X.",
    "chemical handling": "Chemical handling cannot be authorized by Sentinel-X.",
    "handle chemical": "Chemical handling cannot be authorized by Sentinel-X.",
    "handle the chemical": "Chemical handling cannot be authorized by Sentinel-X.",
}


def assess_risk(observation: ObservationResult) -> RiskAssessment:
    settings = get_settings()
    reasons = []
    risk_level = RiskLevel.unknown

    if observation.confidence < settings.confidence_threshold:
        reasons.append("Confidence below threshold; human confirmation required.")

    if observation.unknown_hazard_evidence:
        risk_level = RiskLevel.high
        reasons.append("Unknown hazard evidence is treated as HIGH risk.")

    high_risk_un_codes = [
        un_code for un_code in observation.detected_un_codes if un_code in HIGH_RISK_UN_CODES
    ]
    if high_risk_un_codes:
        risk_level = RiskLevel.high
        reasons.append(
            "Supported high-risk UN code detected: " + ", ".join(high_risk_un_codes)
        )

    high_risk_symbols = [
        symbol
        for symbol in observation.evidence.hazard_symbols
        if symbol in HIGH_RISK_SYMBOLS
    ]
    if high_risk_symbols:
        risk_level = RiskLevel.high
        reasons.append(
            "High-risk hazard symbol detected: " + ", ".join(high_risk_symbols)
        )

    required_confirmation = (
        observation.confidence < settings.confidence_threshold
        or risk_level == RiskLevel.high
        or observation.evidence.conflict_detected
    )

    if required_confirmation and not reasons:
        reasons.append("Human confirmation required by safety policy.")

    return RiskAssessment(
        level=risk_level,
        confidence=observation.confidence,
        required_confirmation=required_confirmation,
        human_confirmation_required=required_confirmation,
        reasons=reasons,
    )


class HumanSafetyGate:
    def review(
        self,
        *,
        risk: RiskAssessment,
        proposed_actions: list[str],
    ) -> SafetyGateResult:
        authorized_actions = []
        blocked_actions = []
        reasons = []

        for action in proposed_actions:
            reason = self._forbidden_reason(action)
            if reason:
                blocked_actions.append(action)
                if reason not in reasons:
                    reasons.append(reason)
            else:
                authorized_actions.append(action)

        approval_required = risk.required_confirmation or bool(blocked_actions)
        if risk.required_confirmation:
            reasons.append("Risk assessment requires human approval.")
        if blocked_actions:
            reasons.append("Forbidden operational actions were blocked.")

        return SafetyGateResult(
            approval_required=approval_required,
            authorized_actions=authorized_actions,
            blocked_actions=blocked_actions,
            reasons=reasons,
        )

    def _forbidden_reason(self, action: str) -> str | None:
        action_lower = action.lower()
        for term, reason in FORBIDDEN_ACTION_TERMS.items():
            if term in action_lower:
                return reason
        return None
