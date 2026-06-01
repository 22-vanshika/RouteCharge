from typing import Dict, List, Set, Tuple

from scheduler.models import Bus, BusSchedule, ChargingStop, Scenario, ScenarioSchedule
from scheduler.planner import plan_charging_stops
from scheduler.resolver import resolve_station, _select_next, _update_context
from scheduler.rules import DEFAULT_RULES
from scheduler.rules.base import SoftRule
from scheduler.rules.individual import _cumulative_km_to
from scheduler.validator import validate_scenario, validate_schedule


def _station_bus_groups(bus_plans: Dict[str, List[str]]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for bus_id, plan in bus_plans.items():
        for station_id in plan:
            groups.setdefault(station_id, []).append(bus_id)
    return groups


def _station_processing_order(
    scenario: Scenario,
    bus_plans: Dict[str, List[str]],
) -> List[str]:
    # Process depth-0 stops before depth-1, etc., so each bus's prior stop is always
    # in scheduled_so_far before its next stop is resolved.
    route_pos: Dict[str, int] = {
        stop.station_id: i for i, stop in enumerate(scenario.route.stops)
    }
    depth_map: Dict[int, Set[str]] = {}
    for plan in bus_plans.values():
        for depth, station_id in enumerate(plan):
            depth_map.setdefault(depth, set()).add(station_id)
    result: List[str] = []
    for depth in sorted(depth_map):
        result.extend(sorted(depth_map[depth], key=lambda sid: route_pos.get(sid, 0)))
    return result


def _resolve_station_pairs(
    scenario: Scenario,
    station_id: str,
    bus_ids: List[str],
    rules: List[SoftRule],
    scheduled_so_far: List[BusSchedule],
) -> List[Tuple[str, ChargingStop]]:
    stops = resolve_station(scenario, station_id, bus_ids, rules, scheduled_so_far)
    remaining = list(bus_ids)
    charger_free_at = 0
    context = list(scheduled_so_far)
    pairs: List[Tuple[str, ChargingStop]] = []
    for stop in stops:
        bus_id = _select_next(scenario, station_id, remaining, charger_free_at, rules, context)
        context = _update_context(context, bus_id, stop)
        charger_free_at = stop.charge_end_minutes
        remaining.remove(bus_id)
        pairs.append((bus_id, stop))
    return pairs


def _final_arrival_time(scenario: Scenario, bus: Bus, last_stop: ChargingStop) -> int:
    last_km = _cumulative_km_to(scenario.route, bus.direction, last_stop.station_id)
    remaining_km = scenario.route.total_distance_km - last_km
    travel_min = remaining_km / scenario.physical_constants.speed_kmh * 60.0
    return last_stop.charge_end_minutes + int(travel_min)


def _assemble_bus_schedules(
    scenario: Scenario,
    bus_stop_map: Dict[str, List[ChargingStop]],
    final_arrivals: Dict[str, int],
) -> List[BusSchedule]:
    return [
        BusSchedule(
            bus_id=bus.id,
            charging_stops=bus_stop_map[bus.id],
            arrival_time_minutes=final_arrivals[bus.id],
        )
        for bus in scenario.buses
    ]


def run(scenario: Scenario) -> ScenarioSchedule:
    validate_scenario(scenario)
    rules: List[SoftRule] = list(DEFAULT_RULES)

    bus_plans: Dict[str, List[str]] = {
        bus.id: plan_charging_stops(scenario, bus) for bus in scenario.buses
    }
    station_groups = _station_bus_groups(bus_plans)
    processing_order = _station_processing_order(scenario, bus_plans)

    scheduled_so_far: List[BusSchedule] = []
    bus_stop_map: Dict[str, List[ChargingStop]] = {bus.id: [] for bus in scenario.buses}

    for station_id in processing_order:
        pairs = _resolve_station_pairs(
            scenario, station_id, station_groups[station_id], rules, scheduled_so_far
        )
        for bus_id, stop in pairs:
            bus_stop_map[bus_id].append(stop)
            scheduled_so_far = _update_context(scheduled_so_far, bus_id, stop)

    final_arrivals: Dict[str, int] = {
        bus.id: _final_arrival_time(scenario, bus, bus_stop_map[bus.id][-1])
        for bus in scenario.buses
    }
    bus_schedules = _assemble_bus_schedules(scenario, bus_stop_map, final_arrivals)
    schedule = ScenarioSchedule(scenario_id=scenario.id, bus_schedules=bus_schedules)
    validate_schedule(scenario, schedule)
    return schedule
