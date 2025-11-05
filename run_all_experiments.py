#!/usr/bin/env python3
"""
Quick experiment runner - executes all scenarios and extracts key metrics
"""

import subprocess
import json
import re
from pathlib import Path
from datetime import datetime

SCENARIOS_DIR = Path("configs/scenarios")
RESULTS_DIR = Path("experiment_results")

# Define scenario groups
SCENARIO_GROUPS = {
    "1_Demand_Scaling": [
        "baseline_500u_50c.yaml",
        "high_demand_1000u_50c.yaml",
        "very_high_demand_2000u_50c.yaml",
    ],
    "2_Fleet_Scaling": [
        "baseline_500u_50c.yaml",
        "large_fleet_1000u_100c.yaml",
        "very_large_fleet_2000u_200c.yaml",
    ],
    "3_Pickup_Radius": [
        "small_radius_500u_50c.yaml",
        "baseline_500u_50c.yaml",
        "large_radius_500u_50c.yaml",
    ],
    "4_Charging_Infrastructure": [
        "limited_charging_500u_50c.yaml",
        "baseline_500u_50c.yaml",
        "abundant_charging_500u_50c.yaml",
    ],
    "5_Relocator_Capacity": [
        "limited_relocators_500u_50c.yaml",
        "baseline_500u_50c.yaml",
        "abundant_relocators_500u_50c.yaml",
    ],
    "6_User_Behavior": [
        "baseline_500u_50c.yaml",
        "frequent_reservations_500u_50c.yaml",
    ],
    "7_Extreme_Scenarios": [
        "stress_test_2000u_30c_limited.yaml",
        "optimal_1000u_100c_abundant.yaml",
    ],
}

def run_scenario(scenario_file):
    """Run a single scenario and capture output"""
    print(f"\n{'='*70}")
    print(f"Running: {scenario_file.stem}")
    print(f"{'='*70}")
    
    cmd = ["python3", "-m", "src.simulation", "--config", str(scenario_file)]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print(f"⚠️  TIMEOUT: {scenario_file.stem}")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

def extract_metrics(output):
    """Extract key metrics from simulation output"""
    if not output:
        return {}
    
    metrics = {}
    
    # Look for common metric patterns
    patterns = {
        'success_rate': r'Success Rate[:\s]+([0-9.]+)%',
        'utilization': r'Utilization[:\s]+([0-9.]+)%',
        'avg_attempts': r'Average Attempts[:\s]+([0-9.]+)',
        'avg_wait_time': r'Average Wait Time[:\s]+([0-9.]+)',
        'avg_walking_time': r'Average Walking Time[:\s]+([0-9.]+)',
        'total_trips': r'Total Trips[:\s]+([0-9]+)',
        'failed_reservations': r'Failed Reservations[:\s]+([0-9]+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            try:
                metrics[key] = float(match.group(1))
            except:
                metrics[key] = match.group(1)
    
    return metrics

def main():
    """Run all scenario groups"""
    RESULTS_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_results = {}
    
    print("\n" + "="*70)
    print("EXPERIMENTAL ANALYSIS - Running All Scenario Groups")
    print("="*70)
    
    for group_name, scenarios in SCENARIO_GROUPS.items():
        print(f"\n\n{'#'*70}")
        print(f"# GROUP: {group_name}")
        print(f"{'#'*70}\n")
        
        group_results = {}
        
        for scenario_name in scenarios:
            scenario_file = SCENARIOS_DIR / scenario_name
            
            if not scenario_file.exists():
                print(f"⚠️  SKIP: {scenario_name} not found")
                continue
            
            # Run scenario
            output = run_scenario(scenario_file)
            
            if output:
                # Extract metrics
                metrics = extract_metrics(output)
                group_results[scenario_name] = metrics
                
                # Print summary
                print(f"\n📊 Results for {scenario_file.stem}:")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
            else:
                group_results[scenario_name] = {"error": "Failed to run"}
        
        all_results[group_name] = group_results
    
    # Save results
    results_file = RESULTS_DIR / f"experiment_results_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n\n{'='*70}")
    print(f"✅ ALL EXPERIMENTS COMPLETE")
    print(f"{'='*70}")
    print(f"\nResults saved to: {results_file}")
    print(f"\nNext steps:")
    print(f"  1. Review results in {results_file}")
    print(f"  2. Create comparison graphs")
    print(f"  3. Write observations for report")
    
    return results_file

if __name__ == "__main__":
    main()
