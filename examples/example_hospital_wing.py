"""
Hospital Wing Example - Patient Room Corridor

Demonstrates:
- Patient rooms arranged along a corridor
- ChainDimension2D for dimensioning room widths along corridor
- Nurses station at corridor center
- Standard hospital room sizes and clearances
- Text annotations for room labels

Building: Single corridor wing with patient rooms
- Corridor: 2.4m wide (ADA/healthcare standard)
- Patient rooms: 4m x 5m (single-bed standard)
- Nurses station: Central location
"""

from datetime import datetime
from pathlib import Path

from bimascode.architecture import (
    Door,
    Floor,
    Wall,
    create_basic_wall_type,
    detect_and_process_wall_joins,
    EndCapType,
)
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.line_styles import LineStyle
from bimascode.drawing.primitives import (
    ChainDimension2D,
    LinearDimension2D,
    Point2D,
    TextAlignment,
    TextNote2D,
)
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.sheet import Sheet, SheetMetadata
from bimascode.drawing.sheet_sizes import SheetSize
from bimascode.drawing.tags import DoorTag, RoomTag, SectionSymbol, SectionSymbolStyle, TagStyle
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room import Room
from bimascode.utils.materials import MaterialLibrary

# Building dimensions (mm)
CORRIDOR_WIDTH = 3000  # 3.0m - wide healthcare corridor
ROOM_WIDTH = 4000  # 4m per room
ROOM_DEPTH = 5000  # 5m depth
WALL_THICKNESS = 200
FLOOR_HEIGHT = 3200

# Layout
NUM_ROOMS_PER_SIDE = 5
NURSES_STATION_WIDTH = 6000
NURSES_STATION_DEPTH = 3000


def create_types():
    """Create element types."""
    concrete = MaterialLibrary.concrete()
    gypsum = MaterialLibrary.gypsum_board()

    # Exterior wall (concrete)
    exterior_wall = create_basic_wall_type("Exterior Wall", 250, concrete)

    # Interior partition (gypsum both sides)
    interior_wall = create_basic_wall_type("Interior Partition", 150, gypsum)

    # Patient room door (wider for bed access)
    patient_door = DoorType(name="Patient Room Door", width=1200, height=2100)

    # Floor slab
    floor_type = FloorType("Concrete Floor")
    floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

    return {
        "exterior_wall": exterior_wall,
        "interior_wall": interior_wall,
        "patient_door": patient_door,
        "floor": floor_type,
    }


