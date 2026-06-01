from typing import Dict, List, Set, Tuple

from scheduler.models import (
    Bus,
    ChargingStop,
    Direction,
    PhysicalConstants,
    Route,
    Scenario,
    ScenarioSchedule,
    Station,
)


# ─── scenario input validators ────────────────────────────────────────────────

def _check_physical_constants(pc: PhysicalConstants) -> None:
    if pc.battery_range_km <= 0:
        raise ValueError(f"battery_range_km={pc.battery_range_km}: must be > 0")
    if pc.charge_time_minutes <= 0:
        raise ValueError(f"charge_time_minutes={pc.charge_time_minutes}: must be > 0")
    if pc.speed_kmh <= 0:
        raise ValueError(f"speed_kmh={pc.speed_kmh}: must be > 0")


def _check_bus_departure_times(buses: List[Bus]) -> None:
    for bus in buses:
        if bus.departure_time_minutes < 0:
            raise ValueError(
                f"Bus '{bus.id}': departure_time_minutes={bus.departure_time_minutes} must be >= 0"
            )


def _check_station_chargers(stations: List[Station]) -> None:
    for station in stations:
        if station.num_chargers < 1:
            raise ValueError(
                f"Station '{station.id}': num_chargers={station.num_chargers} must be >= 1"
            )


def _check_route(route: Route, stations: List[Station], battery_range_km: float) -> None:
    if len(route.stops) < 2:
        raise ValueError(f"Route has {len(route.stops)} stop(s): must have at least 2")
    for stop in route.stops:
        if stop.distance_from_previous_km < 0:
            raise ValueError(
                f"Route stop '{stop.station_id}': distance_from_previous_km="
                f"{stop.distance_from_previous_km} must not be negative"
            )
    if route.total_distance_km > battery_range_km and not stations:
        raise ValueError(
            f"Route total {route.total_distance_km} km exceeds battery_range_km={battery_range_km} km "
            f"with no scheduling stations — trip is impossible"
        )


def _check_duplicate_bus_ids(buses: List[Bus]) -> None:
    seen: Set[str] = set()
    for bus in buses:
        if bus.id in seen:
            raise ValueError(f"Duplicate bus id '{bus.id}'")
        seen.add(bus.id)


def _check_duplicate_station_ids(stations: List[Station]) -> None:
    seen: Set[str] = set()
    for station in stations:
        if station.id in seen:
            raise ValueError(f"Duplicate station id '{station.id}'")
        seen.add(station.id)


def validate_scenario(scenario: Scenario) -> None:
    _check_physical_constants(scenario.physical_constants)
    _check_bus_departure_times(scenario.buses)
    _check_station_chargers(scenario.stations)
    _check_route(
        scenario.route,
        scenario.stations,
        scenario.physical_constants.battery_range_km,
    )
    _check_duplicate_bus_ids(scenario.buses)
    _check_duplicate_station_ids(scenario.stations)


# ─── schedule output validators ───────────────────────────────────────────────

def _check_all_buses_scheduled(buses: List[Bus], schedule: ScenarioSchedule) -> None:
    expected: Set[str] = {bus.id for bus in buses}
    seen: Dict[str, int] = {}
    for bs in schedule.bus_schedules:
        seen[bs.bus_id] = seen.get(bs.bus_id, 0) + 1

    missing = expected - set(seen)
    if missing:
        raise ValueError(f"Buses missing from schedule: {sorted(missing)}")
    duplicates = {bid for bid, n in seen.items() if n > 1}
    if duplicates:
        raise ValueError(f"Buses scheduled more than once: {sorted(duplicates)}")
    extra = set(seen) - expected
    if extra:
        raise ValueError(f"Schedule contains unknown bus ids: {sorted(extra)}")


def _check_charge_durations(schedule: ScenarioSchedule, charge_time_minutes: int) -> None:
    for bs in schedule.bus_schedules:
        for stop in bs.charging_stops:
            duration = stop.charge_end_minutes - stop.charge_start_minutes
            if duration != charge_time_minutes:
                raise ValueError(
                    f"Bus '{bs.bus_id}' at station '{stop.station_id}': "
                    f"charge duration={duration} min, expected {charge_time_minutes} min"
                )


