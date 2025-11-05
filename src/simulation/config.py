"""
Configuration file for the Car Sharing Simulation.
Contains all main simulation parameters.

Now supports YAML-based overrides: set environment variable SIM_CONFIG_FILE
to a YAML file path, or invoke the CLI `python -m src.simulation --config path`.
"""

import os
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # Optional dependency; JSON-only fallback

from .logging_setup import get_logger

__all__ = [
    'SIMULATION_END_TIME', 'MAX_USERS', 'MAP_WIDTH', 'MAP_HEIGHT',
    'NUM_CARS', 'CAR_MAX_CHARGE', 'CAR_CHARGING_THRESHOLD',
    'BASE_USER_ARRIVAL_RATE', 'USER_RESERVATION_RATE', 'USER_PICKUP_RATE',
    'WALKING_SPEED', 'MAX_PICKUP_DISTANCE', 'NO_CAR_RETRY_RATE',
    'USER_MAX_RESERVATION_ATTEMPTS', 'get_current_arrival_rate',
    'get_traffic_factor_for_position', 'TIME_PERIODS', 'TRAFFIC_TIME_MULTIPLIERS',
    'ENABLE_BINNING', 'BIN_INTERVAL', 'CONFIDENCE_LEVEL',
    'logger'
]

logger = get_logger(__name__)


# =============================================================================
# GENERAL SIMULATION PARAMETERS
# =============================================================================

# Simulation time
SIMULATION_END_TIME =  525600
MAX_USERS = 500
# Map dimensions
MAP_WIDTH = 100.0  # km
MAP_HEIGHT = 100.0  # km

# =============================================================================
# STATISTICAL ANALYSIS PARAMETERS (Binning and Transient Detection)
# =============================================================================

# Enable binning to collect periodic snapshots for transient detection and CI
ENABLE_BINNING = True

# Bin interval in simulation minutes (how often to snapshot metrics)
BIN_INTERVAL = 60  # 30 minutes

# Confidence level for confidence intervals (e.g., 0.95 for 95%)
CONFIDENCE_LEVEL = 0.95

# System type: 'STATIONARY' or 'CYCLE_STATIONARY'
# STATIONARY: parameters don't vary with time - focus on transient detection
# CYCLE_STATIONARY: parameters have daily cycles - focus on confidence intervals
SYSTEM_TYPE = 'STATIONARY'

# =============================================================================
# CAR PARAMETERS
# =============================================================================

# Number of cars in the simulation
NUM_CARS = 20

# Battery parameters
CAR_MAX_CHARGE = 100  # kWh
CAR_CHARGING_THRESHOLD = 20  # kWh - threshold to go to charging
CAR_CONSUMPTION_BASE = 0.2  # kWh per km
CAR_CONSUMPTION_VARIANCE = 0.05  # ±variance in consumption

# =============================================================================
# USER PARAMETERS
# =============================================================================

# User arrival process (Poisson)
BASE_USER_ARRIVAL_RATE = 1/10  # users per hour (base rate)

def get_current_arrival_rate(time):
    """Calculate the current user arrival rate based on time of day"""
    minutes_of_day = time % 1440
    for period, (start, end) in TIME_PERIODS.items():
        if start <= minutes_of_day < end:
            return BASE_USER_ARRIVAL_RATE * DEMAND_TIME_MULTIPLIERS[period]
    return BASE_USER_ARRIVAL_RATE  # Default rate

# Reservation process (Poisson)
USER_RESERVATION_RATE = 1/4800  # reservations per hour

# Car pickup process (Poisson)
USER_PICKUP_RATE = 1/30  # pickups per hour

# Walking speed
WALKING_SPEED = 50  

# Maximum distance a user is willing to walk to pick up a car
MAX_PICKUP_DISTANCE = 30.0  # * 0.1 km

# Retry rate when no cars are available
NO_CAR_RETRY_RATE = 60  # attempts per hour
# How many reservation attempts a user will make before giving up
USER_MAX_RESERVATION_ATTEMPTS = 3

# =============================================================================
# CHARGING STATION PARAMETERS
# =============================================================================

# Number of charging stations
NUM_CHARGING_STATIONS = 5

# Charging power (range)
CHARGING_POWER_MIN = 30  # kW
CHARGING_POWER_MAX = 70  # kW

# Station positions (if empty, generated randomly)
CHARGING_STATION_POSITIONS = [
    (20, 20), (80, 20), (20, 80), (80, 80), (50, 50)
]

# =============================================================================
# CAR RELOCATOR PARAMETERS
# =============================================================================

# Number of car relocators
NUM_RELOCATORS = 3

# Relocator speed range (km/h)
RELOCATOR_SPEED_MIN = 50  # km/h
RELOCATOR_SPEED_MAX = 70  # km/h
RELOCATOR_SPEED = 60  # km/h (average, kept for compatibility)

# =============================================================================
# ROAD MAP PARAMETERS
# =============================================================================

# Road grid dimensions
ROAD_GRID_SIZE = 15  # km between nodes

# Variability in node positions
NODE_POSITION_VARIANCE = 3  # km

