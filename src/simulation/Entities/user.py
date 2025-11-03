import random
from .Car import Car
from .car_relocator import relocate_car_event
from ..config import (
    BASE_USER_ARRIVAL_RATE, USER_RESERVATION_RATE, USER_PICKUP_RATE,
    NO_CAR_RETRY_RATE, WALKING_SPEED, MAP_WIDTH, MAP_HEIGHT, MAX_USERS,
    USER_MAX_RESERVATION_ATTEMPTS, MAX_PICKUP_DISTANCE, get_current_arrival_rate,
    format_time, format_distance, format_location, logger
)

from ..metrics import Metrics
def dropoff_event(time, payload, simulator):
    (user, car, start_location, end_location) = payload
    # Calcola la distanza percorsa usando la mappa stradale
    distance_traveled = distance_between(start_location, end_location, simulator.road_map)
    
    logger.info(
        "[{}] Car {} dropped off by user {} at location {} after traveling {}".format(
            format_time(time), car.car_id, user.user_id, format_location(end_location), format_distance(distance_traveled)
        )
    )
    
    # Record trip metrics
    Metrics.record_trip(distance_traveled)
    # Record car state change
    trip_duration = time - car.last_state_change if hasattr(car, 'last_state_change') else 0
    Metrics.record_car_state_time("in_use", trip_duration)
    car.last_state_change = time  # Update state change timestamp
    
    # Aggiorna la posizione e la carica della macchina
    car.update_location(end_location)
    car.update_charge(distance_traveled)
    
    # Libera la macchina solo se ha abbastanza carica
    if car.charge_level > car.charging_threshold:
        car.free_up()
    else:
        # La macchina ha bisogno di ricarica (scarica o sotto soglia)
        if car.charge_level <= 0:
            logger.warning(f"[{format_time(time)}] Car {car.car_id} is discharged and needs charging!")
        else:
            logger.warning(f"[{format_time(time)}] Car {car.car_id} needs charging (charge: {car.charge_level:.1f} kWh)")
        
        # Programma l'evento di spostamento con relocator
        simulator.schedule_event(time, relocate_car_event, car)

    # Schedule user's next reservation (rates are per hour -> convert to minutes)
    res_time = time + 60 * random.expovariate(USER_RESERVATION_RATE)
    # random location
    location = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
    payload = (user, location)
    simulator.schedule_event(res_time, reservation_event, payload)


def pickup_event(time, payload, simulator):
    (user, car, start_location, end_location) = payload
    logger.info(
        f"[{format_time(time)}] User {user.user_id} picked up car {car.car_id} at location {format_location(start_location)}"
    )
    # Record walking time: from successful reservation to pickup
    success_time = getattr(user, 'reservation_success_time', None)
    if success_time is not None:
        walking_time = time - success_time
        if walking_time >= 0:
            Metrics.record_walking_time(walking_time)
    
    # Record car state change from available/reserved to in_use
    idle_time = time - car.last_state_change if hasattr(car, 'last_state_change') else 0
    Metrics.record_car_state_time("available", idle_time)
    car.last_state_change = time  # Update state change timestamp
    
    # schedule dropoff after random time (rates are per hour -> convert to minutes)
    dropoff_time = time + 60 * random.expovariate(USER_PICKUP_RATE)
    # Genera una destinazione casuale per il viaggio
    destination = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
    car.reserve()
    # Passa la destinazione al dropoff event per calcolare la distanza
    # Reset timers after completing the pickup
    user.first_reservation_time = None
    user.reservation_success_time = None
    simulator.schedule_event(dropoff_time, dropoff_event, (user, car, start_location, destination))
    


def distance_between(loc1, loc2, road_map=None):
    """Calcola la distanza tra due posizioni usando la mappa stradale se disponibile"""
    if road_map:
        return road_map.calculate_route_distance(loc1, loc2)
    else:
        # Fallback alla distanza euclidea
        return ((loc1[0] - loc2[0]) ** 2 + (loc1[1] - loc2[1]) ** 2) ** 0.5


