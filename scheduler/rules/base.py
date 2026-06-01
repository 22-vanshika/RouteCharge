from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from scheduler.models import BusSchedule, Scenario


@dataclass
class ChargingCandidate:
    bus_id: str
    station_id: str
    charge_start_minutes: int
    scheduled_so_far: List[BusSchedule]


class SoftRule(ABC):
    @abstractmethod
    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        ...
