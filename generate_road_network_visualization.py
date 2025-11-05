"""
Generate a visualization of the road network graph showing traffic-weighted routing.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np
import networkx as nx
import random

# Simulate road network structure
MAP_WIDTH = 100
MAP_HEIGHT = 100
GRID_SIZE = 20

# Traffic zones with traffic factors
TRAFFIC_ZONES = {
    'center': {'bounds': (30, 30, 70, 70), 'color': '#FF6B6B', 'alpha': 0.15, 'traffic_factor': 2.5},
    'commercial': {'bounds': (20, 20, 80, 80), 'color': '#FFA07A', 'alpha': 0.10, 'traffic_factor': 1.8},
    'residential_nw': {'bounds': (0, 50, 30, 100), 'color': '#4ECDC4', 'alpha': 0.15, 'traffic_factor': 0.7},
    'residential_se': {'bounds': (50, 0, 100, 50), 'color': '#45B7D1', 'alpha': 0.15, 'traffic_factor': 0.7},
    'industrial': {'bounds': (0, 0, 20, 20), 'color': '#98D8C8', 'alpha': 0.15, 'traffic_factor': 0.5}
}

def get_traffic_factor(x, y):
    """Get traffic factor for a position."""
    for zone_name, zone in TRAFFIC_ZONES.items():
        bounds = zone['bounds']
        if bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]:
            return zone['traffic_factor']
    return 1.0  # Default

# Create a sample road network with traffic factors
def create_road_network():
    G = nx.Graph()
    node_positions = {}
    
    # Create grid nodes with traffic factors
    for i in range(0, MAP_WIDTH + 1, GRID_SIZE):
        for j in range(0, MAP_HEIGHT + 1, GRID_SIZE):
            node_id = f"{i}_{j}"
            # Add small random variance
            x = i + random.uniform(-2, 2)
            y = j + random.uniform(-2, 2)
            x = max(0, min(MAP_WIDTH, x))
            y = max(0, min(MAP_HEIGHT, y))
            
            traffic_factor = get_traffic_factor(x, y)
            G.add_node(node_id, pos=(x, y), traffic_factor=traffic_factor)
            node_positions[node_id] = (x, y)
    
    # Add edges with distance and time weights
    speed = 30  # km/h base speed
    for i in range(0, MAP_WIDTH + 1, GRID_SIZE):
        for j in range(0, MAP_HEIGHT + 1, GRID_SIZE):
            current = f"{i}_{j}"
            
            # Horizontal
            if i + GRID_SIZE <= MAP_WIDTH:
                right = f"{i + GRID_SIZE}_{j}"
                if right in G.nodes:
                    pos1 = node_positions[current]
                    pos2 = node_positions[right]
                    distance = np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                    
                    # Calculate time weight considering traffic
                    tf1 = G.nodes[current]['traffic_factor']
                    tf2 = G.nodes[right]['traffic_factor']
                    avg_traffic = (tf1 + tf2) / 2.0
                    time_weight = distance / (speed / avg_traffic)
                    
                    G.add_edge(current, right, distance=distance, time=time_weight)
            
            # Vertical
            if j + GRID_SIZE <= MAP_HEIGHT:
                down = f"{i}_{j + GRID_SIZE}"
                if down in G.nodes:
                    pos1 = node_positions[current]
                    pos2 = node_positions[down]
                    distance = np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                    
                    # Calculate time weight considering traffic
                    tf1 = G.nodes[current]['traffic_factor']
                    tf2 = G.nodes[down]['traffic_factor']
                    avg_traffic = (tf1 + tf2) / 2.0
                    time_weight = distance / (speed / avg_traffic)
                    
                    G.add_edge(current, down, distance=distance, time=time_weight)
    
    return G, node_positions

# Create the figure with two subplots
fig = plt.figure(figsize=(16, 7))

# Left subplot: Road Network with TIME-optimal route
ax1 = fig.add_subplot(1, 2, 1)

# Draw traffic zones (lighter)
for zone_name, zone in TRAFFIC_ZONES.items():
    bounds = zone['bounds']
    x, y, x2, y2 = bounds
    width = x2 - x
    height = y2 - y
    rect = Rectangle((x, y), width, height, linewidth=1, 
                     edgecolor='gray', facecolor=zone['color'], 
                     alpha=zone['alpha'])
    ax1.add_patch(rect)

# Create and draw road network
G, node_positions = create_road_network()

# Draw all edges (roads) in light gray
for edge in G.edges():
    node1, node2 = edge
    x1, y1 = node_positions[node1]
    x2, y2 = node_positions[node2]
    ax1.plot([x1, x2], [y1, y2], 'gray', linewidth=1, alpha=0.4, zorder=1)

# Draw nodes (intersections)
for node, (x, y) in node_positions.items():
    ax1.plot(x, y, 'o', color='darkgray', markersize=4, zorder=2)

# Example route: from bottom-left to top-right (going through center)
start_node = "0_0"
end_node = "80_80"

# Calculate FASTEST path using TIME weights (Dijkstra's algorithm)
try:
    # Path optimized for minimum TIME (considers traffic)
    time_path = nx.shortest_path(G, start_node, end_node, weight='time')
    
    # Draw the TIME-optimal path in blue
    for i in range(len(time_path) - 1):
        node1 = time_path[i]
        node2 = time_path[i + 1]
        x1, y1 = node_positions[node1]
        x2, y2 = node_positions[node2]
        ax1.plot([x1, x2], [y1, y2], 'blue', linewidth=3, alpha=0.8, zorder=3)
    
    # Mark start and end points
    start_x, start_y = node_positions[start_node]
    end_x, end_y = node_positions[end_node]
    
    ax1.plot(start_x, start_y, 'o', color='green', markersize=15, 
             label='Start', zorder=4, markeredgecolor='darkgreen', markeredgewidth=2)
    ax1.plot(end_x, end_y, 's', color='red', markersize=15, 
             label='End', zorder=4, markeredgecolor='darkred', markeredgewidth=2)
    
    # Add arrows along the path
    for i in range(0, len(time_path) - 1, 2):  # Every other segment
        node1 = time_path[i]
        node2 = time_path[i + 1]
        x1, y1 = node_positions[node1]
        x2, y2 = node_positions[node2]
        dx = x2 - x1
        dy = y2 - y1
        ax1.arrow(x1 + dx*0.3, y1 + dy*0.3, dx*0.3, dy*0.3, 
                 head_width=2, head_length=1.5, fc='blue', ec='blue', 
                 alpha=0.7, zorder=3)

except nx.NetworkXNoPath:
    time_path = []

ax1.set_xlim(-5, MAP_WIDTH + 5)
ax1.set_ylim(-5, MAP_HEIGHT + 5)
ax1.set_xlabel('X Position (km)', fontsize=11, fontweight='bold')
ax1.set_ylabel('Y Position (km)', fontsize=11, fontweight='bold')
ax1.set_title('Road Network with Traffic-Weighted Routing\n(Dijkstra\'s Algorithm Minimizes Travel Time)', 
              fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.2, linestyle='--')
ax1.legend(loc='upper left', fontsize=10)
ax1.set_aspect('equal')

# Add explanation text
textstr = 'The graph shows:\n• Gray dots = intersections (nodes)\n• Gray lines = roads (edges)\n• Blue path = FASTEST route\n  (avoids high-traffic areas)'
props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.9, edgecolor='gray')
ax1.text(0.02, 0.35, textstr, transform=ax1.transAxes, fontsize=9,
        verticalalignment='top', bbox=props)


# Right subplot: Comparison visualization
ax2 = fig.add_subplot(1, 2, 2)

# Draw traffic zones again
for zone_name, zone in TRAFFIC_ZONES.items():
    bounds = zone['bounds']
    x, y, x2, y2 = bounds
    width = x2 - x
    height = y2 - y
    rect = Rectangle((x, y), width, height, linewidth=1, 
                     edgecolor='gray', facecolor=zone['color'], 
                     alpha=zone['alpha'])
    ax2.add_patch(rect)

# Show straight line vs actual route
start_x, start_y = node_positions[start_node]
end_x, end_y = node_positions[end_node]

# Straight line (wrong way)
ax2.plot([start_x, end_x], [start_y, end_y], 'r--', linewidth=3, 
         alpha=0.7, label='Straight line (unrealistic)', zorder=2)
ax2.arrow(start_x + (end_x-start_x)*0.4, start_y + (end_y-start_y)*0.4,
         (end_x-start_x)*0.15, (end_y-start_y)*0.15,
         head_width=3, head_length=2, fc='red', ec='red', alpha=0.7, zorder=2)

# Actual TIME-optimal route following roads
if time_path:
    path_x = [node_positions[node][0] for node in time_path]
    path_y = [node_positions[node][1] for node in time_path]
    ax2.plot(path_x, path_y, 'b-', linewidth=3, alpha=0.8, 
             label='Fastest route (considers traffic)', zorder=3)

# Mark points
ax2.plot(start_x, start_y, 'o', color='green', markersize=15, 
         label='Start', zorder=4, markeredgecolor='darkgreen', markeredgewidth=2)
ax2.plot(end_x, end_y, 's', color='red', markersize=15, 
         label='End', zorder=4, markeredgecolor='darkred', markeredgewidth=2)

ax2.set_xlim(-5, MAP_WIDTH + 5)
ax2.set_ylim(-5, MAP_HEIGHT + 5)
ax2.set_xlabel('X Position (km)', fontsize=11, fontweight='bold')
ax2.set_ylabel('Y Position (km)', fontsize=11, fontweight='bold')
ax2.set_title('Why We Need the Graph\n(Realistic vs Unrealistic Distance)', 
              fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.2, linestyle='--')
ax2.legend(loc='upper left', fontsize=10)
ax2.set_aspect('equal')

# Calculate distances
straight_distance = np.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
if time_path:
    graph_distance = sum(np.sqrt((node_positions[time_path[i]][0] - node_positions[time_path[i+1]][0])**2 + 
                                  (node_positions[time_path[i]][1] - node_positions[time_path[i+1]][1])**2)
                         for i in range(len(time_path) - 1))

    # Add comparison text
    comparison_text = f'Distance comparison:\n' \
                     f'Straight line: {straight_distance:.1f} km\n' \
                     f'Graph route: {graph_distance:.1f} km\n' \
                     f'Difference: {graph_distance - straight_distance:.1f} km\n' \
                     f'  ({((graph_distance/straight_distance - 1) * 100):.0f}% longer)'
    props2 = dict(boxstyle='round', facecolor='lightblue', alpha=0.9, edgecolor='gray')
    ax2.text(0.02, 0.45, comparison_text, transform=ax2.transAxes, fontsize=10,
            verticalalignment='top', bbox=props2, family='monospace')

plt.tight_layout()

# Save the figure
output_file = 'road_network_graph.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"Road network visualization saved to {output_file}")

output_pdf = 'road_network_graph.pdf'
plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
print(f"Road network visualization saved to {output_pdf}")

# Don't show the plot interactively to avoid blocking
# plt.show()
