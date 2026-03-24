"""
Residential Home Example - Two-Story Family Home

Demonstrates:
- Multi-level residential building
- Various room types (bedrooms, bathrooms, kitchen, living areas)
- Interior and exterior walls with different thicknesses
- Doors (single, double, sliding concept)
- Windows of various sizes
- Floor slabs
- Roof (flat for simplicity)
- Ceilings throughout
- IFC export + floor plan DXF drawings

Building: 15m x 12m, 2 floors
- Ground Floor: Entry, living room, dining room, kitchen, powder room, garage
- Upper Floor: Master suite with ensuite, 2 bedrooms, shared bathroom, laundry
"""

from datetime import datetime
from pathlib import Path

from bimascode.architecture import (
    Ceiling,
    Door,
    EndCapType,
    Floor,
    Roof,
    Wall,
    Window,
    create_basic_wall_type,
    detect_and_process_wall_joins,
)
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.architecture.door_type import DoorType, create_double_door_type
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.architecture.window_type import WindowType
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.materials import MaterialLibrary

# Building dimensions (mm)
BUILDING_LENGTH = 15000  # 15m
BUILDING_WIDTH = 12000  # 12m
FLOOR_HEIGHT = 3000  # 3m floor-to-floor
CEILING_HEIGHT = 2700  # 2.7m ceiling height

# Wall thicknesses
EXT_WALL_THICKNESS = 300  # Exterior walls
INT_WALL_THICKNESS = 150  # Interior partitions


def create_materials_and_types():
    """Create all materials and element types."""
    concrete = MaterialLibrary.concrete()
    wood = MaterialLibrary.timber()
    gypsum = MaterialLibrary.gypsum_board()

    types = {
        # Walls
        "exterior_wall": create_basic_wall_type("Exterior Wall", EXT_WALL_THICKNESS, concrete),
        "interior_wall": create_basic_wall_type("Interior Wall", INT_WALL_THICKNESS, gypsum),
        "garage_wall": create_basic_wall_type("Garage Wall", 200, concrete),
        # Doors
        "entry_door": DoorType(name="Entry Door", width=1000, height=2200),
        "interior_door": DoorType(name="Interior Door", width=800, height=2100),
        "double_door": create_double_door_type("Double Door", width=1600, height=2100),
        "garage_door": DoorType(name="Garage Door", width=2700, height=2400),
        "sliding_door": DoorType(name="Sliding Door", width=2400, height=2200),
        # Windows
        "large_window": WindowType(
            name="Large Window",
            width=2000,
            height=1500,
            default_sill_height=900,
        ),
        "medium_window": WindowType(
            name="Medium Window",
            width=1200,
            height=1200,
            default_sill_height=1000,
        ),
        "small_window": WindowType(
            name="Small Window",
            width=600,
            height=800,
            default_sill_height=1400,
        ),
        "picture_window": WindowType(
            name="Picture Window",
            width=3000,
            height=1800,
            default_sill_height=600,
        ),
        # Floor
        "ground_floor": FloorType("Ground Floor Slab"),
        "upper_floor": FloorType("Upper Floor"),
        # Ceiling
        "ceiling": CeilingType("Gypsum Ceiling", thickness=15),
        # Roof
        "roof": FloorType("Flat Roof"),
    }

    # Add floor layers
    types["ground_floor"].add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)
    types["upper_floor"].add_layer(wood, 200, LayerFunction.STRUCTURE, structural=True)
    types["roof"].add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)

    return types


