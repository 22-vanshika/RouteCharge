import unittest
from scheduler.models import (
    Scenario, PhysicalConstants, Weights, Route, RouteStop, Station, Bus, Operator, Direction, ChargingStop, ScenarioSchedule, BusSchedule
)
from scheduler.planner import plan_charging_stops
from scheduler.validator import validate_scenario, validate_schedule
from scheduler.loader import _parse_weights
from scheduler.resolver import resolve_station
from scheduler.rules.individual import IndividualWaitRule

def get_test_weights():
    return Weights(values={
        "IndividualWaitRule": 1.0,
        "OperatorFairnessRule": 1.0,
        "OverallNetworkRule": 1.0
    })

class TestBFSPlanner(unittest.TestCase):
    def test_bfs_normal_path(self):
        pc = PhysicalConstants(battery_range_km=240.0, speed_kmh=60.0, charge_time_minutes=25)
        # Route: 0 -> A(100km) -> B(220km) -> C(320km) -> D(440km) -> 540km
        stops = [
            RouteStop("bengaluru", 0.0),
            RouteStop("A", 100.0),
            RouteStop("B", 120.0),
            RouteStop("C", 100.0),
            RouteStop("D", 120.0),
            RouteStop("kochi", 100.0)
        ]
        stations = [
            Station("A", "Station A", 1),
            Station("B", "Station B", 1),
            Station("C", "Station C", 1),
            Station("D", "Station D", 1)
        ]
        bus = Bus("bus-1", Operator("kpn"), Direction.BENGALURU_TO_KOCHI, 1140)
        scenario = Scenario("test", "test", "test", Route(stops), pc, get_test_weights(), [bus], stations)
        
        # BFS should find ['B', 'D'] as the optimal path (minimum hops)
        stops_planned = plan_charging_stops(scenario, bus)
        self.assertEqual(stops_planned, ["B", "D"])

    def test_bfs_unreachable_gap(self):
        pc = PhysicalConstants(battery_range_km=240.0, speed_kmh=60.0, charge_time_minutes=25)
        # Gap between B (220km) and C (480km) is 260km, which exceeds range of 240km!
        stops = [
            RouteStop("bengaluru", 0.0),
            RouteStop("A", 100.0),
            RouteStop("B", 120.0),
            RouteStop("C", 260.0),
            RouteStop("kochi", 100.0)
        ]
        stations = [Station("A", "A", 1), Station("B", "B", 1), Station("C", "C", 1)]
        bus = Bus("bus-1", Operator("kpn"), Direction.BENGALURU_TO_KOCHI, 1140)
        scenario = Scenario("test", "test", "test", Route(stops), pc, get_test_weights(), [bus], stations)
        
        # Pathfinding should fail due to unreachable segment
        with self.assertRaises(ValueError) as context:
            plan_charging_stops(scenario, bus)
        self.assertIn("no reachable charging path", str(context.exception))

    def test_bfs_reverse_direction(self):
        pc = PhysicalConstants(battery_range_km=240.0, speed_kmh=60.0, charge_time_minutes=25)
        # Route: Bengaluru -> A(100km) -> B(220km) -> C(320km) -> D(440km) -> Kochi(540km)
        stops = [
            RouteStop("bengaluru", 0.0),
            RouteStop("A", 100.0),
            RouteStop("B", 120.0),
            RouteStop("C", 100.0),
            RouteStop("D", 120.0),
            RouteStop("kochi", 100.0)
        ]
        stations = [
            Station("A", "Station A", 1),
            Station("B", "Station B", 1),
            Station("C", "Station C", 1),
            Station("D", "Station D", 1)
        ]
        # Reverse Direction: Kochi -> Bengaluru
        bus = Bus("bus-1", Operator("kpn"), Direction.KOCHI_TO_BENGALURU, 1140)
        scenario = Scenario("test", "test", "test", Route(stops), pc, get_test_weights(), [bus], stations)
        
        # BFS should find ['C', 'A'] as the optimal path in reverse (minimum hops)
        stops_planned = plan_charging_stops(scenario, bus)
        self.assertEqual(stops_planned, ["C", "A"])

    def test_bus_with_no_required_charging_stops(self):
        pc = PhysicalConstants(battery_range_km=240.0, speed_kmh=60.0, charge_time_minutes=25)
        # Route: 0 -> A(100km) -> 200km total. Since range is 240km, bus can go from origin to destination without stopping!
        stops = [
            RouteStop("bengaluru", 0.0),
            RouteStop("A", 100.0),
            RouteStop("kochi", 100.0)
        ]
        stations = [Station("A", "Station A", 1)]
        bus = Bus("bus-1", Operator("kpn"), Direction.BENGALURU_TO_KOCHI, 1140)
        scenario = Scenario("test", "test", "test", Route(stops), pc, get_test_weights(), [bus], stations)
        
        # Expected: BFS should return an empty list because no charging stops are required to reach the destination
        stops_planned = plan_charging_stops(scenario, bus)
        self.assertEqual(stops_planned, [])

