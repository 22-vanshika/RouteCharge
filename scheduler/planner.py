from collections import deque
from typing import List, Set, Tuple

from scheduler.models import Bus, Direction, Route, Scenario, Station
from scheduler.utils import cumulative_km_to


def _ordered_stops(route: Route, direction: Direction) -> List[Tuple[str, float]]:
    # Includes endpoint stops — _bfs_select filters to valid charging
    # stations via valid_ids, so non-chargeable endpoints are ignored there.
    origin = route.stops[0] if direction == Direction.BENGALURU_TO_KOCHI else route.stops[-1]
    non_origin = [s for s in route.stops if s.station_id != origin.station_id]
    pairs: List[Tuple[str, float]] = [(origin.station_id, 0.0)] + [
        (s.station_id, cumulative_km_to(route, direction, s.station_id)) for s in non_origin
    ]
    return sorted(pairs, key=lambda x: x[1])


def _valid_station_ids(stations: List[Station]) -> Set[str]:
    return {station.id for station in stations}


def _bfs_select(
    ordered_stops: List[Tuple[str, float]],
    valid_ids: Set[str],
    battery_range_km: float,
    bus_id: str,
) -> List[str]:
    n = len(ordered_stops)
    # queue stores (current_index, path_taken)
    queue = deque([(0, [])])
    visited = {0}

    while queue:
        curr, path = queue.popleft()
        if curr == n - 1:
            return path

        curr_km = ordered_stops[curr][1]
        # Prefer the furthest reachable station when multiple paths of the same stop length exist.
        # This keeps behavior consistent with the original furthest-first heuristic.
        for nxt in range(n - 1, curr, -1):
            nxt_id, nxt_km = ordered_stops[nxt]
            dist = nxt_km - curr_km
            if dist <= battery_range_km:
                if nxt == n - 1 or nxt_id in valid_ids:
                    if nxt not in visited:
                        visited.add(nxt)
                        new_path = path + [nxt_id] if nxt < n - 1 else path
                        queue.append((nxt, new_path))

    raise ValueError(
        f"Bus '{bus_id}': no reachable charging path within {battery_range_km:.0f} km "
        f"— segment exceeds battery range"
    )


def plan_charging_stops(scenario: Scenario, bus: Bus) -> List[str]:
    ordered = _ordered_stops(scenario.route, bus.direction)
    valid_ids = _valid_station_ids(scenario.stations)
    return _bfs_select(
        ordered,
        valid_ids,
        scenario.physical_constants.battery_range_km,
        bus.id,
    )