# =============================================================================
# TRAFFIC ZONE PARAMETERS
# =============================================================================

# Time periods for dynamic traffic patterns (in minutes from start of day)
TIME_PERIODS = {
    'EARLY_MORNING': (0, 360),    # 00:00 - 06:00
    'MORNING_RUSH': (360, 600),   # 06:00 - 10:00
    'MIDDAY': (600, 900),         # 10:00 - 15:00
    'EVENING_RUSH': (900, 1140),  # 15:00 - 19:00
    'EVENING': (1140, 1440)       # 19:00 - 24:00
}

# Traffic multipliers for different time periods
TRAFFIC_TIME_MULTIPLIERS = {
    'EARLY_MORNING': 0.5,   # Light traffic
    'MORNING_RUSH': 2.0,    # Heavy traffic
    'MIDDAY': 1.0,         # Normal traffic
    'EVENING_RUSH': 2.0,    # Heavy traffic
    'EVENING': 0.7         # Moderate traffic
}

# Demand multipliers for different time periods
DEMAND_TIME_MULTIPLIERS = {
    'EARLY_MORNING': 0.3,   # Low demand
    'MORNING_RUSH': 2.0,    # High demand
    'MIDDAY': 1.0,         # Normal demand
    'EVENING_RUSH': 1.8,    # High demand
    'EVENING': 0.6         # Low demand
}

# Traffic zone definitions with base factors and rush hour modifiers
TRAFFIC_ZONES = {
    'center': {
        'bounds': (30, 30, 70, 70),
        'base_traffic_factor': 2.5,
        'description': 'Central zone - heavy traffic',
        'rush_hour_multiplier': 1.5  # Additional multiplier during rush hours
    },
    'residential_nw': {
        'bounds': (0, 50, 30, 100),
        'base_traffic_factor': 0.7,
        'description': 'Northwest residential zone - light traffic',
        'rush_hour_multiplier': 1.2  # More traffic during rush hours
    },
    'residential_se': {
        'bounds': (50, 0, 100, 50),
        'base_traffic_factor': 0.7,
        'description': 'Southeast residential zone - light traffic',
        'rush_hour_multiplier': 1.2  # More traffic during rush hours
    },
    'commercial': {
        'bounds': (20, 20, 80, 80),
        'base_traffic_factor': 1.8,
        'description': 'Commercial zone - medium-high traffic',
        'rush_hour_multiplier': 1.3  # Significant increase during rush hours
    },
    'industrial': {
        'bounds': (0, 0, 20, 20),
        'base_traffic_factor': 0.5,
        'description': 'Industrial zone - very light traffic',
        'rush_hour_multiplier': 1.4  # Big increase during rush hours due to shift changes
    }
}

# =============================================================================
# LOGGING PARAMETERS
# =============================================================================

# Logging detail level
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR

# Enable/disable specific logging
LOG_CAR_MOVEMENTS = True
LOG_CHARGING_EVENTS = True
LOG_RELOCATOR_EVENTS = True
LOG_USER_EVENTS = True

# =============================================================================
# PERFORMANCE PARAMETERS
# =============================================================================

# Visualization update interval (in hours)
VISUALIZATION_UPDATE_INTERVAL = 0.1

# =============================================================================
# VISUALIZATION PARAMETERS
# =============================================================================

# Enable/disable visualization
VISUALIZATION_ENABLED = False
REAL_TIME_VISUALIZATION = True

# Figure dimensions
FIGURE_WIDTH = 12
FIGURE_HEIGHT = 10

# Colors for different car states
CAR_COLORS = {
    "available": "green",
    "reserved": "blue",
    "in_use": "blue",
    "charging": "orange",
    "discharged": "red",
    "needs_charging": "yellow",
}

# Colors for relocator states
RELOCATOR_COLORS = {
    "available": "cyan",
    "busy": "brown",
}

# Color for charging stations
CHARGING_STATION_COLOR = "purple"

# Colors for traffic zones
TRAFFIC_ZONE_COLORS = {
    "city_center": "red",
    "industrial_area": "orange",
    "residential_area": "green",
    "shopping_district": "yellow",
}

# Icons for visualization
CAR_ICON = "🚗"  # Car icon
CHARGING_STATION_ICON = "⚡"  # Charging station icon
RELOCATOR_ICON = "🔄"  # Relocator icon
USER_ICON = "👤"  # User icon
DISCHARGED_CAR_ICON = "🚫"  # Discharged car icon
CHARGING_CAR_ICON = "⚡"  # Charging car icon
NEEDS_CHARGING_CAR_ICON = "⚠️"  # Car that needs charging icon

# =============================================================================
# DEBUGGING PARAMETERS
# =============================================================================

# Enable debug mode
DEBUG_MODE = False

# Print detailed statistics
PRINT_DETAILED_STATS = True

# Save log to file
SAVE_LOG_TO_FILE = False
LOG_FILE_PATH = 'simulation.log'
# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_time(minutes):
    """Convert simulation minutes to readable time format"""
    total_minutes = int(minutes)
    days = total_minutes // 1440  # 24 * 60
    remaining_minutes = total_minutes % 1440
    hours = remaining_minutes // 60
    mins = remaining_minutes % 60
    return f"Day {days+1}, {hours:02d}:{mins:02d}"

