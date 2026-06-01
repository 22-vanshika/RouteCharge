import glob
import json
import os
import streamlit as st

from scheduler.engine import run
from scheduler.loader import load_scenario
from scheduler.models import Direction, Scenario, ScenarioSchedule


# ── required helper functions ─────────────────────────────────────────────────

def _minutes_to_hhmm(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}"


def _direction_label(direction: Direction) -> str:
    if direction == Direction.BENGALURU_TO_KOCHI:
        return "Bengaluru → Kochi"
    return "Kochi → Bengaluru"


def _build_bus_table(scenario: Scenario, schedule: ScenarioSchedule) -> list[dict]:
    bus_map = {bus.id: bus for bus in scenario.buses}
    rows = []
    for bs in sorted(schedule.bus_schedules, key=lambda x: x.arrival_time_minutes):
        bus = bus_map[bs.bus_id]
        for i, stop in enumerate(bs.charging_stops):
            is_last = i == len(bs.charging_stops) - 1
            rows.append({
                "Bus ID": bs.bus_id,
                "Operator": bus.operator.name,
                "Direction": _direction_label(bus.direction),
                "Stop #": i + 1,
                "Station": stop.station_id,
                "Arrives": _minutes_to_hhmm(stop.arrival_time_minutes),
                "Charge Start": _minutes_to_hhmm(stop.charge_start_minutes),
                "Charge End": _minutes_to_hhmm(stop.charge_end_minutes),
                "Wait (min)": stop.wait_minutes,
                "Arrival at Dest": _minutes_to_hhmm(bs.arrival_time_minutes) if is_last else "",
            })
    return rows


def _build_station_table(
    station_id: str,
    schedule: ScenarioSchedule,
    scenario: Scenario,
) -> list[dict]:
    bus_map = {bus.id: bus for bus in scenario.buses}
    station_stops = sorted(
        [
            (bs.bus_id, stop)
            for bs in schedule.bus_schedules
            for stop in bs.charging_stops
            if stop.station_id == station_id
        ],
        key=lambda x: x[1].charge_start_minutes,
    )
    return [
        {
            "Order": i + 1,
            "Bus ID": bus_id,
            "Operator": bus_map[bus_id].operator.name,
            "Arrives": _minutes_to_hhmm(stop.arrival_time_minutes),
            "Charge Start": _minutes_to_hhmm(stop.charge_start_minutes),
            "Charge End": _minutes_to_hhmm(stop.charge_end_minutes),
            "Wait (min)": stop.wait_minutes,
        }
        for i, (bus_id, stop) in enumerate(station_stops)
    ]


# ── data loading ──────────────────────────────────────────────────────────────

def _load_scenario_index(data_dir: str) -> list[dict[str, str]]:
    files = sorted(glob.glob(os.path.join(data_dir, "scenario_*.json")))
    result = []
    for path in files:
        with open(path) as f:
            raw = json.load(f)
        result.append({"filepath": path, "id": raw["id"], "name": raw["name"]})
    return result


@st.cache_data
def _load_and_run(filepath: str) -> tuple[Scenario, ScenarioSchedule]:
    scenario = load_scenario(filepath)
    return scenario, run(scenario)


# ── render helpers ────────────────────────────────────────────────────────────

def _render_input_view(scenario: Scenario) -> None:
    st.header("Scenario Input")
    bus_rows = [
        {
            "Bus ID": bus.id,
            "Operator": bus.operator.name,
            "Direction": _direction_label(bus.direction),
            "Departure": _minutes_to_hhmm(bus.departure_time_minutes),
        }
        for bus in scenario.buses
    ]
    st.dataframe(bus_rows, use_container_width=True)
    weights = {
        "individual": scenario.weights.individual,
        "operator": scenario.weights.operator,
        "overall": scenario.weights.overall,
        **scenario.weights.extra,
    }
    st.markdown("**Weights in use:**")
    st.json(weights)


def _render_per_bus_view(scenario: Scenario, schedule: ScenarioSchedule) -> None:
    st.header("Per-Bus Timetable")
    st.dataframe(_build_bus_table(scenario, schedule), use_container_width=True)


def _render_per_station_view(scenario: Scenario, schedule: ScenarioSchedule) -> None:
    st.header("Per-Station Charging Order")
    station_ids = {station.id for station in scenario.stations}
    ordered = [rs.station_id for rs in scenario.route.stops if rs.station_id in station_ids]
    for station_id in ordered:
        st.subheader(f"Station {station_id}")
        rows = _build_station_table(station_id, schedule, scenario)
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.write("No buses charged at this station.")


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    st.title("RouteCharge — Bus Charging Scheduler")

    scenarios = _load_scenario_index("data")
    options = {s["name"]: s["filepath"] for s in scenarios}
    selected = st.selectbox("Select a scenario", list(options.keys()))
    filepath = options[selected]

    try:
        scenario, schedule = _load_and_run(filepath)
    except ValueError as e:
        st.error(str(e))
        return

    _render_input_view(scenario)
    _render_per_bus_view(scenario, schedule)
    _render_per_station_view(scenario, schedule)


main()
