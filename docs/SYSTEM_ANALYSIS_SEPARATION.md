# System Analysis Separation

## Overview

The simulation now separates statistical analysis based on system type:

### 1. **STATIONARY System**
- **Goal**: Automated transient phase detection
- **Analysis Focus**: Identifying when the system reaches steady-state
- **Method**: Welch's method with moving averages
- **Output**: Transient end time, steady-state mean and std deviation

### 2. **CYCLE-STATIONARY System**
- **Goal**: Confidence intervals for time-varying metrics
- **Analysis Focus**: Statistical bounds on metrics that vary within repeating cycles
- **Method**: Batch means with phase grouping (by time-of-day)
- **Output**: 95% confidence intervals for each phase of the daily cycle

## Configuration

Add to your scenario YAML file:

```yaml
SYSTEM_TYPE: 'STATIONARY'  # or 'CYCLE_STATIONARY'
```

## Usage Examples

### Stationary System

```bash
python3 -m src.simulation --config configs/scenarios/stationary.yaml
```

**Output includes:**
```
🔍 STATIONARY SYSTEM ANALYSIS
Focus: Automated transient phase detection
----------------------------------------

Reservation Success Rate:
  ⏱ Transient phase: bins 0-12 (12h 00m)
  📊 Steady-state mean: 0.8723
  📈 Steady-state std: 0.0453
  ✓ Steady-state bins: 156
```

### Cycle-Stationary System

```bash
python3 -m src.simulation --config configs/scenarios/cycle_stationary.yaml
```

**Output includes:**
```
📈 CYCLE-STATIONARY SYSTEM ANALYSIS
Focus: Confidence intervals for time-varying metrics
----------------------------------------

Success Rate by Time-of-Day (24h cycle):
  Phase 0 (~00:00): mean=65.23%, 95% CI=[62.14, 68.32]%, n=14
  Phase 1 (~06:00): mean=52.41%, 95% CI=[48.87, 55.95]%, n=14
  Phase 2 (~12:00): mean=71.56%, 95% CI=[68.92, 74.20]%, n=14
  Phase 3 (~18:00): mean=58.33%, 95% CI=[55.12, 61.54]%, n=14
```

## Implementation Details

### Transient Detection (Stationary)

The `detect_transient_welch()` method:
1. Computes moving averages of bin metrics
2. Analyzes tail behavior (last 50% of data)
3. Identifies first point entering steady-state range
4. Returns transient end bin, steady-state statistics

**Key metrics analyzed:**
- Reservation success rate
- Average attempts before success
- Car utilization rate
- Average trip distance

### Confidence Intervals (Cycle-Stationary)

The `compute_cycle_stationary_intervals()` method:
1. Groups bins by position in daily cycle (e.g., all 6AM bins together)
2. Computes sample mean and variance for each phase
3. Calculates 95% CI using t-distribution
4. Returns phase-specific confidence intervals

**Key metrics analyzed:**
- Success rate by time-of-day
- Average attempts by time-of-day
- Utilization by time-of-day

## Scenario Files

### `configs/scenarios/stationary.yaml`
- All time multipliers = 1.0 (constant parameters)
- Rush hour multipliers disabled
- Focuses on pure steady-state behavior

### `configs/scenarios/cycle_stationary.yaml`
- Time-varying multipliers (rush hours, night periods)
- Rush hour effects enabled
- Daily cycles with repeating patterns

## Interpretation Guide

### Stationary System
- **Short transient** (< 1 day): System stabilizes quickly
- **Long transient** (> 3 days): May need parameter adjustment
- **High std deviation**: System has high variability even in steady-state

### Cycle-Stationary System
- **Narrow CIs**: Consistent behavior across cycles
- **Wide CIs**: High variability in that phase
- **Non-overlapping CIs**: Phases are statistically different
- **Morning/evening peaks**: Rush hour effects clearly visible

## Tips

1. **For stationary systems**: Run long enough to get sufficient steady-state samples
2. **For cycle-stationary systems**: Run multiple complete cycles (≥7 days recommended)
3. **Bin interval**: Use 30-60 minutes for good temporal resolution
4. **Validation**: Compare transient length across different metrics
