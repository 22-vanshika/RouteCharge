import glob
import json
import os
import streamlit as st
import copy
import time

from scheduler.engine import run
from scheduler.loader import load_scenario
from scheduler.models import Scenario

from ui.styles import inject_styles
from ui.dashboard import render_dashboard


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
def _load_scenario(filepath: str) -> Scenario:
    return load_scenario(filepath)


# ── sidebar helpers ───────────────────────────────────────────────────────────

def _get_selected_filepath() -> str:
    st.sidebar.title("RouteCharge Control Panel")
    scenarios = _load_scenario_index("data")
    options = {s["name"]: s["filepath"] for s in scenarios}
    selected = st.sidebar.selectbox("Select a scenario", list(options.keys()))
    return options[selected]


def _get_slider_values(scenario: Scenario, filepath: str) -> tuple[float, float, float]:
    st.sidebar.markdown("---")
    st.sidebar.header("⚖️ Tune Soft Rule Weights")

    default_ind = scenario.weights.values.get("IndividualWaitRule", 1.0)
    default_op = scenario.weights.values.get("OperatorFairnessRule", 1.0)
    default_net = scenario.weights.values.get("OverallNetworkRule", 1.0)

    slider_ind = st.sidebar.slider(
        "Individual Wait Rule", 0.0, 10.0, float(default_ind), 0.1,
        key=f"slider_ind_{filepath}", help="Higher values penalize long individual wait times."
    )
    slider_op = st.sidebar.slider(
        "Operator Fairness Rule", 0.0, 10.0, float(default_op), 0.1,
        key=f"slider_op_{filepath}", help="Higher values penalize fleet wait disparity."
    )
    slider_net = st.sidebar.slider(
        "Overall Network Rule", 0.0, 10.0, float(default_net), 0.1,
        key=f"slider_net_{filepath}", help="Higher values penalize destination delays."
    )
    return slider_ind, slider_op, slider_net


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="RouteCharge — Bus Charging Scheduler", layout="wide")

    filepath = _get_selected_filepath()
    try:
        scenario = _load_scenario(filepath)
    except ValueError as e:
        st.sidebar.error(f"Failed to load scenario: {e}")
        return

    slider_ind, slider_op, slider_net = _get_slider_values(scenario, filepath)

    # ── Scheduler Execution on copied scenario ──────────────────────────────────
    scenario_copy = copy.deepcopy(scenario)
    scenario_copy.weights.values["IndividualWaitRule"] = slider_ind
    scenario_copy.weights.values["OperatorFairnessRule"] = slider_op
    scenario_copy.weights.values["OverallNetworkRule"] = slider_net

    start_time = time.perf_counter()
    try:
        schedule = run(scenario_copy)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
    except ValueError as e:
        st.error(f"⚠️ **Scheduler Execution Error:** {e}")
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"⏱️ **Solver Speed:** `{elapsed_ms:.2f} ms`")

    st.title("RouteCharge — Bus Charging Scheduler")
    inject_styles()

    render_dashboard(scenario_copy, schedule, slider_ind, slider_op, slider_net)


if __name__ == "__main__":
    main()
