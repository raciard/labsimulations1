"""
Generate a UML class diagram for the car-sharing simulation entities.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

fig, ax = plt.subplots(figsize=(14, 10))

# Define class boxes (x, y, width, height)
classes = {
    'Car': {
        'pos': (1, 7),
        'size': (3, 2.5),
        'attributes': [
            '- car_id: int',
            '- location: (x, y)',
            '- charge_level: float',
            '- status: str',
        ],
        'methods': [
            '+ reserve()',
            '+ free_up()',
            '+ update_charge(distance)',
            '+ is_available(): bool',
        ]
    },
    'ChargingStation': {
        'pos': (5.5, 7),
        'size': (3, 2.5),
        'attributes': [
            '- station_id: int',
            '- location: (x, y)',
            '- charging_queue: list',
            '- available_spots: int',
        ],
        'methods': [
            '+ start_charging(car)',
            '+ stop_charging(car)',
            '+ get_nearest_station()',
        ]
    },
    'CarRelocator': {
        'pos': (10, 7),
        'size': (3, 2.5),
        'attributes': [
            '- relocator_id: int',
            '- speed: float',
            '- busy: bool',
            '- current_task: Car',
        ],
        'methods': [
            '+ assign_task(car)',
            '+ complete_task()',
            '+ calculate_travel_time()',
        ]
    },
    'User': {
        'pos': (1, 3.5),
        'size': (3, 2.2),
        'attributes': [
            '- user_id: int',
            '- reservation_attempts: int',
            '- first_reservation_time',
        ],
        'methods': [
            '+ __init__(simulator, time)',
        ]
    },
    'RoadMap': {
        'pos': (5.5, 3.5),
        'size': (3, 2.2),
        'attributes': [
            '- graph: NetworkX.Graph',
            '- width: int',
            '- height: int',
        ],
        'methods': [
            '+ calculate_route_distance()',
            '+ calculate_route_time()',
            '+ find_nearest_node()',
        ]
    },
    'Simulator': {
        'pos': (10, 3.5),
        'size': (3, 2.2),
        'attributes': [
            '- FES: PriorityQueue',
            '- road_map: RoadMap',
        ],
        'methods': [
            '+ schedule_event()',
            '+ get_next_event()',
            '+ simulate(end_time)',
        ]
    },
}

def draw_class_box(ax, name, info):
    x, y = info['pos']
    width, height = info['size']
    
    # Main box
    box = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.05",
                          edgecolor='#0066CC', facecolor='#E6F2FF', linewidth=2)
    ax.add_patch(box)
    
    # Class name (title)
    ax.text(x + width/2, y + height - 0.25, name,
            ha='center', va='center', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#0066CC', edgecolor='none'),
            color='white')
    
    # Separator line after title
    ax.plot([x + 0.1, x + width - 0.1], [y + height - 0.5, y + height - 0.5],
            'k-', linewidth=1)
    
    # Attributes section
    attr_y = y + height - 0.7
    for attr in info['attributes']:
        ax.text(x + 0.15, attr_y, attr, ha='left', va='top', fontsize=8, family='monospace')
        attr_y -= 0.25
    
    # Separator line before methods
    sep_y = attr_y - 0.05
    ax.plot([x + 0.1, x + width - 0.1], [sep_y, sep_y], 'k-', linewidth=1)
    
    # Methods section
    method_y = sep_y - 0.2
    for method in info['methods']:
        ax.text(x + 0.15, method_y, method, ha='left', va='top', fontsize=8, family='monospace')
        method_y -= 0.25

# Draw all classes
for class_name, info in classes.items():
    draw_class_box(ax, class_name, info)

# Draw relationships
relationships = [
    # Car uses ChargingStation
    {'from': 'Car', 'to': 'ChargingStation', 'label': 'charges at', 'style': '->'},
    # CarRelocator moves Car
    {'from': 'CarRelocator', 'to': 'Car', 'label': 'relocates', 'style': '->'},
    # User reserves Car
    {'from': 'User', 'to': 'Car', 'label': 'reserves', 'style': '->'},
    # Simulator manages everything
    {'from': 'Simulator', 'to': 'RoadMap', 'label': 'uses', 'style': '->'},
]

for rel in relationships:
    from_class = classes[rel['from']]
    to_class = classes[rel['to']]
    
    from_x = from_class['pos'][0] + from_class['size'][0] / 2
    from_y = from_class['pos'][1]
    to_x = to_class['pos'][0] + to_class['size'][0] / 2
    to_y = to_class['pos'][1] + to_class['size'][1]
    
    # Adjust arrow positions
    if rel['from'] == 'Car' and rel['to'] == 'ChargingStation':
        from_x = from_class['pos'][0] + from_class['size'][0]
        from_y = from_class['pos'][1] + from_class['size'][1] / 2
        to_x = to_class['pos'][0]
        to_y = to_class['pos'][1] + to_class['size'][1] / 2
    elif rel['from'] == 'CarRelocator' and rel['to'] == 'Car':
        from_x = from_class['pos'][0]
        from_y = from_class['pos'][1] + from_class['size'][1] / 2
        to_x = to_class['pos'][0] + to_class['size'][0]
        to_y = to_class['pos'][1] + to_class['size'][1] / 2
    elif rel['from'] == 'User' and rel['to'] == 'Car':
        from_y = from_class['pos'][1] + from_class['size'][1]
        to_y = to_class['pos'][1]
    
    arrow = FancyArrowPatch((from_x, from_y), (to_x, to_y),
                           arrowstyle='->', mutation_scale=20, linewidth=1.5,
                           color='#666666', linestyle='--')
    ax.add_patch(arrow)
    
    # Add label
    mid_x = (from_x + to_x) / 2
    mid_y = (from_y + to_y) / 2
    ax.text(mid_x, mid_y, rel['label'], ha='center', va='bottom',
            fontsize=8, style='italic', color='#333333',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'))

# Add title
ax.text(7, 10, 'Car-Sharing Simulation - Class Diagram', 
        ha='center', va='center', fontsize=14, fontweight='bold')

# Add legend
legend_elements = [
    mlines.Line2D([0], [0], color='#666666', linestyle='--', marker='>', 
                  markeredgecolor='#666666', markersize=8, label='Uses/Interacts with')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

# Set axis properties
ax.set_xlim(0, 14)
ax.set_ylim(2.5, 10.5)
ax.set_aspect('equal')
ax.axis('off')

plt.tight_layout()

# Save
output_file = 'uml_class_diagram.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
print(f"UML diagram saved to {output_file}")

output_pdf = 'uml_class_diagram.pdf'
plt.savefig(output_pdf, format='pdf', bbox_inches='tight', facecolor='white')
print(f"UML diagram saved to {output_pdf}")