def reservation_event(time, payload, simulator):
    (user, location) = payload
    logger.info(
        f"[{format_time(time)}] User {user.user_id} made a reservation at location {format_location(location)}"
    )
    # ensure we record the first time this user requested a reservation
    if getattr(user, 'first_reservation_time', None) is None:
        user.first_reservation_time = time
    # schedule next reservation after random time

    # find nearest available car 
    car = Car.get_nearest_car(location) 
    
    # Check if a car is available and within acceptable distance
    if car is not None:
        distance = distance_between(location, car.location, simulator.road_map)
        if distance > MAX_PICKUP_DISTANCE:
            car = None  # Car is too far, treat as if no car available
            logger.warning(
                f"[{format_time(time)}] Nearest car for user {user.user_id} is too far ("
                f"{format_distance(distance)} > {format_distance(MAX_PICKUP_DISTANCE)})"
            )
    
    # schedule car pickup after walking time based on distance from car
    if car is None:
        logger.warning(
            f"[{format_time(time)}] No car available for user {user.user_id}"
        )
        # increment the user's failed attempt counter and possibly stop retrying
        attempts = getattr(user, 'reservation_attempts', 0) + 1
        user.reservation_attempts = attempts
        if attempts >= USER_MAX_RESERVATION_ATTEMPTS:
            logger.warning(f"[{format_time(time)}] User {user.user_id} reached max reservation attempts ({attempts}); will stop retrying")
            Metrics.record_failed_reservation()
            user.first_reservation_time = None  # reset first reservation time
            user.reservation_attempts = 0  # reset attempts
        # schedule next reservation
            new_res_time = time + 60 * random.expovariate(USER_RESERVATION_RATE)
            new_location = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
            simulator.schedule_event(new_res_time, reservation_event, (user, new_location))
            return
        # retry after some time (per-hour rate -> convert to minutes)
        next_trial = time + 60 * random.expovariate(NO_CAR_RETRY_RATE)
        simulator.schedule_event(next_trial, reservation_event, (user, location))
        return
    # record attempts before success (failed attempts + this successful one)
    attempts_before_success = getattr(user, 'reservation_attempts', 0) + 1
    Metrics.record_attempts_before_success(attempts_before_success)
    # mark successful reservation
    Metrics.record_successful_reservation()
    # reset attempts on success
    if hasattr(user, 'reservation_attempts'):
        user.reservation_attempts = 0
    # mark car as reserved and record wait time up to reservation success
    car.reserve()
    # Wait time = from first reservation attempt to reservation success
    first_res = getattr(user, 'first_reservation_time', None)
    if first_res is not None:
        wait_time = time - first_res
        if wait_time >= 0:
            Metrics.record_wait_time(wait_time)
    # mark the time of successful reservation for walking-time measurement
    user.reservation_success_time = time
    # Calcola la distanza usando la mappa stradale
    distance = distance_between(location, car.location, simulator.road_map)

    walking_speed = WALKING_SPEED  # km/h
    # Calcola il tempo di camminata considerando il traffico
    if hasattr(simulator, 'road_map'):
        walking_time = simulator.road_map.calculate_route_time(location, car.location, walking_speed)
    else:
        walking_time = distance / walking_speed
    
    # Aggiungi un po' di casualità (in ore)
    walking_time += random.uniform(-0.5, 0.5)

    # schedule car pickup event (convert walking hours -> minutes)
    pickup_time = time + max(0.0, 60.0 * walking_time)
    simulator.schedule_event(pickup_time, pickup_event, (user, car, location, location))

    # if no car available, log and return

    return


class User:
    _id_counter: int = 0
    
    @staticmethod
    def _get_next_id() -> int:
        User._id_counter += 1
        return User._id_counter

    def __init__(self, simulator, time):
        # progressive id for each user
        self.user_id = User._get_next_id()
        self.simulator = simulator
        self.reservation_time = None  # Track when user makes a reservation
        
        # after random time (Poisson process) user makes reservation (per hour -> minutes)
        res_time = time + 60 * random.expovariate(USER_RESERVATION_RATE)
        # random location
        location = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
        self.reservation_time = res_time  # Set reservation time
        payload = (self, location)
        simulator.schedule_event(res_time, reservation_event, payload)
