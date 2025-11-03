"""
Visualization module for the car sharing simulation.
Handles all matplotlib-based real-time visualization.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from . import config
from .Entities import Car as car_mod
from .Entities import charging_station as charging_station_mod
from .Entities import car_relocator as car_relocator_mod


class SimulationVisualizer:
    """Handles real-time visualization of the simulation state."""
    
    def __init__(self, road_map):
        """Initialize the visualizer with a road map.
        
        Args:
            road_map: RoadMap instance to visualize
        """
        plt.rcParams['font.sans-serif'] = ['WOFF2']
        self.road_map = road_map
        self.legend_created = False
        
        # Create figure and axes
        self.fig, self.ax = plt.subplots(
            figsize=(config.FIGURE_WIDTH, config.FIGURE_HEIGHT)
        )
        self.ax.set_xlim(0, config.MAP_WIDTH)
        self.ax.set_ylim(0, config.MAP_HEIGHT)
        self.ax.set_title("Car Sharing Simulation with Road Map")
        self.ax.set_xlabel("X (km)")
        self.ax.set_ylabel("Y (km)")
        
        # Draw static elements
        self._draw_road_network()
        self._draw_traffic_zones()
        
        # Text annotations for dynamic elements
        self.car_texts = []
        self.station_texts = []
        self.relocator_texts = []
        
        # Enable interactive mode
        plt.ion()
        plt.show()
    
    def _draw_road_network(self):
        """Draw the road network on the visualization."""
        nodes_data, edges_data = self.road_map.get_road_network_data()
        
        # Draw edges (roads)
        for edge in edges_data:
            start_x, start_y = edge["start"]
            end_x, end_y = edge["end"]
            self.ax.plot(
                [start_x, end_x], [start_y, end_y],
                "k-", alpha=0.3, linewidth=0.5
            )
        
        # Draw nodes with color based on traffic factor
        for node in nodes_data:
            color = self._get_node_color(node["traffic_factor"])
            self.ax.scatter(
                node["x"], node["y"],
                c=color, s=20, alpha=0.6
            )
    
    def _get_node_color(self, traffic_factor):
        """Determine node color based on traffic factor."""
        if traffic_factor > 2.0:
            return "red"
        elif traffic_factor > 1.5:
            return "orange"
        else:
            return "green"
    
    def _draw_traffic_zones(self):
        """Draw traffic zones as colored rectangles."""
        zones = self.road_map.traffic_zones
        zone_colors = config.TRAFFIC_ZONE_COLORS
        
        for zone_name, zone_data in zones.items():
            x1, y1, x2, y2 = zone_data["bounds"]
            color = zone_colors.get(zone_name, "gray")
            
            # Draw zone rectangle
            rect = Rectangle(
                (x1, y1), x2 - x1, y2 - y1,
                facecolor=color, alpha=0.1,
                edgecolor=color, linewidth=2
            )
            self.ax.add_patch(rect)
            
            # Add zone label at center
            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
            self.ax.text(
                center_x, center_y,
                zone_name.replace("_", " ").title(),
                ha="center", va="center",
                fontsize=8, alpha=0.7
            )
    
    def update(self, current_time):
        """Update visualization with current simulation state.
        
        Args:
            current_time: Current simulation time in minutes
        """
        # Clear previous dynamic elements
        for txt in self.car_texts + self.station_texts + self.relocator_texts:
            txt.remove()
        self.car_texts.clear()
        self.station_texts.clear()
        self.relocator_texts.clear()
        
        # Update cars
        self._update_cars()
        
        # Update charging stations
        self._update_charging_stations()
        
        # Update relocators
        self._update_relocators()
        
        # Create legend if not already created
        if not self.legend_created:
            self._create_legend()
        
        # Update title with current time
        self.ax.set_title(f"Car Positions and Stations - Time {current_time:.2f}")
        
        # Refresh display
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
    
    def _update_cars(self):
        """Update car positions and colors based on status."""
        car_xs, car_ys, car_colors = [], [], []
        
        for car in car_mod.Car.cars:
            car_xs.append(car.location[0])
            car_ys.append(car.location[1])
            car_colors.append(self._get_car_color(car.status))
        
        # Draw cars as scatter plot
        if car_xs:
            self.ax.scatter(
                car_xs, car_ys,
                c=car_colors, s=100, marker='o',
                edgecolors='black', linewidths=0.5
            )
        
        # Add car icons
        for car in car_mod.Car.cars:
            icon = self._get_car_icon(car.status)
            txt = self.ax.text(
                car.location[0], car.location[1], icon,
                ha="center", va="center",
                fontsize=12, color="black"
            )
            self.car_texts.append(txt)
    
    def _get_car_color(self, status):
        """Get color for car based on status."""
        return config.CAR_COLORS.get(status, "gray")
    
    def _get_car_icon(self, status):
        """Get icon for car based on status."""
        if status == "discharged":
            return config.DISCHARGED_CAR_ICON
        elif status == "charging":
            return config.CHARGING_CAR_ICON
        elif status == "needs_charging":
            return config.NEEDS_CHARGING_CAR_ICON
        else:
            return config.CAR_ICON
    
    def _update_charging_stations(self):
        """Update charging station positions."""
        for station in charging_station_mod.ChargingStation.stations:
            txt = self.ax.text(
                station.location[0], station.location[1],
                config.CHARGING_STATION_ICON,
                ha="center", va="center",
                fontsize=16, color=config.CHARGING_STATION_COLOR
            )
            self.station_texts.append(txt)
    
    def _update_relocators(self):
        """Update relocator positions."""
        for relocator in car_relocator_mod.CarRelocator.relocators:
            color = (config.RELOCATOR_COLORS["busy"] 
                    if relocator.busy 
                    else config.RELOCATOR_COLORS["available"])
            txt = self.ax.text(
                relocator.location[0], relocator.location[1],
                config.RELOCATOR_ICON,
                ha="center", va="center",
                fontsize=14, color=color
            )
            self.relocator_texts.append(txt)
    
    def _create_legend(self):
        """Create legend for the visualization."""
        legend_elements = [
            self.ax.text(0, 0, config.CAR_ICON, color="black", label="Available Cars"),
            self.ax.text(0, 0, config.DISCHARGED_CAR_ICON, color="black", label="Discharged Cars"),
            self.ax.text(0, 0, config.CHARGING_CAR_ICON, color="black", label="Charging Cars"),
            self.ax.text(0, 0, config.NEEDS_CHARGING_CAR_ICON, color="black", label="Needs Charging"),
            self.ax.text(0, 0, config.CHARGING_STATION_ICON, color="black", label="Charging Stations"),
            self.ax.text(0, 0, config.RELOCATOR_ICON, color="cyan", label="Available Relocators"),
            self.ax.text(0, 0, config.RELOCATOR_ICON, color="brown", label="Busy Relocators"),
        ]
        self.ax.legend(
            handles=legend_elements,
            loc="upper right",
            bbox_to_anchor=(1, 1)
        )
        self.legend_created = True
