"""
School Building Example - Elementary School

Demonstrates:
- Large single-story educational building
- Repetitive classroom layout with corridors
- Specialized rooms (gym, cafeteria, library, admin)
- Multiple bathroom facilities
- Extensive window systems for natural light
- Complex wall join processing
- IFC export + floor plan DXF drawings

Building: H-shaped plan, ~90m x 45m
- Central Admin/Library wing
- East Classroom wing (8 classrooms, restrooms)
- West Classroom wing (8 classrooms, restrooms)
- North wing: Gymnasium and Cafeteria
"""

from datetime import datetime
from pathlib import Path

from bimascode.architecture import (
    Ceiling,
    Door,
    EndCapType,
    Floor,
    Wall,
    Window,
    detect_and_process_wall_joins,
)
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.architecture.door_type import DoorType, create_double_door_type
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.architecture.wall_type import WallType
from bimascode.architecture.window_type import WindowType
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.line_styles import LineStyle, LineWeight
from bimascode.drawing.primitives import Point2D, Polyline2D
from bimascode.drawing.view_base import ViewRange
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.materials import MaterialLibrary


def add_window_outlines(result, windows, cut_height):
    """Add black rectangular outlines around windows in the view result.

    This creates a cleaner architectural representation with windows shown
    as outlined rectangles rather than the default three-line representation.

    Args:
        result: ViewResult to add outlines to
        windows: List of Window objects
        cut_height: The cut height to check if windows are visible
    """
    import math

    from bimascode.drawing.line_styles import Layer

    outline_style = LineStyle(weight=LineWeight.MEDIUM, color=(0, 0, 0))

    for window in windows:
        bbox = window.get_bounding_box()
        # Only add outline if window is cut by the view plane
        if not (bbox.min_z <= cut_height <= bbox.max_z):
            continue

        wall = window._host_wall
        wall_start = wall.start_point
        wall_angle = wall.angle
        half_wall = wall.width / 2.0

        cos_a = math.cos(wall_angle)
        sin_a = math.sin(wall_angle)

        offset = window.offset
        width = window.width

        # Window jamb positions along wall
        left_x = wall_start[0] + offset * cos_a
        left_y = wall_start[1] + offset * sin_a
        right_x = wall_start[0] + (offset + width) * cos_a
        right_y = wall_start[1] + (offset + width) * sin_a

        # Use full wall width for outline (perpendicular to wall)
        perp_out = half_wall * 0.35  # Same as window jamb lines

        # Four corners of the rectangle
        corners = [
            Point2D(left_x - perp_out * sin_a, left_y + perp_out * cos_a),
            Point2D(right_x - perp_out * sin_a, right_y + perp_out * cos_a),
            Point2D(right_x + perp_out * sin_a, right_y - perp_out * cos_a),
            Point2D(left_x + perp_out * sin_a, left_y - perp_out * cos_a),
        ]

        outline = Polyline2D(
            points=corners,
            closed=True,
            style=outline_style,
            layer=Layer.WINDOW,
        )
        result.polylines.append(outline)


# Building dimensions (mm)
CLASSROOM_WIDTH = 9000  # 9m wide classrooms
CLASSROOM_DEPTH = 7500  # 7.5m deep classrooms
CORRIDOR_WIDTH = 3000  # 3m wide corridors
WALL_HEIGHT = 3500  # 3.5m wall height
CEILING_HEIGHT = 3000  # 3m ceiling height

# Wing dimensions
CLASSROOMS_PER_SIDE = 4  # 4 classrooms per side of corridor
BATHROOM_WIDTH = 6000
BATHROOM_DEPTH = 4500


