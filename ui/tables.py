from scheduler.models import Direction, Scenario, ScenarioSchedule

def minutes_to_hhmm(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}"


def direction_label(direction: Direction) -> str:
    if direction == Direction.BENGALURU_TO_KOCHI:
        return "Bengaluru → Kochi"
    return "Kochi → Bengaluru"


def build_bus_table(scenario: Scenario, schedule: ScenarioSchedule) -> list[dict]:
    bus_map = {bus.id: bus for bus in scenario.buses}
    rows = []
    for bs in sorted(schedule.bus_schedules, key=lambda x: x.arrival_time_minutes):
        bus = bus_map[bs.bus_id]
        for i, stop in enumerate(bs.charging_stops):
            is_last = i == len(bs.charging_stops) - 1
            rows.append({
                "Bus ID": bs.bus_id,
                "Operator": bus.operator.name,
                "Direction": direction_label(bus.direction),
                "Stop #": i + 1,
                "Station": stop.station_id,
                "Arrives": minutes_to_hhmm(stop.arrival_time_minutes),
                "Charge Start": minutes_to_hhmm(stop.charge_start_minutes),
                "Charge End": minutes_to_hhmm(stop.charge_end_minutes),
                "Wait (min)": stop.wait_minutes,
                "Arrival at Dest": minutes_to_hhmm(bs.arrival_time_minutes) if is_last else "",
            })
    return rows


def build_station_table(
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
            "Arrives": minutes_to_hhmm(stop.arrival_time_minutes),
            "Charge Start": minutes_to_hhmm(stop.charge_start_minutes),
            "Charge End": minutes_to_hhmm(stop.charge_end_minutes),
            "Wait (min)": stop.wait_minutes,
        }
        for i, (bus_id, stop) in enumerate(station_stops)
    ]
