from abc import ABC, abstractmethod

from scheduler.models import ChargingCandidate, Scenario


class SoftRule(ABC):
    @abstractmethod
    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        ...
