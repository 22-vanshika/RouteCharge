from typing import Dict, List, Optional

from scheduler.models import BusSchedule, Scenario
from scheduler.rules.base import ChargingCandidate, SoftRule
from scheduler.rules.individual import _expected_arrival


def _get_operator_name(scenario: Scenario, bus_id: str) -> str:
    return next(b.operator.name for b in scenario.buses if b.id == bus_id)


def _avg_operator_wait(
    scenario: Scenario,
    scheduled_so_far: List[BusSchedule],
    operator_name: str,
) -> Optional[float]:
    """Returns average wait per charging stop for same-operator buses, or None if no peers exist."""
    op_by_bus: Dict[str, str] = {b.id: b.operator.name for b in scenario.buses}
    all_waits = [
        stop.wait_minutes
        for bs in scheduled_so_far
        if op_by_bus.get(bs.bus_id) == operator_name
        for stop in bs.charging_stops
    ]
    return sum(all_waits) / len(all_waits) if all_waits else None


class OperatorFairnessRule(SoftRule):
    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        op_name = _get_operator_name(scenario, candidate.bus_id)
        avg_wait = _avg_operator_wait(scenario, candidate.scheduled_so_far, op_name)
        if avg_wait is None:
            return 0.0
        arrival = _expected_arrival(scenario, candidate)
        candidate_wait = float(max(0, candidate.charge_start_minutes - arrival))
        return float(max(0.0, candidate_wait - avg_wait))
