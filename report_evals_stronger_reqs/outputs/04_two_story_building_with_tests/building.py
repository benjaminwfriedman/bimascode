"""
Eval 04: Two Story Residential Building

A two-story residential building with:
- Ground Floor: Living room (6x5m), Kitchen (4x4m), Entry vestibule (2x2m), Stair area (3x2m)
- Upper Floor: Master bedroom (5x4m), Second bedroom (4x4m), Bathroom (3x2m), Hallway
- 3m floor-to-floor height, 2.7m ceiling height
- 300mm exterior walls (brick + insulation + concrete + gypsum)
- Flat roof over the upper floor
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
    WallFunction,
    Window,
    detect_and_process_wall_joins,
)
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.architecture.opening import Opening
from bimascode.architecture.wall_type import WallType
from bimascode.architecture.window_type import WindowType
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.elevation_view import ElevationDirection, ElevationView
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.sheet import Sheet, SheetMetadata
from bimascode.drawing.sheet_sizes import SheetSize
from bimascode.drawing.title_block import TitleBlock, TitleBlockField
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.materials import MaterialLibrary

# Building dimensions (mm)
FLOOR_HEIGHT = 3000  # 3m floor-to-floor
CEILING_HEIGHT = 2700  # 2.7m ceiling height
EXT_WALL_THICKNESS = 300  # 300mm exterior walls
INT_WALL_THICKNESS = 150  # Interior partitions

# Room dimensions (mm) - internal dimensions
LIVING_WIDTH = 6000  # 6m
LIVING_DEPTH = 5000  # 5m
KITCHEN_WIDTH = 4000  # 4m
KITCHEN_DEPTH = 4000  # 4m
ENTRY_WIDTH = 2000  # 2m
ENTRY_DEPTH = 2000  # 2m
STAIR_WIDTH = 3000  # 3m
STAIR_DEPTH = 2000  # 2m

MASTER_WIDTH = 5000  # 5m
MASTER_DEPTH = 4000  # 4m
BED2_WIDTH = 4000  # 4m
BED2_DEPTH = 4000  # 4m
BATHROOM_WIDTH = 3000  # 3m
BATHROOM_DEPTH = 2000  # 2m

# Building footprint - computed to fit rooms
# Ground floor layout (South to North, West to East):
#   Row 1 (South): Entry (2x2) | Living (6x5)
#   Row 2 (North): Kitchen (4x4) | Stair (3x2) overlapping with Living
BUILDING_WIDTH = LIVING_WIDTH + ENTRY_WIDTH  # 8m in X direction
BUILDING_DEPTH = LIVING_DEPTH  # 5m in Y direction - simplified


def create_types():
    """Create all element types."""
    concrete = MaterialLibrary.concrete()
    brick = MaterialLibrary.brick()
    insulation = MaterialLibrary.insulation_mineral_wool()
    gypsum = MaterialLibrary.gypsum_board()
    wood = MaterialLibrary.timber()

    # Compound exterior wall: brick + insulation + concrete + gypsum = 300mm
    exterior_wall_type = WallType("Exterior Wall - Compound", function=WallFunction.EXTERIOR)
    exterior_wall_type.add_layer(brick, 100, LayerFunction.FINISH_EXTERIOR)
    exterior_wall_type.add_layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
    exterior_wall_type.add_layer(concrete, 100, LayerFunction.STRUCTURE, structural=True)
    exterior_wall_type.add_layer(gypsum, 50, LayerFunction.FINISH_INTERIOR)

    # Interior partition: gypsum + wood stud + gypsum
    interior_wall_type = WallType("Interior Partition", function=WallFunction.INTERIOR)
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)
    interior_wall_type.add_layer(wood, 75, LayerFunction.STRUCTURE, structural=True)
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)

    # Doors
    entry_door = DoorType(name="Entry Door", width=900, height=2100)
    interior_door = DoorType(name="Interior Door", width=800, height=2100)

    # Windows
    large_window = WindowType(
        name="Large Window",
        width=2000,
        height=1500,
        default_sill_height=900,
    )
    medium_window = WindowType(
        name="Medium Window",
        width=1200,
        height=1200,
        default_sill_height=1000,
    )
    small_window = WindowType(
        name="Small Window",
        width=600,
        height=600,
        default_sill_height=1400,
    )

    # Floor slab
    floor_type = FloorType("Concrete Floor")
    floor_type.add_layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
    floor_type.add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)

    # Ceiling
    ceiling_type = CeilingType("Gypsum Ceiling", thickness=15)

    # Roof
    roof_type = FloorType("Flat Roof")
    roof_type.add_layer(insulation, 100, LayerFunction.THERMAL_INSULATION)
    roof_type.add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)

    return {
        "exterior_wall": exterior_wall_type,
        "interior_wall": interior_wall_type,
        "entry_door": entry_door,
        "interior_door": interior_door,
        "large_window": large_window,
        "medium_window": medium_window,
        "small_window": small_window,
        "floor": floor_type,
        "ceiling": ceiling_type,
        "roof": roof_type,
    }


def create_ground_floor(building, types):
    """Create ground floor with living room, kitchen, entry, and stair area.

    Layout (looking from above, +Y is North, +X is East):

    +-------------------+----------------+
    |                   |                |
    |    KITCHEN        |    STAIR       |
    |    (4x4)          |    (3x2)       |
    |                   |                |
    +---+---------------+----------------+
    |   |                                |
    |ENT|        LIVING ROOM             |
    |(2x2)           (6x5)               |
    |   |                                |
    +---+--------------------------------+

    Entry: SW corner (0,0) to (2000, 2000)
    Living: (2000, 0) to (8000, 5000) - most of ground floor
    Kitchen: NW corner (0, 2000) to (4000, 6000) - BUT building is only 5m deep
    Stair: NE area

    Actually, let's simplify:
    Building is 10m x 8m to fit all rooms comfortably.
    """
    level = Level(building, "Ground Floor", elevation=0)

    walls = []
    doors = []
    windows = []
    floors = []
    ceilings = []
    floor_openings = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Let me recalculate building dimensions to fit all rooms:
    # We need: Living (6x5), Kitchen (4x4), Entry (2x2), Stair (3x2)
    # Layout in X: Entry(2) + Living(6) = 8m OR Kitchen(4) + Stair(3) = 7m -> 8m
    # Layout in Y: Entry/Living(5) + part above = need Kitchen(4) to fit
    # So building is 8m x 7m to accommodate

    # Revised layout:
    # Y=0 to Y=5000: Entry (0-2000) | Living (2000-8000)
    # Y=5000 to Y=7000: Kitchen (0-4000) | Stair (4000-7000) | gap (7000-8000)
    # Actually kitchen is 4x4, so it needs Y=5000 to Y=9000

    # Let's do a cleaner layout:
    # Building: 10m x 9m
    # South row (Y=0 to Y=5000): Entry(2x2 at SW) + Living(6x5)
    # North row (Y=5000 to Y=9000): Kitchen(4x4 at NW) + Stair(3x2)

    BLDG_WIDTH = 10000  # 10m
    BLDG_DEPTH = 9000   # 9m

    # Entry: (0, 0) to (2000, 2000)
    # Living: (2000, 0) to (8000, 5000) - internal 6x5
    # Door from Entry to Living: in wall at X=2000
    # Kitchen: (0, 5000) to (4000, 9000) - internal 4x4
    # Stair: (5000, 5000) to (8000, 7000) - internal 3x2

    # Exterior walls
    wall_south = Wall(ext_wall, (0, 0), (BLDG_WIDTH, 0), level, name="Ext_South_G")
    wall_east = Wall(ext_wall, (BLDG_WIDTH, 0), (BLDG_WIDTH, BLDG_DEPTH), level, name="Ext_East_G")
    wall_north = Wall(ext_wall, (BLDG_WIDTH, BLDG_DEPTH), (0, BLDG_DEPTH), level, name="Ext_North_G")
    wall_west = Wall(ext_wall, (0, BLDG_DEPTH), (0, 0), level, name="Ext_West_G")
    walls.extend([wall_south, wall_east, wall_north, wall_west])

    # Entry vestibule walls (interior partition at X=2000 from Y=0 to Y=2000)
    entry_east_wall = Wall(
        int_wall,
        (2000, 0),
        (2000, 2000),
        level,
        name="Entry_East_G",
    )
    walls.append(entry_east_wall)

    # Entry north wall at Y=2000 from X=0 to X=2000
    entry_north_wall = Wall(
        int_wall,
        (0, 2000),
        (2000, 2000),
        level,
        name="Entry_North_G",
    )
    walls.append(entry_north_wall)

    # Front door on south wall in entry area (centered in entry)
    front_door = Door(
        types["entry_door"],
        wall_south,
        offset=1000 - types["entry_door"].width / 2,  # Center in 2m entry
        name="Front_Door",
        mark="D-01",
    )
    doors.append(front_door)

    # Door from entry to living room (in entry_east_wall)
    entry_living_door = Door(
        types["interior_door"],
        entry_east_wall,
        offset=1000 - types["interior_door"].width / 2,  # Centered
        name="Entry_Living_Door",
        mark="D-02",
    )
    doors.append(entry_living_door)

    # Living room large window on south wall (centered in living area: X=2000 to X=8000)
    living_window = Window(
        types["large_window"],
        wall_south,
        offset=5000 - types["large_window"].width / 2,  # Center of living area
        name="Living_Window_South",
        mark="W-01",
    )
    windows.append(living_window)

    # Kitchen area - walls
    # Kitchen south wall at Y=5000 from X=0 to X=4000
    kitchen_south_wall = Wall(
        int_wall,
        (0, 5000),
        (4000, 5000),
        level,
        name="Kitchen_South_G",
    )
    walls.append(kitchen_south_wall)

    # Kitchen east wall at X=4000 from Y=5000 to Y=9000
    kitchen_east_wall = Wall(
        int_wall,
        (4000, 5000),
        (4000, BLDG_DEPTH),
        level,
        name="Kitchen_East_G",
    )
    walls.append(kitchen_east_wall)

    # Door from living/hall area to kitchen
    kitchen_door = Door(
        types["interior_door"],
        kitchen_south_wall,
        offset=2000 - types["interior_door"].width / 2,
        name="Kitchen_Door",
        mark="D-03",
    )
    doors.append(kitchen_door)

    # Kitchen window on west wall
    kitchen_window = Window(
        types["medium_window"],
        wall_west,
        offset=BLDG_DEPTH - 7000 + 2000 - types["medium_window"].height / 2,  # In kitchen area
        name="Kitchen_Window_West",
        mark="W-02",
    )
    windows.append(kitchen_window)

    # Stair area - internal walls
    # Stair south wall at Y=5000 from X=5000 to X=8000 (with gap for access)
    # Actually stair needs access from living area below, so no south wall
    # Stair west wall at X=5000 from Y=5000 to Y=7000
    stair_west_wall = Wall(
        int_wall,
        (5000, 5000),
        (5000, 7000),
        level,
        name="Stair_West_G",
    )
    walls.append(stair_west_wall)

    # Stair east wall at X=8000 from Y=5000 to Y=7000
    stair_east_wall = Wall(
        int_wall,
        (8000, 5000),
        (8000, 7000),
        level,
        name="Stair_East_G",
    )
    walls.append(stair_east_wall)

    # Stair north wall at Y=7000 from X=5000 to X=8000
    stair_north_wall = Wall(
        int_wall,
        (5000, 7000),
        (8000, 7000),
        level,
        name="Stair_North_G",
    )
    walls.append(stair_north_wall)

    # Ground floor slab
    floor_boundary = [
        (0, 0),
        (BLDG_WIDTH, 0),
        (BLDG_WIDTH, BLDG_DEPTH),
        (0, BLDG_DEPTH),
    ]
    floor = Floor(types["floor"], floor_boundary, level, name="Ground_Floor_Slab")
    floors.append(floor)

    # Ceiling
    ceiling_boundary = floor_boundary
    ceiling = Ceiling(
        types["ceiling"],
        ceiling_boundary,
        level,
        height=CEILING_HEIGHT,
        name="Ground_Floor_Ceiling",
    )
    ceilings.append(ceiling)

    return (
        level,
        walls,
        doors,
        windows,
        floors,
        ceilings,
        floor_openings,
        BLDG_WIDTH,
        BLDG_DEPTH,
    )


def create_upper_floor(building, types, bldg_width, bldg_depth):
    """Create upper floor with master bedroom, second bedroom, bathroom, and hallway.

    Layout:
    +-------------------+----------------+
    |                   |                |
    |    BED 2 (4x4)    |   BATH (3x2)   |
    |                   |                |
    +-------------------+----+-----------+
    |         HALLWAY        | STAIR     |
    +------------------------+  (opening)|
    |                        |           |
    |    MASTER (5x4)        |           |
    +------------------------+-----------+

    Upper floor same footprint as ground floor.
    Stair opening at same location as stair walls below.
    """
    level = Level(building, "Upper Floor", elevation=FLOOR_HEIGHT)

    walls = []
    doors = []
    windows = []
    floors = []
    ceilings = []
    floor_openings = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # Exterior walls
    wall_south = Wall(ext_wall, (0, 0), (bldg_width, 0), level, name="Ext_South_U")
    wall_east = Wall(ext_wall, (bldg_width, 0), (bldg_width, bldg_depth), level, name="Ext_East_U")
    wall_north = Wall(ext_wall, (bldg_width, bldg_depth), (0, bldg_depth), level, name="Ext_North_U")
    wall_west = Wall(ext_wall, (0, bldg_depth), (0, 0), level, name="Ext_West_U")
    walls.extend([wall_south, wall_east, wall_north, wall_west])

    # Hallway runs E-W through center
    # Hallway Y = 4000 to 5000 (1m wide hallway)
    hall_south_y = 4000
    hall_north_y = 5000

    # Master bedroom: SW area (0, 0) to (5000, 4000)
    # Master north wall at Y=4000 from X=0 to X=5000
    master_north_wall = Wall(
        int_wall,
        (0, hall_south_y),
        (5000, hall_south_y),
        level,
        name="Master_North_U",
    )
    walls.append(master_north_wall)

    # Master east wall at X=5000 from Y=0 to Y=4000
    master_east_wall = Wall(
        int_wall,
        (5000, 0),
        (5000, hall_south_y),
        level,
        name="Master_East_U",
    )
    walls.append(master_east_wall)

    # Master door in north wall
    master_door = Door(
        types["interior_door"],
        master_north_wall,
        offset=2500 - types["interior_door"].width / 2,
        name="Master_Door",
        mark="D-04",
    )
    doors.append(master_door)

    # Master bedroom window on south wall
    master_window = Window(
        types["large_window"],
        wall_south,
        offset=2500 - types["large_window"].width / 2,
        name="Master_Window_South",
        mark="W-03",
    )
    windows.append(master_window)

    # Bedroom 2: NW area (0, 5000) to (4000, 9000)
    # Bed2 south wall at Y=5000 from X=0 to X=4000
    bed2_south_wall = Wall(
        int_wall,
        (0, hall_north_y),
        (4000, hall_north_y),
        level,
        name="Bed2_South_U",
    )
    walls.append(bed2_south_wall)

    # Bed2 east wall at X=4000 from Y=5000 to Y=9000
    bed2_east_wall = Wall(
        int_wall,
        (4000, hall_north_y),
        (4000, bldg_depth),
        level,
        name="Bed2_East_U",
    )
    walls.append(bed2_east_wall)

    # Bed2 door in south wall
    bed2_door = Door(
        types["interior_door"],
        bed2_south_wall,
        offset=2000 - types["interior_door"].width / 2,
        name="Bed2_Door",
        mark="D-05",
    )
    doors.append(bed2_door)

    # Bed2 window on north wall
    bed2_window = Window(
        types["medium_window"],
        wall_north,
        offset=bldg_width - 2000 - types["medium_window"].width / 2,
        name="Bed2_Window_North",
        mark="W-04",
    )
    windows.append(bed2_window)

    # Bathroom: NE area (5000, 5000) to (8000, 7000) - 3x2
    # But needs to not overlap with stair opening
    # Bathroom is at (4000, 5000) to (7000, 7000)
    # Wait, bed2 east wall is at X=4000, so bathroom starts at X=4000
    # Bath south wall at Y=5000 from X=4000 to X=7000
    bath_south_wall = Wall(
        int_wall,
        (4000, hall_north_y),
        (7000, hall_north_y),
        level,
        name="Bath_South_U",
    )
    walls.append(bath_south_wall)

    # Bath east wall at X=7000 from Y=5000 to Y=7000
    bath_east_wall = Wall(
        int_wall,
        (7000, hall_north_y),
        (7000, 7000),
        level,
        name="Bath_East_U",
    )
    walls.append(bath_east_wall)

    # Bath north wall at Y=7000 from X=4000 to X=7000
    bath_north_wall = Wall(
        int_wall,
        (4000, 7000),
        (7000, 7000),
        level,
        name="Bath_North_U",
    )
    walls.append(bath_north_wall)

    # Bathroom door in south wall
    bath_door = Door(
        types["interior_door"],
        bath_south_wall,
        offset=1500 - types["interior_door"].width / 2,
        name="Bath_Door",
        mark="D-06",
    )
    doors.append(bath_door)

    # Bathroom small window
    bath_window = Window(
        types["small_window"],
        wall_north,
        offset=bldg_width - 5500 - types["small_window"].width / 2,
        name="Bath_Window",
        mark="W-05",
    )
    windows.append(bath_window)

    # Upper floor slab with stair opening
    floor_boundary = [
        (0, 0),
        (bldg_width, 0),
        (bldg_width, bldg_depth),
        (0, bldg_depth),
    ]
    floor = Floor(types["floor"], floor_boundary, level, name="Upper_Floor_Slab")
    floors.append(floor)

    # Stair opening in floor slab - matches stair location on ground floor
    # Stair area: (5000, 5000) to (8000, 7000)
    stair_opening = Opening(
        host_element=floor,
        boundary=[
            (5000, 5000),
            (8000, 5000),
            (8000, 7000),
            (5000, 7000),
        ],
        name="Stair_Opening",
    )
    floor_openings.append(stair_opening)

    # Ceiling
    ceiling_boundary = floor_boundary
    ceiling = Ceiling(
        types["ceiling"],
        ceiling_boundary,
        level,
        height=CEILING_HEIGHT,
        name="Upper_Floor_Ceiling",
    )
    ceilings.append(ceiling)

    return (
        level,
        walls,
        doors,
        windows,
        floors,
        ceilings,
        floor_openings,
    )


def create_roof(types, upper_level, bldg_width, bldg_depth):
    """Create flat roof over upper floor.

    The roof is placed on the upper floor level but positioned
    at the ceiling height (FLOOR_HEIGHT) so it sits on top of the upper floor.
    This keeps the IFC model to only 2 building storeys.
    """
    roof_boundary = [
        (0, 0),
        (bldg_width, 0),
        (bldg_width, bldg_depth),
        (0, bldg_depth),
    ]
    roof = Roof(types["roof"], roof_boundary, upper_level, name="Flat_Roof")

    return [roof]


def build():
    """Create the two-story residential building."""
    building = Building("Two Story Residence")
    types = create_types()

    # Create floors
    (
        ground,
        g_walls,
        g_doors,
        g_windows,
        g_floors,
        g_ceilings,
        g_openings,
        bldg_width,
        bldg_depth,
    ) = create_ground_floor(building, types)

    (
        upper,
        u_walls,
        u_doors,
        u_windows,
        u_floors,
        u_ceilings,
        u_openings,
    ) = create_upper_floor(building, types, bldg_width, bldg_depth)

    roofs = create_roof(types, upper, bldg_width, bldg_depth)

    # Process wall joins per floor
    for walls in [g_walls, u_walls]:
        adjustments = detect_and_process_wall_joins(walls, end_cap_type=EndCapType.EXTERIOR)
        for wall, adj in adjustments.items():
            wall._trim_adjustments = adj

    return building


def main():
    """Create building and export all outputs."""
    print("=" * 70)
    print("Eval 04: Two Story Residential Building")
    print("=" * 70)

    out_dir = Path(__file__).parent
    dxf_dir = out_dir / "dxf"
    dxf_dir.mkdir(parents=True, exist_ok=True)

    # Create building
    print("\nCreating building...")
    building = Building("Two Story Residence")
    types = create_types()

    # Create floors
    print("  Ground Floor...")
    (
        ground,
        g_walls,
        g_doors,
        g_windows,
        g_floors,
        g_ceilings,
        g_openings,
        bldg_width,
        bldg_depth,
    ) = create_ground_floor(building, types)

    print("  Upper Floor...")
    (
        upper,
        u_walls,
        u_doors,
        u_windows,
        u_floors,
        u_ceilings,
        u_openings,
    ) = create_upper_floor(building, types, bldg_width, bldg_depth)

    print("  Roof...")
    roofs = create_roof(types, upper, bldg_width, bldg_depth)

    # Process wall joins
    print("\n  Processing wall joins...")
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
    print(f"    Floor Openings: {len(g_openings) + len(u_openings)}")

    # Export IFC
    print("\n" + "-" * 70)
    print("Exporting IFC...")
    ifc_path = out_dir / "building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path.name}")

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
    print("  Generating floor plans...")
    view_range = ViewRange(cut_height=1200, top=FLOOR_HEIGHT, bottom=0, view_depth=0)

    ground_plan = FloorPlanView(name="Ground Floor Plan", level=ground, view_range=view_range)
    ground_result = ground_plan.generate(g_index, cache)
    exporter.export(ground_result, str(dxf_dir / "ground_floor_plan.dxf"))
    print(f"    Saved: ground_floor_plan.dxf")

    upper_plan = FloorPlanView(name="Upper Floor Plan", level=upper, view_range=view_range)
    upper_result = upper_plan.generate(u_index, cache)
    exporter.export(upper_result, str(dxf_dir / "upper_floor_plan.dxf"))
    print(f"    Saved: upper_floor_plan.dxf")

    # Elevations
    print("  Generating elevations...")
    height_range = (0, FLOOR_HEIGHT * 2 + 500)

    north_elev = ElevationView(
        "North Elevation",
        direction=ElevationDirection.NORTH,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    north_result = north_elev.generate(combined_index, cache)
    exporter.export(north_result, str(dxf_dir / "elevation_north.dxf"))
    print(f"    Saved: elevation_north.dxf")

    south_elev = ElevationView(
        "South Elevation",
        direction=ElevationDirection.SOUTH,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    south_result = south_elev.generate(combined_index, cache)
    exporter.export(south_result, str(dxf_dir / "elevation_south.dxf"))
    print(f"    Saved: elevation_south.dxf")

    east_elev = ElevationView(
        "East Elevation",
        direction=ElevationDirection.EAST,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    east_result = east_elev.generate(combined_index, cache)
    exporter.export(east_result, str(dxf_dir / "elevation_east.dxf"))
    print(f"    Saved: elevation_east.dxf")

    west_elev = ElevationView(
        "West Elevation",
        direction=ElevationDirection.WEST,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    west_result = west_elev.generate(combined_index, cache)
    exporter.export(west_result, str(dxf_dir / "elevation_west.dxf"))
    print(f"    Saved: elevation_west.dxf")

    # Section
    print("  Generating section...")
    section = SectionView(
        name="Section A-A",
        plane_point=(bldg_width / 2, bldg_depth / 2, 0),
        plane_normal=(0, 1, 0),  # Looking north
        depth=bldg_depth,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    section_result = section.generate(combined_index, cache)
    exporter.export(section_result, str(dxf_dir / "section_aa.dxf"))
    print(f"    Saved: section_aa.dxf")

    # Create PDF drawing set with multiple pages
    print("\n" + "-" * 70)
    print("Creating PDF drawing set...")

    # Use matplotlib PdfPages for multi-page PDF
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        pdf_path = out_dir / "04_two_story_building_drawing_set.pdf"
        with PdfPages(str(pdf_path)) as pdf:
            # Create sheets for each view
            views = [
                ("Ground Floor Plan", ground_result),
                ("Upper Floor Plan", upper_result),
                ("North Elevation", north_result),
                ("South Elevation", south_result),
                ("East Elevation", east_result),
                ("West Elevation", west_result),
                ("Section A-A", section_result),
            ]

            for view_name, view_result in views:
                # Create sheet
                sheet = Sheet(
                    size=SheetSize.ARCH_D,
                    number=f"A-{views.index((view_name, view_result)) + 101}",
                    name=view_name,
                    metadata=SheetMetadata(
                        project="Two Story Residence",
                        drawn_by="BIMasCode",
                        date=datetime.now().strftime("%Y-%m-%d"),
                    ),
                )

                # Add viewport
                sheet.add_viewport(
                    view_result,
                    position=(sheet.size.width / 2, sheet.size.height / 2 + 50),
                    scale=ViewScale.SCALE_1_100,
                    name=view_name,
                )

                # Add title block
                title_block = TitleBlock.from_template(
                    "standard_arch_d",
                    fields={
                        TitleBlockField.PROJECT_NAME.value: "Two Story Residence",
                        TitleBlockField.SHEET_NAME.value: sheet.name,
                        TitleBlockField.SHEET_NUMBER.value: sheet.number,
                        TitleBlockField.DRAWN_BY.value: "BIMasCode",
                        TitleBlockField.DATE.value: datetime.now().strftime("%Y-%m-%d"),
                        TitleBlockField.SCALE.value: "1:100",
                    },
                    position=(sheet.size.width - 210, 10),
                )
                sheet.set_title_block(title_block)

                # Export sheet to PDF page
                # Create figure with sheet dimensions
                fig_width = sheet.size.width / 25.4  # Convert mm to inches
                fig_height = sheet.size.height / 25.4

                fig, ax = plt.subplots(figsize=(fig_width, fig_height))
                fig.patch.set_facecolor("white")
                ax.set_facecolor("white")
                ax.set_aspect("equal")
                ax.axis("off")
                ax.set_xlim(0, sheet.size.width)
                ax.set_ylim(0, sheet.size.height)

                # Draw sheet border
                border = plt.Rectangle(
                    (0, 0),
                    sheet.size.width,
                    sheet.size.height,
                    fill=False,
                    edgecolor=(0.7, 0.7, 0.7),
                    linewidth=0.5,
                )
                ax.add_patch(border)

                # Draw view content
                bounds = view_result.get_bounds()
                if bounds:
                    model_center_x = (bounds[0] + bounds[2]) / 2
                    model_center_y = (bounds[1] + bounds[3]) / 2
                    scale = ViewScale.SCALE_1_100.ratio
                    offset_x = sheet.size.width / 2 - model_center_x * scale
                    offset_y = sheet.size.height / 2 + 50 - model_center_y * scale

                    # Draw lines
                    for line in view_result.lines:
                        ax.plot(
                            [line.start.x * scale + offset_x, line.end.x * scale + offset_x],
                            [line.start.y * scale + offset_y, line.end.y * scale + offset_y],
                            color="black",
                            linewidth=0.5,
                        )

                    # Draw arcs
                    import math
                    from matplotlib.patches import Arc as MplArc
                    for arc in view_result.arcs:
                        start_deg = math.degrees(arc.start_angle)
                        end_deg = math.degrees(arc.end_angle)
                        if end_deg < start_deg:
                            end_deg += 360
                        arc_patch = MplArc(
                            (arc.center.x * scale + offset_x, arc.center.y * scale + offset_y),
                            2 * arc.radius * scale,
                            2 * arc.radius * scale,
                            angle=0,
                            theta1=start_deg,
                            theta2=end_deg,
                            fill=False,
                            linewidth=0.5,
                            edgecolor="black",
                        )
                        ax.add_patch(arc_patch)

                    # Draw polylines
                    for polyline in view_result.polylines:
                        if len(polyline.points) >= 2:
                            xs = [p.x * scale + offset_x for p in polyline.points]
                            ys = [p.y * scale + offset_y for p in polyline.points]
                            if polyline.closed:
                                xs.append(xs[0])
                                ys.append(ys[0])
                            ax.plot(xs, ys, color="black", linewidth=0.5)

                # Add view title
                ax.text(
                    sheet.size.width / 2,
                    30,
                    view_name,
                    fontsize=12,
                    ha="center",
                    va="bottom",
                    color="black",
                )

                # Add sheet number
                ax.text(
                    sheet.size.width - 20,
                    20,
                    sheet.number,
                    fontsize=10,
                    ha="right",
                    va="bottom",
                    color="black",
                )

                pdf.savefig(fig, bbox_inches="tight", pad_inches=0)
                plt.close(fig)

        print(f"  Saved: {pdf_path.name}")

    except ImportError as e:
        print(f"  Warning: Could not create PDF (matplotlib not available): {e}")

    # Summary
    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print(f"  {ifc_path.name}")
    for f in sorted(dxf_dir.iterdir()):
        print(f"  dxf/{f.name}")
    if (out_dir / "04_two_story_building_drawing_set.pdf").exists():
        print(f"  04_two_story_building_drawing_set.pdf")


if __name__ == "__main__":
    main()
