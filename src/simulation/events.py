"""
Event handlers for the discrete event simulation.
Each event function follows the pattern: event_function(time, payload, simulator)
"""

import random
from . import config
from .config import (
    BIN_INTERVAL, USER_RESERVATION_RATE, USER_PICKUP_RATE, NO_CAR_RETRY_RATE,
    WALKING_SPEED, MAP_WIDTH, MAP_HEIGHT, MAX_USERS, USER_MAX_RESERVATION_ATTEMPTS,
    MAX_PICKUP_DISTANCE, get_current_arrival_rate, format_time, format_distance,
    format_location, logger
)
from .metrics import Metrics


# ============================================================================
# USER EVENTS
# ============================================================================

def user_subscription_event(time, payload, simulator):
    """Handle new user subscription (arrival) event."""
    from .Entities import user as user_mod
    
    user = user_mod.User(simulator, time)
    simulator.logger.info(
        f"[{format_time(time)}] User {user.user_id} subscribed"
    )
    
    # Schedule next user arrival if under max limit
    if user_mod.User._id_counter < config.MAX_USERS:
        current_rate = get_current_arrival_rate(time)
        next_arrival_time = time + 60 * random.expovariate(current_rate)
        simulator.schedule_event(next_arrival_time, user_subscription_event, ())


def reservation_event(time, payload, simulator):
    """Handle user reservation attempt."""
    from .Entities.Car import Car
    
    (user, location) = payload
    logger.info(
        f"[{format_time(time)}] User {user.user_id} made a reservation at location {format_location(location)}"
    )
    
    # Record first reservation time
    if getattr(user, 'first_reservation_time', None) is None:
        user.first_reservation_time = time
    
    # Find nearest available car
    car = Car.get_nearest_car(location)
    
    # Check if car is within acceptable distance
    if car is not None:
        distance = _distance_between(location, car.location, simulator.road_map)
        if distance > MAX_PICKUP_DISTANCE:
            car = None
            logger.warning(
                f"[{format_time(time)}] Nearest car for user {user.user_id} is too far ("
                f"{format_distance(distance)} > {format_distance(MAX_PICKUP_DISTANCE)})"
            )
    
    # Handle no car available
    if car is None:
        logger.warning(f"[{format_time(time)}] No car available for user {user.user_id}")
        
        attempts = getattr(user, 'reservation_attempts', 0) + 1
        user.reservation_attempts = attempts
        
        if attempts >= USER_MAX_RESERVATION_ATTEMPTS:
            logger.warning(f"[{format_time(time)}] User {user.user_id} reached max attempts ({attempts})")
            Metrics.record_failed_reservation()
            user.first_reservation_time = None
            user.reservation_attempts = 0
            
            # Schedule next reservation
            new_res_time = time + 60 * random.expovariate(USER_RESERVATION_RATE)
            new_location = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
            simulator.schedule_event(new_res_time, reservation_event, (user, new_location))
            return
        
        # Retry
        next_trial = time + 60 * random.expovariate(NO_CAR_RETRY_RATE)
        simulator.schedule_event(next_trial, reservation_event, (user, location))
        return
    
    # Successful reservation
    attempts_before_success = getattr(user, 'reservation_attempts', 0) + 1
    Metrics.record_attempts_before_success(attempts_before_success)
    Metrics.record_successful_reservation()
    
    if hasattr(user, 'reservation_attempts'):
        user.reservation_attempts = 0
    
    car.reserve(time)
    
    # Record wait time
    first_res = getattr(user, 'first_reservation_time', None)
    if first_res is not None:
        wait_time = time - first_res
        if wait_time >= 0:
            Metrics.record_wait_time(wait_time)
    
    user.reservation_success_time = time
    
    # Calculate walking time
    distance = _distance_between(location, car.location, simulator.road_map)
    walking_speed = WALKING_SPEED
    
    if hasattr(simulator, 'road_map'):
        walking_time = simulator.road_map.calculate_route_time(location, car.location, walking_speed, time)
    else:
        walking_time = distance / walking_speed
    
    walking_time += random.uniform(-0.5, 0.5)
    
    # Schedule pickup
    pickup_time = time + max(0.0, 60.0 * walking_time)
    simulator.schedule_event(pickup_time, pickup_event, (user, car, location, location))


def pickup_event(time, payload, simulator):
    """Handle user picking up a car."""
    (user, car, start_location, end_location) = payload
    
    logger.info(
        f"[{format_time(time)}] User {user.user_id} picked up car {car.car_id} at location {format_location(start_location)}"
    )
    
    # Record walking time
    success_time = getattr(user, 'reservation_success_time', None)
    if success_time is not None:
        walking_time = time - success_time
        if walking_time >= 0:
            Metrics.record_walking_time(walking_time)
    
    
    # Generate destination and schedule dropoff
    destination = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
    dropoff_time = time + simulator.road_map.calculate_route_time(start_location, destination, speed=30, current_time=time) * 60
    
    car.start_use(time)  # Transition car to in_use state
    user.first_reservation_time = None
    user.reservation_success_time = None
    
    simulator.schedule_event(dropoff_time, dropoff_event, (user, car, start_location, destination))


