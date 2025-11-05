import random
from ..Entities.Car import Car
from ..config import (
    NUM_CHARGING_STATIONS, CHARGING_POWER_MIN, CHARGING_POWER_MAX,
    CHARGING_STATION_POSITIONS, MAP_WIDTH, MAP_HEIGHT, format_time, logger
)
from ..metrics import Metrics


class ChargingStation:
    stations = []
    
    def __init__(self, location, charging_power=50, capacity=2):
        self.location = location
        self.charging_power = charging_power
        self.capacity = capacity
        self.station_id = len(ChargingStation.stations) + 1
        self.charging_cars = []  # macchine attualmente in ricarica
        ChargingStation.stations.append(self)
    
    def start_charging(self, car, current_time):
        if car not in self.charging_cars:
            self.charging_cars.append(car)
            # Use car's method to transition to charging state
            car.start_charging(current_time)
            # Record charging session start
            Metrics.record_charging_session()
            # Record queue length
            Metrics.record_station_queue(len(self.charging_cars))
            logger.info(f"[{format_time(current_time)}] Car {car.car_id} started charging at station {self.station_id}")
    
    def stop_charging(self, car, current_time):
        if car in self.charging_cars:
            self.charging_cars.remove(car)
            # Use car's method to transition out of charging state
            car.stop_charging(current_time)
            # Record new queue length after car leaves
            Metrics.record_station_queue(len(self.charging_cars))
            logger.info(f"[{format_time(current_time)}] Car {car.car_id} finished charging at station {self.station_id}")
    
    def charge_cars(self, time_delta):
        for car in self.charging_cars[:]:  
            energy_added = self.charging_power * time_delta / 60 
            car.charge(energy_added)
            
            if car.charge_level >= car.max_charge:
                self.stop_charging(car)
    
    @staticmethod
    def get_nearest_station(location):
        """Trova la stazione di ricarica più vicina"""
        nearest_station = None
        min_distance = float("inf")
        
        for station in ChargingStation.stations:
            distance = (
                (station.location[0] - location[0]) ** 2
                + (station.location[1] - location[1]) ** 2
            ) ** 0.5
            if distance < min_distance:
                min_distance = distance
                nearest_station = station
        
        return nearest_station
    
    @staticmethod
    def initialize_stations():
        """Inizializza alcune stazioni di ricarica nella simulazione"""
        # Usa le posizioni dal config o genera casualmente
        if CHARGING_STATION_POSITIONS:
            positions = CHARGING_STATION_POSITIONS[:NUM_CHARGING_STATIONS]
        else:
            positions = []
            for _ in range(NUM_CHARGING_STATIONS):
                pos = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
                positions.append(pos)
        
        for pos in positions:
            charging_power = random.uniform(CHARGING_POWER_MIN, CHARGING_POWER_MAX)
            ChargingStation(pos, charging_power=charging_power)
