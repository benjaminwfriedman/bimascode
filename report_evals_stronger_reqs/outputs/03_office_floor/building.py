"""
Eval 03: Office Floor

A small office floor with reception, 3 private offices, open workspace, and corridor.
Overall dimensions: 20m x 12m
"""
from datetime import datetime
from pathlib import Path

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room import Room

from bimascode.architecture import (
    Wall,
    Door,
    Window,
    Floor,
    WallFunction,
    WallJoinStyle,
    create_basic_wall_type,
)
from bimascode.architecture.wall_joins import join_walls
from bimascode.architecture.door_type import DoorType, create_double_door_type
from bimascode.architecture.window_type import WindowType
from bimascode.architecture.floor_type import FloorType, LayerFunction

from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.elevation_view import ElevationView, ElevationDirection
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.sheet import Sheet, SheetMetadata
from bimascode.drawing.sheet_sizes import SheetSize
from bimascode.drawing.title_block import TitleBlock, TitleBlockField
from bimascode.drawing.primitives import Point2D, TextNote2D, TextAlignment
from bimascode.drawing.tags import DoorTag, WindowTag, RoomTag, TagStyle
from bimascode.drawing.view_base import ViewRange, ViewScale

from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex

from bimascode.utils.materials import MaterialLibrary


# Building dimensions (mm)
BUILDING_LENGTH = 20000  # 20m (X direction - East-West)
BUILDING_WIDTH = 12000   # 12m (Y direction - North-South)
FLOOR_HEIGHT = 3200      # Floor-to-floor height

# Layout dimensions
RECEPTION_WIDTH = 4000   # 4m
RECEPTION_DEPTH = 4000   # 4m
OFFICE_WIDTH = 4000      # 4m per office
OFFICE_DEPTH = 3000      # 3m depth
CORRIDOR_WIDTH = 1500    # 1.5m corridor


def create_types():
    """Create all element types."""
    concrete = MaterialLibrary.concrete()
    gypsum = MaterialLibrary.gypsum_board()

    # Exterior wall
    exterior_wall = create_basic_wall_type(
        "Exterior Wall", 200, concrete, function=WallFunction.EXTERIOR
    )

    # Interior partition
    interior_wall = create_basic_wall_type(
        "Interior Partition", 150, gypsum, function=WallFunction.INTERIOR
    )

    # Door types
    single_door = DoorType(name="Single Door", width=900, height=2100)
    double_door = create_double_door_type("Double Entry Door", width=1800, height=2100)

    # Window types - large windows for east/west facades
    large_window = WindowType(
        name="Large Window",
        width=1800,
        height=1500,
        default_sill_height=900,
    )

    # South facade glazing
    glazing_window = WindowType(
        name="Glazing Panel",
        width=2000,
        height=2000,
        default_sill_height=300,
    )

    # Floor slab
    floor_type = FloorType("Concrete Floor")
    floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

    return {
        "exterior_wall": exterior_wall,
        "interior_wall": interior_wall,
        "single_door": single_door,
        "double_door": double_door,
        "large_window": large_window,
        "glazing_window": glazing_window,
        "floor": floor_type,
    }


