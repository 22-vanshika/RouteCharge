from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class Direction(Enum):
    BENGALURU_TO_KOCHI = "BENGALURU_TO_KOCHI"
    KOCHI_TO_BENGALURU = "KOCHI_TO_BENGALURU"


@dataclass
class Operator:
    name: str


@dataclass
class Station:
    id: str
    name: str
    num_chargers: int


@dataclass
class RouteStop:
    station_id: str
    distance_from_previous_km: float


@dataclass
class Route:
    stops: List[RouteStop]

    @property
    def total_distance_km(self) -> float:
        return sum(stop.distance_from_previous_km for stop in self.stops)


@dataclass
class PhysicalConstants:
    battery_range_km: float
    charge_time_minutes: int
    speed_kmh: float


@dataclass
class Weights:
    individual: float
    operator: float
    overall: float
    # Future weights are added here without a code change — engine reads by key
    extra: Dict[str, float] = field(default_factory=dict)


@dataclass
class Bus:
    id: str
    operator: Operator
    direction: Direction
    departure_time_minutes: int


@dataclass
class ChargingStop:
    station_id: str
    arrival_time_minutes: int
    charge_start_minutes: int
    charge_end_minutes: int

    @property
    def wait_minutes(self) -> int:
        return self.charge_start_minutes - self.arrival_time_minutes


@dataclass
class BusSchedule:
    bus_id: str
    charging_stops: List[ChargingStop]
    arrival_time_minutes: int


@dataclass
class ScenarioSchedule:
    scenario_id: str
    bus_schedules: List[BusSchedule]


@dataclass
class Scenario:
    id: str
    name: str
    description: str
    route: Route
    physical_constants: PhysicalConstants
    weights: Weights
    buses: List[Bus]
    stations: List[Station]
