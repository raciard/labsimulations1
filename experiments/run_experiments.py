import os
import json
import tempfile
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

METRICS_KEYS = [
    'Reservation Success Rate',
    'Total Reservations',
    'Average Attempts Before Success',
    'Total Trips',
    'Average Trip Distance',
    'Total Distance Traveled',
    'In-Use Rate',
    'Charging Rate',
    'Idle Rate',
    'Total Charging Sessions',
    'Average Queue Length',
]

def run_simulator(summary_json_path: str | None = None, config_yaml_path: str | None = None) -> str:
    env = os.environ.copy()
    python_path = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(ROOT) + os.pathsep + python_path
    if summary_json_path:
        env['SIM_SUMMARY_JSON'] = summary_json_path
    cmd = [sys.executable, '-m', 'src.simulation']
    if config_yaml_path:
        cmd += ['--config', config_yaml_path]
    proc = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    return proc.stdout


def parse_metrics(output: str) -> dict:
    metrics = {}
    for key in METRICS_KEYS:
        m = re.search(rf"{re.escape(key)}:\s*(.*)", output)
        if m:
            metrics[key] = m.group(1).strip()
    return metrics


def parse_metrics_json(path: str) -> dict:
    """Parse the JSON summary file into the display keys used by the summary table."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            'Reservation Success Rate': data.get('reservation_success_rate_pct_str', '-'),
            'Total Reservations': str(data.get('total_reservations', '-')),
            'Average Attempts Before Success': data.get('average_attempts_before_success_str', '-') or str(data.get('average_attempts_before_success', '-')),
            'Total Trips': str(data.get('total_trips', '-')),
            'Average Trip Distance': data.get('average_trip_distance_str', '-'),
            'Total Distance Traveled': data.get('total_distance_traveled_str', '-'),
            'In-Use Rate': data.get('in_use_rate_pct_str', '-'),
            'Charging Rate': data.get('charging_rate_pct_str', '-'),
            'Idle Rate': data.get('idle_rate_pct_str', '-'),
            'Total Charging Sessions': str(data.get('total_charging_sessions', '-')),
            'Average Queue Length': data.get('average_queue_length_str', '-'),
        }
    except Exception:
        return {}


def print_summary(results):
    # Simple aligned print
    print("\nEXPERIMENT SUMMARY")
    print("="*80)
    # header
    headers = ["Scenario"] + METRICS_KEYS
    print(" | ".join(headers))
    print("-"*80)
    for name, metrics in results:
        row = [name] + [metrics.get(k, '-') for k in METRICS_KEYS]
        print(" | ".join(row))
    print("="*80)


def main():
    scenarios = [
        ("baseline", None),
        ("high_demand_x2", ROOT / 'configs' / 'scenarios' / 'high_demand_x2.yaml'),
        ("large_fleet_x2", ROOT / 'configs' / 'scenarios' / 'large_fleet_x2.yaml'),
        ("wide_pickup_radius", ROOT / 'configs' / 'scenarios' / 'wide_pickup_radius.yaml'),
        ("fewer_stations", ROOT / 'configs' / 'scenarios' / 'fewer_stations.yaml'),
    ]

    results = []

    for name, config_path in scenarios:
        print(f"\n>>> Running scenario: {name} overrides={config_path if config_path else {}}")

        # Create a temp file for the JSON summary
        with tempfile.NamedTemporaryFile(prefix=f"summary_{name}_", suffix='.json', delete=False) as tf:
            summary_path = tf.name

        out = run_simulator(summary_path, str(config_path) if config_path else None)
        # Prefer JSON summary; fallback to regex on stdout
        metrics = parse_metrics_json(summary_path)
        if not metrics:
            metrics = parse_metrics(out)
        results.append((name, metrics))

        # Cleanup temp files
        try:
            os.unlink(summary_path)
        except Exception:
            pass

    print_summary(results)


if __name__ == '__main__':
    main()
