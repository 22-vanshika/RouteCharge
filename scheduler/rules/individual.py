from scheduler.models import Direction, Route, Scenario
from scheduler.rules.base import ChargingCandidate, SoftRule


def _cumulative_km_to(route: Route, direction: Direction, target_id: str) -> float:
    """Returns cumulative km from the bus's origin to target_id in its travel order."""
    if direction == Direction.BENGALURU_TO_KOCHI:
        ordered = route.stops
        segment_dists = [s.distance_from_previous_km for s in ordered[1:]]
    else:
        ordered = list(reversed(route.stops))
        # In reverse traversal, segment from ordered[i] to ordered[i+1]
        # equals ordered[i].distance_from_previous_km (the leaving stop's original field).
        segment_dists = [s.distance_from_previous_km for s in ordered[:-1]]

    cumulative = 0.0
    for stop, dist in zip(ordered[1:], segment_dists):
        cumulative += dist
        if stop.station_id == target_id:
            return cumulative
    raise ValueError(f"Station '{target_id}' not found in route for direction {direction.value}")


def _expected_arrival(scenario: Scenario, candidate: ChargingCandidate) -> int:
    """Returns the earliest a bus can arrive at the candidate station (minutes since midnight)."""
    bus = next(b for b in scenario.buses if b.id == candidate.bus_id)
    target_km = _cumulative_km_to(scenario.route, bus.direction, candidate.station_id)

    prior = next((bs for bs in candidate.scheduled_so_far if bs.bus_id == candidate.bus_id), None)
    if prior and prior.charging_stops:
        last = prior.charging_stops[-1]
        last_km = _cumulative_km_to(scenario.route, bus.direction, last.station_id)
        travel_min = (target_km - last_km) / scenario.physical_constants.speed_kmh * 60.0
        return last.charge_end_minutes + int(travel_min)

    travel_min = target_km / scenario.physical_constants.speed_kmh * 60.0
    return bus.departure_time_minutes + int(travel_min)


class IndividualWaitRule(SoftRule):
    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        arrival = _expected_arrival(scenario, candidate)
        wait = candidate.charge_start_minutes - arrival
        return float(max(0, wait))
