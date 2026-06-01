from typing import Dict, List, Set

from scheduler.models import Bus, BusSchedule, ChargingStop, Scenario, ScenarioSchedule
from scheduler.utils import cumulative_km_to, travel_minutes
from scheduler.planner import plan_charging_stops
from scheduler.resolver import resolve_station
from scheduler.rules import DEFAULT_RULES
from scheduler.rules.base import SoftRule
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
    # Without depth-first order, KB buses would have their second stop (A)
    # resolved before their first stop (C), producing wrong arrival estimates.
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


def _final_arrival_time(scenario: Scenario, bus: Bus, last_stop: ChargingStop, context = None) -> int:
    last_km = cumulative_km_to(scenario.route, bus.direction, last_stop.station_id, context)
    remaining_km = scenario.route.total_distance_km - last_km
    return last_stop.charge_end_minutes + travel_minutes(remaining_km, scenario.physical_constants.speed_kmh)


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


def _build_partial_context(
    buses: List[Bus],
    bus_stop_map: Dict[str, List[ChargingStop]],
) -> List[BusSchedule]:
    return [
        # arrival_time_minutes=0 is a safe placeholder — only charging_stops is
        # read from partial schedules during resolution; the real value is written
        # by the engine after all stations are processed.
        BusSchedule(bus_id=bus.id, charging_stops=bus_stop_map[bus.id], arrival_time_minutes=0)
        for bus in buses
        if bus_stop_map[bus.id]
    ]


def _build_scheduling_context(scenario: Scenario) -> 'SchedulingContext':
    from scheduler.models import Direction, SchedulingContext
    bus_by_id = {b.id: b for b in scenario.buses}
    op_by_bus = {b.id: b.operator.name for b in scenario.buses}
    station_distances = {}
    for direction in Direction:
        if direction == Direction.BENGALURU_TO_KOCHI:
            ordered = scenario.route.stops
            segment_dists = [s.distance_from_previous_km for s in ordered[1:]]
        else:
            ordered = list(reversed(scenario.route.stops))
            segment_dists = [s.distance_from_previous_km for s in ordered[:-1]]

        cumulative = 0.0
        station_distances[(direction, ordered[0].station_id)] = 0.0
        for stop, dist in zip(ordered[1:], segment_dists):
            cumulative += dist
            station_distances[(direction, stop.station_id)] = cumulative
            
    return SchedulingContext(
        bus_by_id=bus_by_id,
        op_by_bus=op_by_bus,
        station_distances=station_distances
    )


def run(scenario: Scenario) -> ScenarioSchedule:
    validate_scenario(scenario)
    context = _build_scheduling_context(scenario)
    rules: List[SoftRule] = list(DEFAULT_RULES)

    bus_plans: Dict[str, List[str]] = {
        bus.id: plan_charging_stops(scenario, bus, context) for bus in scenario.buses
    }
    station_groups = _station_bus_groups(bus_plans)
    processing_order = _station_processing_order(scenario, bus_plans)

    scheduled_so_far: List[BusSchedule] = []
    bus_stop_map: Dict[str, List[ChargingStop]] = {bus.id: [] for bus in scenario.buses}

    for station_id in processing_order:
        pairs = resolve_station(
            scenario, station_id, station_groups[station_id], rules, scheduled_so_far, context
        )
        for bus_id, stop in pairs:
            bus_stop_map[bus_id].append(stop)
        scheduled_so_far = _build_partial_context(scenario.buses, bus_stop_map)

    final_arrivals: Dict[str, int] = {
        bus.id: _final_arrival_time(scenario, bus, bus_stop_map[bus.id][-1], context)
        for bus in scenario.buses
    }
    bus_schedules = _assemble_bus_schedules(scenario, bus_stop_map, final_arrivals)
    schedule = ScenarioSchedule(scenario_id=scenario.id, bus_schedules=bus_schedules)
    validate_schedule(scenario, schedule)
    return schedule

