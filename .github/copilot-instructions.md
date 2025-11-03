# Car Sharing Simulation - AI Agent Instructions

Python-based discrete event simulation modeling electric car sharing with charging infrastructure, relocators, and traffic-aware routing.

## Project Structure

```
src/simulation/          # Main simulation package (run as module)
├── __main__.py          # CLI entry point with --config support
├── simulator.py         # Simulator class with FES event loop
├── events.py            # Event handler functions
├── visualization.py     # SimulationVisualizer class (matplotlib)
├── config.py            # Configuration with YAML override support
├── metrics.py           # Statistical analysis, binning, transient detection
├── logging_setup.py     # JSON + console logging setup
└── Entities/            # Core domain models
    ├── Car.py           # EV fleet with charge management
    ├── user.py          # User lifecycle events
    ├── charging_station.py  # Station queuing and charging
    ├── car_relocator.py # Automated vehicle repositioning
    └── road_map.py      # NetworkX graph with traffic zones

experiments/             # Batch scenario runner
configs/                 # YAML configuration files
docs/                    # Statistical analysis documentation
```

## Architecture Deep Dive

### Event-Driven Simulation (FES Pattern)
- **All logic is event functions** in `events.py`: `def event_name_event(time, payload, simulator)` 
- Events chain via `simulator.schedule_event(next_time, next_event, payload)`
- Example flow: `user_subscription_event` → `reservation_event` → `pickup_event` → `dropoff_event` → `relocate_car_event`
- Critical: Events at time T can schedule future events but never modify past state

**Event naming convention**: All event functions end with `_event` suffix

### Configuration Override System
**Runtime config loading order**:
1. Defaults in `src/simulation/config.py` (uppercase module vars)
2. Override via `SIM_CONFIG_FILE` env var or `--config` CLI flag
3. `config.load_config_from_file()` merges YAML into module globals

**Pattern**: To add configurable parameter:
```python
# In config.py - define uppercase constant
NEW_PARAM = 42

# In your code - import and use
from ..config import NEW_PARAM

# Override in YAML
NEW_PARAM: 100
```

### Metrics System Architecture
**Two-tier design** (see `src/simulation/metrics.py`):
1. **Continuous tracking**: Static methods record events as they occur (`Metrics.record_trip()`)
2. **Binning subsystem**: Pseudo-event `bin_collection_event` takes periodic snapshots for transient detection

**Key pattern**: All metrics are static class variables, no instance needed:
```python
Metrics.record_successful_reservation()  # Called from event functions
Metrics.print_metrics()                   # Called at simulation end
Metrics.export_summary_json()             # Machine-readable output
```

**Statistical features** (enable with `ENABLE_BINNING: true`):
- Welch's method for transient detection
- Batch means confidence intervals 
- Cycle analysis for periodic behavior
- See `docs/STATISTICAL_ANALYSIS.md`

### Entity State Management
**Cars** (`Car.py`):
- States: `available`, `reserved`, `in_use`, `charging`, `discharged`, `needs_charging`
- Static registry pattern: `Car.cars` list tracks all instances
- Charge tracking: Check `.is_available()` (not just status) - accounts for charge threshold

**Relocators** (`car_relocator.py`):
- Singleton pool: `CarRelocator.relocators` and `.get_available_relocator()`
- Explicitly track `busy` state to prevent double-assignment

**Users** (`user.py`):
- Stateless entities - lifecycle managed purely through events
- Track reservation attempts via `user.reservation_attempts` attribute added at runtime

### Spatial Routing (road_map.py)
**NetworkX graph with traffic zones**:
- Grid-based road network (configurable `ROAD_GRID_SIZE`)
- Zone-based traffic factors (e.g., `city_center`, `industrial_area`)
- Time-of-day multipliers (rush hour vs. night)
- **Distance calculation**: Always use `road_map.calculate_route_distance(loc1, loc2)` not Euclidean

**Traffic factor composition**:
```python
final_factor = base_zone_factor × time_period_multiplier × rush_hour_multiplier
# Example: center (2.2) × morning_rush (1.8) × rush_multiplier (1.6) = 6.34x
```

