
# RouteCharge — Bus Charging Scheduler

## What was built

RouteCharge schedules charging stops for electric buses on a fixed Bengaluru–Kochi corridor (540 km, four intermediate stations). Given a scenario file describing the fleet, route geometry, and rule weights, the scheduler assigns each bus a concrete charging slot at every required station, resolves charger conflicts, and produces a complete timetable. The approach combines greedy stop selection (always charge at the furthest reachable station) with priority-scored conflict resolution using three tunable soft rules: individual wait time, operator fairness, and overall network delay.

## Local setup

```
git clone <repo-url>
pip install -r requirements.txt
streamlit run app.py
```

## How to change a weight

Open any scenario file in `data/` and edit the `weights` block. Scenario 4 (`data/scenario_4.json`) already uses a doubled operator weight to stress-test fairness:

```json
"weights": {
  "individual": 1.0,
  "operator": 2.0,
  "overall": 1.0
}
```

Change any value and reselect the scenario in the UI — the engine reruns immediately with no code changes. Future rule weights can be added as extra keys in the same block (e.g. `"ElectricityCostRule": 0.5`) and the scorer picks them up automatically by matching the key to the rule's class name.

## How to add a new rule

1. Create a new file in `scheduler/rules/` and define a class extending `SoftRule`. Implement `score(scenario, candidate) -> float` — lower score means the slot is preferred.
2. Add an instance of the new class to the `DEFAULT_RULES` list in `scheduler/rules/__init__.py`. This is the only code change required. `engine.py` is not touched.
3. Add a weight key to the scenario JSON `weights` block using the exact class name as the key.
4. No other files change. The engine, scorer, and resolver are untouched.

## How to add a new scenario

1. Copy any existing file in `data/` (e.g. `cp data/scenario_1.json data/scenario_6.json`).
2. Edit `id`, `name`, `description`, `buses`, and `weights`. Change route geometry or physical constants the same way. The new scenario appears in the UI automatically.

## Assumptions

- **Speed (60 km/h):** The spec gave distances and charge times but no travel speed. 60 km/h was chosen as a realistic intercity cruising speed and stored in `physical_constants.speed_kmh` so it is overridable per scenario.
- **Station selection strategy:** The planner uses greedy furthest-first — always charge at the furthest reachable station within battery range. This minimises the number of stops required.
- **Tie-breaking in conflict resolution:** Equal-score buses are ordered by earliest arrival time at the station, then alphabetically by bus id. This makes the output fully deterministic regardless of input ordering.
- **Station processing order:** Stations are processed depth-first (all first stops before any second stops), sorted within each depth by forward route position. Simple A→B→C→D order would resolve KOCHI_TO_BENGALURU buses' second stop (A) before their first stop (C), producing wrong arrival estimates.
- **`arrival_time_minutes=0` placeholder:** During resolution, a bus's final destination arrival is not yet known when its first stop is committed. A placeholder of 0 is used because no downstream code reads `arrival_time_minutes` from partial schedules; the correct value is written after all stations are processed.