def create_materials_and_types():
    """Create all materials and element types."""
    concrete = MaterialLibrary.concrete()
    brick = MaterialLibrary.brick()
    insulation = MaterialLibrary.insulation_mineral_wool()
    gypsum = MaterialLibrary.gypsum_board()

    # Compound exterior wall: brick + insulation + CMU + gypsum
    # Demonstrates per-layer hatching with different patterns
    exterior_wall_type = WallType("Exterior CMU Wall - Compound")
    exterior_wall_type.add_layer(brick, 100, LayerFunction.FINISH_EXTERIOR)
    exterior_wall_type.add_layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
    exterior_wall_type.add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)

    # Interior wall: gypsum + concrete + gypsum
    interior_wall_type = WallType("Interior Wall - Finished")
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)
    interior_wall_type.add_layer(concrete, 100, LayerFunction.STRUCTURE)
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)

    # Corridor wall: concrete CMU (thicker)
    corridor_wall_type = WallType("Corridor Wall - CMU")
    corridor_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)
    corridor_wall_type.add_layer(concrete, 175, LayerFunction.STRUCTURE, structural=True)
    corridor_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)

    types = {
        # Walls - compound types for per-layer hatching
        "exterior_wall": exterior_wall_type,
        "interior_wall": interior_wall_type,
        "corridor_wall": corridor_wall_type,
        # Doors
        "classroom_door": DoorType(name="Classroom Door", width=900, height=2100),
        "double_door": create_double_door_type("Double Door", width=1800, height=2100),
        "entry_door": create_double_door_type("Main Entry", width=2400, height=2400),
        "bathroom_door": DoorType(name="Bathroom Door", width=900, height=2100),
        "gym_door": create_double_door_type("Gym Door", width=2400, height=2400),
        # Windows
        "classroom_window": WindowType(
            name="Classroom Window",
            width=2400,
            height=1500,
            default_sill_height=900,
        ),
        "clerestory_window": WindowType(
            name="Clerestory Window",
            width=1800,
            height=600,
            default_sill_height=2400,
        ),
        "admin_window": WindowType(
            name="Admin Window",
            width=1500,
            height=1200,
            default_sill_height=1000,
        ),
        # Floor
        "floor": FloorType("Concrete Floor"),
        # Ceiling
        "acoustic_ceiling": CeilingType("Acoustic Tile Ceiling", thickness=25),
        "gym_ceiling": CeilingType("Exposed Structure", thickness=10),
    }

    # Floor layers - compound for hatching demonstration
    types["floor"].add_layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
    types["floor"].add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)

    return types


