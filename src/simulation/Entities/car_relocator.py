import random
from .Car import Car
from .charging_station import ChargingStation
from ..config import (
    NUM_RELOCATORS, RELOCATOR_SPEED_MIN, RELOCATOR_SPEED_MAX,
    MAP_WIDTH, MAP_HEIGHT, format_time, logger
)


class CarRelocator:
    relocators = []
    
    def __init__(self, relocator_id, speed=30):
        """
        Initialize a Car Relocator
        speed: movement speed in km/h
        """
        self.relocator_id = relocator_id
        self.speed = speed  # km/h
        self.is_busy = False
        self.current_task = None
        self.location = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))  # random initial position
        CarRelocator.relocators.append(self)
    
    def is_available(self):
        """Check if the relocator is available"""
        return not self.is_busy
    
    def assign_task(self, car, destination):
        """Assign a task to the relocator"""
        if self.is_busy:
            return False
        
        self.is_busy = True
        self.current_task = {
            'car': car,
            'destination': destination,
            'start_location': car.location
        }
        return True
    
    def complete_task(self):
        """Complete the current task"""
        if self.current_task:
            car = self.current_task['car']
            destination = self.current_task['destination']
            
            # Move the car to the destination
            car.update_location(destination)
            self.location = destination  # The relocator also moves
            
            # Free the relocator
            self.is_busy = False
            # compute distance and duration (approx)
            distance = (
                (destination[0] - self.current_task['start_location'][0]) ** 2 +
                (destination[1] - self.current_task['start_location'][1]) ** 2
            ) ** 0.5
            # duration approximated from relocator speed
            duration = distance / self.speed if self.speed > 0 else 0

            # metrics are recorded by the event handler (simulator has context)

            self.current_task = None

            return True
        return False
    
    def calculate_travel_time(self, start_location, end_location, road_map=None):
        """Calculate the time needed to move from one position to another"""
        if road_map:
            # Use the road map to calculate time considering traffic
            return road_map.calculate_route_time(start_location, end_location, self.speed)
        else:
            # Fallback to Euclidean distance
            distance = (
                (end_location[0] - start_location[0]) ** 2
                + (end_location[1] - start_location[1]) ** 2
            ) ** 0.5
            return distance / self.speed
    
    @staticmethod
    def get_available_relocator():
        """Trova un relocator disponibile"""
        for relocator in CarRelocator.relocators:
            if relocator.is_available():
                return relocator
        return None
    
    @staticmethod
    def initialize_relocators(num_relocators=None):
        """Inizializza un numero limitato di relocator"""
        num_relocators = num_relocators or NUM_RELOCATORS
        for i in range(num_relocators):
            speed = random.uniform(RELOCATOR_SPEED_MIN, RELOCATOR_SPEED_MAX)
            CarRelocator(i + 1, speed=speed)


def relocate_car_event(time, payload, simulator):
    """Evento per spostare una macchina verso una stazione di ricarica"""
    car = payload
    
    # Trova un relocator disponibile
    relocator = CarRelocator.get_available_relocator()
    
    if relocator is None:
        # Nessun relocator disponibile, riprova più tardi
        logger.warning(f"[{format_time(time)}] No relocator available for car {car.car_id}, retrying in 5 minutes")
        retry_time = time + 5  # minutes
        simulator.schedule_event(retry_time, relocate_car_event, car)
        return
    
    # Trova la stazione di ricarica più vicina
    station = ChargingStation.get_nearest_station(car.location)
    
    if station is None:
        logger.error(f"[{format_time(time)}] No charging station available for car {car.car_id}")
        return
    
    # Assegna il compito al relocator
    if relocator.assign_task(car, station.location):
        logger.info(
            f"[{format_time(time)}] Relocator {relocator.relocator_id} assigned to move car {car.car_id} to station {station.station_id}"
        )
        
        # Calcola il tempo necessario per raggiungere la stazione usando la mappa stradale
        travel_time = relocator.calculate_travel_time(car.location, station.location, simulator.road_map)
        
        # Programma l'arrivo alla stazione
        arrival_time = time + (travel_time * 60.0)  # convert hours to minutes
        simulator.schedule_event(arrival_time, arrive_at_station_with_relocator_event, (car, station, relocator))
    else:
        logger.error(f"[{format_time(time)}] Failed to assign relocator {relocator.relocator_id} to car {car.car_id}")


def arrive_at_station_with_relocator_event(time, payload, simulator):
    """Evento quando una macchina arriva alla stazione di ricarica con un relocator"""
    car, station, relocator = payload
    
    logger.info(f"[{format_time(time)}] Relocator {relocator.relocator_id} delivered car {car.car_id} to charging station {station.station_id}")
    
    # Completa il compito del relocator (record metrics before completing)
    if relocator.current_task:
        # metrics: relocator task was recorded here previously; removed
        relocator.complete_task()

    # metrics: charging_start was recorded here previously; removed
    station.start_charging(car, time)
    
    # Calcola il tempo necessario per la ricarica completa
    energy_needed = car.max_charge - car.charge_level
    charging_time = energy_needed / station.charging_power  # in ore
    
    # Programma il completamento della ricarica
    completion_time = time + (charging_time * 60.0)  # convert to minutes
    simulator.schedule_event(completion_time, charging_complete_event, (car, station))


def charging_complete_event(time, payload, simulator):
    """Evento quando la ricarica è completata"""
    car, station = payload
    
    logger.info(
        f"[{format_time(time)}] Car {car.car_id} completed charging at station {station.station_id}"
    )
    
    # Completa la ricarica
    car.charge_level = car.max_charge
    station.stop_charging(car, time)
    
    # La macchina è ora disponibile per nuovi viaggi
    car.status = "available"
