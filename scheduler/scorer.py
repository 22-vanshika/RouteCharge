from typing import List

from scheduler.models import ChargingCandidate, Scenario, Weights
from scheduler.rules.base import SoftRule


def compute_score(
    scenario: Scenario,
    candidate: ChargingCandidate,
    rules: List[SoftRule],
    weights: Weights,
    context = None,
) -> float:
    total = 0.0
    for rule in rules:
        # Strict weight resolution: weights are guaranteed by the loader to contain all registered rules
        weight = weights.values[rule.name]
        total += rule.score(scenario, candidate, context) * weight
    return total