def create_ground_floor(building, types):
    """Create ground floor with living areas, kitchen, and garage."""
    ground = Level(building, "Ground Floor", elevation=0)

    walls = []
    doors = []
    windows = []
    floors = []
    ceilings = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Layout (all dimensions in mm):
    # +------------------------+
    # |        GARAGE          |  Garage: 6m x 6m (north-west corner)
    # +--------+---------------+
    # |        |    LIVING     |  Living: 9m x 6m (north-east)
    # | KITCHEN|     ROOM      |
    # +--------+-------+-------+
    # | DINING |POWDER | ENTRY |  Entry: 3m x 3m (south-east corner)
    # |  ROOM  | ROOM  |       |  Powder: 3m x 3m
    # +--------+-------+-------+  Dining: 6m x 6m

    garage_width = 6000
    garage_depth = 6000
    living_width = 9000
    living_depth = 6000
    kitchen_width = 6000
    kitchen_depth = 3000
    dining_width = 6000
    dining_depth = 6000
    powder_width = 3000
    powder_depth = 3000
    entry_width = 3000
    entry_depth = 3000

    # === EXTERIOR WALLS ===
    wall_south = Wall(ext_wall, (0, 0), (BUILDING_LENGTH, 0), ground, name="Ext_South_G")
    wall_east = Wall(
        ext_wall, (BUILDING_LENGTH, 0), (BUILDING_LENGTH, BUILDING_WIDTH), ground, name="Ext_East_G"
    )
    wall_north = Wall(
        ext_wall, (BUILDING_LENGTH, BUILDING_WIDTH), (0, BUILDING_WIDTH), ground, name="Ext_North_G"
    )
    wall_west = Wall(ext_wall, (0, BUILDING_WIDTH), (0, 0), ground, name="Ext_West_G")
    walls.extend([wall_south, wall_east, wall_north, wall_west])

    # === GARAGE WALLS (internal partition) ===
    garage_south = Wall(
        int_wall, (0, dining_depth), (garage_width, dining_depth), ground, name="Garage_South_G"
    )
    garage_east = Wall(
        int_wall,
        (garage_width, dining_depth),
        (garage_width, BUILDING_WIDTH),
        ground,
        name="Garage_East_G",
    )
    walls.extend([garage_south, garage_east])

    # Garage door (north wall)
    garage_door = Door(
        types["garage_door"],
        wall_north,
        offset=BUILDING_LENGTH - garage_width / 2 - types["garage_door"].width / 2,
        name="Garage_Door",
    )
    doors.append(garage_door)

    # Door from garage to house
    garage_house_door = Door(
        types["interior_door"], garage_south, offset=garage_width - 1500, name="Garage_House_Door"
    )
    doors.append(garage_house_door)

    # === KITCHEN WALLS ===
    # Kitchen is between garage and dining, opens to living
    kitchen_south = Wall(
        int_wall, (0, kitchen_depth), (kitchen_width, kitchen_depth), ground, name="Kitchen_South_G"
    )
    kitchen_east = Wall(
        int_wall,
        (kitchen_width, kitchen_depth),
        (kitchen_width, dining_depth),
        ground,
        name="Kitchen_East_G",
    )
    walls.extend([kitchen_south, kitchen_east])

    # Kitchen window (west wall)
    kitchen_window = Window(
        types["medium_window"],
        wall_west,
        offset=kitchen_depth
        + (dining_depth - kitchen_depth) / 2
        - types["medium_window"].height / 2,
        name="Kitchen_Window",
    )
    windows.append(kitchen_window)

    # === DINING ROOM ===
    # Dining is south-west, open to kitchen above
    # Large window on south wall
    dining_window = Window(
        types["large_window"],
        wall_south,
        offset=dining_width / 2 - types["large_window"].width / 2,
        name="Dining_Window",
    )
    windows.append(dining_window)

    # === LIVING ROOM ===
    # Living room is north-east area, large open space
    # Picture window on east wall
    living_picture_window = Window(
        types["picture_window"],
        wall_east,
        offset=dining_depth + living_depth / 2 - types["picture_window"].height / 2,
        name="Living_Picture_Window",
    )
    windows.append(living_picture_window)

    # Medium windows on north wall (living area)
    living_north_window = Window(
        types["large_window"],
        wall_north,
        offset=living_width / 2 - types["large_window"].width / 2,
        name="Living_North_Window",
    )
    windows.append(living_north_window)

    # Sliding door to backyard (east wall, lower)
    sliding_door = Door(
        types["sliding_door"], wall_east, offset=entry_depth + 500, name="Sliding_Door_Backyard"
    )
    doors.append(sliding_door)

    # === ENTRY ===
    entry_x = BUILDING_LENGTH - entry_width
    entry_y = 0

    entry_west = Wall(
        int_wall, (entry_x, entry_y), (entry_x, entry_depth), ground, name="Entry_West_G"
    )
    entry_north = Wall(
        int_wall,
        (entry_x, entry_depth),
        (BUILDING_LENGTH, entry_depth),
        ground,
        name="Entry_North_G",
    )
    walls.extend([entry_west, entry_north])

    # Front door
    front_door = Door(
        types["entry_door"],
        wall_south,
        offset=entry_x + entry_width / 2 - types["entry_door"].width / 2,
        name="Front_Door",
    )
    doors.append(front_door)

    # === POWDER ROOM ===
    powder_x = entry_x - powder_width
    powder_y = 0

    powder_west = Wall(
        int_wall, (powder_x, powder_y), (powder_x, powder_depth), ground, name="Powder_West_G"
    )
    powder_north = Wall(
        int_wall, (powder_x, powder_depth), (entry_x, powder_depth), ground, name="Powder_North_G"
    )
    walls.extend([powder_west, powder_north])

    # Powder room door
    powder_door = Door(
        types["interior_door"],
        powder_north,
        offset=powder_width / 2 - types["interior_door"].width / 2,
        name="Powder_Door",
    )
    doors.append(powder_door)

    # Small window in powder room
    powder_window = Window(
        types["small_window"],
        wall_south,
        offset=powder_x + powder_width / 2 - types["small_window"].width / 2,
        name="Powder_Window",
    )
    windows.append(powder_window)

    # === FLOOR ===
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["ground_floor"], floor_boundary, ground, name="Ground_Floor_Slab")
    floors.append(floor)

    # === CEILINGS ===
    # Living/dining area (open ceiling)
    main_ceiling = Ceiling(
        types["ceiling"],
        [
            (kitchen_width, 0),
            (BUILDING_LENGTH, 0),
            (BUILDING_LENGTH, BUILDING_WIDTH),
            (garage_width, BUILDING_WIDTH),
            (garage_width, dining_depth),
            (kitchen_width, dining_depth),
        ],
        ground,
        height=CEILING_HEIGHT,
        name="Main_Ceiling_G",
    )
    ceilings.append(main_ceiling)

    # Kitchen/dining ceiling
    kitchen_ceiling = Ceiling(
        types["ceiling"],
        [(0, 0), (kitchen_width, 0), (kitchen_width, dining_depth), (0, dining_depth)],
        ground,
        height=CEILING_HEIGHT,
        name="Kitchen_Ceiling_G",
    )
    ceilings.append(kitchen_ceiling)

    # Garage ceiling (lower)
    garage_ceiling = Ceiling(
        types["ceiling"],
        [
            (0, dining_depth),
            (garage_width, dining_depth),
            (garage_width, BUILDING_WIDTH),
            (0, BUILDING_WIDTH),
        ],
        ground,
        height=2500,
        name="Garage_Ceiling_G",
    )
    ceilings.append(garage_ceiling)

    return ground, walls, doors, windows, floors, ceilings


