import random
import math
import networkx as nx
from ..config import (
    MAP_WIDTH, MAP_HEIGHT, ROAD_GRID_SIZE, NODE_POSITION_VARIANCE,
    TRAFFIC_ZONES, get_traffic_factor_for_position, TIME_PERIODS,
    TRAFFIC_TIME_MULTIPLIERS, logger
)


class RoadMap:
    """Gestisce la mappa stradale della città usando NetworkX"""
    
    def __init__(self, width=None, height=None):
        self.width = width or MAP_WIDTH
        self.height = height or MAP_HEIGHT
        self.graph = nx.Graph()  # Grafo non orientato per le strade
        self.traffic_zones = TRAFFIC_ZONES  # Usa le zone dal config
        
        # Genera la rete stradale ottimizzata
        self._generate_road_network()
    
    def _get_time_period(self, time):
        """Determina il periodo del giorno basato sul tempo simulato"""
        minutes_of_day = time % 1440  # Convert to minutes within a day
        for period, (start, end) in TIME_PERIODS.items():
            if start <= minutes_of_day < end:
                return period
        return 'EARLY_MORNING'  # Default period
        
    def _get_traffic_factor(self, x, y, time=0):
        """Determina il fattore di traffico per una posizione e tempo"""
        base_factor = get_traffic_factor_for_position(x, y)
        time_period = self._get_time_period(time)
        time_multiplier = TRAFFIC_TIME_MULTIPLIERS[time_period]
        
        # Get additional rush hour multiplier if the zone has one
        zone_multiplier = 1.0
        for zone in TRAFFIC_ZONES.values():
            bounds = zone['bounds']
            if bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]:
                if time_period in ['MORNING_RUSH', 'EVENING_RUSH']:
                    zone_multiplier = zone.get('rush_hour_multiplier', 1.0)
                break
                
        return base_factor * time_multiplier * zone_multiplier
    
    def _generate_road_network(self):
        """Genera una rete stradale ottimizzata usando NetworkX"""
        # Crea nodi principali su una griglia più sparsa per migliorare le performance
        grid_size = ROAD_GRID_SIZE
        node_positions = {}
        
        # Crea nodi principali
        for i in range(0, self.width + 1, grid_size):
            for j in range(0, self.height + 1, grid_size):
                # Aggiungi un po' di casualità alle posizioni
                x = i + random.uniform(-NODE_POSITION_VARIANCE, NODE_POSITION_VARIANCE)
                y = j + random.uniform(-NODE_POSITION_VARIANCE, NODE_POSITION_VARIANCE)
                
                # Mantieni dentro i confini
                x = max(0, min(self.width, x))
                y = max(0, min(self.height, y))
                
                node_id = f"{i}_{j}"
                traffic_factor = self._get_traffic_factor(x, y)
                
                # Aggiungi nodo al grafo con attributi
                self.graph.add_node(node_id, 
                                  x=x, y=y, 
                                  traffic_factor=traffic_factor,
                                  pos=(x, y))
                
                node_positions[node_id] = (x, y)
        
        # Crea connessioni orizzontali e verticali principali
        # Edge weights represent DISTANCE only - traffic will be applied when calculating time
        for i in range(0, self.width + 1, grid_size):
            for j in range(0, self.height + 1, grid_size):
                current_node = f"{i}_{j}"
                
                # Connessioni orizzontali
                if i + grid_size <= self.width:
                    right_node = f"{i + grid_size}_{j}"
                    if right_node in self.graph.nodes:
                        distance = self._calculate_distance(node_positions[current_node], 
                                                          node_positions[right_node])
                        # Store distance as weight
                        self.graph.add_edge(current_node, right_node, distance=distance)
                
                # Connessioni verticali
                if j + grid_size <= self.height:
                    down_node = f"{i}_{j + grid_size}"
                    if down_node in self.graph.nodes:
                        distance = self._calculate_distance(node_positions[current_node], 
                                                          node_positions[down_node])
                        # Store distance as weight
                        self.graph.add_edge(current_node, down_node, distance=distance)
        
        # Aggiungi alcune strade diagonali principali per maggiore connettività
        self._add_diagonal_roads(node_positions)
        
        logger.info(f"Generated optimized road network with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} roads")
    
    def _calculate_distance(self, pos1, pos2):
        """Calcola la distanza euclidea tra due posizioni"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _add_diagonal_roads(self, node_positions):
        """Aggiunge alcune strade diagonali principali"""
        # Aggiungi alcune connessioni diagonali strategiche
        diagonal_connections = [
            ("0_0", "15_15"), ("15_0", "30_15"), ("30_0", "45_15"),
            ("0_15", "15_30"), ("15_15", "30_30"), ("30_15", "45_30"),
            ("0_30", "15_45"), ("15_30", "30_45"), ("30_30", "45_45")
        ]
        
        for node1, node2 in diagonal_connections:
            if node1 in self.graph.nodes and node2 in self.graph.nodes:
                distance = self._calculate_distance(node_positions[node1], node_positions[node2])
                self.graph.add_edge(node1, node2, distance=distance)
    
    def find_nearest_node(self, x, y):
        """Trova il nodo più vicino a una posizione usando NetworkX"""
        min_distance = float('inf')
        nearest_node_id = None
        
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            node_x, node_y = node_data['x'], node_data['y']
            distance = math.sqrt((node_x - x)**2 + (node_y - y)**2)
            
            if distance < min_distance:
                min_distance = distance
                nearest_node_id = node_id
        
        return nearest_node_id
    
    def calculate_route_distance(self, start_pos, end_pos):
        """Calcola la distanza reale tra due posizioni usando NetworkX"""
        start_node = self.find_nearest_node(start_pos[0], start_pos[1])
        end_node = self.find_nearest_node(end_pos[0], end_pos[1])
        
        if start_node is None or end_node is None or start_node == end_node:
            # Fallback alla distanza euclidea
            return math.sqrt((start_pos[0] - end_pos[0])**2 + (start_pos[1] - end_pos[1])**2)
        
        try:
            # Usa NetworkX per trovare il percorso più breve (by distance)
            path = nx.shortest_path(self.graph, start_node, end_node, weight='distance')
            
            # Calcola la distanza totale del percorso
            total_distance = 0
            for i in range(len(path) - 1):
                edge_data = self.graph[path[i]][path[i + 1]]
                total_distance += edge_data['distance']
            
            return total_distance
            
        except nx.NetworkXNoPath:
            # Fallback alla distanza euclidea se non c'è percorso
            return math.sqrt((start_pos[0] - end_pos[0])**2 + (start_pos[1] - end_pos[1])**2)
    
    def calculate_route_time(self, start_pos, end_pos, speed=7/6, current_time=0):
        """Calcola il tempo necessario per percorrere un percorso considerando il traffico.
        
        Uses Dijkstra's algorithm to find the path with minimum travel TIME (not distance).
        Edge weights are computed as: distance / (speed / traffic_factor)
        
        Args:
            start_pos: Starting position (x, y)
            end_pos: Ending position (x, y)
            speed: Base driving speed in km/h
            current_time: Current simulation time to determine traffic conditions
            
        Returns:
            Travel time in hours
        """
        start_node = self.find_nearest_node(start_pos[0], start_pos[1])
        end_node = self.find_nearest_node(end_pos[0], end_pos[1])
        
        if start_node is None or end_node is None or start_node == end_node:
            # Fallback to simple calculation
            distance = math.sqrt((start_pos[0] - end_pos[0])**2 + (start_pos[1] - end_pos[1])**2)
            return distance / speed
        
        try:
            # Create a custom weight function that computes travel time for each edge
            # Weight = time = distance / effective_speed
            # where effective_speed = base_speed / traffic_factor
            
            def time_weight(u, v, edge_data):
                # Get distance of this edge
                distance = edge_data.get('distance', 1.0)
                
                # Get traffic factors at both nodes
                node_u_data = self.graph.nodes[u]
                node_v_data = self.graph.nodes[v]
                
                # Use average traffic factor for the edge
                # (traffic factor slows down the vehicle)
                avg_traffic_factor = (node_u_data['traffic_factor'] + node_v_data['traffic_factor']) / 2.0
                
                # Effective speed is reduced by traffic
                effective_speed = speed / avg_traffic_factor
                
                # Time = distance / speed
                travel_time = distance / effective_speed
                
                return travel_time
            
            # Use Dijkstra's algorithm to find shortest path by TIME (not distance)
            path = nx.shortest_path(self.graph, start_node, end_node, weight=time_weight)
            
            # Calculate total travel time along the path
            total_time = 0
            for i in range(len(path) - 1):
                edge_data = self.graph[path[i]][path[i + 1]]
                total_time += time_weight(path[i], path[i + 1], edge_data)
            
            return total_time
                
        except nx.NetworkXNoPath:
            # Fallback if no path exists
            distance = math.sqrt((start_pos[0] - end_pos[0])**2 + (start_pos[1] - end_pos[1])**2)
            return distance / speed
    
    def get_road_network_data(self):
        """Restituisce i dati della rete stradale per la visualizzazione usando NetworkX"""
        nodes_data = []
        edges_data = []
        
        # Estrai dati dei nodi
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            nodes_data.append({
                'id': node_id,
                'x': node_data['x'],
                'y': node_data['y'],
                'traffic_factor': node_data['traffic_factor']
            })
        
        # Estrai dati degli archi
        for edge in self.graph.edges(data=True):
            node1_id, node2_id, edge_data = edge
            node1_data = self.graph.nodes[node1_id]
            node2_data = self.graph.nodes[node2_id]
            
            edges_data.append({
                'start': (node1_data['x'], node1_data['y']),
                'end': (node2_data['x'], node2_data['y']),
                'distance': edge_data['weight']
            })
        
        return nodes_data, edges_data