def format_duration(minutes: float) -> str:
    """Format a duration given in minutes as Hh MMm (no day calendar)."""
    try:
        total_minutes = int(round(minutes))
    except Exception:
        total_minutes = 0
    hours = total_minutes // 60
    mins = total_minutes % 60
    return f"{hours}h {mins:02d}m"

def format_distance(km):
    """Format distances in a more realistic way
    Converts simulation kilometers to meters if less than 1km
    NOTE: Output-only scaling — divide displayed km by 10 without changing logic.
    """
    try:
        scaled_km = km / 10.0
    except Exception:
        scaled_km = 0.0
    if scaled_km < 1:
        return f"{int(scaled_km * 1000)}m"
    return f"{scaled_km:.1f}km"

def format_location(coord, decimals: int = 2):
    """Format a 2D coordinate tuple with limited decimal precision.
    Example: (12.34567, 98.76543) -> "(12.35, 98.77)" when decimals=2
    """
    try:
        x, y = coord
        return f"({x:.{decimals}f}, {y:.{decimals}f})"
    except Exception:
        # Fallback to plain string if input unexpected
        return str(coord)

def get_traffic_factor_for_position(x, y, time=0):
    """Returns the traffic factor for a position and time"""
    # Get base traffic factor from zone
    base_factor = 1.0
    current_zone = None
    for zone_name, zone_data in TRAFFIC_ZONES.items():
        x1, y1, x2, y2 = zone_data['bounds']
        if x1 <= x <= x2 and y1 <= y <= y2:
            base_factor = zone_data['base_traffic_factor']
            current_zone = zone_data
            break
    
    # Apply time-based multiplier
    minutes_of_day = time % 1440
    for period, (start, end) in TIME_PERIODS.items():
        if start <= minutes_of_day < end:
            time_multiplier = TRAFFIC_TIME_MULTIPLIERS[period]
            # Apply additional rush hour multiplier if in a zone during rush hour
            if current_zone and period in ['MORNING_RUSH', 'EVENING_RUSH']:
                rush_multiplier = current_zone.get('rush_hour_multiplier', 1.0)
                return base_factor * time_multiplier * rush_multiplier
            return base_factor * time_multiplier
            
    return base_factor  # Default case

def get_zone_description(x, y):
    """Returns the zone description for a position"""
    for zone_name, zone_data in TRAFFIC_ZONES.items():
        x1, y1, x2, y2 = zone_data['bounds']
        if x1 <= x <= x2 and y1 <= y <= y2:
            return zone_data['description']
    return "Unspecified zone"

def print_configuration_summary():
    """Print a configuration summary"""
    print("=" * 60)
    print("CAR SHARING SIMULATION CONFIGURATION")
    print("=" * 60)
    print(f"Simulation time: {SIMULATION_END_TIME} hours")
    # Scale output distances by 1/10 for display only
    print(f"Map dimensions: {format_distance(MAP_WIDTH)}x{format_distance(MAP_HEIGHT)}")
    print(f"Number of cars: {NUM_CARS}")
    print(f"Number of stations: {NUM_CHARGING_STATIONS}")
    print(f"Number of relocators: {NUM_RELOCATORS}")
    print(f"Charging threshold: {CAR_CHARGING_THRESHOLD} kWh")
    print(f"Traffic zones: {len(TRAFFIC_ZONES)}")
    print("=" * 60)


# =============================================================================
# YAML CONFIG LOADING
# =============================================================================

def _apply_overrides(mapping: Dict[str, Any]) -> None:
    """Apply overrides from a mapping to module-level uppercase symbols only.
    Nested dicts (like TRAFFIC_ZONES) are assigned wholesale if present.
    """
    g = globals()
    for k, v in mapping.items():
        if not isinstance(k, str):
            continue
        if k.isupper() and k in g:
            g[k] = v


def load_config_from_mapping(mapping: Dict[str, Any]) -> None:
    """Public: apply mapping of overrides to config module."""
    _apply_overrides(mapping)


def load_config_from_file(path: str) -> None:
    """Load configuration overrides from a YAML (preferred) or JSON file."""
    if not os.path.exists(path):
        logger.warning(f"Config file not found: {path}")
        return
    data: Dict[str, Any] = {}
    try:
        if (yaml is not None) and (path.lower().endswith(('.yml', '.yaml'))):
            with open(path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f) or {}
        else:
            # Fallback: try JSON for .json
            import json
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
        if not isinstance(loaded, dict):
            logger.warning(f"Config file must contain a mapping at top-level: {path}")
            return
        data = loaded
    except Exception as e:
        logger.warning(f"Failed to load config from {path}: {e}")
        return
    _apply_overrides(data)


# Auto-load from environment if provided BEFORE modules import values
_ENV_CONFIG_FILE = os.environ.get('SIM_CONFIG_FILE')
if _ENV_CONFIG_FILE:
    load_config_from_file(_ENV_CONFIG_FILE)