def create_upper_floor(building, types):
    """Create upper floor with bedrooms and bathrooms."""
    upper = Level(building, "Upper Floor", elevation=FLOOR_HEIGHT)

    walls = []
    doors = []
    windows = []
    floors = []
    ceilings = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Layout:
    # +--------+-------+-------+
    # | MASTER |MASTER | BATH  |  Master: 6m x 6m with ensuite 3m x 3m
    # | BED    |ENSUITE|       |  Shared bath: 3m x 3m
    # +--------+-------+-------+
    # |  BED 2 |LAUNDRY| BED 3 |  Bed 2 & 3: 4.5m x 6m each
    # |        |       |       |  Laundry: 3m x 3m (above entry)
    # +--------+-------+-------+

    master_width = 6000
    master_depth = 6000
    ensuite_width = 3000
    ensuite_depth = 3000
    bath_width = 3000
    bath_depth = 3000
    bed2_width = 6000
    bed2_depth = 6000
    laundry_width = 3000
    laundry_depth = 6000
    bed3_width = 6000
    bed3_depth = 6000

    # Hallway runs east-west through center
    hallway_width = BUILDING_LENGTH
    hallway_depth = 1500
    hallway_y = (BUILDING_WIDTH - hallway_depth) / 2

    # === EXTERIOR WALLS ===
    wall_south = Wall(ext_wall, (0, 0), (BUILDING_LENGTH, 0), upper, name="Ext_South_U")
    wall_east = Wall(
        ext_wall, (BUILDING_LENGTH, 0), (BUILDING_LENGTH, BUILDING_WIDTH), upper, name="Ext_East_U"
    )
    wall_north = Wall(
        ext_wall, (BUILDING_LENGTH, BUILDING_WIDTH), (0, BUILDING_WIDTH), upper, name="Ext_North_U"
    )
    wall_west = Wall(ext_wall, (0, BUILDING_WIDTH), (0, 0), upper, name="Ext_West_U")
    walls.extend([wall_south, wall_east, wall_north, wall_west])

    # === HALLWAY WALLS ===
    hall_south = Wall(
        int_wall, (0, hallway_y), (BUILDING_LENGTH, hallway_y), upper, name="Hall_South_U"
    )
    hall_north = Wall(
        int_wall,
        (BUILDING_LENGTH, hallway_y + hallway_depth),
        (0, hallway_y + hallway_depth),
        upper,
        name="Hall_North_U",
    )
    walls.extend([hall_south, hall_north])

    # === MASTER BEDROOM (north-west) ===
    master_east = Wall(
        int_wall,
        (master_width, hallway_y + hallway_depth),
        (master_width, BUILDING_WIDTH),
        upper,
        name="Master_East_U",
    )
    walls.append(master_east)

    # Master door
    master_door = Door(
        types["interior_door"],
        hall_north,
        offset=BUILDING_LENGTH - master_width / 2 - types["interior_door"].width / 2,
        name="Master_Door",
    )
    doors.append(master_door)

    # Master windows
    master_west_window = Window(
        types["large_window"],
        wall_west,
        offset=hallway_y
        + hallway_depth
        + (BUILDING_WIDTH - hallway_y - hallway_depth) / 2
        - types["large_window"].height / 2,
        name="Master_West_Window",
    )
    master_north_window = Window(
        types["medium_window"],
        wall_north,
        offset=BUILDING_LENGTH - master_width / 2 - types["medium_window"].width / 2,
        name="Master_North_Window",
    )
    windows.extend([master_west_window, master_north_window])

    # === MASTER ENSUITE (attached to master) ===
    ensuite_south = Wall(
        int_wall,
        (master_width, hallway_y + hallway_depth),
        (master_width, hallway_y + hallway_depth + ensuite_depth),
        upper,
        name="Ensuite_South_U",
    )
    ensuite_east = Wall(
        int_wall,
        (master_width + ensuite_width, hallway_y + hallway_depth + ensuite_depth),
        (master_width + ensuite_width, hallway_y + hallway_depth),
        upper,
        name="Ensuite_East_U",
    )
    # Ensuite partition from master
    ensuite_west = Wall(
        int_wall,
        (master_width, BUILDING_WIDTH - ensuite_depth),
        (master_width, BUILDING_WIDTH),
        upper,
        name="Ensuite_West_U",
    )
    walls.extend([ensuite_west, ensuite_east])

    # Ensuite door (from master)
    ensuite_door = Door(
        types["interior_door"],
        ensuite_west,
        offset=ensuite_depth / 2 - types["interior_door"].width / 2,
        name="Ensuite_Door",
    )
    doors.append(ensuite_door)

    # Ensuite window
    ensuite_window = Window(
        types["small_window"],
        wall_north,
        offset=BUILDING_LENGTH - master_width - ensuite_width / 2 - types["small_window"].width / 2,
        name="Ensuite_Window",
    )
    windows.append(ensuite_window)

    # === SHARED BATHROOM (north-east corner) ===
    bath_west = Wall(
        int_wall,
        (BUILDING_LENGTH - bath_width, hallway_y + hallway_depth),
        (BUILDING_LENGTH - bath_width, BUILDING_WIDTH),
        upper,
        name="Bath_West_U",
    )
    walls.append(bath_west)

    # Bathroom door
    bath_door = Door(
        types["interior_door"],
        hall_north,
        offset=bath_width / 2 - types["interior_door"].width / 2,
        name="Bath_Door",
    )
    doors.append(bath_door)

    # Bathroom window
    bath_window = Window(
        types["small_window"],
        wall_north,
        offset=bath_width / 2 - types["small_window"].width / 2,
        name="Bath_Window",
    )
    windows.append(bath_window)

    # === BEDROOM 2 (south-west) ===
    bed2_east = Wall(int_wall, (bed2_width, 0), (bed2_width, hallway_y), upper, name="Bed2_East_U")
    walls.append(bed2_east)

    # Bed 2 door
    bed2_door = Door(
        types["interior_door"],
        hall_south,
        offset=BUILDING_LENGTH - bed2_width / 2 - types["interior_door"].width / 2,
        name="Bed2_Door",
    )
    doors.append(bed2_door)

    # Bed 2 windows
    bed2_south_window = Window(
        types["large_window"],
        wall_south,
        offset=bed2_width / 2 - types["large_window"].width / 2,
        name="Bed2_South_Window",
    )
    bed2_west_window = Window(
        types["medium_window"],
        wall_west,
        offset=hallway_y / 2 - types["medium_window"].height / 2,
        name="Bed2_West_Window",
    )
    windows.extend([bed2_south_window, bed2_west_window])

    # === LAUNDRY (center south, above stair/entry) ===
    laundry_west = Wall(
        int_wall, (bed2_width, 0), (bed2_width, hallway_y), upper, name="Laundry_West_U"
    )
    laundry_east = Wall(
        int_wall,
        (bed2_width + laundry_width, hallway_y),
        (bed2_width + laundry_width, 0),
        upper,
        name="Laundry_East_U",
    )
    # Note: laundry_west already added as bed2_east

    # Laundry door
    laundry_door = Door(
        types["interior_door"],
        hall_south,
        offset=BUILDING_LENGTH - bed2_width - laundry_width / 2 - types["interior_door"].width / 2,
        name="Laundry_Door",
    )
    doors.append(laundry_door)

    walls.append(laundry_east)

    # === BEDROOM 3 (south-east) ===
    # Uses laundry_east as its west wall
    bed3_door = Door(
        types["interior_door"],
        hall_south,
        offset=bed3_width / 2 - types["interior_door"].width / 2,
        name="Bed3_Door",
    )
    doors.append(bed3_door)

    # Bed 3 windows
    bed3_south_window = Window(
        types["large_window"],
        wall_south,
        offset=BUILDING_LENGTH - bed3_width / 2 - types["large_window"].width / 2,
        name="Bed3_South_Window",
    )
    bed3_east_window = Window(
        types["medium_window"],
        wall_east,
        offset=hallway_y / 2 - types["medium_window"].height / 2,
        name="Bed3_East_Window",
    )
    windows.extend([bed3_south_window, bed3_east_window])

    # === FLOOR ===
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["upper_floor"], floor_boundary, upper, name="Upper_Floor_Slab")
    floors.append(floor)

    # === CEILINGS ===
    ceiling = Ceiling(
        types["ceiling"], floor_boundary, upper, height=CEILING_HEIGHT, name="Upper_Ceiling"
    )
    ceilings.append(ceiling)

    return upper, walls, doors, windows, floors, ceilings


