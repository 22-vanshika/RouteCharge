from typing import List, Set, Tuple

from scheduler.models import Bus, Direction, Route, Scenario, Station
from scheduler.utils import cumulative_km_to


def _ordered_stops(route: Route, direction: Direction) -> List[Tuple[str, float]]:
    origin = route.stops[0] if direction == Direction.BENGALURU_TO_KOCHI else route.stops[-1]
    non_origin = [s for s in route.stops if s.station_id != origin.station_id]
    pairs: List[Tuple[str, float]] = [(origin.station_id, 0.0)] + [
        (s.station_id, cumulative_km_to(route, direction, s.station_id)) for s in non_origin
    ]
    return sorted(pairs, key=lambda x: x[1])


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
