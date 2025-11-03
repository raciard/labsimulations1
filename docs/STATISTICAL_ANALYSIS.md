# Statistical Analysis Features

## Overview

The simulation now includes automatic binning and statistical analysis capabilities to:
1. **Detect transient phases** - Identify when the system reaches steady-state
2. **Compute confidence intervals** - Provide statistical bounds on metrics

## Configuration

Add these parameters to your YAML config or modify `src/simulation/config.py`:

```yaml
ENABLE_BINNING: true          # Enable periodic metrics snapshots
BIN_INTERVAL: 720             # Snapshot interval in simulation minutes (e.g., 720 = 12 hours)
CONFIDENCE_LEVEL: 0.95        # Confidence level for intervals (0.95 = 95%)
```

## How It Works

### Bin Collection
- A pseudo-event is automatically scheduled at regular intervals (BIN_INTERVAL)
- At each bin boundary, the system captures a snapshot of cumulative metrics
- Delta metrics are computed for each bin (e.g., trips in this bin, success rate in this bin)

### Transient Detection (Welch's Method)
- Uses moving averages to detect when metrics stabilize
- Compares tail behavior to identify steady-state onset
- Reports: transient end bin, steady-state mean, and standard deviation

### Confidence Intervals
- Computed using batch means method
- Applied to steady-state data (after transient is excluded)
- Reports: mean, half-width, lower bound, upper bound

## Metrics Analyzed

The system automatically analyzes:
- **Reservation Success Rate** - Fraction of reservations that succeed
- **Average Attempts Before Success** - How many tries users need
- **Car Utilization Rate** - Fraction of time cars are in use

## Example Output

```
STATISTICAL ANALYSIS (60 bins collected)
========================================

Reservation Success Rate:
  Transient phase: bins 0-3 (~48h 00m)
  Steady-state mean: 0.8940
  Steady-state std: 0.2346
  95% CI (steady-state): [0.8325, 0.9554]

Average Attempts:
  Transient phase: bins 0-22 (~276h 00m)
  Steady-state mean: 1.2383
  Steady-state std: 0.2972
  95% CI (steady-state): [1.1425, 1.3340]

Car Utilization Rate:
  Transient phase: bins 0-1 (~24h 00m)
  Steady-state mean: 0.4387
  Steady-state std: 0.3309
  95% CI (steady-state): [0.3535, 0.5238]
```

## Interpretation

### Transient Phase
- Shows how many bins (and time duration) before steady-state
- Longer transients suggest the system needs time to stabilize
- Can vary by metric (some stabilize faster than others)

### Confidence Intervals
- Narrower intervals = more precise estimates
- If CI doesn't include a target value, system differs significantly
- Use to compare scenarios: non-overlapping CIs indicate real differences

## Usage Example

```bash
# Run with binning enabled
python3 -m src.simulation --config configs/scenarios/long_run_analysis.yaml
```

## Advanced Usage

Access bins programmatically:

```python
from src.simulation.metrics import Metrics

# After simulation
bins = Metrics.get_bins()
for i, bin_data in enumerate(bins):
    print(f"Bin {i}: {bin_data['bin_total_trips']} trips, "
          f"success rate = {bin_data['bin_success_rate']:.2%}")

# Custom analysis
transient_end, mean, std = Metrics.detect_transient_welch('bin_avg_attempts')
mean, hw, lower, upper = Metrics.compute_confidence_interval(
    'bin_utilization_rate', 
    confidence=0.99,
    start_bin=transient_end
)
```

## Choosing Bin Interval

- **Too small** (e.g., 60 min): Noisy bins, harder to detect trends
- **Too large** (e.g., 10080 min = 1 week): Fewer bins, less resolution
- **Recommended**: 720-1440 minutes (12-24 hours) for day-scale dynamics

## Lab Objectives Addressed

1. **Transient Detection**: Welch's method automatically identifies steady-state onset
2. **Confidence Intervals**: Batch means provides statistical bounds for non-stationary metrics
3. **Automation**: Pseudo-events eliminate manual intervention; results printed automatically
