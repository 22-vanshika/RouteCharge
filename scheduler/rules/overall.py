from scheduler.models import Scenario
from scheduler.rules.base import ChargingCandidate, SoftRule
from scheduler.rules.individual import _expected_arrival


class OverallNetworkRule(SoftRule):
    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        earliest = _expected_arrival(scenario, candidate)
        delay = candidate.charge_start_minutes - earliest
        return float(max(0.0, delay))