def create_classroom_wing(start_x, start_y, direction, level, types, wing_name):
    """
    Create a classroom wing with corridor.

    Args:
        start_x, start_y: Starting corner of the wing
        direction: 1 for east (positive X), -1 for west (negative X)
        level: Building level
        types: Element types dictionary
        wing_name: Name prefix for elements

    Returns:
        walls, doors, windows lists
    """
    walls = []
    doors = []
    windows = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]
    corr_wall = types["corridor_wall"]

    # Wing dimensions
    wing_length = CLASSROOMS_PER_SIDE * CLASSROOM_WIDTH + BATHROOM_WIDTH
    wing_width = CLASSROOM_DEPTH * 2 + CORRIDOR_WIDTH

    # Adjust start position based on direction
    if direction < 0:
        start_x = start_x - wing_length

    # Exterior walls of the wing
    # South wall
    wall_south = Wall(
        ext_wall,
        (start_x, start_y),
        (start_x + wing_length, start_y),
        level,
        name=f"{wing_name}_Ext_South",
    )
    # North wall
    wall_north = Wall(
        ext_wall,
        (start_x + wing_length, start_y + wing_width),
        (start_x, start_y + wing_width),
        level,
        name=f"{wing_name}_Ext_North",
    )
    # End wall (east or west depending on direction)
    if direction > 0:
        wall_end = Wall(
            ext_wall,
            (start_x + wing_length, start_y),
            (start_x + wing_length, start_y + wing_width),
            level,
            name=f"{wing_name}_Ext_End",
        )
    else:
        wall_end = Wall(
            ext_wall,
            (start_x, start_y + wing_width),
            (start_x, start_y),
            level,
            name=f"{wing_name}_Ext_End",
        )

    walls.extend([wall_south, wall_north, wall_end])

    # Corridor walls (parallel to exterior)
    corridor_y_south = start_y + CLASSROOM_DEPTH
    corridor_y_north = corridor_y_south + CORRIDOR_WIDTH

    corr_south = Wall(
        corr_wall,
        (start_x, corridor_y_south),
        (start_x + wing_length, corridor_y_south),
        level,
        name=f"{wing_name}_Corridor_South",
    )
    corr_north = Wall(
        corr_wall,
        (start_x + wing_length, corridor_y_north),
        (start_x, corridor_y_north),
        level,
        name=f"{wing_name}_Corridor_North",
    )
    walls.extend([corr_south, corr_north])

    # Create classrooms on south side
    for i in range(CLASSROOMS_PER_SIDE):
        room_x = start_x + i * CLASSROOM_WIDTH

        # Partition wall between classrooms
        if i > 0:
            partition = Wall(
                int_wall,
                (room_x, start_y),
                (room_x, corridor_y_south),
                level,
                name=f"{wing_name}_S_Partition_{i}",
            )
            walls.append(partition)

        # Classroom door
        door = Door(
            types["classroom_door"],
            corr_south,
            offset=room_x - start_x + CLASSROOM_WIDTH / 2 - types["classroom_door"].width / 2,
            name=f"{wing_name}_Classroom_S{i+1}_Door",
        )
        doors.append(door)

        # Classroom windows (2 per classroom on exterior)
        for w in range(2):
            win_offset = room_x - start_x + 1500 + w * 4000
            win = Window(
                types["classroom_window"],
                wall_south,
                offset=win_offset,
                name=f"{wing_name}_Classroom_S{i+1}_Win_{w+1}",
            )
            windows.append(win)

    # Create classrooms on north side
    for i in range(CLASSROOMS_PER_SIDE):
        room_x = start_x + i * CLASSROOM_WIDTH

        # Partition wall between classrooms
        if i > 0:
            partition = Wall(
                int_wall,
                (room_x, corridor_y_north),
                (room_x, start_y + wing_width),
                level,
                name=f"{wing_name}_N_Partition_{i}",
            )
            walls.append(partition)

        # Classroom door
        door = Door(
            types["classroom_door"],
            corr_north,
            offset=wing_length
            - (room_x - start_x)
            - CLASSROOM_WIDTH / 2
            - types["classroom_door"].width / 2,
            name=f"{wing_name}_Classroom_N{i+1}_Door",
        )
        doors.append(door)

        # Classroom windows
        for w in range(2):
            win_offset = wing_length - (room_x - start_x) - CLASSROOM_WIDTH + 1500 + w * 4000
            win = Window(
                types["classroom_window"],
                wall_north,
                offset=win_offset,
                name=f"{wing_name}_Classroom_N{i+1}_Win_{w+1}",
            )
            windows.append(win)

    # Bathrooms at the end of the wing
    bath_x = start_x + CLASSROOMS_PER_SIDE * CLASSROOM_WIDTH

    # South bathroom (Boys or Girls based on wing)
    bath_s_partition = Wall(
        int_wall,
        (bath_x, start_y),
        (bath_x, corridor_y_south),
        level,
        name=f"{wing_name}_Bath_S_West",
    )
    walls.append(bath_s_partition)

    bath_s_door = Door(
        types["bathroom_door"],
        corr_south,
        offset=bath_x - start_x + BATHROOM_WIDTH / 2 - types["bathroom_door"].width / 2,
        name=f"{wing_name}_Bath_S_Door",
    )
    doors.append(bath_s_door)

    # North bathroom
    bath_n_partition = Wall(
        int_wall,
        (bath_x, corridor_y_north),
        (bath_x, start_y + wing_width),
        level,
        name=f"{wing_name}_Bath_N_West",
    )
    walls.append(bath_n_partition)

    bath_n_door = Door(
        types["bathroom_door"],
        corr_north,
        offset=wing_length
        - (bath_x - start_x)
        - BATHROOM_WIDTH / 2
        - types["bathroom_door"].width / 2,
        name=f"{wing_name}_Bath_N_Door",
    )
    doors.append(bath_n_door)

    # Small bathroom windows
    bath_s_win = Window(
        types["admin_window"],
        wall_south,
        offset=bath_x - start_x + BATHROOM_WIDTH / 2 - types["admin_window"].width / 2,
        name=f"{wing_name}_Bath_S_Win",
    )
    bath_n_win = Window(
        types["admin_window"],
        wall_north,
        offset=wing_length
        - (bath_x - start_x)
        - BATHROOM_WIDTH / 2
        - types["admin_window"].width / 2,
        name=f"{wing_name}_Bath_N_Win",
    )
    windows.extend([bath_s_win, bath_n_win])

    return walls, doors, windows, (start_x, start_y, wing_length, wing_width)


