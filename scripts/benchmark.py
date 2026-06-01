import time
import random
import resource
import sys
from scheduler.models import (
    Scenario, PhysicalConstants, Weights, Route, RouteStop, Station, Bus, Operator, Direction
)
from scheduler.engine import run

def create_bench_scenario(num_buses, num_stations=10, chargers_per_station=4) -> Scenario:
    # 1. Physical constants
    pc = PhysicalConstants(battery_range_km=240.0, charge_time_minutes=25, speed_kmh=60.0)
    
    # 2. Route stops
    stops = [RouteStop(station_id="origin", distance_from_previous_km=0.0)]
    for i in range(num_stations):
        stops.append(RouteStop(station_id=f"S{i}", distance_from_previous_km=50.0))
    stops.append(RouteStop(station_id="destination", distance_from_previous_km=50.0))
    route = Route(stops=stops)
    
    # 3. Stations
    stations = [Station(id=f"S{i}", name=f"Station S{i}", num_chargers=chargers_per_station) for i in range(num_stations)]
    
    # 4. Weights
    weights = Weights(values={
        "IndividualWaitRule": 1.0,
        "OperatorFairnessRule": 1.0,
        "OverallNetworkRule": 1.0
    })
    
    # 5. Buses
    operators = [Operator("kpn"), Operator("freshbus"), Operator("flixbus")]
    buses = []
    for i in range(num_buses):
        direction = Direction.BENGALURU_TO_KOCHI if i % 2 == 0 else Direction.KOCHI_TO_BENGALURU
        dept_time = random.randint(0, 1440)
        buses.append(Bus(
            id=f"bus-{i:04d}",
            operator=random.choice(operators),
            direction=direction,
            departure_time_minutes=dept_time
        ))
        
    return Scenario(
        id=f"bench_{num_buses}",
        name=f"Benchmark Scenario {num_buses} Buses",
        description=f"Automated benchmark scenario with {num_buses} buses.",
        route=route,
        physical_constants=pc,
        weights=weights,
        buses=buses,
        stations=stations
    )

def format_memory(bytes_val):
    if bytes_val >= 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.2f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.2f} KB"
    return f"{bytes_val} B"

def run_benchmark():
    random.seed(42)
    # Peak memory usage on macOS is reported in bytes, on Linux in kilobytes
    is_macos = sys.platform == "darwin"
    
    sizes = [100, 500, 1000]
    print("=" * 60)
    print(" ROUTECHARGE - AUTOMATED SCHEDULER PERFORMANCE PROFILE")
    print("=" * 60)
    print(f"{'Fleet Size':<15} | {'Runtime (s)':<15} | {'Avg time/bus':<15} | {'Peak RSS Memory':<15}")
    print("-" * 60)
    
    for size in sizes:
        scenario = create_bench_scenario(size)
        
        # Reset peak memory before run by measuring baseline
        baseline_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if not is_macos:
            baseline_mem *= 1024  # Convert KB to bytes on Linux
            
        t0 = time.perf_counter()
        schedule = run(scenario)
        t1 = time.perf_counter()
        
        peak_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if not is_macos:
            peak_mem *= 1024  # Convert KB to bytes on Linux
            
        elapsed = t1 - t0
        avg_ms_per_bus = (elapsed / size) * 1000
        mem_formatted = format_memory(peak_mem)
        
        print(f"{size:<15d} | {elapsed:<15.4f} | {avg_ms_per_bus:<13.2f} ms | {mem_formatted:<15}")
        
    print("=" * 60)

if __name__ == "__main__":
    run_benchmark()
