# Code Organization - Event Consolidation

## Overview
All event functions have been consolidated into a single file (`src/simulation/events.py`) for better code organization and maintainability.

## Changes Made

### 1. Centralized Event Handling
All event functions are now located in `src/simulation/events.py`:

#### USER EVENTS (4 functions)
- `user_subscription_event` - Handles new user subscriptions
- `reservation_event` - Processes user reservation requests
- `pickup_event` - Handles car pickups by users
- `dropoff_event` - Processes car dropoffs

#### CAR RELOCATION EVENTS (3 functions)
- `relocate_car_event` - Initiates car relocation to charging station
- `arrive_at_station_with_relocator_event` - Handles arrival at charging station
- `charging_complete_event` - Processes charging completion

#### METRICS EVENTS (1 function)
- `bin_collection_event` - Collects periodic metrics snapshots

#### HELPER FUNCTIONS (1 function)
- `_distance_between` - Calculates distance using road map

### 2. Entity Files Cleaned Up
Entity files now contain **only class definitions**, not event logic:

- **`src/simulation/Entities/user.py`**
  - Removed: `reservation_event`, `pickup_event`, `dropoff_event`, `distance_between`
  - Kept: `User` class definition
  - Now imports `reservation_event` from `events` module

- **`src/simulation/Entities/car_relocator.py`**
  - Removed: `relocate_car_event`, `arrive_at_station_with_relocator_event`, `charging_complete_event`
  - Kept: `CarRelocator` class definition

- **`src/simulation/infrastructure/charging_station.py`**
  - Removed: `charging_event`, `arrive_at_station_event`, `charging_complete_event` (duplicate)
  - Kept: `ChargingStation` class definition

### 3. Benefits
- **Separation of Concerns**: Entity files define classes, `events.py` handles event logic
- **Centralized Event Management**: All events in one place for easy reference
- **Eliminated Duplicates**: Removed duplicate `charging_complete_event` that existed in two files
- **Better Organization**: Events grouped by category with clear section headers
- **Easier Maintenance**: Single file to modify when adding/updating event logic

## Project Structure After Consolidation

```
src/simulation/
├── events.py              # ALL EVENT FUNCTIONS (centralized)
├── simulator.py           # Main simulation loop (FES)
├── metrics.py            # Performance tracking
├── config.py             # Configuration management
├── Entities/             # Active participants (CLASSES ONLY)
│   ├── Car.py
│   ├── user.py
│   └── car_relocator.py
└── infrastructure/       # Physical systems (CLASSES ONLY)
    ├── road_map.py
    └── charging_station.py
```

## Usage Pattern
When adding new events:
1. Define the event function in `events.py`
2. Follow naming convention: `event_name_event(time, payload, simulator)`
3. Add to appropriate section (USER, CAR RELOCATION, METRICS, etc.)
4. Import and schedule from other modules as needed

## Testing
✓ Simulation runs successfully after consolidation
✓ No syntax errors in any modified files
✓ All event chains work correctly
