from abc import ABC, abstractmethod
from typing import ClassVar

from scheduler.models import ChargingCandidate, Scenario


class SoftRule(ABC):
    """Base class for all soft scheduling rules. Lower score means a preferred slot."""

    name: ClassVar[str]  # stable semantic identifier, independent of class name

    @abstractmethod
    def score(self, scenario: Scenario, candidate: ChargingCandidate, context = None) -> float:
        """Return a non-negative penalty for this candidate slot. Return 0.0 for no penalty."""
        ...