class TestValidator(unittest.TestCase):
    def test_unregistered_station_in_route(self):
        pc = PhysicalConstants(battery_range_km=240.0, speed_kmh=60.0, charge_time_minutes=25)
        # Route stop 'Z' is not registered in the stations list!
        stops = [RouteStop("bengaluru", 0.0), RouteStop("Z", 100.0), RouteStop("kochi", 100.0)]
        stations = [Station("A", "A", 1)]
        bus = Bus("bus-1", Operator("kpn"), Direction.BENGALURU_TO_KOCHI, 1140)
        scenario = Scenario("test", "test", "test", Route(stops), pc, get_test_weights(), [bus], stations)
        
        with self.assertRaises(ValueError) as context:
            validate_scenario(scenario)
        self.assertIn("is not a registered scheduling station", str(context.exception))

    def test_duplicate_station_ids(self):
        pc = PhysicalConstants(battery_range_km=240.0, speed_kmh=60.0, charge_time_minutes=25)
        stops = [RouteStop("bengaluru", 0.0), RouteStop("A", 100.0), RouteStop("kochi", 100.0)]
        # Duplicate station id 'A'!
        stations = [Station("A", "A1", 1), Station("A", "A2", 1)]
        bus = Bus("bus-1", Operator("kpn"), Direction.BENGALURU_TO_KOCHI, 1140)
        scenario = Scenario("test", "test", "test", Route(stops), pc, get_test_weights(), [bus], stations)
        
        with self.assertRaises(ValueError) as context:
            validate_scenario(scenario)
        self.assertIn("Duplicate station id 'A'", str(context.exception))

class TestWeightsValidation(unittest.TestCase):
    def test_weights_typo_rejection(self):
        # Misspelling 'operator' key as 'operatorfairnes'
        weights_data = {
            "individual": 1.0,
            "overall": 1.0,
            "operatorfairnes": 2.0
        }
        with self.assertRaises(ValueError) as context:
            _parse_weights(weights_data)
        self.assertIn("Unrecognized weight key", str(context.exception))

    def test_missing_registered_rule_weight(self):
        # Missing 'overall' weight
        weights_data = {
            "individual": 1.0,
            "operator": 1.0
        }
        with self.assertRaises(ValueError) as context:
            _parse_weights(weights_data)
        self.assertIn("Missing required weight key", str(context.exception))

class TestMultiChargerScheduling(unittest.TestCase):
    def test_concurrent_charging_under_limit(self):
        pc = PhysicalConstants(battery_range_km=240.0, speed_kmh=60.0, charge_time_minutes=25)
        stops = [RouteStop("bengaluru", 0.0), RouteStop("A", 100.0), RouteStop("kochi", 100.0)]
        # Station A has 2 chargers
        stations = [Station("A", "Station A", 2)]
        
        # Two buses arriving concurrently at Station A
        bus_ids = ["bus-1", "bus-2"]
        buses = [
            Bus("bus-1", Operator("kpn"), Direction.BENGALURU_TO_KOCHI, 1140),
            Bus("bus-2", Operator("freshbus"), Direction.BENGALURU_TO_KOCHI, 1140)
        ]
        scenario = Scenario("test", "test", "test", Route(stops), pc, get_test_weights(), buses, stations)
        
        # Resolve station charging timeline
        rules = [IndividualWaitRule()]
        resolved = resolve_station(scenario, "A", bus_ids, rules, [])
        
        # Since num_chargers = 2, both buses should charge concurrently starting at arrival time
        stop1 = next(stop for bid, stop in resolved if bid == "bus-1")
        stop2 = next(stop for bid, stop in resolved if bid == "bus-2")
        self.assertEqual(stop1.charge_start_minutes, stop1.arrival_time_minutes)
        self.assertEqual(stop2.charge_start_minutes, stop2.arrival_time_minutes)

    def test_validation_exceeding_capacity(self):
        pc = PhysicalConstants(battery_range_km=240.0, speed_kmh=60.0, charge_time_minutes=25)
        stops = [RouteStop("bengaluru", 0.0), RouteStop("A", 100.0), RouteStop("kochi", 100.0)]
        # Station A has only 1 charger
        stations = [Station("A", "Station A", 1)]
        buses = [
            Bus("bus-1", Operator("kpn"), Direction.BENGALURU_TO_KOCHI, 1140),
            Bus("bus-2", Operator("freshbus"), Direction.BENGALURU_TO_KOCHI, 1140)
        ]
        scenario = Scenario("test", "test", "test", Route(stops), pc, get_test_weights(), buses, stations)
        
        # Manually construct overlapping schedules on a single charger (violating limit)
        bus_schedules = [
            BusSchedule("bus-1", [ChargingStop("A", 1240, 1240, 1265)], 1340),
            BusSchedule("bus-2", [ChargingStop("A", 1240, 1245, 1270)], 1340)
        ]
        schedule = ScenarioSchedule("test", bus_schedules)
        
        # Validator should catch the concurrent charger overlap limit breach
        with self.assertRaises(ValueError) as context:
            validate_schedule(scenario, schedule)
        self.assertIn("charger overlap — number of concurrent buses charging (2) exceeds limit (1)", str(context.exception))

if __name__ == "__main__":
    unittest.main()
