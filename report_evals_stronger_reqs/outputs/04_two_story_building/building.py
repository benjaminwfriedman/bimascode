"""
Eval 04: Two Story Building

A two-story residential building with:
- Ground Floor: Living room, kitchen, entry vestibule, stair area
- Upper Floor: Master bedroom, second bedroom, bathroom, hallway
- 3m floor-to-floor height, 2.7m ceiling height
- 300mm exterior walls (brick + insulation + concrete + gypsum)
- Flat roof over upper floor
"""
from pathlib import Path

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import (
    Wall,
    Door,
    Window,
    Floor,
    Ceiling,
    Roof,
    WallFunction,
    LayerFunction,
    EndCapType,
    detect_and_process_wall_joins,
)
from bimascode.architecture.wall_type import WallType
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.window_type import WindowType
from bimascode.architecture.floor_type import FloorType
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.utils.materials import MaterialLibrary

from bimascode.drawing import (
    FloorPlanView,
    ElevationView,
    ElevationDirection,
    SectionView,
    Sheet,
    SheetSize,
    ViewRange,
    ViewScale,
    DXFExporter,
    PDFExporter,
)
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex


# Building dimensions (all in mm)
# Ground floor layout (6m x 5m living + 4m x 4m kitchen + 2m x 2m entry + 3m x 2m stair)
# Envelope size based on room layout: need to accommodate all rooms
FLOOR_HEIGHT = 3000  # 3m floor-to-floor
CEILING_HEIGHT = 2700  # 2.7m ceiling height

# Ground floor dimensions
LIVING_WIDTH = 6000
LIVING_DEPTH = 5000
KITCHEN_WIDTH = 4000
KITCHEN_DEPTH = 4000
ENTRY_WIDTH = 2000
ENTRY_DEPTH = 2000
STAIR_WIDTH = 3000
STAIR_DEPTH = 2000

# Upper floor dimensions
MASTER_WIDTH = 5000
MASTER_DEPTH = 4000
BEDROOM2_WIDTH = 4000
BEDROOM2_DEPTH = 4000
BATHROOM_WIDTH = 3000
BATHROOM_DEPTH = 2000
HALLWAY_WIDTH = 2000  # Connection space

# Building envelope (calculated from room layout)
# Layout: Living room (6x5) on south, Kitchen (4x4) on west of living,
# Entry (2x2) south-west corner, Stair (3x2) near entry
# Total width = max room extents, Total depth = max room extents
BUILDING_LENGTH = 10000  # 10m east-west
BUILDING_WIDTH = 7000   # 7m north-south


def create_materials_and_types():
    """Create all material and element types."""
    brick = MaterialLibrary.brick()
    insulation = MaterialLibrary.insulation_mineral_wool()
    concrete = MaterialLibrary.concrete()
    gypsum = MaterialLibrary.gypsum_board()

    # Exterior wall: 300mm total (brick + insulation + concrete + gypsum)
    # 100mm brick + 50mm insulation + 130mm concrete + 20mm gypsum = 300mm
    exterior_wall_type = WallType("Exterior Wall - 300mm", function=WallFunction.EXTERIOR)
    exterior_wall_type.add_layer(brick, 100, LayerFunction.FINISH_EXTERIOR)
    exterior_wall_type.add_layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
    exterior_wall_type.add_layer(concrete, 130, LayerFunction.STRUCTURE, structural=True)
    exterior_wall_type.add_layer(gypsum, 20, LayerFunction.FINISH_INTERIOR)

    # Interior wall: 150mm
    interior_wall_type = WallType("Interior Wall", function=WallFunction.INTERIOR)
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)
    interior_wall_type.add_layer(concrete, 125, LayerFunction.STRUCTURE)
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)

    types = {
        # Walls
        "exterior_wall": exterior_wall_type,
        "interior_wall": interior_wall_type,
        # Doors
        "front_door": DoorType(name="Front Door", width=900, height=2100),
        "interior_door": DoorType(name="Interior Door", width=800, height=2100),
        "bathroom_door": DoorType(name="Bathroom Door", width=700, height=2100),
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
            height=600,
            default_sill_height=1400,
        ),
        # Floor
        "floor": FloorType("Concrete Floor"),
        # Ceiling
        "ceiling": CeilingType("Gypsum Ceiling", thickness=15),
        # Roof
        "roof": FloorType("Flat Roof"),
    }

    # Add floor layers
    types["floor"].add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

    # Add roof layers
    types["roof"].add_layer(insulation, 100, LayerFunction.THERMAL_INSULATION)
    types["roof"].add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)

    return types


