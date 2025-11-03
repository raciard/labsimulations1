"""
Discrete Event Simulation for Car Sharing System.
Main simulator class and execution logic.
"""

import queue
from . import config
from .metrics import Metrics
from .visualization import SimulationVisualizer
from .events import user_subscription_event, bin_collection_event
from .Entities import user as user_mod
from .Entities import Car as car_mod
from .Entities import charging_station as charging_station_mod
from .Entities import car_relocator as car_relocator_mod
from .Entities import road_map as road_map_mod


class Simulator:
    """Discrete event simulator using Future Event Set (FES) pattern."""
    
    def __init__(self):
        """Initialize the simulator with empty FES and logger."""
        self.FES = queue.PriorityQueue()
        self.logger = config.logger
        self.road_map = None
        self.visualizer = None
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
            width=config.MAP_WIDTH,
            height=config.MAP_HEIGHT
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

    def _draw_road_network(self):
        """Disegna la rete stradale"""
        nodes_data, edges_data = self.road_map.get_road_network_data()

        # Disegna le strade
        for edge in edges_data:
            start_x, start_y = edge["start"]
            end_x, end_y = edge["end"]
            self.ax.plot(
                [start_x, end_x], [start_y, end_y], "k-", alpha=0.3, linewidth=0.5
            )

        # Disegna i nodi
        for node in nodes_data:
            color = (
                "red"
                if node["traffic_factor"] > 2.0
                else "orange"
                if node["traffic_factor"] > 1.5
                else "green"
            )
            self.ax.scatter(node["x"], node["y"], c=color, s=20, alpha=0.6)

    def _draw_traffic_zones(self):
        """Disegna le zone di traffico"""
        zones = self.road_map.traffic_zones

        # Colori per diverse zone
        zone_colors = config.TRAFFIC_ZONE_COLORS

        for zone_name, zone_data in zones.items():
            x1, y1, x2, y2 = zone_data["bounds"]
            color = zone_colors.get(zone_name, "gray")

            # Disegna rettangolo per la zona
            from matplotlib.patches import Rectangle

            rect = Rectangle(
                (x1, y1),
                x2 - x1,
                y2 - y1,
                facecolor=color,
                alpha=0.1,
                edgecolor=color,
                linewidth=2,
            )
            self.ax.add_patch(rect)

            # Aggiungi etichetta
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            self.ax.text(
                center_x,
                center_y,
                zone_name.replace("_", " ").title(),
                ha="center",
                va="center",
                fontsize=8,
                alpha=0.7,
            )

    def update(self, current_time):
        """Aggiorna il grafico con la posizione attuale delle auto e stazioni di ricarica"""
        # Colori diversi per diversi stati delle macchine
        car_colors = []
        car_xs = []
        car_ys = []

        for car in car_mod.Car.cars:
            car_xs.append(car.location[0])
            car_ys.append(car.location[1])

            if car.status == "discharged":
                car_colors.append(config.CAR_COLORS["discharged"])
            elif car.status == "charging":
                car_colors.append(config.CAR_COLORS["charging"])
            elif car.status == "needs_charging":
                car_colors.append(config.CAR_COLORS["needs_charging"])
            elif car.status == "available":
                car_colors.append(config.CAR_COLORS["available"])
            else:
                car_colors.append(config.CAR_COLORS["reserved"])

        # Posizioni delle stazioni di ricarica
        station_xs = [station.location[0] for station in charging_station_mod.ChargingStation.stations]
        station_ys = [station.location[1] for station in charging_station_mod.ChargingStation.stations]

        # Posizioni dei relocator
        relocator_xs = [relocator.location[0] for relocator in car_relocator_mod.CarRelocator.relocators]
        relocator_ys = [relocator.location[1] for relocator in car_relocator_mod.CarRelocator.relocators]
        relocator_colors = [
            config.RELOCATOR_COLORS["busy"] if relocator.is_busy else config.RELOCATOR_COLORS["available"]
            for relocator in car_relocator_mod.CarRelocator.relocators
        ]

        # Remove old texts
        for text in self.car_texts:
            text.remove()
        for text in self.station_texts:
            text.remove()
        for text in self.relocator_texts:
            text.remove()
        
        self.car_texts = []
        self.station_texts = []
        self.relocator_texts = []

        # Add cars with appropriate icons
        for x, y, status in zip(car_xs, car_ys, [car.status for car in car_mod.Car.cars]):
            if status == "discharged":
                icon = config.DISCHARGED_CAR_ICON
            elif status == "charging":
                icon = config.CHARGING_CAR_ICON
            elif status == "needs_charging":
                icon = config.NEEDS_CHARGING_CAR_ICON
            else:
                icon = config.CAR_ICON
            text = self.ax.text(x, y, icon, ha='center', va='center', fontsize=10)
            self.car_texts.append(text)

        # Add charging stations
        for x, y in zip(station_xs, station_ys):
            text = self.ax.text(x, y, config.CHARGING_STATION_ICON, ha='center', va='center', fontsize=12)
            self.station_texts.append(text)

        # Add relocators
        for x, y, is_busy in zip(relocator_xs, relocator_ys, [r.is_busy for r in car_relocator_mod.CarRelocator.relocators]):
            text = self.ax.text(x, y, config.RELOCATOR_ICON, ha='center', va='center', fontsize=10, 
                              color='brown' if is_busy else 'cyan')
            self.relocator_texts.append(text)

        # Crea la legenda con i colori delle macchine
        if not hasattr(self, "legend_created"):
            from matplotlib.patches import Patch

            legend_elements = [
                self.ax.text(0, 0, config.CAR_ICON, color="black", label="Macchine Disponibili"),
                self.ax.text(0, 0, config.DISCHARGED_CAR_ICON, color="black", label="Macchine Scariche"),
                self.ax.text(0, 0, config.CHARGING_CAR_ICON, color="black", label="Macchine in Ricarica"),
                self.ax.text(0, 0, config.NEEDS_CHARGING_CAR_ICON, color="black", label="Macchine Bisognose di Ricarica"),
                self.ax.text(0, 0, config.CHARGING_STATION_ICON, color="black", label="Stazioni di Ricarica"),
                self.ax.text(0, 0, config.RELOCATOR_ICON, color="cyan", label="Relocator Disponibili"),
                self.ax.text(0, 0, config.RELOCATOR_ICON, color="brown", label="Relocator Occupati"),
            ]
            self.ax.legend(
                handles=legend_elements, loc="upper right", bbox_to_anchor=(1, 1)
            )
            self.legend_created = True

        self.ax.set_title(f"Posizione delle auto e stazioni - tempo {current_time:.2f}")
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