def create_hospital_wing(building, types):
    """Create hospital wing with patient rooms and nurses station."""
    level = Level(building, "Level 1", elevation=0)

    all_walls = []
    all_doors = []
    all_rooms = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]
    door_type = types["patient_door"]

    # Calculate total corridor length
    # Rooms on each side + nurses station in middle
    total_rooms = NUM_ROOMS_PER_SIDE * 2
    corridor_length = total_rooms * ROOM_WIDTH + NURSES_STATION_WIDTH

    # Corridor Y positions
    corridor_south_y = 0
    corridor_north_y = CORRIDOR_WIDTH

    # Room positions
    south_room_y = corridor_south_y - ROOM_DEPTH
    north_room_y = corridor_north_y + ROOM_DEPTH

    # -- Exterior walls --

    # South exterior wall (outer edge of south rooms)
    wall_south = Wall(
        ext_wall,
        (0, south_room_y),
        (corridor_length, south_room_y),
        level,
        name="Ext_South",
    )
    all_walls.append(wall_south)

    # North exterior wall (outer edge of north rooms)
    wall_north = Wall(
        ext_wall,
        (corridor_length, north_room_y),
        (0, north_room_y),
        level,
        name="Ext_North",
    )
    all_walls.append(wall_north)

    # West exterior wall
    wall_west = Wall(
        ext_wall,
        (0, north_room_y),
        (0, south_room_y),
        level,
        name="Ext_West",
    )
    all_walls.append(wall_west)

    # East exterior wall
    wall_east = Wall(
        ext_wall,
        (corridor_length, south_room_y),
        (corridor_length, north_room_y),
        level,
        name="Ext_East",
    )
    all_walls.append(wall_east)

    # -- Corridor walls --

    # South corridor wall (with doors to south rooms)
    corridor_wall_south = Wall(
        int_wall,
        (0, corridor_south_y),
        (corridor_length, corridor_south_y),
        level,
        name="Corridor_South",
    )
    all_walls.append(corridor_wall_south)

    # North corridor wall (with doors to north rooms)
    corridor_wall_north = Wall(
        int_wall,
        (corridor_length, corridor_north_y),
        (0, corridor_north_y),
        level,
        name="Corridor_North",
    )
    all_walls.append(corridor_wall_north)

    # -- Patient rooms (South side) --
    # First 5 rooms on west, then nurses station, then 5 more on east

    room_partition_points_south = [0]  # Start at west end

    for i in range(NUM_ROOMS_PER_SIDE):
        room_x = i * ROOM_WIDTH

        # Partition wall between rooms (skip first)
        if i > 0:
            partition = Wall(
                int_wall,
                (room_x, corridor_south_y),
                (room_x, south_room_y),
                level,
                name=f"Partition_S{i}",
            )
            all_walls.append(partition)

        room_partition_points_south.append(room_x + ROOM_WIDTH)

        # Door to room (mark matches room number)
        door = Door(
            door_type,
            corridor_wall_south,
            offset=room_x + ROOM_WIDTH / 2 - door_type.width / 2,
            name=f"Door_S{i + 1}",
            mark=str(101 + i),
        )
        all_doors.append(door)

        # Create patient room
        patient_room = Room(
            name="Patient Room",
            number=str(101 + i),
            boundary=[
                (room_x, south_room_y),
                (room_x + ROOM_WIDTH, south_room_y),
                (room_x + ROOM_WIDTH, corridor_south_y),
                (room_x, corridor_south_y),
            ],
            level=level,
        )
        all_rooms.append(patient_room)

    # Nurses station position (center)
    nurses_x_start = NUM_ROOMS_PER_SIDE * ROOM_WIDTH
    nurses_x_end = nurses_x_start + NURSES_STATION_WIDTH

    # Partition before nurses station
    partition = Wall(
        int_wall,
        (nurses_x_start, corridor_south_y),
        (nurses_x_start, south_room_y),
        level,
        name="Partition_Nurses_West",
    )
    all_walls.append(partition)
    room_partition_points_south.append(nurses_x_end)

    # Partition after nurses station
    partition = Wall(
        int_wall,
        (nurses_x_end, corridor_south_y),
        (nurses_x_end, south_room_y),
        level,
        name="Partition_Nurses_East",
    )
    all_walls.append(partition)

    # East side rooms (South)
    for i in range(NUM_ROOMS_PER_SIDE):
        room_x = nurses_x_end + i * ROOM_WIDTH

        # Partition wall between rooms (skip first - already have nurses station partition)
        if i > 0:
            partition = Wall(
                int_wall,
                (room_x, corridor_south_y),
                (room_x, south_room_y),
                level,
                name=f"Partition_SE{i}",
            )
            all_walls.append(partition)

        room_partition_points_south.append(room_x + ROOM_WIDTH)

        # Door to room (mark matches room number)
        door = Door(
            door_type,
            corridor_wall_south,
            offset=room_x + ROOM_WIDTH / 2 - door_type.width / 2,
            name=f"Door_SE{i + 1}",
            mark=str(106 + i),
        )
        all_doors.append(door)

        # Create patient room
        patient_room = Room(
            name="Patient Room",
            number=str(106 + i),
            boundary=[
                (room_x, south_room_y),
                (room_x + ROOM_WIDTH, south_room_y),
                (room_x + ROOM_WIDTH, corridor_south_y),
                (room_x, corridor_south_y),
            ],
            level=level,
        )
        all_rooms.append(patient_room)

    # -- Patient rooms (North side) --
    room_partition_points_north = [0]

    for i in range(NUM_ROOMS_PER_SIDE):
        room_x = i * ROOM_WIDTH

        if i > 0:
            partition = Wall(
                int_wall,
                (room_x, corridor_north_y),
                (room_x, north_room_y),
                level,
                name=f"Partition_N{i}",
            )
            all_walls.append(partition)

        room_partition_points_north.append(room_x + ROOM_WIDTH)

        # Door to room (mark matches room number)
        door = Door(
            door_type,
            corridor_wall_north,
            offset=corridor_length - room_x - ROOM_WIDTH / 2 - door_type.width / 2,
            name=f"Door_N{i + 1}",
            mark=str(201 + i),
        )
        all_doors.append(door)

        # Create patient room
        patient_room = Room(
            name="Patient Room",
            number=str(201 + i),
            boundary=[
                (room_x, corridor_north_y),
                (room_x + ROOM_WIDTH, corridor_north_y),
                (room_x + ROOM_WIDTH, north_room_y),
                (room_x, north_room_y),
            ],
            level=level,
        )
        all_rooms.append(patient_room)

    # North nurses station partitions
    partition = Wall(
        int_wall,
        (nurses_x_start, corridor_north_y),
        (nurses_x_start, north_room_y),
        level,
        name="Partition_Nurses_North_West",
    )
    all_walls.append(partition)
    room_partition_points_north.append(nurses_x_end)

    partition = Wall(
        int_wall,
        (nurses_x_end, corridor_north_y),
        (nurses_x_end, north_room_y),
        level,
        name="Partition_Nurses_North_East",
    )
    all_walls.append(partition)

    # East side rooms (North)
    for i in range(NUM_ROOMS_PER_SIDE):
        room_x = nurses_x_end + i * ROOM_WIDTH

        if i > 0:
            partition = Wall(
                int_wall,
                (room_x, corridor_north_y),
                (room_x, north_room_y),
                level,
                name=f"Partition_NE{i}",
            )
            all_walls.append(partition)

        room_partition_points_north.append(room_x + ROOM_WIDTH)

        # Door to room (mark matches room number)
        door = Door(
            door_type,
            corridor_wall_north,
            offset=corridor_length - room_x - ROOM_WIDTH / 2 - door_type.width / 2,
            name=f"Door_NE{i + 1}",
            mark=str(206 + i),
        )
        all_doors.append(door)

        # Create patient room
        patient_room = Room(
            name="Patient Room",
            number=str(206 + i),
            boundary=[
                (room_x, corridor_north_y),
                (room_x + ROOM_WIDTH, corridor_north_y),
                (room_x + ROOM_WIDTH, north_room_y),
                (room_x, north_room_y),
            ],
            level=level,
        )
        all_rooms.append(patient_room)

    # Create nurses station rooms (south and north)
    nurses_station_south = Room(
        name="Nurses Station",
        number="NS-S",
        boundary=[
            (nurses_x_start, south_room_y),
            (nurses_x_end, south_room_y),
            (nurses_x_end, corridor_south_y),
            (nurses_x_start, corridor_south_y),
        ],
        level=level,
    )
    all_rooms.append(nurses_station_south)

    nurses_station_north = Room(
        name="Nurses Station",
        number="NS-N",
        boundary=[
            (nurses_x_start, corridor_north_y),
            (nurses_x_end, corridor_north_y),
            (nurses_x_end, north_room_y),
            (nurses_x_start, north_room_y),
        ],
        level=level,
    )
    all_rooms.append(nurses_station_north)

    # Create corridor room
    corridor_room = Room(
        name="Corridor",
        number="CORR",
        boundary=[
            (0, corridor_south_y),
            (corridor_length, corridor_south_y),
            (corridor_length, corridor_north_y),
            (0, corridor_north_y),
        ],
        level=level,
    )
    all_rooms.append(corridor_room)

    # Floor slab
    floor_boundary = [
        (0, south_room_y),
        (corridor_length, south_room_y),
        (corridor_length, north_room_y),
        (0, north_room_y),
    ]
    floor = Floor(types["floor"], floor_boundary, level, name="Floor_L1")

    return (
        level,
        all_walls,
        all_doors,
        [floor],
        all_rooms,
        room_partition_points_south,
        room_partition_points_north,
        nurses_x_start,
        nurses_x_end,
        corridor_length,
        south_room_y,
        north_room_y,
    )


