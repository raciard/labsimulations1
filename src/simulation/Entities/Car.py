import random
from ..config import (
    CAR_MAX_CHARGE, CAR_CHARGING_THRESHOLD, CAR_CONSUMPTION_BASE, 
    CAR_CONSUMPTION_VARIANCE, MAP_WIDTH, MAP_HEIGHT,
    format_time, format_distance, logger
)
from ..metrics import Metrics

class Car:
    cars: list = []

    _id_counter: int = 0
    
    @staticmethod
    def _get_next_id() -> int:
        Car._id_counter += 1
        return Car._id_counter
    
    def calculate_energy_consumption(self, distance):
        """Calculate energy consumption for a given distance"""
        return distance * (CAR_CONSUMPTION_BASE + random.uniform(-CAR_CONSUMPTION_VARIANCE, CAR_CONSUMPTION_VARIANCE))

    def __init__(self, time=0):
        # random location
        # maximum charging level
        # status available by default
        self.location = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
        self.max_charge = CAR_MAX_CHARGE
        self.charge_level = CAR_MAX_CHARGE
        self.charging_threshold = CAR_CHARGING_THRESHOLD
        self.status = "available"  # available, reserved, in_use, charging, discharged, needs_charging
        self.car_id = Car._get_next_id()
        self.total_distance = 0  # total distance traveled
        self.cars.append(self)
        self.idle_time = 0
        self.in_use_time = 0
        self.last_state_change = time
        self.charging_time = 0

    def update_location(self, new_location):
        self.location = new_location

    def reserve(self, time):
        self.status = "reserved"
        self.idle_time += time - self.last_state_change
        self.last_state_change = time
    
    def start_use(self, time):
        """Transition car to in_use state when user picks it up"""
        if self.status == "reserved":
            # No time to add since reserved is a transition state
            pass
        else:
            # Track time in previous state
            self.idle_time += time - self.last_state_change
        
        self.status = "in_use"
        self.last_state_change = time

    def free_up(self, time):
        self.status = "available"
        self.in_use_time += time - self.last_state_change
        self.last_state_change = time
    
    def start_charging(self, time):
        """Transition car to charging state"""
        if self.status != "charging":
            # Track time in previous state
            if self.status == "in_use":
                self.in_use_time += time - self.last_state_change
            elif self.status in ["available", "needs_charging", "discharged"]:
                self.idle_time += time - self.last_state_change
            
            self.status = "charging"
            self.last_state_change = time
    
    def stop_charging(self, time):
        """Transition car out of charging state"""
        if self.status == "charging":
            self.charging_time += time - self.last_state_change
            self.status = "available"
            self.last_state_change = time


    def update_charge(self, distance, time=None):
        """Update the charge level based on distance traveled"""
        # Consumption with variability
        consumption = distance * (CAR_CONSUMPTION_BASE + random.uniform(-CAR_CONSUMPTION_VARIANCE, CAR_CONSUMPTION_VARIANCE))
        self.charge_level -= consumption
        self.total_distance += distance
        
        # If the battery is completely discharged, the car is no longer usable
        if self.charge_level <= 0:
            self.charge_level = 0
            self.status = "discharged"
            if time is not None:
                logger.warning(f"[{format_time(time)}] Car {self.car_id} is discharged and needs charging!")
        # If the battery drops below the threshold, mark as needs charging
        elif self.charge_level <= self.charging_threshold and self.status == "available":
            self.status = "needs_charging"
            if time is not None:
                logger.info(f"[{format_time(time)}] Car {self.car_id} needs charging (charge: {self.charge_level:.2f} kWh)")
    
    def is_available(self):
        """Check if the car is available (not discharged, not in use, and not needing charge)"""
        return self.status == "available" and self.charge_level > self.charging_threshold
    
    def charge(self, amount, time=None):
        """Charge the car"""
        self.charge_level = min(self.max_charge, self.charge_level + amount)
        if self.charge_level > 0 and self.status == "discharged":
            self.status = "available"
            if time is not None:
                logger.info(f"[{format_time(time)}] Car {self.car_id} is now charged and available!")
    
    def get_charge_percentage(self):
        """Return the charge percentage"""
        return (self.charge_level / self.max_charge) * 100

    @staticmethod
    def get_nearest_car(location):
        nearest_car = None
        min_distance = float("inf")
        for car in Car.cars:
            if car.is_available():  # Use the new method that also checks charge
                distance = (
                    (car.location[0] - location[0]) ** 2
                    + (car.location[1] - location[1]) ** 2
                ) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    nearest_car = car
        return nearest_car
