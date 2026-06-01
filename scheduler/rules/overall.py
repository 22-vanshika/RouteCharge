from scheduler.models import ChargingCandidate, Scenario
from scheduler.rules.base import SoftRule
from scheduler.utils import expected_arrival


class OverallNetworkRule(SoftRule):
    name = "OverallNetworkRule"

    def score(self, scenario: Scenario, candidate: ChargingCandidate, context = None) -> float:
        earliest = expected_arrival(scenario, candidate, context)
        delay = candidate.charge_start_minutes - earliest
        return float(max(0.0, delay))