def create_ground_floor(building, types):
    """Create ground floor with living room, kitchen, entry, and stair area."""
    ground = Level(building, "Ground Floor", elevation=0)

    walls = []
    doors = []
    windows = []
    floors_list = []
    ceilings = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Layout (all dimensions in mm):
    # Building is 10m x 7m
    # +------------------+--------+
    # |                  | STAIR  |  Stair: 3m x 2m (north-east corner)
    # |    LIVING        | (open) |
    # |    6m x 5m       +--------+
    # |                  |        |
    # +--------+---------+ KITCHEN|  Kitchen: 4m x 4m (east side)
    # | ENTRY  |         | 4m x 4m|
    # | 2m x 2m|         |        |
    # +--------+---------+--------+
    #    ^--- South wall (Y=0)

    # Room positions:
    # Entry: (0, 0) to (2000, 2000) - SW corner
    # Living: (0, 2000) to (6000, 7000) - west side, above entry
    # Kitchen: (6000, 0) to (10000, 4000) - SE corner area
    # Stair: (7000, 5000) to (10000, 7000) - NE corner

    # === EXTERIOR WALLS ===
    # South wall (Y=0)
    wall_south = Wall(ext_wall, (0, 0), (BUILDING_LENGTH, 0), ground, name="Ext_South_G")
    # East wall (X=10000)
    wall_east = Wall(
        ext_wall, (BUILDING_LENGTH, 0), (BUILDING_LENGTH, BUILDING_WIDTH), ground, name="Ext_East_G"
    )
    # North wall (Y=7000)
    wall_north = Wall(
        ext_wall, (BUILDING_LENGTH, BUILDING_WIDTH), (0, BUILDING_WIDTH), ground, name="Ext_North_G"
    )
    # West wall (X=0)
    wall_west = Wall(ext_wall, (0, BUILDING_WIDTH), (0, 0), ground, name="Ext_West_G")
    walls.extend([wall_south, wall_east, wall_north, wall_west])

    # === INTERIOR WALLS ===
    # Entry north wall (separates entry from living)
    entry_north = Wall(
        int_wall, (0, ENTRY_DEPTH), (ENTRY_WIDTH, ENTRY_DEPTH), ground, name="Entry_North_G"
    )
    walls.append(entry_north)

    # Entry east wall (separates entry from kitchen area)
    entry_east = Wall(
        int_wall, (ENTRY_WIDTH, 0), (ENTRY_WIDTH, ENTRY_DEPTH), ground, name="Entry_East_G"
    )
    walls.append(entry_east)

    # Living/Kitchen separator (north-south running wall)
    living_kitchen_wall = Wall(
        int_wall, (LIVING_WIDTH, ENTRY_DEPTH), (LIVING_WIDTH, BUILDING_WIDTH), ground, name="Living_Kitchen_G"
    )
    walls.append(living_kitchen_wall)

    # Kitchen north wall (separates kitchen from stair area)
    kitchen_north = Wall(
        int_wall, (LIVING_WIDTH, KITCHEN_DEPTH), (BUILDING_LENGTH, KITCHEN_DEPTH), ground, name="Kitchen_North_G"
    )
    walls.append(kitchen_north)

    # Stair area south wall (this is actually the kitchen north wall above)
    # Stair west wall
    stair_west = Wall(
        int_wall, (LIVING_WIDTH + 1000, KITCHEN_DEPTH), (LIVING_WIDTH + 1000, BUILDING_WIDTH), ground, name="Stair_West_G"
    )
    walls.append(stair_west)

    # === WINDOWS ===
    # Large south-facing window on living room (south wall, west portion)
    # Position window with 300mm clearance from wall corner
    living_window_offset = 500  # Offset from west corner
    living_window = Window(
        types["large_window"],
        wall_south,
        offset=BUILDING_LENGTH - living_window_offset - types["large_window"].width - ENTRY_WIDTH,
        name="Living_South_Window",
    )
    windows.append(living_window)

    # Kitchen window on west wall (actually west portion of building is living, kitchen is east)
    # Kitchen is on east side, so window on east wall
    kitchen_window = Window(
        types["medium_window"],
        wall_east,
        offset=KITCHEN_DEPTH / 2 - types["medium_window"].height / 2 + 300,
        name="Kitchen_Window",
    )
    windows.append(kitchen_window)

    # === DOORS ===
    # Front door in entry (south wall)
    front_door = Door(
        types["front_door"],
        wall_south,
        offset=ENTRY_WIDTH / 2 - types["front_door"].width / 2,
        name="Front_Door",
    )
    doors.append(front_door)

    # Door from entry to living (opening in entry_north wall)
    entry_to_living = Door(
        types["interior_door"],
        entry_north,
        offset=ENTRY_WIDTH / 2 - types["interior_door"].width / 2,
        name="Entry_Living_Door",
    )
    doors.append(entry_to_living)

    # Door from living to kitchen
    living_to_kitchen = Door(
        types["interior_door"],
        living_kitchen_wall,
        offset=1500,  # Position along the wall
        name="Living_Kitchen_Door",
    )
    doors.append(living_to_kitchen)

    # === FLOOR SLAB ===
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["floor"], floor_boundary, ground, name="Ground_Floor_Slab")

    # Add stair opening (3m x 2m in NE area)
    stair_opening = [
        (LIVING_WIDTH + 1000 + 300, KITCHEN_DEPTH + 300),
        (BUILDING_LENGTH - 300, KITCHEN_DEPTH + 300),
        (BUILDING_LENGTH - 300, BUILDING_WIDTH - 300),
        (LIVING_WIDTH + 1000 + 300, BUILDING_WIDTH - 300),
    ]
    floor.add_opening(stair_opening, name="Stair_Opening")
    floors_list.append(floor)

    # === CEILING ===
    ceiling = Ceiling(
        types["ceiling"],
        floor_boundary,
        ground,
        height=CEILING_HEIGHT,
        name="Ground_Ceiling",
    )
    ceilings.append(ceiling)

    return ground, walls, doors, windows, floors_list, ceilings