def build():
    """Create the office floor building."""
    building = Building("Small Office Floor")
    level = Level(building, "Ground Floor", elevation=0)
    types = create_types()

    all_walls = []
    all_doors = []
    all_windows = []
    all_rooms = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # ==========================================================================
    # EXTERIOR WALLS - 20m x 12m building envelope
    # ==========================================================================

    # South wall (Y=0, runs west to east)
    wall_south = Wall(
        ext_wall,
        (0, 0),
        (BUILDING_LENGTH, 0),
        level,
        name="Ext_South",
    )
    all_walls.append(wall_south)

    # East wall (X=20000, runs south to north)
    wall_east = Wall(
        ext_wall,
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        level,
        name="Ext_East",
    )
    all_walls.append(wall_east)

    # North wall (Y=12000, runs east to west)
    wall_north = Wall(
        ext_wall,
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
        level,
        name="Ext_North",
    )
    all_walls.append(wall_north)

    # West wall (X=0, runs north to south)
    wall_west = Wall(
        ext_wall,
        (0, BUILDING_WIDTH),
        (0, 0),
        level,
        name="Ext_West",
    )
    all_walls.append(wall_west)

    # Exterior corner joins (MITER for clean diagonal corners)
    join_walls(WallJoinStyle.MITER, wall_south, wall_west)
    join_walls(WallJoinStyle.MITER, wall_south, wall_east)
    join_walls(WallJoinStyle.MITER, wall_east, wall_north)
    join_walls(WallJoinStyle.MITER, wall_north, wall_west)

    # ==========================================================================
    # MAIN ENTRANCE - Double door on south wall (1.8m wide)
    # ==========================================================================
    # Center the door: (20000 - 1800) / 2 = 9100
    main_entry = Door(
        types["double_door"],
        wall_south,
        offset=9100,  # Centered on south wall
        name="Main_Entry",
        mark="D-01",
    )
    all_doors.append(main_entry)

    # ==========================================================================
    # SOUTH FACADE GLAZING - Windows with at least 300mm clearance
    # ==========================================================================
    # Door at offset 9100, width 1800, so occupies 9100-10900
    # Windows need 300mm clearance from door and corners

    # Glazing windows on south facade (left of door)
    south_glazing_1 = Window(
        types["glazing_window"],
        wall_south,
        offset=1500,  # 1500mm from west corner (> 300mm clearance)
        name="Glazing_S1",
        mark="W-01",
    )
    all_windows.append(south_glazing_1)

    south_glazing_2 = Window(
        types["glazing_window"],
        wall_south,
        offset=4500,  # Another panel, > 300mm from first (ends at 3500)
        name="Glazing_S2",
        mark="W-02",
    )
    all_windows.append(south_glazing_2)

    # Skip around door (9100 - 10900)

    south_glazing_3 = Window(
        types["glazing_window"],
        wall_south,
        offset=12000,  # After door, > 300mm clearance from door end (10900)
        name="Glazing_S3",
        mark="W-03",
    )
    all_windows.append(south_glazing_3)

    south_glazing_4 = Window(
        types["glazing_window"],
        wall_south,
        offset=15000,  # Another panel, > 300mm from previous
        name="Glazing_S4",
        mark="W-04",
    )
    all_windows.append(south_glazing_4)

    # ==========================================================================
    # LARGE WINDOWS ON EAST AND WEST WALLS
    # ==========================================================================
    # East wall is 12m long (12000mm). Large windows 1800mm wide.
    # At least 300mm from corners and 300mm between windows.

    east_win_1 = Window(
        types["large_window"],
        wall_east,
        offset=1500,  # Near south corner but > 300mm
        name="Win_E1",
        mark="W-05",
    )
    all_windows.append(east_win_1)

    east_win_2 = Window(
        types["large_window"],
        wall_east,
        offset=5000,  # Middle area
        name="Win_E2",
        mark="W-06",
    )
    all_windows.append(east_win_2)

    east_win_3 = Window(
        types["large_window"],
        wall_east,
        offset=8500,  # Near north but > 300mm from end
        name="Win_E3",
        mark="W-07",
    )
    all_windows.append(east_win_3)

    # West wall runs from (0, 12000) to (0, 0)
    # Offset 0 is at Y=12000 (north), increasing offset moves toward Y=0 (south)
    west_win_1 = Window(
        types["large_window"],
        wall_west,
        offset=1500,  # Near north corner
        name="Win_W1",
        mark="W-08",
    )
    all_windows.append(west_win_1)

    west_win_2 = Window(
        types["large_window"],
        wall_west,
        offset=5000,  # Middle
        name="Win_W2",
        mark="W-09",
    )
    all_windows.append(west_win_2)

    west_win_3 = Window(
        types["large_window"],
        wall_west,
        offset=8500,  # Near south corner
        name="Win_W3",
        mark="W-10",
    )
    all_windows.append(west_win_3)

    # ==========================================================================
    # INTERIOR LAYOUT - Reception, Corridor, Private Offices, Open Workspace
    # ==========================================================================
    # Layout:
    # - Reception: Near entrance (south-west), 4m x 4m
    # - Corridor: Runs east-west connecting reception to open workspace, 1.5m wide
    # - Private offices: 3 offices (4m x 3m each) along north wall
    # - Open workspace: Remaining area in the east portion

    # Corridor Y positions
    corridor_south_y = RECEPTION_DEPTH
    corridor_north_y = RECEPTION_DEPTH + CORRIDOR_WIDTH

    # Offices are along north wall
    office_south_y = BUILDING_WIDTH - OFFICE_DEPTH

    # ==========================================================================
    # RECEPTION AREA (4m x 4m at southwest corner)
    # ==========================================================================
    # Reception east wall (from Y=0 to Y=corridor_south_y at X=RECEPTION_WIDTH)
    reception_east_wall = Wall(
        int_wall,
        (RECEPTION_WIDTH, 0),
        (RECEPTION_WIDTH, corridor_south_y),
        level,
        name="Reception_East",
    )
    all_walls.append(reception_east_wall)

    # Join reception wall to exterior
    join_walls(WallJoinStyle.BUTT, reception_east_wall, wall_south)

    # Reception room
    reception_room = Room(
        name="Reception",
        number="001",
        boundary=[
            (0, 0),
            (RECEPTION_WIDTH, 0),
            (RECEPTION_WIDTH, corridor_south_y),
            (0, corridor_south_y),
        ],
        level=level,
    )
    all_rooms.append(reception_room)

    # ==========================================================================
    # CORRIDOR - Connecting reception to offices and open workspace
    # ==========================================================================
    # Corridor south wall from reception to east exterior
    corridor_wall_south = Wall(
        int_wall,
        (RECEPTION_WIDTH, corridor_south_y),
        (BUILDING_LENGTH, corridor_south_y),
        level,
        name="Corridor_South",
    )
    all_walls.append(corridor_wall_south)

    # Joins
    join_walls(WallJoinStyle.BUTT, reception_east_wall, corridor_wall_south)
    join_walls(WallJoinStyle.BUTT, corridor_wall_south, wall_east)

    # North corridor wall (separates corridor from office zone)
    corridor_wall_north = Wall(
        int_wall,
        (0, corridor_north_y),
        (BUILDING_LENGTH, corridor_north_y),
        level,
        name="Corridor_North",
    )
    all_walls.append(corridor_wall_north)

    # Join corridor north wall to exteriors
    join_walls(WallJoinStyle.BUTT, corridor_wall_north, wall_west)
    join_walls(WallJoinStyle.BUTT, corridor_wall_north, wall_east)

    # Corridor room
    corridor_room = Room(
        name="Corridor",
        number="CORR",
        boundary=[
            (0, corridor_south_y),
            (BUILDING_LENGTH, corridor_south_y),
            (BUILDING_LENGTH, corridor_north_y),
            (0, corridor_north_y),
        ],
        level=level,
    )
    all_rooms.append(corridor_room)

    # ==========================================================================
    # PRIVATE OFFICES - 3 offices (4m x 3m) along north wall
    # ==========================================================================
    # Offices run from Y = office_south_y (9000) to Y = BUILDING_WIDTH (12000)
    # Each office is 4m wide (4000mm)
    # Offices start from the west side

    # Wall at office southern boundary
    office_corridor_wall = Wall(
        int_wall,
        (0, office_south_y),
        (3 * OFFICE_WIDTH, office_south_y),  # Only spans the 3 offices (12000mm)
        level,
        name="Office_Corridor_South",
    )
    all_walls.append(office_corridor_wall)

    # Join to west exterior
    join_walls(WallJoinStyle.BUTT, office_corridor_wall, wall_west)

    # Create partitions between offices and doors to corridor
    for i in range(3):
        office_x_start = i * OFFICE_WIDTH
        office_x_end = (i + 1) * OFFICE_WIDTH

        # Partition wall between offices (except for first office - west wall serves)
        if i > 0:
            partition = Wall(
                int_wall,
                (office_x_start, office_south_y),
                (office_x_start, BUILDING_WIDTH),
                level,
                name=f"Office_Partition_{i}",
            )
            all_walls.append(partition)
            # Join partition to office corridor wall and north exterior
            join_walls(WallJoinStyle.BUTT, partition, office_corridor_wall)
            join_walls(WallJoinStyle.BUTT, partition, wall_north)

        # Door from corridor to office (on office_corridor_wall)
        # Door centered in each office: offset from start of wall
        door_offset = office_x_start + (OFFICE_WIDTH - types["single_door"].width) / 2
        office_door = Door(
            types["single_door"],
            office_corridor_wall,
            offset=door_offset,
            name=f"Office_{i+1}_Door",
            mark=f"D-0{i+2}",
        )
        all_doors.append(office_door)

        # Office room
        office_room = Room(
            name=f"Office {i+1}",
            number=f"10{i+1}",
            boundary=[
                (office_x_start, office_south_y),
                (office_x_end, office_south_y),
                (office_x_end, BUILDING_WIDTH),
                (office_x_start, BUILDING_WIDTH),
            ],
            level=level,
        )
        all_rooms.append(office_room)

    # Wall at east end of office zone (separates offices from open workspace)
    office_east_wall = Wall(
        int_wall,
        (3 * OFFICE_WIDTH, office_south_y),
        (3 * OFFICE_WIDTH, BUILDING_WIDTH),
        level,
        name="Office_East",
    )
    all_walls.append(office_east_wall)

    # Join office east wall
    join_walls(WallJoinStyle.BUTT, office_east_wall, office_corridor_wall)
    join_walls(WallJoinStyle.BUTT, office_east_wall, wall_north)

    # ==========================================================================
    # OPEN WORKSPACE - Remaining area
    # ==========================================================================
    open_workspace_room = Room(
        name="Open Workspace",
        number="200",
        boundary=[
            (3 * OFFICE_WIDTH, corridor_north_y),
            (BUILDING_LENGTH, corridor_north_y),
            (BUILDING_LENGTH, BUILDING_WIDTH),
            (3 * OFFICE_WIDTH, BUILDING_WIDTH),
        ],
        level=level,
    )
    all_rooms.append(open_workspace_room)

    # ==========================================================================
    # FLOOR SLAB
    # ==========================================================================
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["floor"], floor_boundary, level, name="Floor_G")

    return building, level, all_walls, all_doors, all_windows, [floor], all_rooms