def add_door_tags(result, doors, style: TagStyle | None = None):
    """Add door tags to the floor plan.

    Each door gets a tag displaying its mark (room number).

    Args:
        result: ViewResult to add tags to
        doors: List of doors to tag
        style: Optional custom TagStyle (defaults to TagStyle.door_default())
    """
    for door in doors:
        if door.mark:
            tag = DoorTag(door=door, style=style) if style else DoorTag(door=door)
            result.door_tags.append(tag)


def add_annotations(
    result,
    rooms,
    room_points_south,
    room_points_north,
    nurses_x_start,
    nurses_x_end,
    corridor_length,
    south_room_y,
    north_room_y,
):
    """Add dimensions and room tags to the floor plan.

    This demonstrates PROPER use of ChainDimension2D:
    - Dimensioning room widths along the corridor (collinear points)
    - Chain dimensions share a continuous baseline

    Room labels are now added using RoomTag instead of TextNote.
    """
    dim_style = LineStyle.dimension()

    # -- CHAIN DIMENSIONS --
    # These are PROPER uses of chain dimensions: dimensioning collinear wall
    # segments along a corridor. All points lie on the same line.

    # South room widths - chain dimension along exterior wall
    # Points are the room partition X coordinates at the south wall Y
    south_chain_points = tuple(Point2D(x, south_room_y) for x in room_points_south)

    south_chain = ChainDimension2D(
        points=south_chain_points,
        offset=-1500,  # Below the south wall
        precision=0,
        style=dim_style,
    )
    result.chain_dimensions.append(south_chain)

    # North room widths - chain dimension along exterior wall
    north_chain_points = tuple(Point2D(x, north_room_y) for x in room_points_north)

    north_chain = ChainDimension2D(
        points=north_chain_points,
        offset=1500,  # Above the north wall
        precision=0,
        style=dim_style,
    )
    result.chain_dimensions.append(north_chain)

    # -- OVERALL DIMENSION --
    # Single linear dimension for total corridor length
    overall_dim = LinearDimension2D(
        start=Point2D(0, south_room_y),
        end=Point2D(corridor_length, south_room_y),
        offset=-3000,  # Further below the chain dimension
        precision=0,
        style=dim_style,
    )
    result.dimensions.append(overall_dim)

    # Room depth dimensions (perpendicular to corridor)
    # West side room depth
    depth_dim_west = LinearDimension2D(
        start=Point2D(0, south_room_y),
        end=Point2D(0, 0),  # corridor south edge
        offset=1500,
        precision=0,
        style=dim_style,
    )
    result.dimensions.append(depth_dim_west)

    # Corridor width dimension
    corridor_dim = LinearDimension2D(
        start=Point2D(0, 0),
        end=Point2D(0, CORRIDOR_WIDTH),
        offset=1500,
        precision=0,
        style=dim_style,
    )
    result.dimensions.append(corridor_dim)

    # North room depth
    depth_dim_north = LinearDimension2D(
        start=Point2D(0, CORRIDOR_WIDTH),
        end=Point2D(0, north_room_y),
        offset=1500,
        precision=0,
        style=dim_style,
    )
    result.dimensions.append(depth_dim_north)

    # -- ROOM TAGS --
    # Room labels using RoomTag (replaces TextNote for room labels)
    room_style = TagStyle.room_default()
    for room in rooms:
        result.room_tags.append(RoomTag(room=room, style=room_style))

    # Title (keep as TextNote - this is a drawing title, not a room label)
    result.text_notes.append(
        TextNote2D(
            position=Point2D(0, south_room_y - 5000),
            content="HOSPITAL WING - LEVEL 1\nScale: 1:100",
            height=300,
            alignment=TextAlignment.TOP_LEFT,
        )
    )


