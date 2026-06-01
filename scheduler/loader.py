import json

from scheduler.models import (
    Bus,
    Direction,
    Operator,
    PhysicalConstants,
    Route,
    RouteStop,
    Scenario,
    Station,
    Weights,
)


def _require(data: dict, key: str, context: str) -> object:
    if key not in data:
        raise ValueError(f"Missing required field '{key}' in {context}")
    return data[key]


def _parse_physical_constants(data: dict) -> PhysicalConstants:
    ctx = "physical_constants"
    return PhysicalConstants(
        battery_range_km=float(_require(data, "battery_range_km", ctx)),
        charge_time_minutes=int(_require(data, "charge_time_minutes", ctx)),
        speed_kmh=float(_require(data, "speed_kmh", ctx)),
    )


def _parse_weights(data: dict) -> Weights:
    ctx = "weights"
    legacy_mapping = {
        "individual": "IndividualWaitRule",
        "operator": "OperatorFairnessRule",
        "overall": "OverallNetworkRule",
    }
    
    # Proactive Failure Detection: Dynamically validate weight keys against registered rules
    from scheduler.rules import DEFAULT_RULES
    valid_rule_names = {rule.name for rule in DEFAULT_RULES}
    valid_keys = {"individual", "operator", "overall"}.union(valid_rule_names)

    for key in data:
        if key not in valid_keys:
            raise ValueError(
                f"Unrecognized weight key '{key}' in scenario weights configuration (possible typo). "
                f"Valid keys are: {sorted(list(valid_keys))}"
            )

    values = {}
    for k, v in data.items():
        mapped_key = legacy_mapping.get(k, k)
        values[mapped_key] = float(v)

    # Secure Validation: Every registered rule must have an explicit weight defined in scenario JSON.
    # This prevents runtime KeyErrors or silent fallbacks.
    for name in valid_rule_names:
        if name not in values:
            raise ValueError(
                f"Missing required weight key for registered rule '{name}' in weights configuration."
            )

    return Weights(values=values)





def _parse_route_stop(data: dict, index: int) -> RouteStop:
    ctx = f"route.stops[{index}]"
    return RouteStop(
        station_id=str(_require(data, "station_id", ctx)),
        distance_from_previous_km=float(_require(data, "distance_from_previous_km", ctx)),
    )


def _parse_route(data: dict) -> Route:
    stops_data: list = _require(data, "stops", "route")
    if not stops_data:
        raise ValueError("route.stops must not be empty")
    return Route(stops=[_parse_route_stop(s, i) for i, s in enumerate(stops_data)])


def _parse_station(data: dict, index: int) -> Station:
    ctx = f"stations[{index}]"
    return Station(
        id=str(_require(data, "id", ctx)),
        name=str(_require(data, "name", ctx)),
        num_chargers=int(_require(data, "num_chargers", ctx)),
    )


def _parse_direction(value: str, bus_id: str) -> Direction:
    try:
        return Direction(value)
    except ValueError:
        valid = [d.value for d in Direction]
        raise ValueError(
            f"Bus '{bus_id}': unrecognized direction '{value}'. Valid values: {valid}"
        )


def _parse_bus(data: dict, index: int) -> Bus:
    bus_id = str(_require(data, "id", f"buses[{index}]"))
    ctx = f"bus '{bus_id}'"
    return Bus(
        id=bus_id,
        operator=Operator(name=str(_require(data, "operator", ctx))),
        direction=_parse_direction(str(_require(data, "direction", ctx)), bus_id),
        departure_time_minutes=int(_require(data, "departure_time_minutes", ctx)),
    )


def load_scenario(filepath: str) -> Scenario:
    try:
        with open(filepath, "r") as f:
            raw: dict = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in '{filepath}': {e}") from e

    return Scenario(
        id=str(_require(raw, "id", "scenario")),
        name=str(_require(raw, "name", "scenario")),
        description=str(_require(raw, "description", "scenario")),
        physical_constants=_parse_physical_constants(
            _require(raw, "physical_constants", "scenario")
        ),
        weights=_parse_weights(_require(raw, "weights", "scenario")),
        route=_parse_route(_require(raw, "route", "scenario")),
        stations=[
            _parse_station(s, i)
            for i, s in enumerate(_require(raw, "stations", "scenario"))
        ],
        buses=[
            _parse_bus(b, i)
            for i, b in enumerate(_require(raw, "buses", "scenario"))
        ],
    )
