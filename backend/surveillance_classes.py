"""
Surveillance-focused object classes for YOLOv8 filtering.
Defines relevant classes for security and monitoring applications.
"""

# Core surveillance classes - most important for security monitoring
SURVEILLANCE_CORE = [
    'person',           # People detection (most important)
    'bicycle',          # Bikes/scooters
    'car',              # Cars
    'motorcycle',       # Motorcycles
    'bus',              # Buses
    'truck',            # Trucks/vans
]

# Extended surveillance classes - includes more vehicle types
SURVEILLANCE_EXTENDED = [
    'person',           # People detection
    'bicycle',          # Bikes/scooters
    'car',              # Cars
    'motorcycle',       # Motorcycles
    'airplane',         # Aircraft (for airports/airfields)
    'bus',              # Buses
    'train',            # Trains (for stations/railways)
    'truck',            # Trucks/vans
    'boat',             # Boats (for ports/marinas)
]

# Traffic monitoring classes - focused on road traffic
TRAFFIC_MONITORING = [
    'person',           # Pedestrians
    'bicycle',          # Cyclists
    'car',              # Cars
    'motorcycle',       # Motorcycles
    'bus',              # Buses
    'truck',            # Trucks
    'traffic light',    # Traffic signals
    'stop sign',        # Stop signs
    'fire hydrant',     # Fire hydrants (traffic obstacles)
]

# Perimeter security classes - for boundary monitoring
PERIMETER_SECURITY = [
    'person',           # Intruders
    'bicycle',          # Vehicles
    'car',              # Vehicles
    'motorcycle',       # Vehicles
    'bus',              # Large vehicles
    'truck',            # Large vehicles
    'dog',              # Animals
    'cat',              # Animals
    'horse',            # Large animals
]

# Retail security classes - for stores and shopping areas
RETAIL_SECURITY = [
    'person',           # Customers/employees
    'handbag',          # Bags
    'backpack',         # Backpacks
    'suitcase',         # Luggage
    'car',              # Vehicles in parking
    'bicycle',          # Bikes
    'motorcycle',       # Motorcycles
]

# Custom classes for specific use cases
CUSTOM_CLASSES = {
    'people_only': ['person'],
    'vehicles_only': ['bicycle', 'car', 'motorcycle', 'bus', 'truck'],
    'transport': ['car', 'bus', 'truck', 'train', 'boat', 'airplane'],
    'personal_items': ['person', 'handbag', 'backpack', 'suitcase'],
}

def get_class_names(class_set: str) -> list:
    """
    Get class names for a specific surveillance category.
    
    Args:
        class_set: Name of the class set ('core', 'extended', 'traffic', 'perimeter', 'retail', or custom name)
        
    Returns:
        List of class names
    """
    class_sets = {
        'core': SURVEILLANCE_CORE,
        'extended': SURVEILLANCE_EXTENDED,
        'traffic': TRAFFIC_MONITORING,
        'perimeter': PERIMETER_SECURITY,
        'retail': RETAIL_SECURITY,
    }
    
    # Add custom classes
    class_sets.update(CUSTOM_CLASSES)
    
    return class_sets.get(class_set.lower(), SURVEILLANCE_CORE)

def get_available_class_sets() -> dict:
    """Get all available class sets."""
    return {
        'core': SURVEILLANCE_CORE,
        'extended': SURVEILLANCE_EXTENDED,
        'traffic': TRAFFIC_MONITORING,
        'perimeter': PERIMETER_SECURITY,
        'retail': RETAIL_SECURITY,
        **CUSTOM_CLASSES
    }

def print_class_info():
    """Print information about available class sets."""
    print("Available Surveillance Class Sets:")
    print("=" * 50)
    
    class_sets = get_available_class_sets()
    
    for name, classes in class_sets.items():
        print(f"\n{name.upper()}:")
        print(f"  Classes ({len(classes)}): {', '.join(classes)}")
    
    print(f"\nAll YOLOv8 Classes (80 total):")
    all_classes = [
        'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
        'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog',
        'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella',
        'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
        'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 'bottle',
        'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich',
        'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
        'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
        'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book',
        'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
    ]
    print(f"  {', '.join(all_classes)}")

if __name__ == "__main__":
    print_class_info()