def main():
    """Create hospital wing and generate floor plan with chain dimensions."""
    print("=" * 70)
    print("Hospital Wing Example - Chain Dimensions Demo")
    print("=" * 70)

    # Output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / "outputs" / "hospital" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Create building
    print("\nCreating hospital wing...")
    building = Building("Hospital Wing")
    types = create_types()

    (
        level,
        walls,
        doors,
        floors,
        rooms,
        room_points_south,
        room_points_north,
        nurses_x_start,
        nurses_x_end,
        corridor_length,
        south_room_y,
        north_room_y,
    ) = create_hospital_wing(building, types)

    # Process wall joins
    print("  Processing wall joins...")
    adjustments = detect_and_process_wall_joins(walls, end_cap_type=EndCapType.EXTERIOR)
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj

    print(f"  Walls: {len(walls)}")
    print(f"  Doors: {len(doors)}")
    print(f"  Patient rooms: {NUM_ROOMS_PER_SIDE * 2 * 2} (2 wings x 2 sides)")

    # Create spatial index
    spatial_index = SpatialIndex()
    for elem in walls + doors + floors:
        spatial_index.insert(elem)

    cache = RepresentationCache()

    # Generate floor plan
    print("\nGenerating floor plan...")
    view_range = ViewRange(cut_height=1200, top=FLOOR_HEIGHT, bottom=0, view_depth=0)
    floor_plan = FloorPlanView(
        name="Hospital Wing Level 1",
        level=level,
        view_range=view_range,
    )
    result = floor_plan.generate(spatial_index, cache)

    # Add annotations including chain dimensions and room tags
    add_annotations(
        result,
        rooms,
        room_points_south,
        room_points_north,
        nurses_x_start,
        nurses_x_end,
        corridor_length,
        south_room_y,
        north_room_y,
    )

    # Add door tags with custom style (larger hexagons with more padding)
    door_tag_style = TagStyle(
        size=700.0,  # Larger hexagon for more padding
        text_height=180.0,  # Same text size
    )
    add_door_tags(result, doors, style=door_tag_style)

    print(f"  Elements: {result.element_count}")
    print(f"  Total geometry: {result.total_geometry_count}")
    print(f"  Chain dimensions: {len(result.chain_dimensions)}")
    print(f"  Linear dimensions: {len(result.dimensions)}")
    print(f"  Text notes: {len(result.text_notes)}")
    print(f"  Door tags: {len(result.door_tags)}")
    print(f"  Room tags: {len(result.room_tags)}")

    # Generate section view through center of building
    # Section cuts parallel to corridor (north-south line through center)
    # Using BIM-style section line: draw line on plan, specify look direction
    print("\nGenerating section view...")
    section_x = corridor_length / 2  # Cut through center of building
    section_start = (section_x, north_room_y + 1000)  # Section line start (north)
    section_end = (section_x, south_room_y - 1000)  # Section line end (south)

    section_view = SectionView.from_section_line(
        name="Section A-A",
        start_point=section_start,
        end_point=section_end,
        look_direction="right",  # Looking west (right when walking north to south)
        depth=corridor_length / 2,  # View depth to see half the building
        height_range=(0, FLOOR_HEIGHT),  # Floor to ceiling
        scale=ViewScale.SCALE_1_50,
    )
    section_result = section_view.generate(spatial_index, cache)
    print(f"  Section elements: {section_result.element_count}")
    print(f"  Section geometry: {section_result.total_geometry_count}")

    # Add section symbol to floor plan
    # This marks where the section cut is located with arrows showing view direction
    print("\nAdding section symbol to floor plan...")
    section_symbol = SectionSymbol.from_section_view(
        section_view=section_view,
        start_point=Point2D(section_start[0], section_start[1]),
        end_point=Point2D(section_end[0], section_end[1]),
        section_id="A",
        sheet_number="A-101",
        style=SectionSymbolStyle(
            bubble_radius=400.0,  # Larger bubbles for visibility
            text_height=200.0,
            arrow_size=300.0,
            line_extension=800.0,  # Move bubbles further from section line ends
        ),
    )
    result.section_symbols.append(section_symbol)
    print(f"  Section symbol added: {section_symbol.section_id} on sheet {section_symbol.sheet_number}")

    # Generate second section view through patient rooms (cuts through doors)
    # This section runs north-south through the center of the first patient room
    print("\nGenerating section B-B through patient rooms...")
    section_b_x = ROOM_WIDTH / 2  # Center of first room (cuts through door)
    section_b_start = (section_b_x, north_room_y + 1000)  # Section line start (north)
    section_b_end = (section_b_x, south_room_y - 1000)  # Section line end (south)

    section_view_b = SectionView.from_section_line(
        name="Section B-B",
        start_point=section_b_start,
        end_point=section_b_end,
        look_direction="left",  # Looking east (left when walking north to south)
        depth=ROOM_WIDTH * 3,  # Show 3 rooms worth of depth
        height_range=(0, FLOOR_HEIGHT),  # Floor to ceiling
        scale=ViewScale.SCALE_1_50,
    )
    section_b_result = section_view_b.generate(spatial_index, cache)
    print(f"  Section B elements: {section_b_result.element_count}")
    print(f"  Section B geometry: {section_b_result.total_geometry_count}")

    # Add section B symbol to floor plan
    section_symbol_b = SectionSymbol.from_section_view(
        section_view=section_view_b,
        start_point=Point2D(section_b_start[0], section_b_start[1]),
        end_point=Point2D(section_b_end[0], section_b_end[1]),
        section_id="B",
        sheet_number="A-102",
        style=SectionSymbolStyle(
            bubble_radius=400.0,
            text_height=200.0,
            arrow_size=300.0,
            line_extension=800.0,  # Move bubbles further from section line ends
        ),
    )
    result.section_symbols.append(section_symbol_b)
    print(f"  Section symbol added: {section_symbol_b.section_id} on sheet {section_symbol_b.sheet_number}")

    # Generate third section view through main corridor (perpendicular to A and B)
    # This section runs east-west through the center of the corridor
    print("\nGenerating section C-C through main corridor...")
    section_c_y = CORRIDOR_WIDTH / 2  # Center of corridor
    section_c_start = (-1000, section_c_y)  # Section line start (west, outside building)
    section_c_end = (corridor_length + 1000, section_c_y)  # Section line end (east, outside)

    section_view_c = SectionView.from_section_line(
        name="Section C-C",
        start_point=section_c_start,
        end_point=section_c_end,
        look_direction="right",  # Looking south (right when walking west to east)
        depth=ROOM_DEPTH + CORRIDOR_WIDTH / 2,  # See south rooms from corridor center
        height_range=(0, FLOOR_HEIGHT),  # Floor to ceiling
        scale=ViewScale.SCALE_1_100,  # Smaller scale for long section
    )
    section_c_result = section_view_c.generate(spatial_index, cache)
    print(f"  Section C elements: {section_c_result.element_count}")
    print(f"  Section C geometry: {section_c_result.total_geometry_count}")

    # Add section C symbol to floor plan
    section_symbol_c = SectionSymbol.from_section_view(
        section_view=section_view_c,
        start_point=Point2D(section_c_start[0], section_c_start[1]),
        end_point=Point2D(section_c_end[0], section_c_end[1]),
        section_id="C",
        sheet_number="A-103",
        style=SectionSymbolStyle(
            bubble_radius=400.0,
            text_height=200.0,
            arrow_size=300.0,
            line_extension=800.0,  # Move bubbles further from section line ends
        ),
    )
    result.section_symbols.append(section_symbol_c)
    print(f"  Section symbol added: {section_symbol_c.section_id} on sheet {section_symbol_c.sheet_number}")
    print(f"  Floor plan now has {len(result.section_symbols)} section symbol(s)")

    # Export floor plan DXF (includes section symbol)
    print("\nExporting DXF files...")
    exporter = DXFExporter()
    dxf_path = output_dir / "hospital_wing_plan.dxf"
    exporter.export(result, str(dxf_path))
    print(f"  Saved: {dxf_path.name}")

    # Export section DXF (standalone)
    section_dxf_path = output_dir / "hospital_wing_section_A.dxf"
    exporter.export(section_result, str(section_dxf_path))
    print(f"  Saved: {section_dxf_path.name}")

    # Export section B DXF (through patient rooms with doors)
    section_b_dxf_path = output_dir / "hospital_wing_section_B.dxf"
    exporter.export(section_b_result, str(section_b_dxf_path))
    print(f"  Saved: {section_b_dxf_path.name}")

    # Export section C DXF (through main corridor)
    section_c_dxf_path = output_dir / "hospital_wing_section_C.dxf"
    exporter.export(section_c_result, str(section_c_dxf_path))
    print(f"  Saved: {section_c_dxf_path.name}")

    # Create sheet with floor plan and section viewports
    print("\nCreating construction document sheet...")
    sheet = Sheet(
        size=SheetSize.ARCH_D,  # 24" x 36" architectural sheet
        number="A-101",
        name="Level 1 Floor Plan & Section",
        metadata=SheetMetadata(
            project="Hospital Wing",
            drawn_by="BIMasCode",
            date=datetime.now().strftime("%Y-%m-%d"),
            revision="A",
        ),
    )

    # Layout all 4 viewports on single sheet
    # ARCH_D is 609.6mm x 914.4mm (portrait), center X = 304.8
    # Layout:
    #   - Floor plan at top (centered)
    #   - Section C (corridor, horizontal) in middle (centered)
    #   - Sections A and B side by side at bottom

    # Floor plan viewport (top of sheet)
    sheet.add_viewport(
        result,
        position=(304.8, 730),  # Centered horizontally, top
        scale=ViewScale.SCALE_1_100,
        name="Floor Plan",
    )

    # Section C viewport (middle - long corridor section)
    sheet.add_viewport(
        section_c_result,
        position=(304.8, 420),  # Centered horizontally, middle
        scale=ViewScale.SCALE_1_100,
        name="Section C-C",
    )

    # Section A viewport (bottom left)
    sheet.add_viewport(
        section_result,
        position=(160, 150),  # Left side, bottom
        scale=ViewScale.SCALE_1_50,
        name="Section A-A",
    )

    # Section B viewport (bottom right)
    sheet.add_viewport(
        section_b_result,
        position=(450, 150),  # Right side, bottom
        scale=ViewScale.SCALE_1_50,
        name="Section B-B",
    )

    print(f"  Sheet: {sheet.number} - {sheet.name}")
    print(f"  Size: {sheet.size.name} ({sheet.size.width}mm x {sheet.size.height}mm)")
    print(f"  Viewports: {len(sheet.viewports)}")

    # Export sheet to DXF
    sheet_dxf_path = output_dir / "hospital_wing_sheet_A101.dxf"
    sheet.export_dxf(str(sheet_dxf_path))
    print(f"  Saved: {sheet_dxf_path.name}")

    # Export IFC
    print("\nExporting IFC...")
    ifc_path = output_dir / "hospital_wing.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path.name}")

    # Summary
    print("\n" + "=" * 70)
    print("Chain Dimension Usage Example")
    print("=" * 70)
    print("""
PROPER USE OF CHAIN DIMENSIONS:
- Room widths along south corridor wall (5 rooms + nurses station + 5 rooms)
- Room widths along north corridor wall (same pattern)

These are COLLINEAR points sharing a continuous baseline - exactly what
chain dimensions are designed for.

IMPROPER USE (not demonstrated):
- Radial distances from rooms to a central point (nurses station)
- Non-aligned measurements between scattered locations

For radial/scattered measurements, use individual LinearDimension2D instead.
""")

    print(f"\nOutput directory: {output_dir}")


if __name__ == "__main__":
    main()
