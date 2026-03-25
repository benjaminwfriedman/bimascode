"""
Office Building Example - Modern Open-Plan Office

Demonstrates:
- Multi-level building with elevator core
- Open-plan workspace with structural grid
- Private offices and meeting rooms
- Structural columns and beams
- Floor slabs with openings
- Ceilings (suspended in offices, exposed in open areas)
- View templates for architectural vs structural plans
- IFC export + multiple DXF drawings

Building: 30m x 20m, 2 floors
- Ground Floor: Reception, open workspace, 4 meeting rooms, elevator/stair core
- First Floor: 6 private offices, open workspace, 2 large conference rooms
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
    create_basic_wall_type,
    detect_and_process_wall_joins,
)
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.architecture.door_type import DoorType, create_double_door_type
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.architecture.wall_type import WallType
from bimascode.architecture.window_type import WindowType
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.line_styles import LineWeight
from bimascode.drawing.primitives import Point2D, TextAlignment, TextNote2D
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.drawing.view_templates import CategoryVisibility, GraphicOverride, ViewTemplate
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.structure import (
    Beam,
    StructuralColumn,
    create_rectangular_beam_type,
    create_square_column_type,
)
from bimascode.utils.materials import MaterialLibrary

# Building dimensions (mm)
BUILDING_LENGTH = 30000  # 30m
BUILDING_WIDTH = 20000  # 20m
FLOOR_HEIGHT = 3500  # 3.5m floor-to-floor
CEILING_HEIGHT = 2700  # 2.7m ceiling height

# Structural grid (6m x 5m)
GRID_X = [0, 6000, 12000, 18000, 24000, 30000]
GRID_Y = [0, 5000, 10000, 15000, 20000]

# Core dimensions (elevator/stair)
CORE_WIDTH = 6000
CORE_DEPTH = 5000
CORE_X = 12000  # Centered on grid


def create_materials_and_types():
    """Create all material and element types."""
    concrete = MaterialLibrary.concrete()
    steel = MaterialLibrary.steel()
    glass = MaterialLibrary.glass()
    insulation = MaterialLibrary.insulation_mineral_wool()
    gypsum = MaterialLibrary.gypsum_board()

    # Compound exterior wall: glass + insulation + concrete
    # Demonstrates per-layer hatching with different patterns
    exterior_wall_type = WallType("Exterior Wall - Curtain")
    exterior_wall_type.add_layer(glass, 25, LayerFunction.FINISH_EXTERIOR)
    exterior_wall_type.add_layer(insulation, 75, LayerFunction.THERMAL_INSULATION)
    exterior_wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

    # Interior partition: gypsum + steel stud + gypsum
    interior_wall_type = WallType("Interior Partition")
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)
    interior_wall_type.add_layer(steel, 75, LayerFunction.STRUCTURE)
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)

    types = {
        # Walls - compound types for per-layer hatching
        "exterior_wall": exterior_wall_type,
        "interior_wall": interior_wall_type,
        "core_wall": create_basic_wall_type("Core Wall", 200, concrete),
        # Doors
        "single_door": DoorType(name="Single Door", width=900, height=2100),
        "double_door": create_double_door_type("Double Door", width=1800, height=2100),
        "glass_door": DoorType(name="Glass Entry", width=2400, height=2400),
        # Windows
        "curtain_window": WindowType(
            name="Curtain Wall Window",
            width=2400,
            height=2000,
            default_sill_height=800,
        ),
        "office_window": WindowType(
            name="Office Window",
            width=1500,
            height=1500,
            default_sill_height=900,
        ),
        # Floor
        "floor": FloorType("Concrete Floor Slab"),
        # Ceiling
        "suspended_ceiling": CeilingType("Suspended Ceiling", thickness=20),
        # Structure
        "column": create_square_column_type("Steel Column", size=400, material=steel),
        "main_beam": create_rectangular_beam_type(
            "Main Beam", width=300, height=500, material=steel
        ),
        "secondary_beam": create_rectangular_beam_type(
            "Secondary Beam", width=200, height=400, material=steel
        ),
    }

    # Add floor layers - compound for hatching demonstration
    types["floor"].add_layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
    types["floor"].add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

    return types


def create_structural_grid(level, types, floor_num):
    """Create columns and beams for a floor."""
    columns = []
    beams = []

    column_type = types["column"]
    main_beam = types["main_beam"]
    secondary_beam = types["secondary_beam"]

    # Columns at all grid intersections
    for i, x in enumerate(GRID_X):
        for j, y in enumerate(GRID_Y):
            # Skip columns inside the core area
            if CORE_X <= x <= CORE_X + CORE_WIDTH and GRID_Y[1] <= y <= GRID_Y[2]:
                if not (x == CORE_X or x == CORE_X + CORE_WIDTH):
                    continue

            col = StructuralColumn(
                column_type,
                level,
                position=(x, y),
                height=FLOOR_HEIGHT,
                rotation=0,
                name=f"Col_{chr(65+i)}{j+1}_F{floor_num}",
            )
            columns.append(col)

    # Main beams in X direction (along Y gridlines)
    beam_z = FLOOR_HEIGHT - main_beam.height / 2
    for j, y in enumerate(GRID_Y):
        for i in range(len(GRID_X) - 1):
            beam = Beam(
                main_beam,
                level,
                start_point=(GRID_X[i], y, beam_z),
                end_point=(GRID_X[i + 1], y, beam_z),
                name=f"MainBeam_X_{chr(65+i)}{j+1}_F{floor_num}",
            )
            beams.append(beam)

    # Secondary beams in Y direction (along X gridlines)
    sec_beam_z = beam_z - main_beam.height / 2 - secondary_beam.height / 2
    for i, x in enumerate(GRID_X):
        for j in range(len(GRID_Y) - 1):
            beam = Beam(
                secondary_beam,
                level,
                start_point=(x, GRID_Y[j], sec_beam_z),
                end_point=(x, GRID_Y[j + 1], sec_beam_z),
                name=f"SecBeam_Y_{chr(65+i)}{j+1}_F{floor_num}",
            )
            beams.append(beam)

    return columns, beams


def create_core(level, types, floor_num):
    """Create elevator/stair core walls."""
    walls = []
    doors = []

    core_type = types["core_wall"]
    door_type = types["single_door"]

    core_y = GRID_Y[1]  # Core starts at second gridline

    # Core walls
    walls.append(
        Wall(
            core_type,
            (CORE_X, core_y),
            (CORE_X + CORE_WIDTH, core_y),
            level,
            name=f"Core_South_F{floor_num}",
        )
    )
    walls.append(
        Wall(
            core_type,
            (CORE_X + CORE_WIDTH, core_y),
            (CORE_X + CORE_WIDTH, core_y + CORE_DEPTH),
            level,
            name=f"Core_East_F{floor_num}",
        )
    )
    walls.append(
        Wall(
            core_type,
            (CORE_X + CORE_WIDTH, core_y + CORE_DEPTH),
            (CORE_X, core_y + CORE_DEPTH),
            level,
            name=f"Core_North_F{floor_num}",
        )
    )
    walls.append(
        Wall(
            core_type,
            (CORE_X, core_y + CORE_DEPTH),
            (CORE_X, core_y),
            level,
            name=f"Core_West_F{floor_num}",
        )
    )

    # Core doors (south side for access)
    core_door = Door(
        door_type,
        walls[0],
        offset=CORE_WIDTH / 2 - door_type.width / 2,
        name=f"Core_Door_F{floor_num}",
    )
    doors.append(core_door)

    return walls, doors


def create_ground_floor(building, types):
    """Create ground floor with reception, open workspace, and meeting rooms."""
    ground = Level(building, "Ground Floor", elevation=0)

    all_walls = []
    all_doors = []
    all_windows = []
    all_floors = []
    all_ceilings = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Exterior walls
    wall_south = Wall(ext_wall, (0, 0), (BUILDING_LENGTH, 0), ground, name="Ext_South_G")
    wall_east = Wall(
        ext_wall, (BUILDING_LENGTH, 0), (BUILDING_LENGTH, BUILDING_WIDTH), ground, name="Ext_East_G"
    )
    wall_north = Wall(
        ext_wall, (BUILDING_LENGTH, BUILDING_WIDTH), (0, BUILDING_WIDTH), ground, name="Ext_North_G"
    )
    wall_west = Wall(ext_wall, (0, BUILDING_WIDTH), (0, 0), ground, name="Ext_West_G")
    all_walls.extend([wall_south, wall_east, wall_north, wall_west])

    # Main entrance (south wall, center)
    main_entry = Door(
        types["glass_door"],
        wall_south,
        offset=BUILDING_LENGTH / 2 - types["glass_door"].width / 2,
        name="Main_Entry",
    )
    all_doors.append(main_entry)

    # Windows on exterior walls
    window_type = types["curtain_window"]
    for i in range(4):
        # South windows (skip center for door)
        if i != 1 and i != 2:
            win = Window(window_type, wall_south, offset=3000 + i * 6000, name=f"Win_S_{i}")
            all_windows.append(win)
        # North windows
        win = Window(window_type, wall_north, offset=3000 + i * 6000, name=f"Win_N_{i}")
        all_windows.append(win)

    for i in range(3):
        # East windows
        win = Window(window_type, wall_east, offset=2500 + i * 5000, name=f"Win_E_{i}")
        all_windows.append(win)
        # West windows
        win = Window(window_type, wall_west, offset=2500 + i * 5000, name=f"Win_W_{i}")
        all_windows.append(win)

    # Reception area (front, south-west corner)
    reception_width = 8000
    reception_depth = 6000
    reception_wall = Wall(
        int_wall,
        (reception_width, 0),
        (reception_width, reception_depth),
        ground,
        name="Reception_East_G",
    )
    all_walls.append(reception_wall)

    # Meeting rooms (4 rooms along west wall, behind reception)
    meeting_room_width = 5000
    meeting_room_depth = 4000
    meeting_y_start = reception_depth + 1000

    for i in range(4):
        room_y = meeting_y_start + i * (meeting_room_depth + 500)
        if room_y + meeting_room_depth > BUILDING_WIDTH:
            break

        # Room walls
        room_south = Wall(
            int_wall,
            (0, room_y),
            (meeting_room_width, room_y),
            ground,
            name=f"Meeting{i+1}_South_G",
        )
        room_east = Wall(
            int_wall,
            (meeting_room_width, room_y),
            (meeting_room_width, room_y + meeting_room_depth),
            ground,
            name=f"Meeting{i+1}_East_G",
        )
        room_north = Wall(
            int_wall,
            (meeting_room_width, room_y + meeting_room_depth),
            (0, room_y + meeting_room_depth),
            ground,
            name=f"Meeting{i+1}_North_G",
        )
        all_walls.extend([room_south, room_east, room_north])

        # Meeting room door
        door = Door(
            types["single_door"],
            room_east,
            offset=meeting_room_depth / 2 - types["single_door"].width / 2,
            name=f"Meeting{i+1}_Door_G",
        )
        all_doors.append(door)

    # Core walls and doors
    core_walls, core_doors = create_core(ground, types, 0)
    all_walls.extend(core_walls)
    all_doors.extend(core_doors)

    # Floor slab
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["floor"], floor_boundary, ground, name="Floor_G")
    all_floors.append(floor)

    # Ceiling over enclosed areas (reception + meeting rooms)
    ceiling_boundary = [
        (0, 0),
        (meeting_room_width + 1000, 0),
        (meeting_room_width + 1000, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    ceiling = Ceiling(
        types["suspended_ceiling"],
        ceiling_boundary,
        ground,
        height=CEILING_HEIGHT,
        name="Ceiling_West_G",
    )
    all_ceilings.append(ceiling)

    # Structure
    columns, beams = create_structural_grid(ground, types, 0)

    return ground, all_walls, all_doors, all_windows, all_floors, all_ceilings, columns, beams


def create_first_floor(building, types):
    """Create first floor with private offices and conference rooms."""
    first = Level(building, "First Floor", elevation=FLOOR_HEIGHT)

    all_walls = []
    all_doors = []
    all_windows = []
    all_floors = []
    all_ceilings = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Exterior walls
    wall_south = Wall(ext_wall, (0, 0), (BUILDING_LENGTH, 0), first, name="Ext_South_1")
    wall_east = Wall(
        ext_wall, (BUILDING_LENGTH, 0), (BUILDING_LENGTH, BUILDING_WIDTH), first, name="Ext_East_1"
    )
    wall_north = Wall(
        ext_wall, (BUILDING_LENGTH, BUILDING_WIDTH), (0, BUILDING_WIDTH), first, name="Ext_North_1"
    )
    wall_west = Wall(ext_wall, (0, BUILDING_WIDTH), (0, 0), first, name="Ext_West_1")
    all_walls.extend([wall_south, wall_east, wall_north, wall_west])

    # Windows
    window_type = types["curtain_window"]
    for i in range(5):
        win_s = Window(window_type, wall_south, offset=2000 + i * 5500, name=f"Win_S1_{i}")
        win_n = Window(window_type, wall_north, offset=2000 + i * 5500, name=f"Win_N1_{i}")
        all_windows.extend([win_s, win_n])

    for i in range(3):
        win_e = Window(window_type, wall_east, offset=2500 + i * 5000, name=f"Win_E1_{i}")
        win_w = Window(window_type, wall_west, offset=2500 + i * 5000, name=f"Win_W1_{i}")
        all_windows.extend([win_e, win_w])

    # Private offices along south wall (6 offices, 4m x 4m each)
    office_width = 4000
    office_depth = 4000
    office_start_x = 1000

    # Corridor wall
    corridor_wall = Wall(
        int_wall, (0, office_depth), (BUILDING_LENGTH, office_depth), first, name="Corridor_South_1"
    )
    all_walls.append(corridor_wall)

    for i in range(6):
        office_x = office_start_x + i * (office_width + 500)
        if office_x + office_width > BUILDING_LENGTH - 1000:
            break

        # Partition between offices
        if i > 0:
            partition = Wall(
                int_wall, (office_x, 0), (office_x, office_depth), first, name=f"Office{i+1}_West_1"
            )
            all_walls.append(partition)

        # Office door
        door = Door(
            types["single_door"],
            corridor_wall,
            offset=office_x + office_width / 2 - types["single_door"].width / 2,
            name=f"Office{i+1}_Door_1",
        )
        all_doors.append(door)

    # Conference rooms along north wall (2 large rooms)
    conf_width = 8000
    conf_depth = 5000
    conf_y = BUILDING_WIDTH - conf_depth

    # Corridor wall for conference area
    conf_corridor = Wall(
        int_wall, (0, conf_y), (BUILDING_LENGTH, conf_y), first, name="Corridor_North_1"
    )
    all_walls.append(conf_corridor)

    for i in range(2):
        conf_x = 3000 + i * (conf_width + 6000)

        # Conference room walls (just partitions, exterior already exists)
        if i == 0:
            conf_west = Wall(
                int_wall,
                (conf_x, conf_y),
                (conf_x, BUILDING_WIDTH),
                first,
                name=f"Conf{i+1}_West_1",
            )
            all_walls.append(conf_west)

        conf_east = Wall(
            int_wall,
            (conf_x + conf_width, BUILDING_WIDTH),
            (conf_x + conf_width, conf_y),
            first,
            name=f"Conf{i+1}_East_1",
        )
        all_walls.append(conf_east)

        # Double door for conference room
        door = Door(
            types["double_door"],
            conf_corridor,
            offset=conf_x + conf_width / 2 - types["double_door"].width / 2,
            name=f"Conf{i+1}_Door_1",
        )
        all_doors.append(door)

    # Core
    core_walls, core_doors = create_core(first, types, 1)
    all_walls.extend(core_walls)
    all_doors.extend(core_doors)

    # Floor slab
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["floor"], floor_boundary, first, name="Floor_1")
    all_floors.append(floor)

    # Ceiling over offices and conference rooms
    office_ceiling = Ceiling(
        types["suspended_ceiling"],
        [
            (0, 0),
            (BUILDING_LENGTH, 0),
            (BUILDING_LENGTH, office_depth + 1000),
            (0, office_depth + 1000),
        ],
        first,
        height=CEILING_HEIGHT,
        name="Ceiling_Offices_1",
    )
    conf_ceiling = Ceiling(
        types["suspended_ceiling"],
        [
            (0, conf_y - 1000),
            (BUILDING_LENGTH, conf_y - 1000),
            (BUILDING_LENGTH, BUILDING_WIDTH),
            (0, BUILDING_WIDTH),
        ],
        first,
        height=CEILING_HEIGHT,
        name="Ceiling_Conf_1",
    )
    all_ceilings.extend([office_ceiling, conf_ceiling])

    # Structure
    columns, beams = create_structural_grid(first, types, 1)

    return first, all_walls, all_doors, all_windows, all_floors, all_ceilings, columns, beams


def create_view_templates():
    """Create architectural and structural view templates."""
    arch_template = ViewTemplate("Architectural Plan")
    arch_template.set_category_override(
        "Wall",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            cut_line_weight=LineWeight.HEAVY,
            projection_line_weight=LineWeight.NARROW,
        ),
    )
    arch_template.set_category_override(
        "Door",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            cut_line_weight=LineWeight.WIDE,
        ),
    )
    arch_template.set_category_override(
        "Window",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            cut_line_weight=LineWeight.WIDE,
        ),
    )
    arch_template.set_category_override(
        "StructuralColumn",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            cut_line_weight=LineWeight.MEDIUM,
            halftone=True,
        ),
    )
    arch_template.set_category_override(
        "Beam",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            line_weight=LineWeight.FINE,
            halftone=True,
        ),
    )

    struct_template = ViewTemplate("Structural Plan")
    struct_template.set_category_override(
        "StructuralColumn",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            cut_line_weight=LineWeight.HEAVY,
        ),
    )
    struct_template.set_category_override(
        "Beam",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            line_weight=LineWeight.MEDIUM,
        ),
    )
    struct_template.set_category_override(
        "Wall",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            line_weight=LineWeight.FINE,
            halftone=True,
        ),
    )
    struct_template.set_category_override(
        "Door",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            line_weight=LineWeight.FINE,
            halftone=True,
        ),
    )
    struct_template.set_category_override(
        "Window",
        GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            line_weight=LineWeight.FINE,
            halftone=True,
        ),
    )

    return arch_template, struct_template


def add_ground_floor_annotations(result):
    """Add text notes to ground floor plan."""
    # Room labels
    result.text_notes.append(
        TextNote2D(
            position=Point2D(4000, 3000),
            content="RECEPTION",
            height=250,
            alignment=TextAlignment.MIDDLE_CENTER,
        )
    )
    result.text_notes.append(
        TextNote2D(
            position=Point2D(18000, 10000),
            content="OPEN WORKSPACE",
            height=300,
            alignment=TextAlignment.MIDDLE_CENTER,
        )
    )
    result.text_notes.append(
        TextNote2D(
            position=Point2D(CORE_X + CORE_WIDTH / 2, GRID_Y[1] + CORE_DEPTH / 2),
            content="CORE",
            height=200,
            alignment=TextAlignment.MIDDLE_CENTER,
        )
    )

    # Meeting room labels
    meeting_y_start = 7000
    for i in range(3):
        room_y = meeting_y_start + i * 4500
        result.text_notes.append(
            TextNote2D(
                position=Point2D(2500, room_y + 2000),
                content=f"MEETING\n{i + 1}",
                height=150,
                alignment=TextAlignment.MIDDLE_CENTER,
            )
        )

    # General note
    result.text_notes.append(
        TextNote2D(
            position=Point2D(-500, -2000),
            content="GROUND FLOOR PLAN\nScale: 1:100",
            height=150,
            alignment=TextAlignment.TOP_LEFT,
            width=3000,
        )
    )


def add_first_floor_annotations(result):
    """Add text notes to first floor plan."""
    # Office labels
    office_start_x = 1000
    office_width = 4000
    for i in range(6):
        office_x = office_start_x + i * 4500
        if office_x + office_width > BUILDING_LENGTH - 1000:
            break
        result.text_notes.append(
            TextNote2D(
                position=Point2D(office_x + office_width / 2, 2000),
                content=f"OFFICE\n{i + 1}",
                height=150,
                alignment=TextAlignment.MIDDLE_CENTER,
            )
        )

    # Conference room labels
    result.text_notes.append(
        TextNote2D(
            position=Point2D(7000, 17500),
            content="CONFERENCE\nROOM A",
            height=200,
            alignment=TextAlignment.MIDDLE_CENTER,
        )
    )
    result.text_notes.append(
        TextNote2D(
            position=Point2D(21000, 17500),
            content="CONFERENCE\nROOM B",
            height=200,
            alignment=TextAlignment.MIDDLE_CENTER,
        )
    )

    # Open workspace (positioned between conference rooms and office corridor)
    result.text_notes.append(
        TextNote2D(
            position=Point2D(15000, 12500),
            content="OPEN WORKSPACE",
            height=300,
            alignment=TextAlignment.MIDDLE_CENTER,
        )
    )

    # Core
    result.text_notes.append(
        TextNote2D(
            position=Point2D(CORE_X + CORE_WIDTH / 2, GRID_Y[1] + CORE_DEPTH / 2),
            content="CORE",
            height=200,
            alignment=TextAlignment.MIDDLE_CENTER,
        )
    )

    # General note
    result.text_notes.append(
        TextNote2D(
            position=Point2D(-500, -2000),
            content="FIRST FLOOR PLAN\nScale: 1:100",
            height=150,
            alignment=TextAlignment.TOP_LEFT,
            width=3000,
        )
    )


def generate_floor_plan(
    name, level, spatial_index, cache, output_path, template=None, add_annotations_fn=None
):
    """Generate and export a floor plan."""
    print(f"  Generating {name}...")

    view_range = ViewRange(cut_height=1200, top=3000, bottom=0, view_depth=0)
    floor_plan = FloorPlanView(name=name, level=level, view_range=view_range, template=template)
    result = floor_plan.generate(spatial_index, cache)

    # Add annotations if function provided
    if add_annotations_fn:
        add_annotations_fn(result)

    print(f"    Elements: {result.element_count}, Geometry: {result.total_geometry_count}")
    if result.text_notes:
        print(f"    Text notes: {len(result.text_notes)}")

    exporter = DXFExporter()
    exporter.export(result, str(output_path))


def generate_section(name, spatial_index, cache, point, normal, output_path, height_range):
    """Generate and export a section view."""
    print(f"  Generating {name}...")

    section = SectionView(
        name=name,
        plane_point=point,
        plane_normal=normal,
        depth=25000,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
        show_hidden_lines=False,
    )
    result = section.generate(spatial_index, cache)

    print(f"    Elements: {result.element_count}, Geometry: {result.total_geometry_count}")

    exporter = DXFExporter()
    exporter.export(result, str(output_path))


def main():
    """Create office building and generate all outputs."""
    print("=" * 70)
    print("Office Building Example")
    print("=" * 70)

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / "outputs" / "office" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Create building
    print("\nCreating building...")
    building = Building("Modern Office Building")
    types = create_materials_and_types()

    # Create floors
    print("\n  Ground Floor...")
    ground, g_walls, g_doors, g_windows, g_floors, g_ceilings, g_columns, g_beams = (
        create_ground_floor(building, types)
    )

    print("  First Floor...")
    first, f_walls, f_doors, f_windows, f_floors, f_ceilings, f_columns, f_beams = (
        create_first_floor(building, types)
    )

    # Process wall joins per floor
    print("\n  Processing wall joins...")
    for walls in [g_walls, f_walls]:
        adjustments = detect_and_process_wall_joins(walls, end_cap_type=EndCapType.EXTERIOR)
        for wall, adj in adjustments.items():
            wall._trim_adjustments = adj

    # Summary
    all_elements = (
        g_walls
        + f_walls
        + g_doors
        + f_doors
        + g_windows
        + f_windows
        + g_floors
        + f_floors
        + g_ceilings
        + f_ceilings
        + g_columns
        + f_columns
        + g_beams
        + f_beams
    )
    print(f"\n  Total elements: {len(all_elements)}")
    print(f"    Walls: {len(g_walls) + len(f_walls)}")
    print(f"    Doors: {len(g_doors) + len(f_doors)}")
    print(f"    Windows: {len(g_windows) + len(f_windows)}")
    print(f"    Floors: {len(g_floors) + len(f_floors)}")
    print(f"    Ceilings: {len(g_ceilings) + len(f_ceilings)}")
    print(f"    Columns: {len(g_columns) + len(f_columns)}")
    print(f"    Beams: {len(g_beams) + len(f_beams)}")

    # Export IFC
    print("\n" + "-" * 70)
    print("Exporting IFC...")
    ifc_path = output_dir / "office_building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path.name}")

    # Create spatial indices for each floor
    print("\n" + "-" * 70)
    print("Generating drawings...")

    g_index = SpatialIndex()
    for elem in g_walls + g_doors + g_windows + g_floors + g_ceilings + g_columns + g_beams:
        g_index.insert(elem)

    f_index = SpatialIndex()
    for elem in f_walls + f_doors + f_windows + f_floors + f_ceilings + f_columns + f_beams:
        f_index.insert(elem)

    cache = RepresentationCache()
    arch_template, struct_template = create_view_templates()

    # Floor plans
    generate_floor_plan(
        "Ground Floor - Architectural",
        ground,
        g_index,
        cache,
        output_dir / "ground_floor_arch.dxf",
        arch_template,
        add_ground_floor_annotations,
    )
    generate_floor_plan(
        "Ground Floor - Structural",
        ground,
        g_index,
        cache,
        output_dir / "ground_floor_struct.dxf",
        struct_template,
    )
    generate_floor_plan(
        "First Floor - Architectural",
        first,
        f_index,
        cache,
        output_dir / "first_floor_arch.dxf",
        arch_template,
        add_first_floor_annotations,
    )
    generate_floor_plan(
        "First Floor - Structural",
        first,
        f_index,
        cache,
        output_dir / "first_floor_struct.dxf",
        struct_template,
    )

    # Sections (combine both floors)
    combined_index = SpatialIndex()
    for elem in all_elements:
        combined_index.insert(elem)

    generate_section(
        "Section A-A (Through Core)",
        combined_index,
        cache,
        (BUILDING_LENGTH / 2, BUILDING_WIDTH / 2, 0),
        (0, 1, 0),
        output_dir / "section_AA.dxf",
        (0, FLOOR_HEIGHT * 2 + 500),
    )
    generate_section(
        "Section B-B (Through Offices)",
        combined_index,
        cache,
        (BUILDING_LENGTH / 2, 2000, 0),
        (0, 1, 0),
        output_dir / "section_BB.dxf",
        (0, FLOOR_HEIGHT * 2 + 500),
    )

    # Summary
    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    for f in sorted(output_dir.iterdir()):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name} ({size_kb:.1f} KB)")

    print("\nBuilding summary:")
    print("  - 2 floors (Ground + First)")
    print("  - Ground: Reception, 4 meeting rooms, open workspace")
    print("  - First: 6 private offices, 2 conference rooms, open workspace")
    print("  - Central elevator/stair core")
    print("  - 6m x 5m structural grid with steel columns and beams")

    print(f"\nOutput directory: {output_dir}")


if __name__ == "__main__":
    main()
