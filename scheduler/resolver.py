from typing import List, Tuple

from scheduler.models import BusSchedule, ChargingStop, Scenario
from scheduler.rules.base import ChargingCandidate, SoftRule
from scheduler.rules.individual import _expected_arrival
from scheduler.scorer import compute_score


def _arrival_at(
    scenario: Scenario,
    bus_id: str,
    station_id: str,
    scheduled_so_far: List[BusSchedule],
) -> int:
    # charge_start_minutes is not read by _expected_arrival; 0 is a safe placeholder.
    temp = ChargingCandidate(
        bus_id=bus_id,
        station_id=station_id,
        charge_start_minutes=0,
        scheduled_so_far=scheduled_so_far,
    )
    return _expected_arrival(scenario, temp)


def _select_next(
    scenario: Scenario,
    station_id: str,
    remaining_ids: List[str],
    charger_free_at: int,
    rules: List[SoftRule],
    scheduled_so_far: List[BusSchedule],
) -> str:
    def _rank(bus_id: str) -> Tuple[float, int, str]:
        arrival = _arrival_at(scenario, bus_id, station_id, scheduled_so_far)
        charge_start = max(arrival, charger_free_at)
        candidate = ChargingCandidate(bus_id, station_id, charge_start, scheduled_so_far)
        score = compute_score(scenario, candidate, rules, scenario.weights)
        return (score, arrival, bus_id)

    return min(remaining_ids, key=_rank)


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
    return scheduled_so_far + [BusSchedule(bus_id=bus_id, charging_stops=[new_stop], arrival_time_minutes=0)]


def resolve_station(
    scenario: Scenario,
    station_id: str,
    bus_ids: List[str],
    rules: List[SoftRule],
    scheduled_so_far: List[BusSchedule],
) -> List[ChargingStop]:
    remaining = list(bus_ids)
    charger_free_at = 0
    context = list(scheduled_so_far)
    result: List[ChargingStop] = []

    while remaining:
        bus_id = _select_next(scenario, station_id, remaining, charger_free_at, rules, context)
        arrival = _arrival_at(scenario, bus_id, station_id, context)
        charge_start = max(arrival, charger_free_at)
        charge_end = charge_start + scenario.physical_constants.charge_time_minutes
        stop = ChargingStop(
            station_id=station_id,
            arrival_time_minutes=arrival,
            charge_start_minutes=charge_start,
            charge_end_minutes=charge_end,
        )
        result.append(stop)
        context = _update_context(context, bus_id, stop)
        charger_free_at = charge_end
        remaining.remove(bus_id)

    return result
