from typing import List

from scheduler.models import ChargingCandidate, Scenario, Weights
from scheduler.rules.base import SoftRule


def compute_score(
    scenario: Scenario,
    candidate: ChargingCandidate,
    rules: List[SoftRule],
    weights: Weights,
) -> float:
    total = 0.0
    for rule in rules:
        # Default weight of 1.0 ensures a newly registered rule is always counted
        # rather than silently ignored while its weight key is being added to the scenario.
        weight = weights.values.get(rule.name, 1.0)
        total += rule.score(scenario, candidate) * weight
    return total