def dropoff_event(time, payload, simulator):
    """Handle user dropping off a car."""
    (user, car, start_location, end_location) = payload
    
    distance_traveled = _distance_between(start_location, end_location, simulator.road_map)
    
    logger.info(
        "[{}] Car {} dropped off by user {} at location {} after traveling {}".format(
            format_time(time), car.car_id, user.user_id, format_location(end_location), format_distance(distance_traveled)
        )
    )
    
    # Record metrics
    Metrics.record_trip(distance_traveled)
    
    # Update car state
    car.update_location(end_location)
    car.update_charge(distance_traveled)
    
    # Check if car needs charging
    if car.charge_level > car.charging_threshold:
        car.free_up(time)
    else:
        if car.charge_level <= 0:
            logger.warning(f"[{format_time(time)}] Car {car.car_id} is discharged and needs charging!")
        else:
            logger.warning(f"[{format_time(time)}] Car {car.car_id} needs charging (charge: {car.charge_level:.1f} kWh)")
        
        simulator.schedule_event(time, relocate_car_event, car)
    
    # Schedule user's next reservation
    res_time = time + 60 * random.expovariate(USER_RESERVATION_RATE)
    location = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
    simulator.schedule_event(res_time, reservation_event, (user, location))


# ============================================================================
# CAR RELOCATION EVENTS
# ============================================================================

def relocate_car_event(time, payload, simulator):
    """Handle car relocation to charging station."""
    from .Entities.car_relocator import CarRelocator
    from .infrastructure.charging_station import ChargingStation
    
    car = payload
    
    # Find available relocator
    relocator = CarRelocator.get_available_relocator()
    
    if relocator is None:
        logger.warning(f"[{format_time(time)}] No relocator available for car {car.car_id}, retrying in 5 minutes")
        retry_time = time + 5
        simulator.schedule_event(retry_time, relocate_car_event, car)
        return
    
    # Find nearest station
    station = ChargingStation.get_nearest_station(car.location)
    
    if station is None:
        logger.error(f"[{format_time(time)}] No charging station available for car {car.car_id}")
        return
    
    # Assign task
    if relocator.assign_task(car, station.location):
        logger.info(
            f"[{format_time(time)}] Relocator {relocator.relocator_id} assigned to move car {car.car_id} to station {station.station_id}"
        )
        
        travel_time = relocator.calculate_travel_time(car.location, station.location, simulator.road_map)
        arrival_time = time + (travel_time * 60.0)
        
        simulator.schedule_event(arrival_time, arrive_at_station_with_relocator_event, (car, station, relocator))
    else:
        logger.error(f"[{format_time(time)}] Failed to assign relocator {relocator.relocator_id} to car {car.car_id}")


def arrive_at_station_with_relocator_event(time, payload, simulator):
    """Handle car arrival at charging station with relocator."""
    car, station, relocator = payload
    
    logger.info(f"[{format_time(time)}] Relocator {relocator.relocator_id} delivered car {car.car_id} to charging station {station.station_id}")
    
    # Complete relocator task
    if relocator.current_task:
        relocator.complete_task()
    
    # Start charging
    station.start_charging(car, time)
    
    # Calculate charging time
    energy_needed = car.max_charge - car.charge_level
    charging_time = 2  # hours
    
    completion_time = time + (charging_time * 60.0)  # convert to minutes
    simulator.schedule_event(completion_time, charging_complete_event, (car, station))


def charging_complete_event(time, payload, simulator):
    """Handle completion of car charging."""
    car, station = payload
    
    logger.info(f"[{format_time(time)}] Car {car.car_id} completed charging at station {station.station_id}")
    
    # Complete charging
    car.charge_level = car.max_charge
    station.stop_charging(car, time)
    car.status = "available"


# ============================================================================
# METRICS COLLECTION EVENT
# ============================================================================

def bin_collection_event(time, payload, simulator):
    """Collect a snapshot of current metrics into a bin for later analysis."""
    total_reservations = Metrics._successful_reservations + Metrics._failed_reservations
    if total_reservations > 0:
        Metrics.snapshot_bin(time)
    
    next_bin_time = time + BIN_INTERVAL
    simulator.schedule_event(next_bin_time, bin_collection_event, None)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _distance_between(loc1, loc2, road_map=None):
    """Calculate distance between two locations using road map if available."""
    if road_map:
        return road_map.calculate_route_distance(loc1, loc2)
    else:
        return ((loc1[0] - loc2[0]) ** 2 + (loc1[1] - loc2[1]) ** 2) ** 0.5
