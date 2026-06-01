# ARCHITECTURE.md — RouteCharge

## Scheduling approach

The scheduler uses greedy planning plus priority-scored conflict resolution. The planner assigns the minimum required charging stations per bus (furthest reachable station first). The resolver handles contention: when buses compete for the same charger, it ranks them by weighted penalty score and assigns slots sequentially, propagating each committed slot into the scoring context so later decisions reflect what earlier buses received.

This is deterministic, easy to reason about, and open for extension. Adding a rule means adding one file — the engine iterates whatever rules are registered, applies weights from the scenario JSON, and makes no assumptions about which rules exist.

## Data structure design

Every scenario file is fully self-describing. Physical constants, route geometry, rule weights, and the full bus list all live in JSON. No value is hardcoded in any Python file — changing battery range or segment distance requires editing one file, not code.

`Weights` has named fields for the three built-in rules and an `extra: Dict[str, float]` for future keys. The scorer merges both at runtime, keying on class name. A new rule with a matching key in `extra` picks up its weight with zero code changes.

All times are integers (minutes since midnight). This eliminates format parsing from the engine, makes arithmetic trivial, and avoids timezone ambiguity. Display conversion to HH:MM happens in exactly one place in `app.py`.

`Station.num_chargers` is stored in the scenario data today and defaults to 1. A future resolver that reads this field and tracks multiple concurrent slots can replace the current one without any other file changing.

## Anticipated future changes

| Change | How the design handles it |
|---|---|
| Add a new station to the route | Edit scenario JSON: add stop to `route.stops`, add entry to `stations` list |
| Add a second charger at a station | Edit scenario JSON: set `num_chargers` to 2; update resolver to use the field — isolated to `resolver.py` |
| Change a segment distance | Edit scenario JSON: change `distance_from_previous_km` on the relevant stop |
| Add a new operator | Edit scenario JSON: use the new operator name string on any bus entry |
| Add a new bus | Edit scenario JSON: add a bus entry with id, operator, direction, departure time |
| Change battery range or charge time | Edit scenario JSON: update `physical_constants` fields |
| Add a new soft rule (e.g. electricity cost) | New file in `scheduler/rules/`, add instance to `DEFAULT_RULES` in `scheduler/rules/__init__.py`, add weight key to scenario JSON |
| Change any weight | Edit one value in the scenario JSON `weights` block |
| Add a priority flag to buses | Add `priority` field to bus entries in JSON; add a new soft or hard rule that reads it — no engine changes |
| Add a new route (second corridor) | New scenario JSON file with different `route.stops` and `stations` |
| Multiple routes sharing a station | Station id is the unique key; resolver handles contention by station id regardless of route |
| Driver shift constraints | Add `shift_end_minutes` to bus entries in JSON; enforce in `validator.py` as a new hard constraint |
| Time-of-day electricity costs | Add cost schedule to `physical_constants` in JSON; implement as a new `SoftRule` — one file, one JSON key, zero engine changes |
| Variable charge speed (fast vs standard charger) | Add `charger_type` to station entries and a fast charge time constant to `physical_constants`; planner and resolver read from scenario |
| Minimum headway between buses at a station | Add `min_headway_minutes` to `physical_constants` in JSON; enforce in `validator.py` as a new hard constraint |
| Bus depot release time (available only from a certain hour) | Add `available_from_minutes` to bus entries in JSON; validator enforces it, no planner changes needed |

## How to change a weight

Open the relevant scenario JSON file and edit the value in the `weights` block — for example, change `"operator": 2.0` to `"operator": 3.0` in `data/scenario_4.json`. No Python file is touched.

## How to add a new rule

1. Create a file in `scheduler/rules/` extending `SoftRule` from `base.py`. Implement `score(scenario, candidate) -> float`; return 0.0 for no penalty.
2. Add an instance of the new class to `DEFAULT_RULES` in `scheduler/rules/__init__.py` — this is the only code change. `engine.py` is never touched.
3. Add the class name as a key in the `weights` block of any scenario JSON where the rule applies (e.g. `"ElectricityCostRule": 0.5`). Scenarios without the key fall back to the default weight of 1.0.
4. No other files change.

**One known limitation:** the scorer maps rule class names to weights using
`type(rule).__name__` matched against the string keys in `_build_weight_map`
(e.g. `"IndividualWaitRule": weights.individual`). If a rule class is renamed,
the old string key no longer matches and the rule silently falls back to a weight of
`1.0`. To avoid this: when renaming a rule class, update the
corresponding string key in `scheduler/scorer.py::_build_weight_map` in the
same commit.

Example skeleton for a new rule (`scheduler/rules/electricity_cost.py`):

```python
from scheduler.models import Scenario
from scheduler.rules.base import ChargingCandidate, SoftRule


class ElectricityCostRule(SoftRule):
    def score(self, scenario: Scenario, candidate: ChargingCandidate) -> float:
        # Read cost schedule from scenario.physical_constants.extra (if present).
        # Return a penalty proportional to how expensive this charge window is.
        # Return 0.0 if no cost schedule is defined.
        cost_schedule = scenario.physical_constants.__dict__.get("extra", {})
        return 0.0  # replace with real cost lookup
```

Then add `"ElectricityCostRule": 0.5` to the `weights` block in any scenario JSON.

## Assumptions

- **Speed (60 km/h):** The spec gave distances and charge times but no speed. 60 km/h matches realistic intercity coach speeds and is stored in `physical_constants.speed_kmh`, overridable per scenario.
- **Greedy furthest-first station selection:** Advancing to the furthest reachable station minimises total stop count — the optimal strategy under a single range constraint.
- **Tie-breaking order (score → arrival → bus id):** Arrival time breaks score ties by rewarding the bus that arrived first. Bus id alphabetically ensures full reproducibility regardless of input order.
- **Depth-first station processing order:** Processing all first stops before any second stops ensures each bus's prior stop is in context before its next stop is resolved. Forward route order (A→B→C→D) would commit KOCHI_TO_BENGALURU buses' second stop (A) before their first stop (C), producing wrong arrival estimates.
- **`arrival_time_minutes=0` placeholder:** When a first stop is committed, final destination arrival is unknown. Zero is safe because no scoring function reads `arrival_time_minutes` from partial schedules; the correct value is written after all stations are processed.
