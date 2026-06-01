from typing import Dict, List, Tuple

from scheduler.models import BusSchedule, ChargingCandidate, ChargingStop, Scenario
from scheduler.rules.base import SoftRule
from scheduler.utils import expected_arrival
from scheduler.scorer import compute_score


def _arrival_at(
    scenario: Scenario,
    bus_id: str,
    station_id: str,
    scheduled_so_far: List[BusSchedule],
) -> int:
    # charge_start_minutes is not read by expected_arrival; 0 is a safe placeholder.
    temp = ChargingCandidate(
        bus_id=bus_id,
        station_id=station_id,
        charge_start_minutes=0,
        scheduled_so_far=scheduled_so_far,
    )
    return expected_arrival(scenario, temp)


def _select_next(
    scenario: Scenario,
    station_id: str,
    remaining_ids: List[str],
    charger_free_times: List[int],
    rules: List[SoftRule],
    scheduled_so_far: List[BusSchedule],
) -> str:
    # Performance Optimization: Precompute average wait per operator once from scheduled_so_far.
    # This prevents OperatorFairnessRule from performing O(B*S) scans on every scoring calculation.
    op_by_bus = scenario._op_by_bus if hasattr(scenario, "_op_by_bus") else {b.id: b.operator.name for b in scenario.buses}
    op_waits: Dict[str, List[int]] = {}
    for bs in scheduled_so_far:
        op = op_by_bus.get(bs.bus_id)
        if op:
            for stop in bs.charging_stops:
                op_waits.setdefault(op, []).append(stop.wait_minutes)
                
    scenario._avg_op_waits = {
        op: sum(waits) / len(waits) for op, waits in op_waits.items()
    }

    def _rank(bus_id: str) -> Tuple[float, int, str]:
        arrival = _arrival_at(scenario, bus_id, station_id, scheduled_so_far)
        # Select earliest available charger
        earliest_charger_free = min(charger_free_times)
        charge_start = max(arrival, earliest_charger_free)
        candidate = ChargingCandidate(bus_id, station_id, charge_start, scheduled_so_far)
        score = compute_score(scenario, candidate, rules, scenario.weights)
        return (score, arrival, bus_id)

    res = min(remaining_ids, key=_rank)

    # Clean up temporary lookup to avoid namespace pollution
    if hasattr(scenario, "_avg_op_waits"):
        del scenario._avg_op_waits

    return res


def _update_context(
    scheduled_so_far: List[BusSchedule],
    bus_id: str,
    new_stop: ChargingStop,
) -> List[BusSchedule]:
    existing = next((bs for bs in scheduled_so_far if bs.bus_id == bus_id), None)
    if existing:
        updated = BusSchedule(
            bus_id=bus_id,
            charging_stops=existing.charging_stops + [new_stop],
            arrival_time_minutes=existing.arrival_time_minutes,
        )
        return [updated if bs.bus_id == bus_id else bs for bs in scheduled_so_far]
    # arrival_time_minutes=0 is a safe placeholder — only charging_stops is
    # read from partial schedules during resolution; the real value is written
    # by the engine after all stations are processed.
    return scheduled_so_far + [BusSchedule(bus_id=bus_id, charging_stops=[new_stop], arrival_time_minutes=0)]


def resolve_station(
    scenario: Scenario,
    station_id: str,
    bus_ids: List[str],
    rules: List[SoftRule],
    scheduled_so_far: List[BusSchedule],
) -> List[Tuple[str, ChargingStop]]:
    # Dynamic Charger Resolution: Lookup actual station count to support concurrent charging
    station = next(s for s in scenario.stations if s.id == station_id)
    num_chargers = max(1, station.num_chargers)

    remaining = list(bus_ids)
    charger_free_times = [0] * num_chargers
    context = list(scheduled_so_far)
    result: List[Tuple[str, ChargingStop]] = []

    while remaining:
        bus_id = _select_next(scenario, station_id, remaining, charger_free_times, rules, context)
        arrival = _arrival_at(scenario, bus_id, station_id, context)
        
        # Chronological Greedy charger assignment: assign the bus to the charger that becomes free earliest
        earliest_charger_idx = min(range(num_chargers), key=lambda idx: charger_free_times[idx])
        earliest_charger_free = charger_free_times[earliest_charger_idx]
        
        charge_start = max(arrival, earliest_charger_free)
        charge_end = charge_start + scenario.physical_constants.charge_time_minutes
        
        stop = ChargingStop(
            station_id=station_id,
            arrival_time_minutes=arrival,
            charge_start_minutes=charge_start,
            charge_end_minutes=charge_end,
        )
        result.append((bus_id, stop))
        context = _update_context(context, bus_id, stop)
        
        # Update specific charger's timeline
        charger_free_times[earliest_charger_idx] = charge_end
        remaining.remove(bus_id)

    # Sort chronological results to ensure presentation order is clean
    result.sort(key=lambda x: x[1].charge_start_minutes)
    return result

