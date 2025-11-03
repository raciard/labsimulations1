import random
from ..config import (
    CAR_MAX_CHARGE, CAR_CHARGING_THRESHOLD, CAR_CONSUMPTION_BASE, 
    CAR_CONSUMPTION_VARIANCE, MAP_WIDTH, MAP_HEIGHT,
    format_time, format_distance, logger
)


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

    def __init__(self):
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

    def update_location(self, new_location):
        self.location = new_location

    def reserve(self):
        self.status = "reserved"

    def free_up(self):
        self.status = "available"

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
