from scheduler.models import ChargingCandidate, Scenario
from scheduler.utils import expected_arrival
from scheduler.rules.base import SoftRule


class IndividualWaitRule(SoftRule):
    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        arrival = expected_arrival(scenario, candidate)
        wait = candidate.charge_start_minutes - arrival
        return float(max(0, wait))