class Simulator:
    # future event set
    def __init__(self):
        self.FES = queue.PriorityQueue()
        # use centralized logger
        self.logger = config.logger
        # metrics subsystem removed — do not create a SimulationMetrics instance
        self.metrics = None

    def schedule_event(self, event_time, event, payload):
        # put with priority event_time
        self.FES.put((event_time, event, payload))

    def get_next_event(self):
        return self.FES.get()

    def print_metrics_report(self):
        """Print the final simulation metrics report"""
        print("\n" + "=" * 60)
        print("SIMULATION METRICS REPORT")
        print("=" * 60)
        print("Metrics subsystem removed: no metrics to report.")
        print("\n" + "=" * 60)

    def simulate(self, end_time):
        current_time = 0

        # Inizializza la mappa stradale
        self.road_map = road_map_mod.RoadMap(width=100, height=100)
        self.logger.info("Initialized road map with traffic zones")

        if config.VISUALIZATION_ENABLED:
            visualizer = Visualizer(self.road_map)

        # Inizializza le macchine
        for _ in range(config.NUM_CARS):
            car = car_mod.Car()

        # Inizializza le stazioni di ricarica
        charging_station_mod.ChargingStation.initialize_stations()
        self.logger.info(
            f"Initialized {len(charging_station_mod.ChargingStation.stations)} charging stations"
        )
        # Initialize metrics for each station
        # previously we sampled stations into metrics here; metrics removed

        # Inizializza i Car Relocator
        car_relocator_mod.CarRelocator.initialize_relocators()
        self.logger.info(f"Initialized {len(car_relocator_mod.CarRelocator.relocators)} car relocators")

        # schedule a random user arrival at time 0
        self.schedule_event(0, user_subscription, ())
        
        # Schedule first bin collection event if binning is enabled
        if config.ENABLE_BINNING:
            self.schedule_event(config.BIN_INTERVAL, bin_collection_event, ())
            self.logger.info(f"Binning enabled: collecting snapshots every {config.BIN_INTERVAL} minutes")
        
        while not self.FES.empty():
            event_time, event, payload = self.get_next_event()
            if event_time > end_time:
                break
            current_time = event_time
            event(current_time, payload, self)
            if config.VISUALIZATION_ENABLED:
                visualizer.update(current_time)

def run():
    # print configuration summary
    config.print_configuration_summary()
    sim = Simulator()
    sim.simulate(config.SIMULATION_END_TIME)
    Metrics.print_metrics()
    Metrics.export_summary_json()


if __name__ == "__main__":
    # Accept no arguments here; prefer running via `python -m src.simulation --config <file>`
    run()
