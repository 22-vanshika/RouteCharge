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
| Add a second charger at a station | Edit scenario JSON: set `num_chargers` to 2; update `resolver.py` to track multiple concurrent slots per station, and update `validator.py` to allow overlapping intervals up to `num_chargers` — both isolated changes |
| Change a segment distance | Edit scenario JSON: change `distance_from_previous_km` on the relevant stop |
| Add a new operator | Edit scenario JSON: use the new operator name string on any bus entry |
| Add a new bus | Edit scenario JSON: add a bus entry with id, operator, direction, departure time |
| Change battery range or charge time | Edit scenario JSON: update `physical_constants` fields |
| Add a new soft rule (e.g. electricity cost) | New file in `scheduler/rules/`, add instance to `DEFAULT_RULES` in `scheduler/rules/__init__.py`, add weight key to scenario JSON |
| Change any weight | Edit one value in the scenario JSON `weights` block |
| Add a priority flag to buses | Add `priority` field to bus entries in JSON; add a new soft or hard rule that reads it — no engine changes |
| Add a new route (second corridor) | New scenario JSON file with different `route.stops` and `stations` |
| Multiple routes sharing a station | Merge buses from both routes into a single scenario file with a shared `stations` list. Each `engine.run()` is self-contained — cross-route contention only resolves if both routes' buses are in the same scenario |
| Time-of-day electricity costs | Add `extra: Dict` field to `PhysicalConstants` (same pattern as `Weights.extra`) and update `_parse_physical_constants` in `loader.py` to collect unknown keys. Then implement as a new `SoftRule` reading from `scenario.physical_constants.extra` |
| Variable charge speed (fast vs standard charger) | Add `charger_type` to station entries and a fast charge time constant to `physical_constants`; planner and resolver read from scenario |
| Minimum headway between buses at a station | Add `min_headway_minutes` to `physical_constants` in JSON; enforce in `validator.py` as a new hard constraint |
| Bus depot release time (available only from a certain hour) | Add `available_from_minutes` to bus entries in JSON; validator enforces it, no planner changes needed |
| Bus does not start with full charge | Add `initial_charge_km` to bus entries in JSON; update `planner.py::_greedy_select` to use this as starting range instead of assuming `battery_range_km` |
| Station temporarily out of service | Add `available: bool` to station entries in JSON; `planner.py::_valid_station_ids` filters by this field — data-only change |
| Driver shift constraints | Add `shift_end_minutes` to bus entries in JSON; enforce in `validator.py` as a hard constraint AND add a `ShiftUrgencyRule` soft rule — post-hoc validation alone cannot recover a committed schedule that violates a deadline |

**Known limitations:**

The `Direction` enum currently encodes Bengaluru–Kochi route semantics directly. Adding a second route would require replacing it with a route-agnostic concept such as `is_forward: bool` on `Bus` — the one change with multi-file blast radius touching models, loader, planner, utils, and validator.

The `extra: Dict` extensibility pattern applied to `Weights` is not yet applied to `Bus`, `Station`, or `PhysicalConstants`. Adding a new field to those models currently requires changes to both `models.py` and `loader.py`. This inconsistency is the next thing to address.

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