def create_upper_floor(building, types):
    """Create upper floor with master bedroom, second bedroom, bathroom, and hallway."""
    upper = Level(building, "Upper Floor", elevation=FLOOR_HEIGHT)

    walls = []
    doors = []
    windows = []
    floors_list = []
    ceilings = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Layout (all dimensions in mm):
    # +--------+---------+--------+
    # | MASTER |  HALL   | BED2   |  Master: 5m x 4m (NW)
    # | 5m x 4m|  2m x Xm| 4m x 4m|  Bedroom 2: 4m x 4m (NE - overlaps stair)
    # +--------+---------+--------+
    # | (open  | BATHROOM|        |  Bathroom: 3m x 2m (center-south)
    # | to     | 3m x 2m |        |  Hallway connects all rooms
    # | below) |         |        |
    # +--------+---------+--------+

    # Room positions:
    # Master: (0, 3000) to (5000, 7000) - NW
    # Bedroom 2: (6000, 3000) to (10000, 7000) - NE
    # Bathroom: (5000, 0) to (8000, 2000) - center south
    # Hallway: (5000, 2000) to (6000, 7000) - central corridor

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

    # === INTERIOR WALLS ===
    # Master bedroom east wall (separates master from hallway)
    master_east = Wall(
        int_wall, (MASTER_WIDTH, 0), (MASTER_WIDTH, BUILDING_WIDTH), upper, name="Master_East_U"
    )
    walls.append(master_east)

    # Bedroom 2 west wall (separates bedroom 2 from hallway)
    bed2_west_x = MASTER_WIDTH + HALLWAY_WIDTH
    bed2_west = Wall(
        int_wall, (bed2_west_x, BATHROOM_DEPTH), (bed2_west_x, BUILDING_WIDTH), upper, name="Bed2_West_U"
    )
    walls.append(bed2_west)

    # Bathroom north wall (separates bathroom from hallway)
    bathroom_north = Wall(
        int_wall, (MASTER_WIDTH, BATHROOM_DEPTH), (MASTER_WIDTH + BATHROOM_WIDTH, BATHROOM_DEPTH), upper, name="Bathroom_North_U"
    )
    walls.append(bathroom_north)

    # Bathroom east wall
    bathroom_east = Wall(
        int_wall, (MASTER_WIDTH + BATHROOM_WIDTH, 0), (MASTER_WIDTH + BATHROOM_WIDTH, BATHROOM_DEPTH), upper, name="Bathroom_East_U"
    )
    walls.append(bathroom_east)

    # === WINDOWS ===
    # Master bedroom - south wall window
    master_window = Window(
        types["medium_window"],
        wall_south,
        offset=MASTER_WIDTH / 2 - types["medium_window"].width / 2,
        name="Master_South_Window",
    )
    windows.append(master_window)

    # Bedroom 2 - north wall window
    bed2_window = Window(
        types["medium_window"],
        wall_north,
        offset=BUILDING_LENGTH - (bed2_west_x + (BUILDING_LENGTH - bed2_west_x) / 2 + types["medium_window"].width / 2),
        name="Bed2_North_Window",
    )
    windows.append(bed2_window)

    # Bathroom - small window on south wall
    bathroom_window = Window(
        types["small_window"],
        wall_south,
        offset=MASTER_WIDTH + BATHROOM_WIDTH / 2 - types["small_window"].width / 2,
        name="Bathroom_Window",
    )
    windows.append(bathroom_window)

    # === DOORS ===
    # Master bedroom door (from hallway)
    master_door = Door(
        types["interior_door"],
        master_east,
        offset=1000,
        name="Master_Door",
    )
    doors.append(master_door)

    # Bedroom 2 door (from hallway)
    bed2_door = Door(
        types["interior_door"],
        bed2_west,
        offset=1000,
        name="Bed2_Door",
    )
    doors.append(bed2_door)

    # Bathroom door (from hallway)
    bathroom_door = Door(
        types["bathroom_door"],
        bathroom_north,
        offset=BATHROOM_WIDTH / 2 - types["bathroom_door"].width / 2,
        name="Bathroom_Door",
    )
    doors.append(bathroom_door)

    # === FLOOR SLAB ===
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["floor"], floor_boundary, upper, name="Upper_Floor_Slab")
    floors_list.append(floor)

    # === CEILING ===
    ceiling = Ceiling(
        types["ceiling"],
        floor_boundary,
        upper,
        height=CEILING_HEIGHT,
        name="Upper_Ceiling",
    )
    ceilings.append(ceiling)

    return upper, walls, doors, windows, floors_list, ceilings