## Critical Developer Workflows

### Running Simulations
```bash
# Basic run with default config
python3 -m src.simulation

# Override with YAML scenario
python3 -m src.simulation --config configs/scenarios/high_demand_x2.yaml

# Batch experiments (writes summary table)
python3 experiments/run_experiments.py
```

### Adding New Events
1. Define event function in `events.py` (or appropriate entity file):
   ```python
   def new_action_event(time, payload, simulator):
       # Unpack payload
       entity, param = payload
       
       # Update state
       entity.status = "new_state"
       
       # Schedule follow-up event
       next_time = time + compute_delay()
       simulator.schedule_event(next_time, next_event, new_payload)
   ```

2. Schedule initial event from another event or `simulator._schedule_initial_events()`

3. **Convention**: 
   - System-wide events go in `events.py`
   - Entity-specific events go in entity files (e.g., `user.py`)
   - All event functions end with `_event` suffix

### Configuration Patterns
**YAML override example** (`configs/example.yaml`):
```yaml
SIMULATION_END_TIME: 525600  # 1 year in minutes
NUM_CARS: 30
BASE_USER_ARRIVAL_RATE: 0.25  # users/hour

# Override nested structures wholesale
TRAFFIC_ZONES:
  downtown:
    bounds: [40, 40, 60, 60]
    base_traffic_factor: 2.5
```

**Access in code**:
```python
from . import config  # Import module, not individual constants
config.NUM_CARS  # Access as module attribute (picks up overrides)
```

### Logging Conventions
- Use centralized logger: `from .config import logger`
- Format helpers: `format_time()`, `format_distance()`, `format_location()`, `format_duration()`
- Example: `logger.info(f"[{format_time(time)}] User {user.user_id} reserved car {car.car_id}")`
- Structured JSON logs written to `simulation.log`

### Distance Display Scaling
**Internal vs. Display**: Simulation logic uses "internal km" but display divides by 10
- Inside code: distances are in raw simulation units
- Output only: `format_distance()` divides by 10 (e.g., 100 internal → "10.0km")
- **Never scale distances in calculation logic** - only in display strings

## Testing & Validation

No formal test suite currently. Validation via:
1. **Experiment runner**: `experiments/run_experiments.py` compares scenarios
2. **Metrics consistency**: Check reservation counts match trip counts
3. **Visual debugging**: Set `VISUALIZATION_ENABLED: true` in config

## Common Pitfalls

1. **Mutating car/relocator state without checking availability** → Double-assignments
   - Always use `.is_available()` for cars (not just `.status == "available"`)
   - Check `CarRelocator.get_available_relocator()` returns non-None

2. **Scheduling events in the past** → FES ordering breaks
   - Ensure `event_time >= current_time` when calling `schedule_event()`

3. **Forgetting to chain events** → Entities get "stuck"
   - Every terminal event should either free resources OR schedule next state

4. **Using Euclidean distance** → Unrealistic routing
   - Always use `road_map.calculate_route_distance()` for car movement

5. **Hardcoding config values** → Overrides don't work
   - Import from `config` module, never copy constants

## Extension Patterns

### Adding a New Entity Type
1. Create `src/simulation/Entities/new_entity.py`
2. Use static registry pattern: `class NewEntity: entities = []`
3. Initialize in `simulator.simulate()` before scheduling events
4. Define event functions for lifecycle in same file

### Adding Metrics
1. Add static class variable to `Metrics`: `_new_metric = 0`
2. Add recording method: `@staticmethod def record_new_metric(value): ...`
3. Add getter: `@staticmethod def get_new_metric(): ...`
4. Update `print_metrics()` and `get_summary_dict()` for output
5. If binning needed, add to `snapshot_bin()` delta computation

### Scenario Configuration
Create `configs/scenarios/my_scenario.yaml` with selective overrides:
```yaml
# Only override what changes from baseline
NUM_CARS: 50
BASE_USER_ARRIVAL_RATE: 0.5
```

Run via: `python3 -m src.simulation --config configs/scenarios/my_scenario.yaml`