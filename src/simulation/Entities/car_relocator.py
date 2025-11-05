import random
from ..config import (
    NUM_RELOCATORS, RELOCATOR_SPEED_MIN, RELOCATOR_SPEED_MAX,
    MAP_WIDTH, MAP_HEIGHT
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
