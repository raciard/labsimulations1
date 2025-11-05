"""
Discrete Event Simulation for Car Sharing System.
Main simulator class and execution logic.
"""

import queue
from . import config
from .metrics import Metrics
from .visualization import SimulationVisualizer
from .events import user_subscription_event, bin_collection_event
from .Entities import Car as car_mod
from .infrastructure import charging_station as charging_station_mod
from .Entities import car_relocator as car_relocator_mod
from .infrastructure import road_map as road_map_mod


class Simulator:
    """Discrete event simulator using Future Event Set (FES) pattern."""
    
    def __init__(self):
        """Initialize the simulator with empty FES and logger."""
        self.FES = queue.PriorityQueue()
        self.logger = config.logger
        self.road_map = None
        self.visualizer = None
    
    def schedule_event(self, event_time, event_function, payload):
        """Schedule an event to occur at a specific time.
        
        Args:
            event_time: Time when event should occur
            event_function: Function to call for this event
            payload: Data to pass to event function
        """
        self.FES.put((event_time, event_function, payload))
    
    def get_next_event(self):
        """Retrieve the next event from the FES.
        
        Returns:
            Tuple of (event_time, event_function, payload)
        """
        return self.FES.get()
    
    def _initialize_entities(self):
        """Initialize all simulation entities."""
        # Initialize road map
        self.road_map = road_map_mod.RoadMap(
            width=int(config.MAP_WIDTH),
            height=int(config.MAP_HEIGHT)
        )
        self.logger.info("Initialized road map with traffic zones")
        
        # Initialize cars
        for _ in range(config.NUM_CARS):
            car_mod.Car()
        self.logger.info(f"Initialized {config.NUM_CARS} cars")
        
        # Initialize charging stations
        charging_station_mod.ChargingStation.initialize_stations()
        self.logger.info(
            f"Initialized {len(charging_station_mod.ChargingStation.stations)} charging stations"
        )
        
        # Initialize relocators
        car_relocator_mod.CarRelocator.initialize_relocators()
        self.logger.info(
            f"Initialized {len(car_relocator_mod.CarRelocator.relocators)} relocators"
        )
    
    def _initialize_visualization(self):
        """Initialize visualization if enabled."""
        if config.VISUALIZATION_ENABLED:
            self.visualizer = SimulationVisualizer(self.road_map)
            self.logger.info("Visualization enabled")
    
    def _schedule_initial_events(self):
        """Schedule the initial events to start the simulation."""
        # Schedule first user arrival
        self.schedule_event(0, user_subscription_event, ())
        
        # Schedule first bin collection if enabled
        if config.ENABLE_BINNING:
            self.schedule_event(config.BIN_INTERVAL, bin_collection_event, ())
            self.logger.info(
                f"Binning enabled: snapshots every {config.BIN_INTERVAL} minutes"
            )
    
    def simulate(self, end_time):
        """Run the simulation until end_time.
        
        Args:
            end_time: Simulation end time in minutes
        """
        current_time = 0
        
        # Initialize all components
        self._initialize_entities()
        self._initialize_visualization()
        self._schedule_initial_events()
        
        self.logger.info(f"Starting simulation (end time: {end_time} minutes)")
        
        # Main event loop
        while not self.FES.empty():
            event_time, event_function, payload = self.get_next_event()
            
            # Stop if we've passed end time
            if event_time > end_time:
                break
            
            current_time = event_time
            
            # Execute event
            event_function(current_time, payload, self)
            
            # Update visualization if enabled
            if self.visualizer:
                self.visualizer.update(current_time)
        
        self.logger.info(f"Simulation completed at time {current_time:.2f}")


def run():
    """Main entry point to run the simulation."""
    # Print configuration summary
    config.print_configuration_summary()
    
    # Create and run simulator
    sim = Simulator()
    sim.simulate(config.SIMULATION_END_TIME)
    
    # Print and export metrics
    Metrics.print_metrics()
    Metrics.export_summary_json()


if __name__ == "__main__":
    run()
