from typing import Dict, List

from scheduler.models import ChargingCandidate, Scenario, Weights
from scheduler.rules.base import SoftRule


def _build_weight_map(weights: Weights) -> Dict[str, float]:
    return {
        "IndividualWaitRule": weights.individual,
        "OperatorFairnessRule": weights.operator,
        "OverallNetworkRule": weights.overall,
        **weights.extra,
    }


def compute_score(
    scenario: Scenario,
    candidate: ChargingCandidate,
    rules: List[SoftRule],
    weights: Weights,
) -> float:
    weight_map = _build_weight_map(weights)
    total = 0.0
    for rule in rules:
        rule_name = type(rule).__name__
        # Default weight of 1.0 ensures a newly registered rule is always counted
        # rather than silently ignored while its weight key is being added to the scenario.
        weight = weight_map.get(rule_name, 1.0)
        total += rule.score(scenario, candidate) * weight
    return total