def create_central_wing(center_x, start_y, wing_depth, level, types):
    """Create the central admin/library wing."""
    walls = []
    doors = []
    windows = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Central wing dimensions
    admin_width = 18000  # Total width of central wing
    library_depth = 12000
    admin_depth = 8000
    lobby_depth = 6000

    wing_start_x = center_x - admin_width / 2

    # Main entry lobby at south
    lobby_width = 8000
    lobby_x = center_x - lobby_width / 2

    # Exterior walls - South (with entry)
    lobby_south = Wall(
        ext_wall, (lobby_x, start_y), (lobby_x + lobby_width, start_y), level, name="Lobby_South"
    )
    walls.append(lobby_south)

    # Main entry doors
    entry_door = Door(
        types["entry_door"],
        lobby_south,
        offset=lobby_width / 2 - types["entry_door"].width / 2,
        name="Main_Entry",
    )
    doors.append(entry_door)

    # Lobby side walls connecting to classroom wings
    lobby_sw = Wall(
        ext_wall, (wing_start_x, start_y + wing_depth), (lobby_x, start_y), level, name="Lobby_SW"
    )
    lobby_se = Wall(
        ext_wall,
        (lobby_x + lobby_width, start_y),
        (wing_start_x + admin_width, start_y + wing_depth),
        level,
        name="Lobby_SE",
    )
    walls.extend([lobby_sw, lobby_se])

    # Admin offices on west side of lobby
    admin_x = wing_start_x
    admin_y = start_y + wing_depth

    admin_south = Wall(
        int_wall, (admin_x, admin_y), (admin_x + admin_depth, admin_y), level, name="Admin_South"
    )
    admin_east = Wall(
        int_wall,
        (admin_x + admin_depth, admin_y),
        (admin_x + admin_depth, admin_y + admin_depth),
        level,
        name="Admin_East",
    )
    walls.extend([admin_south, admin_east])

    # Admin door
    admin_door = Door(
        types["classroom_door"],
        admin_south,
        offset=admin_depth / 2 - types["classroom_door"].width / 2,
        name="Admin_Door",
    )
    doors.append(admin_door)

    # Library on east side
    library_x = wing_start_x + admin_width - library_depth
    library_y = admin_y

    library_south = Wall(
        int_wall,
        (library_x, library_y),
        (library_x + library_depth, library_y),
        level,
        name="Library_South",
    )
    library_west = Wall(
        int_wall,
        (library_x, library_y + library_depth),
        (library_x, library_y),
        level,
        name="Library_West",
    )
    walls.extend([library_south, library_west])

    # Library double doors
    library_door = Door(
        types["double_door"],
        library_south,
        offset=library_depth / 2 - types["double_door"].width / 2,
        name="Library_Door",
    )
    doors.append(library_door)

    # North exterior wall (connecting to gym/cafeteria)
    north_wall_y = admin_y + max(admin_depth, library_depth)
    wall_north = Wall(
        ext_wall,
        (wing_start_x + admin_width, north_wall_y),
        (wing_start_x, north_wall_y),
        level,
        name="Central_North",
    )
    walls.append(wall_north)

    # Side walls
    wall_west = Wall(
        ext_wall, (wing_start_x, north_wall_y), (wing_start_x, admin_y), level, name="Central_West"
    )
    wall_east = Wall(
        ext_wall,
        (wing_start_x + admin_width, admin_y),
        (wing_start_x + admin_width, north_wall_y),
        level,
        name="Central_East",
    )
    walls.extend([wall_west, wall_east])

    # Windows
    # Admin windows
    admin_win = Window(
        types["admin_window"],
        wall_west,
        offset=admin_depth / 2 - types["admin_window"].height / 2,
        name="Admin_Window",
    )
    windows.append(admin_win)

    # Library windows (multiple)
    for i in range(3):
        lib_win = Window(
            types["classroom_window"],
            wall_east,
            offset=admin_depth / 2 + i * 3000,
            name=f"Library_Window_{i+1}",
        )
        windows.append(lib_win)

    return walls, doors, windows, (wing_start_x, admin_y, admin_width, north_wall_y - admin_y)


