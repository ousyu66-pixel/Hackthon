from sentinel_x.core.models import ObservationResult, RiskAssessment
from sentinel_x.core.policy import assess_risk


class RiskAgent:
    def assess(self, observation: ObservationResult) -> RiskAssessment:
        return assess_risk(observation)