def create_drawing_sheet(name, number, view_result, scale=ViewScale.SCALE_1_100):
    """Create a single sheet with one viewport."""
    sheet = Sheet(
        size=SheetSize.ARCH_D,
        number=number,
        name=name,
        metadata=SheetMetadata(
            project="Small Office Floor",
            drawn_by="BIMasCode",
            date=datetime.now().strftime("%Y-%m-%d"),
            revision="A",
        ),
    )

    # Add viewport
    sheet.add_viewport(
        view_result,
        position=(450, 500),
        scale=scale,
        name=name,
    )

    # Add title block
    title_block = TitleBlock.from_template(
        "standard_arch_d",
        fields={
            TitleBlockField.PROJECT_NAME.value: "Small Office Floor",
            TitleBlockField.PROJECT_ADDRESS.value: "Office Building",
            TitleBlockField.CLIENT_NAME.value: "Client",
            TitleBlockField.SHEET_NAME.value: name,
            TitleBlockField.SHEET_NUMBER.value: number,
            TitleBlockField.DRAWN_BY.value: "BIMasCode",
            TitleBlockField.CHECKED_BY.value: "QA",
            TitleBlockField.DATE.value: datetime.now().strftime("%Y-%m-%d"),
            TitleBlockField.SCALE.value: "1:100",
            TitleBlockField.REVISION.value: "A",
        },
        position=(
            sheet.size.width - 200 - 10,
            10,
        ),
    )
    sheet.set_title_block(title_block)

    return sheet


