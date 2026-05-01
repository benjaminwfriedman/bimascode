"""
Architectural elements (walls, floors, roofs, doors, windows, etc.).
"""

from .ceiling import Ceiling

# Sprint 4: Ceilings
from .ceiling_type import (
    CeilingType,
    create_gypsum_ceiling_type,
    create_suspended_ceiling_type,
)
from .door import Door

# Sprint 3: Doors, Windows, Openings, Wall Joins
from .door_type import (
    DoorOperationType,
    DoorType,
    SwingDirection,
    create_double_door_type,
    create_standard_door_type,
)
from .floor import Floor
from .floor_type import (
    FloorType,
    create_basic_floor_type,
    create_concrete_floor_type,
)
from .opening import (
    Opening,
    create_circular_opening,
    create_rectangular_opening,
)
from .roof import Roof
from .wall import Wall
from .wall_joins import (
    EndCapType,
    JoinType,
    WallJoin,
    WallJoinDetector,
    WallJoinProcessor,
    WallJoinStyle,
    clean_wall_joins,
    detect_and_process_wall_joins,
    reset_wall_joins,
)
from .wall_type import (
    Layer,
    LayerFunction,
    WallFunction,
    WallType,
    create_basic_wall_type,
    create_stud_wall_type,
)
from .window import Window
from .window_type import (
    WindowOperationType,
    WindowType,
    create_double_window_type,
    create_fixed_window_type,
    create_standard_window_type,
)

__all__ = [
    # Wall types and elements
    "WallType",
    "WallFunction",
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
    "WallJoinStyle",
    "EndCapType",
    "WallJoin",
    "WallJoinDetector",
    "WallJoinProcessor",
    "detect_and_process_wall_joins",
    "clean_wall_joins",
    "reset_wall_joins",
    # Ceiling types and elements (Sprint 4)
    "CeilingType",
    "Ceiling",
    "create_gypsum_ceiling_type",
    "create_suspended_ceiling_type",
]