def create_roof(building, types):
    """Create flat roof over upper floor."""
    roof_level = Level(building, "Roof", elevation=FLOOR_HEIGHT * 2)

    roof_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    roof = Roof(types["roof"], roof_boundary, roof_level, name="Flat_Roof")

    return roof_level, [roof]


def build():
    """Build the two-story residential building."""
    building = Building("Two Story Residential Building")
    types = create_materials_and_types()

    # Create floors
    ground, g_walls, g_doors, g_windows, g_floors, g_ceilings = create_ground_floor(building, types)
    upper, u_walls, u_doors, u_windows, u_floors, u_ceilings = create_upper_floor(building, types)
    roof_level, roofs = create_roof(building, types)

    # Process wall joins per floor
    for walls in [g_walls, u_walls]:
        adjustments = detect_and_process_wall_joins(walls, end_cap_type=EndCapType.EXTERIOR)
        for wall, adj in adjustments.items():
            wall._trim_adjustments = adj

    return building


def main():
    """Create building and generate all exports."""
    out_dir = Path(__file__).parent
    dxf_dir = out_dir / "dxf"
    dxf_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("Eval 04: Two Story Building")
    print("=" * 70)

    # Build the building
    print("\nCreating building...")
    building = Building("Two Story Residential Building")
    types = create_materials_and_types()

    # Create floors
    print("  Ground Floor...")
    ground, g_walls, g_doors, g_windows, g_floors, g_ceilings = create_ground_floor(building, types)

    print("  Upper Floor...")
    upper, u_walls, u_doors, u_windows, u_floors, u_ceilings = create_upper_floor(building, types)

    print("  Roof...")
    roof_level, roofs = create_roof(building, types)

    # Process wall joins
    print("  Processing wall joins...")
    for walls in [g_walls, u_walls]:
        adjustments = detect_and_process_wall_joins(walls, end_cap_type=EndCapType.EXTERIOR)
        for wall, adj in adjustments.items():
            wall._trim_adjustments = adj

    # Summary
    all_elements = (
        g_walls + u_walls +
        g_doors + u_doors +
        g_windows + u_windows +
        g_floors + u_floors +
        g_ceilings + u_ceilings +
        roofs
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
    ifc_path = out_dir / "building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path}")

    # Create spatial indices
    print("\n" + "-" * 70)
    print("Generating drawings...")

    g_index = SpatialIndex()
    for elem in g_walls + g_doors + g_windows + g_floors + g_ceilings:
        g_index.insert(elem)

    u_index = SpatialIndex()
    for elem in u_walls + u_doors + u_windows + u_floors + u_ceilings:
        u_index.insert(elem)

    combined_index = SpatialIndex()
    for elem in all_elements:
        combined_index.insert(elem)

    cache = RepresentationCache()
    exporter = DXFExporter()

    # Floor plans
    print("  Ground Floor Plan...")
    view_range = ViewRange(cut_height=1200, top=3000, bottom=0, view_depth=0)
    ground_plan = FloorPlanView(name="Ground Floor Plan", level=ground, view_range=view_range)
    ground_result = ground_plan.generate(g_index, cache)
    exporter.export(ground_result, str(dxf_dir / "ground_floor_plan.dxf"))

    print("  Upper Floor Plan...")
    upper_plan = FloorPlanView(name="Upper Floor Plan", level=upper, view_range=view_range)
    upper_result = upper_plan.generate(u_index, cache)
    exporter.export(upper_result, str(dxf_dir / "upper_floor_plan.dxf"))

    # Elevations
    height_range = (0, FLOOR_HEIGHT * 2 + 500)

    print("  North Elevation...")
    north_elev = ElevationView(
        name="North Elevation",
        direction=ElevationDirection.NORTH,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    north_result = north_elev.generate(combined_index, cache)
    exporter.export(north_result, str(dxf_dir / "elevation_north.dxf"))

    print("  South Elevation...")
    south_elev = ElevationView(
        name="South Elevation",
        direction=ElevationDirection.SOUTH,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    south_result = south_elev.generate(combined_index, cache)
    exporter.export(south_result, str(dxf_dir / "elevation_south.dxf"))

    print("  East Elevation...")
    east_elev = ElevationView(
        name="East Elevation",
        direction=ElevationDirection.EAST,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    east_result = east_elev.generate(combined_index, cache)
    exporter.export(east_result, str(dxf_dir / "elevation_east.dxf"))

    print("  West Elevation...")
    west_elev = ElevationView(
        name="West Elevation",
        direction=ElevationDirection.WEST,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    west_result = west_elev.generate(combined_index, cache)
    exporter.export(west_result, str(dxf_dir / "elevation_west.dxf"))

    # Section
    print("  Section A-A...")
    section = SectionView(
        name="Section A-A",
        plane_point=(BUILDING_LENGTH / 2, BUILDING_WIDTH / 2, 0),
        plane_normal=(0, 1, 0),
        depth=15000,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    section_result = section.generate(combined_index, cache)
    exporter.export(section_result, str(dxf_dir / "section_AA.dxf"))

    # PDF drawing set
    print("\n" + "-" * 70)
    print("Creating PDF drawing set...")

    sheet = Sheet(
        size=SheetSize.ARCH_D,
        number="A-101",
        name="Floor Plans and Section",
    )

    # Add viewports to sheet
    sheet.add_viewport(ground_result, position=(300, 450), scale=ViewScale.SCALE_1_100, name="Ground Floor")
    sheet.add_viewport(upper_result, position=(550, 450), scale=ViewScale.SCALE_1_100, name="Upper Floor")
    sheet.add_viewport(section_result, position=(400, 150), scale=ViewScale.SCALE_1_100, name="Section A-A")

    pdf_path = out_dir / "04_two_story_building_drawing_set.pdf"
    sheet.export_pdf(str(pdf_path))
    print(f"  Saved: {pdf_path}")

    # Summary
    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print(f"  IFC: {ifc_path}")
    print(f"  PDF: {pdf_path}")
    print("  DXF files:")
    for f in sorted(dxf_dir.iterdir()):
        print(f"    {f.name}")

    print(f"\nOutput directory: {out_dir}")


if __name__ == "__main__":
    main()