def main():
    """Generate the office floor and export all outputs."""
    print("=" * 70)
    print("Eval 03: Office Floor (with tests)")
    print("=" * 70)

    # Output directory
    out_dir = Path(__file__).parent
    dxf_dir = out_dir / "dxf"
    dxf_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nOutput directory: {out_dir}")

    # Create building
    print("\nCreating office floor...")
    building, level, walls, doors, windows, floors, rooms = build()

    print(f"  Walls: {len(walls)}")
    print(f"  Doors: {len(doors)}")
    print(f"  Windows: {len(windows)}")
    print(f"  Rooms: {len(rooms)}")

    # Create spatial index
    spatial_index = SpatialIndex()
    for elem in walls + doors + windows + floors:
        spatial_index.insert(elem)

    cache = RepresentationCache()
    exporter = DXFExporter()

    # ==========================================================================
    # FLOOR PLAN
    # ==========================================================================
    print("\nGenerating floor plan...")
    view_range = ViewRange(cut_height=1200, top=FLOOR_HEIGHT, bottom=0, view_depth=0)
    floor_plan = FloorPlanView(
        name="Ground Floor Plan",
        level=level,
        view_range=view_range,
    )
    floor_plan_result = floor_plan.generate(spatial_index, cache)

    # Add door tags
    door_style = TagStyle(size=600.0, text_height=150.0)
    for door in doors:
        if door.mark:
            floor_plan_result.door_tags.append(DoorTag(door=door, style=door_style))

    # Add window tags
    window_style = TagStyle.window_default()
    for window in windows:
        if window.mark:
            floor_plan_result.window_tags.append(WindowTag(window=window, style=window_style))

    # Add room tags
    room_style = TagStyle.room_default()
    for room in rooms:
        floor_plan_result.room_tags.append(RoomTag(room=room, style=room_style))

    # Title note
    floor_plan_result.text_notes.append(
        TextNote2D(
            position=Point2D(-500, -2000),
            content="GROUND FLOOR PLAN\nScale: 1:100",
            height=150,
            alignment=TextAlignment.TOP_LEFT,
            width=3000,
        )
    )

    print(f"  Elements: {floor_plan_result.element_count}")
    print(f"  Geometry: {floor_plan_result.total_geometry_count}")

    # Export floor plan DXF
    floor_plan_dxf = dxf_dir / "ground_floor_plan.dxf"
    exporter.export(floor_plan_result, str(floor_plan_dxf))
    print(f"  Saved: {floor_plan_dxf.name}")

    # ==========================================================================
    # ELEVATIONS
    # ==========================================================================
    print("\nGenerating elevations...")

    # North Elevation
    north_elev = ElevationView(
        name="North Elevation",
        direction=ElevationDirection.NORTH,
        height_range=(0, FLOOR_HEIGHT),
        front_clip_depth=1000,
    )
    north_elev_result = north_elev.generate(spatial_index, cache)
    north_elev_dxf = dxf_dir / "elevation_north.dxf"
    exporter.export(north_elev_result, str(north_elev_dxf))
    print(f"  North Elevation: {north_elev_result.element_count} elements")

    # South Elevation
    south_elev = ElevationView(
        name="South Elevation",
        direction=ElevationDirection.SOUTH,
        height_range=(0, FLOOR_HEIGHT),
        front_clip_depth=1000,
    )
    south_elev_result = south_elev.generate(spatial_index, cache)
    south_elev_dxf = dxf_dir / "elevation_south.dxf"
    exporter.export(south_elev_result, str(south_elev_dxf))
    print(f"  South Elevation: {south_elev_result.element_count} elements")

    # East Elevation
    east_elev = ElevationView(
        name="East Elevation",
        direction=ElevationDirection.EAST,
        height_range=(0, FLOOR_HEIGHT),
        front_clip_depth=1000,
    )
    east_elev_result = east_elev.generate(spatial_index, cache)
    east_elev_dxf = dxf_dir / "elevation_east.dxf"
    exporter.export(east_elev_result, str(east_elev_dxf))
    print(f"  East Elevation: {east_elev_result.element_count} elements")

    # West Elevation
    west_elev = ElevationView(
        name="West Elevation",
        direction=ElevationDirection.WEST,
        height_range=(0, FLOOR_HEIGHT),
        front_clip_depth=1000,
    )
    west_elev_result = west_elev.generate(spatial_index, cache)
    west_elev_dxf = dxf_dir / "elevation_west.dxf"
    exporter.export(west_elev_result, str(west_elev_dxf))
    print(f"  West Elevation: {west_elev_result.element_count} elements")

    # ==========================================================================
    # SECTION
    # ==========================================================================
    print("\nGenerating section...")

    # Section through the middle of the building (north-south cut)
    section_x = BUILDING_LENGTH / 2  # Cut at X = 10000
    section = SectionView.from_section_line(
        name="Section A-A",
        start_point=(section_x, BUILDING_WIDTH + 1000),
        end_point=(section_x, -1000),
        look_direction="right",  # Looking west
        depth=BUILDING_LENGTH / 2,
        height_range=(0, FLOOR_HEIGHT),
        scale=ViewScale.SCALE_1_100,
    )
    section_result = section.generate(spatial_index, cache)
    section_dxf = dxf_dir / "section_AA.dxf"
    exporter.export(section_result, str(section_dxf))
    print(f"  Section A-A: {section_result.element_count} elements")

    # ==========================================================================
    # PDF DRAWING SET - Create sheets for all views (at least 6 pages)
    # ==========================================================================
    print("\nCreating PDF drawing set...")

    from bimascode.drawing.pdf_exporter import PDFExporter
    import fitz  # PyMuPDF for combining PDFs

    pdf_exporter = PDFExporter()
    temp_pdfs = []

    # Sheet 1: Floor Plan (A-101)
    sheet1 = create_drawing_sheet("Ground Floor Plan", "A-101", floor_plan_result)
    sheet1_pdf = out_dir / "temp_A101.pdf"
    sheet1.export_pdf(str(sheet1_pdf))
    temp_pdfs.append(sheet1_pdf)

    # Sheet 2: North Elevation (A-201)
    sheet2 = create_drawing_sheet("North Elevation", "A-201", north_elev_result)
    sheet2_pdf = out_dir / "temp_A201.pdf"
    sheet2.export_pdf(str(sheet2_pdf))
    temp_pdfs.append(sheet2_pdf)

    # Sheet 3: South Elevation (A-202)
    sheet3 = create_drawing_sheet("South Elevation", "A-202", south_elev_result)
    sheet3_pdf = out_dir / "temp_A202.pdf"
    sheet3.export_pdf(str(sheet3_pdf))
    temp_pdfs.append(sheet3_pdf)

    # Sheet 4: East Elevation (A-203)
    sheet4 = create_drawing_sheet("East Elevation", "A-203", east_elev_result)
    sheet4_pdf = out_dir / "temp_A203.pdf"
    sheet4.export_pdf(str(sheet4_pdf))
    temp_pdfs.append(sheet4_pdf)

    # Sheet 5: West Elevation (A-204)
    sheet5 = create_drawing_sheet("West Elevation", "A-204", west_elev_result)
    sheet5_pdf = out_dir / "temp_A204.pdf"
    sheet5.export_pdf(str(sheet5_pdf))
    temp_pdfs.append(sheet5_pdf)

    # Sheet 6: Section (A-301)
    sheet6 = create_drawing_sheet("Section A-A", "A-301", section_result)
    sheet6_pdf = out_dir / "temp_A301.pdf"
    sheet6.export_pdf(str(sheet6_pdf))
    temp_pdfs.append(sheet6_pdf)

    # Combine all PDFs into one drawing set
    pdf_path = out_dir / "03_office_floor_drawing_set.pdf"
    combined_pdf = fitz.open()
    for temp_pdf in temp_pdfs:
        doc = fitz.open(temp_pdf)
        combined_pdf.insert_pdf(doc)
        doc.close()
    combined_pdf.save(str(pdf_path))
    combined_pdf.close()

    # Clean up temp files
    for temp_pdf in temp_pdfs:
        temp_pdf.unlink()

    print(f"  Saved: {pdf_path.name} ({len(temp_pdfs)} pages)")

    # ==========================================================================
    # IFC EXPORT
    # ==========================================================================
    print("\nExporting IFC...")
    ifc_path = out_dir / "building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path.name}")

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 70)
    print("Export Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print(f"  - {ifc_path.name}")
    print(f"  - {pdf_path.name}")
    print("  - dxf/ground_floor_plan.dxf")
    print("  - dxf/elevation_north.dxf")
    print("  - dxf/elevation_south.dxf")
    print("  - dxf/elevation_east.dxf")
    print("  - dxf/elevation_west.dxf")
    print("  - dxf/section_AA.dxf")

    print("\nBuilding summary:")
    print("  - Overall: 20m x 12m")
    print("  - Reception: 4m x 4m near entrance")
    print("  - 3 Private offices: 4m x 3m each along north wall")
    print("  - Open workspace: Remaining area")
    print("  - Corridor connecting all spaces")
    print("  - Main entrance: 1.8m double door on south wall")
    print("  - Large windows on east and west facades")
    print("  - Glazing panels on south facade")


if __name__ == "__main__":
    main()