def _build_travel_segments(
    departure: int,
    arrival: int,
    stops: List[ChargingStop],
) -> List[Tuple[int, int, str]]:
    if not stops:
        return [(departure, arrival, "departure→arrival")]
    segments: List[Tuple[int, int, str]] = [
        (departure, stops[0].arrival_time_minutes, f"departure→{stops[0].station_id}")
    ]
    for i in range(len(stops) - 1):
        segments.append((
            stops[i].charge_end_minutes,
            stops[i + 1].arrival_time_minutes,
            f"{stops[i].station_id}→{stops[i + 1].station_id}",
        ))
    segments.append((stops[-1].charge_end_minutes, arrival, f"{stops[-1].station_id}→arrival"))
    return segments


def _check_range_rule(scenario: Scenario, schedule: ScenarioSchedule) -> None:
    pc = scenario.physical_constants
    bus_by_id: Dict[str, Bus] = {bus.id: bus for bus in scenario.buses}

    for bs in schedule.bus_schedules:
        bus = bus_by_id[bs.bus_id]
        segments = _build_travel_segments(
            bus.departure_time_minutes, bs.arrival_time_minutes, bs.charging_stops
        )
        for start_t, end_t, label in segments:
            distance = (end_t - start_t) / 60.0 * pc.speed_kmh
            if distance > pc.battery_range_km:
                raise ValueError(
                    f"Bus '{bs.bus_id}': range violation on '{label}' — "
                    f"distance={distance:.1f} km exceeds battery_range_km={pc.battery_range_km} km"
                )


def _check_station_order(scenario: Scenario, schedule: ScenarioSchedule) -> None:
    station_pos: Dict[str, int] = {
        stop.station_id: i for i, stop in enumerate(scenario.route.stops)
    }
    bus_by_id: Dict[str, Bus] = {bus.id: bus for bus in scenario.buses}

    for bs in schedule.bus_schedules:
        bus = bus_by_id[bs.bus_id]
        stops = bs.charging_stops
        if len(stops) < 2:
            continue
        is_forward = bus.direction == Direction.BENGALURU_TO_KOCHI
        for i in range(len(stops) - 1):
            cur_id, nxt_id = stops[i].station_id, stops[i + 1].station_id
            cur_pos, nxt_pos = station_pos.get(cur_id, -1), station_pos.get(nxt_id, -1)
            violation = (is_forward and cur_pos >= nxt_pos) or (not is_forward and cur_pos <= nxt_pos)
            if violation:
                raise ValueError(
                    f"Bus '{bs.bus_id}' ({bus.direction.value}): station order violation — "
                    f"'{cur_id}' visited before '{nxt_id}'"
                )


def _check_no_charger_overlap(scenario: Scenario, schedule: ScenarioSchedule) -> None:
    # Build a lookup for station num_chargers to support concurrent charging
    charger_limits = {station.id: max(1, station.num_chargers) for station in scenario.stations}

    intervals: Dict[str, List[Tuple[int, int, str]]] = {}
    for bs in schedule.bus_schedules:
        for stop in bs.charging_stops:
            intervals.setdefault(stop.station_id, []).append(
                (stop.charge_start_minutes, stop.charge_end_minutes, bs.bus_id)
            )

    for station_id, slots in intervals.items():
        limit = charger_limits.get(station_id, 1)
        # Create events: (time, event_type, bus_id)
        # We sort end (-1) before start (+1) at the same minute to allow seamless charger handovers
        events: List[Tuple[int, int, str]] = []
        for start, end, bus_id in slots:
            events.append((start, 1, bus_id))
            events.append((end, -1, bus_id))

        events.sort(key=lambda x: (x[0], x[1]))

        active_buses = set()
        for time, ev_type, bus_id in events:
            if ev_type == 1:
                active_buses.add(bus_id)
                if len(active_buses) > limit:
                    raise ValueError(
                        f"Station '{station_id}': charger overlap — "
                        f"number of concurrent buses charging ({len(active_buses)}) "
                        f"exceeds limit ({limit}) at minute {time}. "
                        f"Buses involved: {sorted(active_buses)}"
                    )
            else:
                active_buses.discard(bus_id)


def validate_schedule(scenario: Scenario, schedule: ScenarioSchedule) -> None:
    _check_all_buses_scheduled(scenario.buses, schedule)
    _check_charge_durations(schedule, scenario.physical_constants.charge_time_minutes)
    _check_station_order(scenario, schedule)
    _check_range_rule(scenario, schedule)
    _check_no_charger_overlap(scenario, schedule)

