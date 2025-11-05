"""
Generate a visualization of the traffic zones on the city map.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import numpy as np

# Traffic zones configuration
TRAFFIC_ZONES = {
    'center': {
        'bounds': (30, 30, 70, 70),
        'base_traffic_factor': 2.5,
        'description': 'Central zone - heavy traffic',
        'rush_hour_multiplier': 1.5,
        'color': '#FF6B6B'  # Red
    },
    'residential_nw': {
        'bounds': (0, 50, 30, 100),
        'base_traffic_factor': 0.7,
        'description': 'Northwest residential zone - light traffic',
        'rush_hour_multiplier': 1.2,
        'color': '#4ECDC4'  # Teal
    },
    'residential_se': {
        'bounds': (50, 0, 100, 50),
        'base_traffic_factor': 0.7,
        'description': 'Southeast residential zone - light traffic',
        'rush_hour_multiplier': 1.2,
        'color': '#45B7D1'  # Blue
    },
    'commercial': {
        'bounds': (20, 20, 80, 80),
        'base_traffic_factor': 1.8,
        'description': 'Commercial zone - medium-high traffic',
        'rush_hour_multiplier': 1.3,
        'color': '#FFA07A'  # Light salmon
    },
    'industrial': {
        'bounds': (0, 0, 20, 20),
        'base_traffic_factor': 0.5,
        'description': 'Industrial zone - very light traffic',
        'rush_hour_multiplier': 1.4,
        'color': '#98D8C8'  # Light green
    }
}

MAP_WIDTH = 100
MAP_HEIGHT = 100

# Create figure and axis
fig, ax = plt.subplots(figsize=(15, 10))

# Draw each traffic zone
zone_order = ['commercial', 'center', 'residential_nw', 'residential_se', 'industrial']

# Custom label positions to avoid overlap (offsets from center)
label_offsets = {
    'center': (0, 8),           # Center zone: shift up
    'commercial': (-20, -20),      # Commercial zone: shift down
    'residential_nw': (0, 0),   # No offset needed
    'residential_se': (0, 0),   # No offset needed
    'industrial': (0, 0)        # No offset needed
}

for zone_name in zone_order:
    zone = TRAFFIC_ZONES[zone_name]
    bounds = zone['bounds']
    x, y, x2, y2 = bounds
    width = x2 - x
    height = y2 - y
    
    # Create rectangle
    rect = Rectangle(
        (x, y), width, height,
        linewidth=2,
        edgecolor='black',
        facecolor=zone['color'],
        alpha=0.5,
        label=f"{zone_name.replace('_', ' ').title()}"
    )
    ax.add_patch(rect)
    
    # Add zone label in the center with custom offset
    center_x = x + width / 2
    center_y = y + height / 2
    offset_x, offset_y = label_offsets[zone_name]
    label_y = center_y + offset_y
    
    # Zone name
    ax.text(center_x + offset_x, label_y + 2, zone_name.replace('_', ' ').upper(),
            ha='center', va='center', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
    
    # Traffic factor
    ax.text(center_x + offset_x, label_y - 3, f"Traffic: {zone['base_traffic_factor']}×",
            ha='center', va='center', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    # Rush hour multiplier
    ax.text(center_x + offset_x, label_y - 7, f"Rush: {zone['rush_hour_multiplier']}×",
            ha='center', va='center', fontsize=8, style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.5))

# Set limits and labels
ax.set_xlim(0, MAP_WIDTH)
ax.set_ylim(0, MAP_HEIGHT)
ax.set_xlabel('X Position (km)', fontsize=12, fontweight='bold')
ax.set_ylabel('Y Position (km)', fontsize=12, fontweight='bold')
ax.set_title('Traffic Zones Map - Car Sharing Service Area', fontsize=14, fontweight='bold', pad=15)

# Add grid
ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
ax.set_axisbelow(True)

# Add legend
legend = ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
legend.set_title('Traffic Zones', prop={'size': 11, 'weight': 'bold'})

# Add a text box with explanation
textstr = 'Traffic Factor: Base speed reduction multiplier\nRush Hour: Additional multiplier during peak hours'
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
        verticalalignment='top', bbox=props)

# Tight layout
plt.tight_layout()

# Save the figure
output_file = 'traffic_zones_map.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"Map saved to {output_file}")

# Also save as PDF for better quality in LaTeX
output_pdf = 'traffic_zones_map.pdf'
plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
print(f"Map saved to {output_pdf}")

plt.show()
