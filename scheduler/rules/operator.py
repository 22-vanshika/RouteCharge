from typing import Dict, List, Optional

from scheduler.models import BusSchedule, ChargingCandidate, Scenario
from scheduler.rules.base import SoftRule
from scheduler.utils import expected_arrival


def _avg_operator_wait(
    op_by_bus: Dict[str, str],
    scheduled_so_far: List[BusSchedule],
    operator_name: str,
) -> Optional[float]:
    """Returns average wait per charging stop for same-operator buses, or None if no peers exist."""
    all_waits = [
        stop.wait_minutes
        for bs in scheduled_so_far
        if op_by_bus.get(bs.bus_id) == operator_name
        for stop in bs.charging_stops
    ]
    return sum(all_waits) / len(all_waits) if all_waits else None


class OperatorFairnessRule(SoftRule):
    name = "OperatorFairnessRule"

    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        # Performance Optimization: Use precomputed indices and averages if available on scenario
        if hasattr(scenario, "_avg_op_waits") and hasattr(scenario, "_op_by_bus"):
            op_by_bus = scenario._op_by_bus
            op_name = op_by_bus.get(candidate.bus_id)
            avg_wait = scenario._avg_op_waits.get(op_name) if op_name else None
        else:
            op_by_bus = {b.id: b.operator.name for b in scenario.buses}
            op_name = op_by_bus[candidate.bus_id]
            avg_wait = _avg_operator_wait(op_by_bus, candidate.scheduled_so_far, op_name)

        if avg_wait is None:
            return 0.0
        arrival = expected_arrival(scenario, candidate)
        candidate_wait = float(max(0, candidate.charge_start_minutes - arrival))
        return float(max(0.0, candidate_wait - avg_wait))

