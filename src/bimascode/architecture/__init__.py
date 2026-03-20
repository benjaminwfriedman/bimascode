"""
Architectural elements (walls, floors, roofs, doors, windows, etc.).
"""

from .wall_type import (
    WallType,
    Layer,
    LayerFunction,
    create_basic_wall_type,
    create_stud_wall_type,
)
from .wall import Wall
from .floor_type import (
    FloorType,
    create_basic_floor_type,
    create_concrete_floor_type,
)
from .floor import Floor
from .roof import Roof

# Sprint 3: Doors, Windows, Openings, Wall Joins
from .door_type import (
    DoorType,
    SwingDirection,
    DoorOperationType,
    create_standard_door_type,
    create_double_door_type,
)
from .door import Door
from .window_type import (
    WindowType,
    WindowOperationType,
    create_standard_window_type,
    create_double_window_type,
    create_fixed_window_type,
)
from .window import Window
from .opening import (
    Opening,
    create_rectangular_opening,
    create_circular_opening,
)
from .wall_joins import (
    JoinType,
    EndCapType,
    WallJoin,
    WallJoinDetector,
    WallJoinProcessor,
    detect_and_process_wall_joins,
)

__all__ = [
    # Wall types and elements
    "WallType",
    "Layer",
    "LayerFunction",
    "Wall",
    "create_basic_wall_type",
    "create_stud_wall_type",
    # Floor types and elements
    "FloorType",
    "Floor",
    "create_basic_floor_type",
    "create_concrete_floor_type",
    # Roof
    "Roof",
    # Door types and elements (Sprint 3)
    "DoorType",
    "SwingDirection",
    "DoorOperationType",
    "Door",
    "create_standard_door_type",
    "create_double_door_type",
    # Window types and elements (Sprint 3)
    "WindowType",
    "WindowOperationType",
    "Window",
    "create_standard_window_type",
    "create_double_window_type",
    "create_fixed_window_type",
    # Openings (Sprint 3)
    "Opening",
    "create_rectangular_opening",
    "create_circular_opening",
    # Wall joins (Sprint 3)
    "JoinType",
    "EndCapType",
    "WallJoin",
    "WallJoinDetector",
    "WallJoinProcessor",
    "detect_and_process_wall_joins",
]
