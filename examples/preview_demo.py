"""Preview Demo - Simple building for testing the preview server.

Run with:
    bimascode serve examples/preview_demo.py

This script demonstrates the preview server by creating a simple
two-room building that you can modify and see updates in real-time.
"""

from bimascode.architecture import (
    Door,
    Wall,
    WallFunction,
    Window,
    create_basic_wall_type,
)
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.window_type import WindowType
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room import Room
from bimascode.utils.materials import MaterialLibrary

# Create building - this variable is at module level so preview server can find it
building = Building("Preview Demo")

# Materials and types
concrete = MaterialLibrary.concrete()
ext_wall_type = create_basic_wall_type("Exterior", 200, concrete, function=WallFunction.EXTERIOR)
int_wall_type = create_basic_wall_type("Interior", 100, concrete, function=WallFunction.INTERIOR)
door_type = DoorType("Standard Door", width=900, height=2100)
window_type = WindowType("Standard Window", width=1200, height=1500, default_sill_height=900)

# Building dimensions (mm)
WIDTH = 10000  # 10m
DEPTH = 8000  # 8m

# Create ground floor
ground = Level(building, "Ground Floor", elevation=0)

# Exterior walls
wall_south = Wall(ext_wall_type, (0, 0), (WIDTH, 0), ground, name="South")
wall_east = Wall(ext_wall_type, (WIDTH, 0), (WIDTH, DEPTH), ground, name="East")
wall_north = Wall(ext_wall_type, (WIDTH, DEPTH), (0, DEPTH), ground, name="North")
wall_west = Wall(ext_wall_type, (0, DEPTH), (0, 0), ground, name="West")

# Interior partition
wall_partition = Wall(int_wall_type, (WIDTH / 2, 0), (WIDTH / 2, DEPTH), ground, name="Partition")

# Entry door
entry = Door(door_type, wall_south, offset=1500, name="Entry", mark="D-01")

# Interior door
interior_door = Door(door_type, wall_partition, offset=DEPTH / 2, name="Interior", mark="D-02")

# Windows
Window(window_type, wall_south, offset=WIDTH - 2500, mark="W-01")
Window(window_type, wall_north, offset=1500, mark="W-02")
Window(window_type, wall_north, offset=WIDTH - 2500, mark="W-03")

# Rooms
Room(
    name="Living Room",
    number="01",
    boundary=[(0, 0), (WIDTH / 2, 0), (WIDTH / 2, DEPTH), (0, DEPTH)],
    level=ground,
)
Room(
    name="Bedroom",
    number="02",
    boundary=[(WIDTH / 2, 0), (WIDTH, 0), (WIDTH, DEPTH), (WIDTH / 2, DEPTH)],
    level=ground,
)

# Print info when run directly
if __name__ == "__main__":
    print(f"Building: {building.name}")
    print(f"Levels: {len(building.levels)}")
    for level in building.levels:
        print(f"  - {level.name}: {len(level.elements)} elements")