def create_gym_cafeteria(center_x, start_y, level, types):
    """Create the gymnasium and cafeteria wing."""
    walls = []
    doors = []
    windows = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Gym and cafeteria dimensions
    total_width = 36000
    gym_depth = 24000
    cafeteria_depth = 15000

    wing_x = center_x - total_width / 2
    gym_width = 18000
    cafeteria_width = 18000

    # Gym on west side
    gym_south = Wall(
        ext_wall, (wing_x, start_y), (wing_x + gym_width, start_y), level, name="Gym_South"
    )
    gym_north = Wall(
        ext_wall,
        (wing_x + gym_width, start_y + gym_depth),
        (wing_x, start_y + gym_depth),
        level,
        name="Gym_North",
    )
    gym_west = Wall(
        ext_wall, (wing_x, start_y + gym_depth), (wing_x, start_y), level, name="Gym_West"
    )
    walls.extend([gym_south, gym_north, gym_west])

    # Gym doors
    gym_entry = Door(
        types["gym_door"],
        gym_south,
        offset=gym_width / 2 - types["gym_door"].width / 2,
        name="Gym_Entry",
    )
    doors.append(gym_entry)

    # Gym windows (clerestory)
    for i in range(4):
        win = Window(
            types["clerestory_window"],
            gym_north,
            offset=2000 + i * 4000,
            name=f"Gym_Clerestory_{i+1}",
        )
        windows.append(win)

    # Cafeteria on east side
    caf_south = Wall(
        ext_wall,
        (wing_x + gym_width, start_y),
        (wing_x + total_width, start_y),
        level,
        name="Cafeteria_South",
    )
    caf_north = Wall(
        ext_wall,
        (wing_x + total_width, start_y + cafeteria_depth),
        (wing_x + gym_width, start_y + cafeteria_depth),
        level,
        name="Cafeteria_North",
    )
    caf_east = Wall(
        ext_wall,
        (wing_x + total_width, start_y),
        (wing_x + total_width, start_y + cafeteria_depth),
        level,
        name="Cafeteria_East",
    )
    walls.extend([caf_south, caf_north, caf_east])

    # Partition between gym and cafeteria
    gym_caf_wall = Wall(
        int_wall,
        (wing_x + gym_width, start_y),
        (wing_x + gym_width, start_y + cafeteria_depth),
        level,
        name="Gym_Caf_Partition",
    )
    walls.append(gym_caf_wall)

    # Cafeteria doors
    caf_entry = Door(
        types["double_door"],
        caf_south,
        offset=cafeteria_width / 2 - types["double_door"].width / 2,
        name="Cafeteria_Entry",
    )
    doors.append(caf_entry)

    # Cafeteria windows
    for i in range(3):
        win = Window(
            types["classroom_window"],
            caf_east,
            offset=2000 + i * 4000,
            name=f"Cafeteria_Window_{i+1}",
        )
        windows.append(win)

    # Fill in the gap between gym and cafeteria on north side
    if gym_depth > cafeteria_depth:
        fill_wall = Wall(
            ext_wall,
            (wing_x + gym_width, start_y + cafeteria_depth),
            (wing_x + gym_width, start_y + gym_depth),
            level,
            name="Gym_Caf_Fill",
        )
        walls.append(fill_wall)

    return walls, doors, windows


