# RouteCharge — Bus Charging Scheduler

RouteCharge schedules charging stops for electric buses on a fixed Bengaluru–Kochi corridor (540 km, four intermediate stations). Given a scenario file describing the fleet, route geometry, and rule weights, the scheduler assigns each bus a concrete charging slot at every required station, resolves charger conflicts, and produces a complete timetable.

The approach combines greedy stop selection (utilizing a BFS-based furthest-first path planner) with priority-scored conflict resolution using three tunable soft rules: individual wait time, operator fairness, and overall network delay.

---

## The Problem

Electric buses run in both directions along a fixed corridor with shared, single-charger stations. Each bus leaves with a full charge but can't complete the trip without recharging along the way — so the scheduler has to decide **which stations each bus uses** and, when several buses want the same charger at once, **who charges first and who waits**.

The interesting part isn't today's fixed setup (4 stations, 1 charger each, 20 buses). It's building a scheduler that stays correct and easy to change as the world grows: more buses, more chargers, new operators, new routes, and new optimization rules. So the design is deliberately **data-driven and rule-pluggable**:

- **Every scenario is self-describing JSON** — route, distances, battery range, charger counts, fleet, and rule weights all live in data, never hardcoded.
- **Optimization weights are tunable** in one obvious place (the scenario file, or live via UI sliders), balancing three goals: minimizing individual bus waits, keeping each operator's fleet fair, and lowering total network delay.
- **New rules slot in as a single file** without touching the engine, so the system extends without a rewrite.

---

## 🌟 Interactive Streamlit UI Features

The application features a clean, modern frontend for exploring and stress-testing schedules:

1. **Global Control Panel (Left Sidebar)**
   * **Dynamic Scenario Selectbox**: Cycle through the 5 pre-loaded scenarios instantly.
   * **⚖️ Tunable Soft Rule Sliders**: Override and tune rule weights (*Individual*, *Operator Fairness*, *Overall Network*) in real-time. Sliders automatically reset to the scenario's default values when switching datasets using scoped state keys.
   * **⏱️ Performance Speedometer**: Real-time solver instrumentation displaying exact resolution speeds in milliseconds (typically `< 2.0 ms`).
2. **📊 Tabbed Analytical Dashboard**
   * **Tab 1: Dashboard**:
     * **KPI Performance Metrics**: Real-time cards displaying *Total Wait Time*, *Average Wait*, *Maximum Wait*, *Charging Stops*, and *Total Buses*. Metrics update instantly as sliders move.
     * **Scenario Summary Card**: Visual grid summarizing fleet size, station count, operator count, route distance, and total chargers.
     * **Validation Status Checklist**: Active, green compliance checks verifying that all hard physical constraints (battery range, station sequencing, charger capacities, and charge durations) are successfully validated.
   * **Tab 2: Bus Schedules**: Renders scenario input departures alongside the chronological per-bus charging timetable.
   * **Tab 3: Station View**: Chronologically displays charger occupation lists grouped by station.
   * **Tab 4: Technical Specs**: An in-app architecture summary explaining engine details, soft rules, and data structures.

---

## 🚀 Local Setup

Ensure you have Python 3.8+ installed, then run:

```bash
# Clone the repository
git clone <repo-url>
cd RouteCharge

# Install dependencies
pip install -r requirements.txt

# Launch the Streamlit application
streamlit run app.py
```

---

## ⚖️ How Weight Tuning Works

Weights can be tuned in two ways:
1. **Interactive UI Sliders (Recommended)**: Drag the sliders in the left-hand sidebar. The scheduler instantly creates a `copy.deepcopy()` of the scenario, applies the slider values, and re-calculates the entire timetable dynamically without mutating cached scenario data.
2. **Scenario File Defaults**: Open any scenario file in `data/` and edit the `weights` block. Scenario 4 (`data/scenario_4.json`) already uses a doubled operator weight to stress-test fairness:
   ```json
   "weights": {
     "individual": 1.0,
     "operator": 2.0,
     "overall": 1.0
   }
   ```

---

## 📐 System Architecture & Specifications

### 1. BFS Path Planner (`planner.py`)
* **Fewest Stops Guarantee**: Every stop incurs a fixed 25-minute charging duration plus deceleration/acceleration overhead. Minimizing the *number of stops* is the primary efficiency driver.
* **Why BFS instead of Dijkstra?**: On a route sequence where each edge represents reachability within the **240 km battery range** and edge weights are uniform (1 stop), BFS naturally finds the path with the minimum number of stops in linear $O(V+E)$ time. Dijkstra represents unnecessary overhead ($O(E + V \log V)$).
* **Furthest-First Tie-Breaking**: Biases BFS to search furthest stops first, maximizing distance driven before stopping if stop counts are equal.

### 2. Immutable `SchedulingContext` (`models.py`, `resolver.py`)
* **Pure Functional Design**: The solver utilizes an immutable context block. As the resolver steps through stations, it constructs new contexts (leveraging `dataclasses.replace` for operators' average waits) rather than modifying global state in place. This guarantees deterministic behavior and completely eliminates state leaks or race conditions during Streamlit reruns.

### 3. Dynamic Multi-Charger Support (`resolver.py`)
* **Horizontal Scalability**: Stations are resolved using a list of availability timelines (`charger_free_times = [0] * num_chargers`) matching the station's actual `num_chargers` parameter. This allows the system to scale to multiple chargers per station seamlessly through data configuration changes alone.

---

## 🛠️ Developer Checklist

### How to Add a New Soft Rule
1. Create a new file in `scheduler/rules/` defining a class that extends `SoftRule`. Implement `score(scenario, candidate, context) -> float` (lower scores are preferred).
2. Append an instance of your class to the `DEFAULT_RULES` list in `scheduler/rules/__init__.py`. 
3. Add a corresponding weight key to your scenario JSON `weights` block using the class name (e.g. `"ElectricityCostRule": 0.5`). 
4. The solver, scorers, and engine will dynamically pick it up with **zero** changes to `engine.py` or the resolver.

### Running Unit Tests
Validate core scheduling logic and rules by executing:
```bash
python3 -m unittest tests/test_scheduler.py
```
*(All 11 tests are passing with 100% compliance).*
