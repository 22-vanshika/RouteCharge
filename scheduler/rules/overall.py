from scheduler.models import ChargingCandidate, Scenario
from scheduler.rules.base import SoftRule
from scheduler.utils import expected_arrival


class OverallNetworkRule(SoftRule):
    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        earliest = expected_arrival(scenario, candidate)
        delay = candidate.charge_start_minutes - earliest
        return float(max(0.0, delay))
