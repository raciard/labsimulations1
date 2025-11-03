"""
Event handlers for the discrete event simulation.
Each event function follows the pattern: event_function(time, payload, simulator)
"""

import random
from . import config
from .config import BIN_INTERVAL
from .metrics import Metrics


def user_subscription_event(time, payload, simulator):
    """Handle new user subscription (arrival) event.
    
    Args:
        time: Current simulation time
        payload: Empty tuple (no data needed)
        simulator: Simulator instance
    """
    from .Entities import user as user_mod
    
    user = user_mod.User(simulator, time)
    simulator.logger.info(
        f"[{config.format_time(time)}] User {user.user_id} subscribed"
    )
    
    # Schedule next user arrival if under max limit
    if user_mod.User._id_counter < config.MAX_USERS:
        current_rate = config.get_current_arrival_rate(time)
        # Rates are per hour; simulation clock is in minutes
        next_arrival_time = time + 60 * random.expovariate(current_rate)
        simulator.schedule_event(next_arrival_time, user_subscription_event, ())


def bin_collection_event(time, payload, simulator):
    """Collect a snapshot of current metrics into a bin for later analysis."""
    # Only collect bins if there has been any activity (reservations)
    total_reservations = Metrics._successful_reservations + Metrics._failed_reservations
    if total_reservations > 0:
        Metrics.snapshot_bin(time)
    
    # Schedule next bin collection (simulator will stop scheduling if time exceeds end_time)
    next_bin_time = time + BIN_INTERVAL
    simulator.schedule_event(next_bin_time, bin_collection_event, None)
