import random
from .Car import Car
from ..config import (
    NUM_CHARGING_STATIONS, CHARGING_POWER_MIN, CHARGING_POWER_MAX,
    CHARGING_STATION_POSITIONS, MAP_WIDTH, MAP_HEIGHT, format_time, logger
)
from ..metrics import Metrics


class ChargingStation:
    stations = []
    
    def __init__(self, location, charging_power=50, capacity=2):
        """
        Inizializza una stazione di ricarica
        location: posizione della stazione (x, y)
        charging_power: potenza di ricarica in kW
        capacity: numero massimo di auto che possono caricare contemporaneamente
        """
        self.location = location
        self.charging_power = charging_power
        self.capacity = capacity
        self.station_id = len(ChargingStation.stations) + 1
        self.charging_cars = []  # macchine attualmente in ricarica
        ChargingStation.stations.append(self)
    
    def start_charging(self, car, current_time):
        """Inizia la ricarica di una macchina"""
        if car not in self.charging_cars:
            self.charging_cars.append(car)
            car.status = "charging"
            # Record charging session start
            Metrics.record_charging_session()
            # Record queue length
            Metrics.record_station_queue(len(self.charging_cars))
            # Record car state change
            if hasattr(car, 'last_state_change'):
                idle_time = current_time - car.last_state_change
                Metrics.record_car_state_time("available", idle_time)
            car.last_state_change = current_time  # Update state change timestamp
            logger.info(f"[{format_time(current_time)}] Car {car.car_id} started charging at station {self.station_id}")
    
    def stop_charging(self, car, current_time):
        """Termina la ricarica di una macchina"""
        if car in self.charging_cars:
            self.charging_cars.remove(car)
            car.status = "available"
            # Record car state change
            if hasattr(car, 'last_state_change'):
                charging_time = current_time - car.last_state_change
                Metrics.record_car_state_time("charging", charging_time)
            car.last_state_change = current_time
            # Record new queue length after car leaves
            Metrics.record_station_queue(len(self.charging_cars))
            logger.info(f"[{format_time(current_time)}] Car {car.car_id} finished charging at station {self.station_id}")
    
    def charge_cars(self, time_delta):
        """Ricarica tutte le macchine nella stazione"""
        for car in self.charging_cars[:]:  # Usa una copia per evitare problemi durante l'iterazione
            # Calcola quanta energia caricare in base al tempo trascorso
            energy_added = self.charging_power * time_delta / 60  # Converti minuti in ore
            car.charge(energy_added)
            
            # Se la macchina è completamente carica, rimuovila dalla stazione
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


def charging_event(time, payload, simulator):
    """Evento per gestire la ricarica delle macchine"""
    car = payload
    
    # Trova la stazione più vicina
    station = ChargingStation.get_nearest_station(car.location)
    
    if station:
        # Calcola il tempo per raggiungere la stazione
        distance_to_station = (
            (station.location[0] - car.location[0]) ** 2
            + (station.location[1] - car.location[1]) ** 2
        ) ** 0.5
        
        # Assumiamo che la macchina si muova automaticamente verso la stazione
        travel_time = distance_to_station / 30  # 30 km/h velocità media
        
        # Programma l'arrivo alla stazione
        arrival_time = time + travel_time
        simulator.schedule_event(arrival_time, arrive_at_station_event, (car, station))


def arrive_at_station_event(time, payload, simulator):
    """Evento quando una macchina arriva alla stazione di ricarica"""
    car, station = payload
    
    logger.info(
        f"[{format_time(time)}] Car {car.car_id} arrived at charging station {station.station_id}"
    )
    
    # Inizia la ricarica
    station.start_charging(car, time)
    
    # Calcola il tempo necessario per la ricarica completa
    energy_needed = car.max_charge - car.charge_level
    charging_time = energy_needed / station.charging_power  # in ore
    
    # Programma il completamento della ricarica
    completion_time = time + charging_time
    simulator.schedule_event(completion_time, charging_complete_event, (car, station))


def charging_complete_event(time, payload, simulator):
    """Evento quando la ricarica è completata"""
    car, station = payload
    
    logger.info(
        f"[{format_time(time)}] Car {car.car_id} completed charging at station {station.station_id}"
    )
    
    # Completa la ricarica
    energy_added = car.max_charge - car.charge_level
    car.charge_level = car.max_charge
    station.stop_charging(car, time)