def create_roof(building, types):
    """Create flat roof."""
    roof_level = Level(building, "Roof", elevation=FLOOR_HEIGHT * 2)

    roof_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    roof = Roof(types["roof"], roof_boundary, roof_level, name="Flat_Roof")

    return roof_level, [roof]


def generate_floor_plan(name, level, spatial_index, cache, output_path):
    """Generate and export a floor plan."""
    print(f"  Generating {name}...")

    view_range = ViewRange(cut_height=1200, top=2700, bottom=0, view_depth=0)
    floor_plan = FloorPlanView(name=name, level=level, view_range=view_range)
    result = floor_plan.generate(spatial_index, cache)

    print(f"    Elements: {result.element_count}, Geometry: {result.total_geometry_count}")

    exporter = DXFExporter()
    exporter.export(result, str(output_path))


def generate_section(name, spatial_index, cache, point, normal, output_path, height_range):
    """Generate and export a section view."""
    print(f"  Generating {name}...")

    section = SectionView(
        name=name,
        plane_point=point,
        plane_normal=normal,
        depth=20000,
        height_range=height_range,
        scale=ViewScale.SCALE_1_50,
        show_hidden_lines=False,
    )
    result = section.generate(spatial_index, cache)

    print(f"    Elements: {result.element_count}, Geometry: {result.total_geometry_count}")

    exporter = DXFExporter()
    exporter.export(result, str(output_path))