def main():
    """Create school building and generate all outputs."""
    print("=" * 70)
    print("School Building Example - Elementary School")
    print("=" * 70)

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / "outputs" / "school" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Create building
    print("\nCreating building...")
    building = Building("Elementary School")
    ground = Level(building, "Ground Floor", elevation=0)
    types = create_materials_and_types()

    all_walls = []
    all_doors = []
    all_windows = []

    # Calculate overall layout
    classroom_wing_length = CLASSROOMS_PER_SIDE * CLASSROOM_WIDTH + BATHROOM_WIDTH
    classroom_wing_width = CLASSROOM_DEPTH * 2 + CORRIDOR_WIDTH

    # Center of the building
    center_x = classroom_wing_length + 9000  # Gap for central wing

    # Create East classroom wing
    print("  East Classroom Wing...")
    e_walls, e_doors, e_windows, e_bounds = create_classroom_wing(
        center_x + 9000, 0, 1, ground, types, "East"
    )
    all_walls.extend(e_walls)
    all_doors.extend(e_doors)
    all_windows.extend(e_windows)

    # Create West classroom wing
    print("  West Classroom Wing...")
    w_walls, w_doors, w_windows, w_bounds = create_classroom_wing(
        center_x - 9000, 0, -1, ground, types, "West"
    )
    all_walls.extend(w_walls)
    all_doors.extend(w_doors)
    all_windows.extend(w_windows)

    # Create Central admin/library wing
    print("  Central Wing (Admin/Library)...")
    c_walls, c_doors, c_windows, c_bounds = create_central_wing(
        center_x, -6000, classroom_wing_width, ground, types
    )
    all_walls.extend(c_walls)
    all_doors.extend(c_doors)
    all_windows.extend(c_windows)

    # Create Gym/Cafeteria wing
    print("  North Wing (Gym/Cafeteria)...")
    gym_start_y = classroom_wing_width + 3000
    g_walls, g_doors, g_windows = create_gym_cafeteria(center_x, gym_start_y, ground, types)
    all_walls.extend(g_walls)
    all_doors.extend(g_doors)
    all_windows.extend(g_windows)

    # Add connecting walls between classroom wings and central/gym areas
    print("  Adding connecting walls...")
    ext_wall = types["exterior_wall"]

    # The central wing has diagonal lobby walls that connect from:
    # - lobby_sw: (wing_start_x, start_y + wing_depth) to (lobby_x, start_y)
    # - lobby_se: (lobby_x + lobby_width, start_y) to (wing_start_x + admin_width, start_y + wing_depth)
    # where start_y = -6000, wing_depth = 18000, so the upper point is at Y = 12000
    # But the classroom wings' south walls are at Y = 0
    # Need walls from Y=0 to Y=12000 on each side to close the gap

    admin_width = 18000
    central_start_y = -6000  # start_y passed to create_central_wing
    central_wing_depth = classroom_wing_width  # wing_depth passed to create_central_wing
    diagonal_upper_y = central_start_y + central_wing_depth  # Y = 12000

    wing_start_x = center_x - admin_width / 2  # = 42000
    wing_end_x = wing_start_x + admin_width  # = 60000

    # West side: connect west wing south wall (Y=0) to diagonal wall upper point (Y=12000)
    # The west wing south wall ends at x = w_bounds[0] + w_bounds[2] = 42000
    # The diagonal lobby_sw starts at (wing_start_x, diagonal_upper_y) = (42000, 12000)
    west_wing_inner_x = w_bounds[0] + w_bounds[2]  # = 42000

    # Wall from west classroom wing south (Y=0) up to diagonal junction (Y=12000)
    west_south_connect = Wall(
        ext_wall,
        (west_wing_inner_x, 0),
        (west_wing_inner_x, diagonal_upper_y),
        ground,
        name="West_South_Connect",
    )
    all_walls.append(west_south_connect)

    # East side: same pattern
    east_wing_inner_x = e_bounds[0]  # = 60000

    # Wall from east classroom wing south (Y=0) up to diagonal junction (Y=12000)
    east_south_connect = Wall(
        ext_wall,
        (east_wing_inner_x, diagonal_upper_y),
        (east_wing_inner_x, 0),
        ground,
        name="East_South_Connect",
    )
    all_walls.append(east_south_connect)

    # North connections: close gap between classroom wings and gym
    gym_total_width = 36000
    gym_x = center_x - gym_total_width / 2  # = 33000
    gym_east_x = gym_x + gym_total_width  # = 69000

    # West wing north (Y=18000) to gym south (Y=21000)
    # West wing ends at X=42000, gym starts at X=33000
    # Need wall from (42000, 18000) to (42000, 21000) at west wing inner edge
    west_north_connect = Wall(
        ext_wall,
        (west_wing_inner_x, classroom_wing_width),
        (west_wing_inner_x, gym_start_y),
        ground,
        name="West_North_Connect",
    )
    all_walls.append(west_north_connect)

    # East wing north (Y=18000) to gym south (Y=21000)
    east_north_connect = Wall(
        ext_wall,
        (east_wing_inner_x, gym_start_y),
        (east_wing_inner_x, classroom_wing_width),
        ground,
        name="East_North_Connect",
    )
    all_walls.append(east_north_connect)

    # Process wall joins
    print("\n  Processing wall joins...")
    adjustments = detect_and_process_wall_joins(all_walls, end_cap_type=EndCapType.EXTERIOR)
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj
    print(f"    Processed {len(adjustments)} wall join adjustments")

    # Create floor slab (simplified rectangular for now)
    print("  Creating floor...")
    # Calculate bounding box of entire school
    # X bounds: from west wing to east wing
    min_x = min(w_bounds[0], e_bounds[0], c_bounds[0]) - 500
    max_x = (
        max(w_bounds[0] + w_bounds[2], e_bounds[0] + e_bounds[2], c_bounds[0] + c_bounds[2]) + 500
    )
    # Y bounds: from south entry to north of gym
    # The lobby extends south from central_start_y (-6000)
    central_start_y_floor = -6000  # Same as central_start_y passed to create_central_wing
    min_y = central_start_y_floor - 500  # South of entry lobby
    # Gym extends from gym_start_y to gym_start_y + 24000 (gym_depth)
    gym_depth = 24000
    max_y = gym_start_y + gym_depth + 500  # Include full gym

    floor_boundary = [
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    ]
    floor = Floor(types["floor"], floor_boundary, ground, name="School_Floor")
    all_floors = [floor]

    # Create ceilings
    print("  Creating ceilings...")
    ceiling = Ceiling(
        types["acoustic_ceiling"],
        floor_boundary,
        ground,
        height=CEILING_HEIGHT,
        name="School_Ceiling",
    )
    all_ceilings = [ceiling]

    # Summary
    all_elements = all_walls + all_doors + all_windows + all_floors + all_ceilings
    print(f"\n  Total elements: {len(all_elements)}")
    print(f"    Walls: {len(all_walls)}")
    print(f"    Doors: {len(all_doors)}")
    print(f"    Windows: {len(all_windows)}")
    print(f"    Floors: {len(all_floors)}")
    print(f"    Ceilings: {len(all_ceilings)}")

    # Export IFC
    print("\n" + "-" * 70)
    print("Exporting IFC...")
    ifc_path = output_dir / "school_building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path.name}")

    # Create spatial index
    print("\n" + "-" * 70)
    print("Generating drawings...")

    spatial_index = SpatialIndex()
    for elem in all_elements:
        spatial_index.insert(elem)

    cache = RepresentationCache()

    # Floor plan
    print("  Generating floor plan...")
    view_range = ViewRange(cut_height=1200, top=3000, bottom=0, view_depth=0)
    floor_plan = FloorPlanView(name="Ground Floor Plan", level=ground, view_range=view_range)
    result = floor_plan.generate(spatial_index, cache)

    # Add window outlines (black rectangles with empty fill)
    add_window_outlines(result, all_windows, view_range.cut_height)

    print(f"    Elements: {result.element_count}, Geometry: {result.total_geometry_count}")
    print(f"    Lines: {len(result.lines)}, Arcs: {len(result.arcs)}")
    print(f"    Polylines: {len(result.polylines)} (includes window outlines)")
    print(f"    Generation time: {result.generation_time*1000:.1f}ms")

    exporter = DXFExporter()
    dxf_path = output_dir / "school_floor_plan.dxf"
    exporter.export(result, str(dxf_path))
    print(f"  Saved: {dxf_path.name}")

    # Summary
    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    for f in sorted(output_dir.iterdir()):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name} ({size_kb:.1f} KB)")

    print("\nSchool summary:")
    print("  - Single-story H-shaped plan")
    print(f"  - East Wing: {CLASSROOMS_PER_SIDE * 2} classrooms, 2 restrooms")
    print(f"  - West Wing: {CLASSROOMS_PER_SIDE * 2} classrooms, 2 restrooms")
    print("  - Central: Main entry, admin offices, library")
    print("  - North: Gymnasium (18m x 24m), Cafeteria (18m x 15m)")
    print(f"  - Total classrooms: {CLASSROOMS_PER_SIDE * 4}")
    print("  - Approximate building footprint: ~90m x 45m")

    print(f"\nOutput directory: {output_dir}")


if __name__ == "__main__":
    main()
