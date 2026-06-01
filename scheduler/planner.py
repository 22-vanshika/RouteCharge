from typing import List, Set, Tuple

from scheduler.models import Bus, Direction, Route, Scenario, Station


def _ordered_stops(route: Route, direction: Direction) -> List[Tuple[str, float]]:
    """Build (station_id, cumulative_km_from_origin) for each stop in travel order."""
    if direction == Direction.BENGALURU_TO_KOCHI:
        ordered = route.stops
        # Each stop's distance_from_previous_km is the segment leading into it.
        segment_dists = [s.distance_from_previous_km for s in ordered[1:]]
    else:
        ordered = list(reversed(route.stops))
        # In reverse traversal, the segment from ordered[i] to ordered[i+1]
        # equals the original distance_from_previous_km of ordered[i] (the "leaving" stop).
        segment_dists = [s.distance_from_previous_km for s in ordered[:-1]]

    result: List[Tuple[str, float]] = [(ordered[0].station_id, 0.0)]
    cumulative = 0.0
    for station_id, dist in zip((s.station_id for s in ordered[1:]), segment_dists):
        cumulative += dist
        result.append((station_id, cumulative))
    return result


def _valid_station_ids(stations: List[Station]) -> Set[str]:
    return {station.id for station in stations}


def _greedy_select(
    ordered_stops: List[Tuple[str, float]],
    valid_ids: Set[str],
    battery_range_km: float,
    bus_id: str,
) -> List[str]:
    destination_km = ordered_stops[-1][1]
    current_km = 0.0
    current_id = ordered_stops[0][0]
    result: List[str] = []

    while destination_km - current_km > battery_range_km:
        reachable = [
            (sid, km) for sid, km in ordered_stops
            if km > current_km and km <= current_km + battery_range_km and sid in valid_ids
        ]
        if not reachable:
            raise ValueError(
                f"Bus '{bus_id}': no reachable charging station within {battery_range_km:.0f} km "
                f"of '{current_id}' — segment exceeds battery range"
            )
        furthest_id, furthest_km = max(reachable, key=lambda x: x[1])
        result.append(furthest_id)
        current_km = furthest_km
        current_id = furthest_id

    return result


def plan_charging_stops(scenario: Scenario, bus: Bus) -> List[str]:
    ordered = _ordered_stops(scenario.route, bus.direction)
    valid_ids = _valid_station_ids(scenario.stations)
    return _greedy_select(
        ordered,
        valid_ids,
        scenario.physical_constants.battery_range_km,
        bus.id,
    )