def main():
    """Create residential home and generate all outputs."""
    print("=" * 70)
    print("Residential Home Example - Two-Story Family Home")
    print("=" * 70)

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / "outputs" / "home" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Create building
    print("\nCreating building...")
    building = Building("Family Home")
    types = create_materials_and_types()

    # Create floors
    print("\n  Ground Floor...")
    ground, g_walls, g_doors, g_windows, g_floors, g_ceilings = create_ground_floor(building, types)

    print("  Upper Floor...")
    upper, u_walls, u_doors, u_windows, u_floors, u_ceilings = create_upper_floor(building, types)

    print("  Roof...")
    roof_level, roofs = create_roof(building, types)

    # Process wall joins per floor
    print("\n  Processing wall joins...")
    for walls in [g_walls, u_walls]:
        adjustments = detect_and_process_wall_joins(walls, end_cap_type=EndCapType.EXTERIOR)
        for wall, adj in adjustments.items():
            wall._trim_adjustments = adj

    # Summary
    all_elements = (
        g_walls
        + u_walls
        + g_doors
        + u_doors
        + g_windows
        + u_windows
        + g_floors
        + u_floors
        + g_ceilings
        + u_ceilings
        + roofs
    )
    print(f"\n  Total elements: {len(all_elements)}")
    print(f"    Walls: {len(g_walls) + len(u_walls)}")
    print(f"    Doors: {len(g_doors) + len(u_doors)}")
    print(f"    Windows: {len(g_windows) + len(u_windows)}")
    print(f"    Floors: {len(g_floors) + len(u_floors)}")
    print(f"    Ceilings: {len(g_ceilings) + len(u_ceilings)}")
    print(f"    Roofs: {len(roofs)}")

    # Export IFC
    print("\n" + "-" * 70)
    print("Exporting IFC...")
    ifc_path = output_dir / "residential_home.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path.name}")

    # Create spatial indices for each floor
    print("\n" + "-" * 70)
    print("Generating drawings...")

    g_index = SpatialIndex()
    for elem in g_walls + g_doors + g_windows + g_floors + g_ceilings:
        g_index.insert(elem)

    u_index = SpatialIndex()
    for elem in u_walls + u_doors + u_windows + u_floors + u_ceilings:
        u_index.insert(elem)

    cache = RepresentationCache()

    # Floor plans
    generate_floor_plan(
        "Ground Floor Plan", ground, g_index, cache, output_dir / "ground_floor_plan.dxf"
    )
    generate_floor_plan(
        "Upper Floor Plan", upper, u_index, cache, output_dir / "upper_floor_plan.dxf"
    )

    # Sections (combine both floors)
    combined_index = SpatialIndex()
    for elem in all_elements:
        combined_index.insert(elem)

    generate_section(
        "Section A-A (North-South)",
        combined_index,
        cache,
        (BUILDING_LENGTH / 2, BUILDING_WIDTH / 2, 0),
        (1, 0, 0),
        output_dir / "section_NS.dxf",
        (0, FLOOR_HEIGHT * 2 + 500),
    )
    generate_section(
        "Section B-B (East-West)",
        combined_index,
        cache,
        (BUILDING_LENGTH / 2, BUILDING_WIDTH / 2, 0),
        (0, 1, 0),
        output_dir / "section_EW.dxf",
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

    print("\nHome summary:")
    print("  - 2 floors (Ground + Upper)")
    print("  - Ground: Living room, dining room, kitchen, powder room, garage")
    print("  - Upper: Master suite with ensuite, 2 bedrooms, shared bath, laundry")
    print("  - Total area: ~180 sqm per floor")
    print("  - Features: Picture window, sliding door to backyard, double garage")

    print(f"\nOutput directory: {output_dir}")


if __name__ == "__main__":
    main()
