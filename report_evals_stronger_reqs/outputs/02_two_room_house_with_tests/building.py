"""
Eval 02: Two Room House

A small house with two rooms: a living room (6m x 5m) and a bedroom (4m x 5m).
The rooms share a wall. The living room has a large window (2m wide) on the south
wall and an entry door. The bedroom has a medium window on the north wall.
Exterior walls use brick finish (100mm) over concrete structure (150mm).
An interior door connects the two rooms.
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
)
from bimascode.architecture.wall_type import WallType
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.window_type import WindowType
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.architecture.wall_joins import (
    WallJoinDetector,
    WallJoinStyle,
    JoinType,
    join_walls,
)
from bimascode.utils.materials import MaterialLibrary
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.elevation_view import ElevationView, ElevationDirection
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.sheet import Sheet, SheetMetadata
from bimascode.drawing.sheet_sizes import SheetSize
from bimascode.drawing.title_block import TitleBlock, TitleBlockField
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.drawing.tags import RoomTag, DoorTag, WindowTag, TagStyle
from bimascode.drawing.primitives import TextNote2D, Point2D, TextAlignment
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.performance.representation_cache import RepresentationCache


# Building dimensions (mm)
LIVING_ROOM_WIDTH = 6000  # 6m
LIVING_ROOM_DEPTH = 5000  # 5m
BEDROOM_WIDTH = 4000  # 4m
BEDROOM_DEPTH = 5000  # 5m

# Total building dimensions
BUILDING_WIDTH = LIVING_ROOM_WIDTH + BEDROOM_WIDTH  # 10m total
BUILDING_DEPTH = 5000  # Both rooms share the same depth

# Heights
FLOOR_HEIGHT = 3000  # 3m floor-to-floor

# Wall thicknesses
EXTERIOR_WALL_THICKNESS = 250  # 100mm brick + 150mm concrete


def apply_wall_joins(walls, tolerance=50.0):
    """Join walls at corners and intersections."""
    for j in WallJoinDetector(list(walls), tolerance=tolerance).detect_joins():
        style = (
            WallJoinStyle.MITER if j.join_type == JoinType.L_JUNCTION
            else WallJoinStyle.BUTT
        )
        try:
            join_walls(style, j.wall_a, j.wall_b, tolerance=tolerance)
        except Exception:
            try:
                join_walls(WallJoinStyle.BUTT, j.wall_a, j.wall_b, tolerance=tolerance)
            except Exception:
                pass


def create_types():
    """Create all element types."""
    # Materials
    brick = MaterialLibrary.brick()
    concrete = MaterialLibrary.concrete()
    gypsum = MaterialLibrary.gypsum_board()

    # Exterior wall type: brick finish (100mm) over concrete structure (150mm)
    exterior_wall_type = WallType("Exterior Wall", function=WallFunction.EXTERIOR)
    exterior_wall_type.add_layer(brick, 100, LayerFunction.FINISH_EXTERIOR)
    exterior_wall_type.add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)

    # Interior wall type (shared wall between rooms)
    interior_wall_type = WallType("Interior Wall", function=WallFunction.INTERIOR)
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)
    interior_wall_type.add_layer(concrete, 100, LayerFunction.STRUCTURE)
    interior_wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)

    # Door types
    entry_door_type = DoorType(name="Entry Door", width=900, height=2100)
    interior_door_type = DoorType(name="Interior Door", width=800, height=2100)

    # Window types
    large_window_type = WindowType(
        name="Large Window",
        width=2000,  # 2m wide as specified
        height=1500,
        default_sill_height=900,
    )
    medium_window_type = WindowType(
        name="Medium Window",
        width=1200,
        height=1200,
        default_sill_height=1000,
    )

    # Floor type
    floor_type = FloorType("Concrete Floor")
    floor_type.add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)

    return {
        "exterior_wall": exterior_wall_type,
        "interior_wall": interior_wall_type,
        "entry_door": entry_door_type,
        "interior_door": interior_door_type,
        "large_window": large_window_type,
        "medium_window": medium_window_type,
        "floor": floor_type,
    }


def build():
    """Create and return the two room house building."""
    building = Building("Two Room House")
    level = Level(building, "Ground Floor", elevation=0)
    types = create_types()

    walls = []
    doors = []
    windows = []
    rooms = []

    ext_wall = types["exterior_wall"]
    int_wall = types["interior_wall"]

    # === EXTERIOR WALLS ===
    # Layout:
    # +--------+------+
    # |        |      |
    # | Living | Bed  |
    # | Room   | room |
    # |  6x5m  | 4x5m |
    # +--------+------+
    #
    # Living room is on the west (left), bedroom is on the east (right)
    # South wall is at Y=0, North wall is at Y=5000

    # South wall (runs west to east along Y=0)
    wall_south = Wall(
        ext_wall,
        (0, 0),
        (BUILDING_WIDTH, 0),
        level,
        name="Ext_South",
    )
    walls.append(wall_south)

    # East wall (runs south to north along X=BUILDING_WIDTH)
    wall_east = Wall(
        ext_wall,
        (BUILDING_WIDTH, 0),
        (BUILDING_WIDTH, BUILDING_DEPTH),
        level,
        name="Ext_East",
    )
    walls.append(wall_east)

    # North wall (runs east to west along Y=BUILDING_DEPTH)
    wall_north = Wall(
        ext_wall,
        (BUILDING_WIDTH, BUILDING_DEPTH),
        (0, BUILDING_DEPTH),
        level,
        name="Ext_North",
    )
    walls.append(wall_north)

    # West wall (runs north to south along X=0)
    wall_west = Wall(
        ext_wall,
        (0, BUILDING_DEPTH),
        (0, 0),
        level,
        name="Ext_West",
    )
    walls.append(wall_west)

    # === INTERIOR WALL (shared wall between living room and bedroom) ===
    # The interior wall runs north-south at X=LIVING_ROOM_WIDTH
    interior_wall = Wall(
        int_wall,
        (LIVING_ROOM_WIDTH, 0),
        (LIVING_ROOM_WIDTH, BUILDING_DEPTH),
        level,
        name="Interior_Wall",
    )
    walls.append(interior_wall)

    # Apply wall joins
    apply_wall_joins(walls)

    # === DOORS ===
    # Entry door on south wall (living room side)
    # Position: centered on living room with 300mm clearance from interior wall
    # Living room south wall runs from X=0 to X=6000
    # Door width = 900mm, center at X=3000
    entry_door_offset = (LIVING_ROOM_WIDTH / 2) - (types["entry_door"].width / 2)
    entry_door = Door(
        types["entry_door"],
        wall_south,
        offset=entry_door_offset,
        name="Entry_Door",
        mark="D-01",
    )
    doors.append(entry_door)

    # Interior door connecting the two rooms (in the shared interior wall)
    # Position: centered on the interior wall with clearance from edges
    # Wall runs from Y=0 to Y=5000, door at center
    interior_door_offset = (BUILDING_DEPTH / 2) - (types["interior_door"].width / 2)
    interior_door = Door(
        types["interior_door"],
        interior_wall,
        offset=interior_door_offset,
        name="Interior_Door",
        mark="D-02",
    )
    doors.append(interior_door)

    # === WINDOWS ===
    # Large window (2m wide) on south wall in living room
    # Position: 300mm clearance from west wall corner
    large_window_offset = 300  # 300mm clearance from west corner
    large_window = Window(
        types["large_window"],
        wall_south,
        offset=large_window_offset,
        name="Living_Window",
        mark="W-01",
    )
    windows.append(large_window)

    # Medium window on north wall in bedroom
    # Bedroom north wall runs from X=6000 to X=10000 (offset from wall start)
    # Wall_north runs from X=10000 to X=0 (east to west)
    # So bedroom portion is offset 0 to 4000 from wall start
    # Center window in bedroom: center at 2000mm from wall start
    medium_window_offset = (BEDROOM_WIDTH / 2) - (types["medium_window"].width / 2)
    medium_window = Window(
        types["medium_window"],
        wall_north,
        offset=medium_window_offset,
        name="Bedroom_Window",
        mark="W-02",
    )
    windows.append(medium_window)

    # === FLOOR ===
    floor_boundary = [
        (0, 0),
        (BUILDING_WIDTH, 0),
        (BUILDING_WIDTH, BUILDING_DEPTH),
        (0, BUILDING_DEPTH),
    ]
    floor = Floor(types["floor"], floor_boundary, level, name="Ground_Floor")

    # === ROOMS ===
    living_room = Room(
        name="Living Room",
        number="101",
        boundary=[
            (0, 0),
            (LIVING_ROOM_WIDTH, 0),
            (LIVING_ROOM_WIDTH, LIVING_ROOM_DEPTH),
            (0, LIVING_ROOM_DEPTH),
        ],
        level=level,
    )
    rooms.append(living_room)

    bedroom = Room(
        name="Bedroom",
        number="102",
        boundary=[
            (LIVING_ROOM_WIDTH, 0),
            (BUILDING_WIDTH, 0),
            (BUILDING_WIDTH, BEDROOM_DEPTH),
            (LIVING_ROOM_WIDTH, BEDROOM_DEPTH),
        ],
        level=level,
    )
    rooms.append(bedroom)

    return building, level, walls, doors, windows, [floor], rooms


def main():
    """Generate building and export to IFC, DXF, and PDF."""
    print("=" * 70)
    print("Two Room House - Building Generation")
    print("=" * 70)

    out_dir = Path(__file__).parent
    dxf_dir = out_dir / "dxf"
    dxf_dir.mkdir(parents=True, exist_ok=True)

    # Build the house
    print("\nCreating building...")
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

    # === Export IFC ===
    print("\nExporting IFC...")
    ifc_path = out_dir / "building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path.name}")

    # === Generate DXF drawings ===
    print("\nGenerating DXF drawings...")
    exporter = DXFExporter()

    # Floor plan
    print("  Floor plan...")
    view_range = ViewRange(cut_height=1200, top=FLOOR_HEIGHT, bottom=0, view_depth=0)
    floor_plan = FloorPlanView(
        name="Ground Floor Plan",
        level=level,
        view_range=view_range,
    )
    plan_result = floor_plan.generate(spatial_index, cache)

    # Add room tags
    room_style = TagStyle.room_default()
    for room in rooms:
        plan_result.room_tags.append(RoomTag(room=room, style=room_style))

    # Add door tags
    door_style = TagStyle.door_default()
    for door in doors:
        if door.mark:
            plan_result.door_tags.append(DoorTag(door=door, style=door_style))

    # Add window tags
    window_style = TagStyle.window_default()
    for window in windows:
        if window.mark:
            plan_result.window_tags.append(WindowTag(window=window, style=window_style))

    # Add title note
    plan_result.text_notes.append(
        TextNote2D(
            position=Point2D(-500, -1500),
            content="GROUND FLOOR PLAN\nScale: 1:100",
            height=150,
            alignment=TextAlignment.TOP_LEFT,
        )
    )

    plan_dxf = dxf_dir / "ground_floor_plan.dxf"
    exporter.export(plan_result, str(plan_dxf))
    print(f"    Saved: {plan_dxf.name}")

    # Elevations
    elevation_configs = [
        ("North Elevation", ElevationDirection.NORTH, "elevation_north.dxf"),
        ("South Elevation", ElevationDirection.SOUTH, "elevation_south.dxf"),
        ("East Elevation", ElevationDirection.EAST, "elevation_east.dxf"),
        ("West Elevation", ElevationDirection.WEST, "elevation_west.dxf"),
    ]

    elevation_results = []
    for name, direction, filename in elevation_configs:
        print(f"  {name}...")
        elevation = ElevationView(
            name=name,
            direction=direction,
            height_range=(0, FLOOR_HEIGHT),
            scale=ViewScale.SCALE_1_100,
        )
        result = elevation.generate(spatial_index, cache)
        elevation_results.append((name, result))
        elev_dxf = dxf_dir / filename
        exporter.export(result, str(elev_dxf))
        print(f"    Saved: {filename}")

    # Section (through the center, north-south)
    print("  Section A-A...")
    section_view = SectionView.from_section_line(
        name="Section A-A",
        start_point=(BUILDING_WIDTH / 2, BUILDING_DEPTH + 1000),
        end_point=(BUILDING_WIDTH / 2, -1000),
        look_direction="left",  # Looking west
        depth=BUILDING_WIDTH,
        height_range=(0, FLOOR_HEIGHT),
        scale=ViewScale.SCALE_1_50,
    )
    section_result = section_view.generate(spatial_index, cache)
    section_dxf = dxf_dir / "section_AA.dxf"
    exporter.export(section_result, str(section_dxf))
    print(f"    Saved: section_AA.dxf")

    # === Generate PDF drawing set (multi-page) ===
    print("\nGenerating PDF drawing set...")

    # Use matplotlib PdfPages for multi-page PDF
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from bimascode.drawing.pdf_exporter import PDFExporter

    pdf_path = out_dir / "02_two_room_house_drawing_set.pdf"
    pdf_exporter = PDFExporter()

    with PdfPages(str(pdf_path)) as pdf:
        # Page 1: Floor Plan
        print("  Page 1: Floor Plan...")
        sheet1 = Sheet(
            size=SheetSize.ARCH_D,
            number="A-101",
            name="Floor Plan",
            metadata=SheetMetadata(
                project="Two Room House",
                drawn_by="BIMasCode",
                date=datetime.now().strftime("%Y-%m-%d"),
                revision="A",
            ),
        )
        sheet1.add_viewport(
            plan_result,
            position=(304.8, 500),
            scale=ViewScale.SCALE_1_100,
            name="Ground Floor Plan",
        )
        title_block1 = TitleBlock.from_template(
            "standard_arch_d",
            fields={
                TitleBlockField.PROJECT_NAME.value: "Two Room House",
                TitleBlockField.SHEET_NAME.value: sheet1.name,
                TitleBlockField.SHEET_NUMBER.value: sheet1.number,
                TitleBlockField.DRAWN_BY.value: "BIMasCode",
                TitleBlockField.DATE.value: datetime.now().strftime("%Y-%m-%d"),
                TitleBlockField.SCALE.value: "1:100",
                TitleBlockField.REVISION.value: "A",
            },
            position=(sheet1.size.width - 200 - 10, 10),
        )
        sheet1.set_title_block(title_block1)

        # Render sheet1 to figure and add to PDF
        fig_width = sheet1.size.width / 25.4
        fig_height = sheet1.size.height / 25.4
        fig1, ax1 = plt.subplots(figsize=(fig_width, fig_height))
        ax1.set_aspect("equal")
        ax1.axis("off")
        ax1.set_xlim(0, sheet1.size.width)
        ax1.set_ylim(0, sheet1.size.height)
        fig1.patch.set_facecolor("white")
        ax1.set_facecolor("white")

        # Draw viewports
        for viewport in sheet1.viewports:
            view_result = viewport.view_result
            bounds = view_result.get_bounds()
            if bounds:
                model_center_x = (bounds[0] + bounds[2]) / 2
                model_center_y = (bounds[1] + bounds[3]) / 2
                scale = viewport.scale.ratio
                offset_x = viewport.position.x - model_center_x * scale
                offset_y = viewport.position.y - model_center_y * scale
                scaled_view = view_result.scale_and_translate(scale, offset_x, offset_y)
                pdf_exporter._draw_view_result(ax1, scaled_view, scale=1.0)

        # Draw title block
        if sheet1.title_block:
            full_geometry = sheet1.title_block.get_full_geometry()
            pdf_exporter._draw_view_result(ax1, full_geometry, scale=1.0)

        pdf.savefig(fig1, bbox_inches="tight", pad_inches=0)
        plt.close(fig1)

        # Page 2: Elevations
        print("  Page 2: Elevations...")
        sheet2 = Sheet(
            size=SheetSize.ARCH_D,
            number="A-201",
            name="Elevations",
            metadata=SheetMetadata(
                project="Two Room House",
                drawn_by="BIMasCode",
                date=datetime.now().strftime("%Y-%m-%d"),
                revision="A",
            ),
        )
        # Add all 4 elevations to the sheet
        y_positions = [650, 450, 250, 50]
        for i, (name, result) in enumerate(elevation_results):
            sheet2.add_viewport(
                result,
                position=(304.8, y_positions[i]),
                scale=ViewScale.SCALE_1_100,
                name=name,
            )
        title_block2 = TitleBlock.from_template(
            "standard_arch_d",
            fields={
                TitleBlockField.PROJECT_NAME.value: "Two Room House",
                TitleBlockField.SHEET_NAME.value: sheet2.name,
                TitleBlockField.SHEET_NUMBER.value: sheet2.number,
                TitleBlockField.DRAWN_BY.value: "BIMasCode",
                TitleBlockField.DATE.value: datetime.now().strftime("%Y-%m-%d"),
                TitleBlockField.SCALE.value: "1:100",
                TitleBlockField.REVISION.value: "A",
            },
            position=(sheet2.size.width - 200 - 10, 10),
        )
        sheet2.set_title_block(title_block2)

        fig2, ax2 = plt.subplots(figsize=(fig_width, fig_height))
        ax2.set_aspect("equal")
        ax2.axis("off")
        ax2.set_xlim(0, sheet2.size.width)
        ax2.set_ylim(0, sheet2.size.height)
        fig2.patch.set_facecolor("white")
        ax2.set_facecolor("white")

        for viewport in sheet2.viewports:
            view_result = viewport.view_result
            bounds = view_result.get_bounds()
            if bounds:
                model_center_x = (bounds[0] + bounds[2]) / 2
                model_center_y = (bounds[1] + bounds[3]) / 2
                scale = viewport.scale.ratio
                offset_x = viewport.position.x - model_center_x * scale
                offset_y = viewport.position.y - model_center_y * scale
                scaled_view = view_result.scale_and_translate(scale, offset_x, offset_y)
                pdf_exporter._draw_view_result(ax2, scaled_view, scale=1.0)

        if sheet2.title_block:
            full_geometry = sheet2.title_block.get_full_geometry()
            pdf_exporter._draw_view_result(ax2, full_geometry, scale=1.0)

        pdf.savefig(fig2, bbox_inches="tight", pad_inches=0)
        plt.close(fig2)

        # Page 3: Section
        print("  Page 3: Section...")
        sheet3 = Sheet(
            size=SheetSize.ARCH_D,
            number="A-301",
            name="Section",
            metadata=SheetMetadata(
                project="Two Room House",
                drawn_by="BIMasCode",
                date=datetime.now().strftime("%Y-%m-%d"),
                revision="A",
            ),
        )
        sheet3.add_viewport(
            section_result,
            position=(304.8, 400),
            scale=ViewScale.SCALE_1_50,
            name="Section A-A",
        )
        title_block3 = TitleBlock.from_template(
            "standard_arch_d",
            fields={
                TitleBlockField.PROJECT_NAME.value: "Two Room House",
                TitleBlockField.SHEET_NAME.value: sheet3.name,
                TitleBlockField.SHEET_NUMBER.value: sheet3.number,
                TitleBlockField.DRAWN_BY.value: "BIMasCode",
                TitleBlockField.DATE.value: datetime.now().strftime("%Y-%m-%d"),
                TitleBlockField.SCALE.value: "1:50",
                TitleBlockField.REVISION.value: "A",
            },
            position=(sheet3.size.width - 200 - 10, 10),
        )
        sheet3.set_title_block(title_block3)

        fig3, ax3 = plt.subplots(figsize=(fig_width, fig_height))
        ax3.set_aspect("equal")
        ax3.axis("off")
        ax3.set_xlim(0, sheet3.size.width)
        ax3.set_ylim(0, sheet3.size.height)
        fig3.patch.set_facecolor("white")
        ax3.set_facecolor("white")

        for viewport in sheet3.viewports:
            view_result = viewport.view_result
            bounds = view_result.get_bounds()
            if bounds:
                model_center_x = (bounds[0] + bounds[2]) / 2
                model_center_y = (bounds[1] + bounds[3]) / 2
                scale = viewport.scale.ratio
                offset_x = viewport.position.x - model_center_x * scale
                offset_y = viewport.position.y - model_center_y * scale
                scaled_view = view_result.scale_and_translate(scale, offset_x, offset_y)
                pdf_exporter._draw_view_result(ax3, scaled_view, scale=1.0)

        if sheet3.title_block:
            full_geometry = sheet3.title_block.get_full_geometry()
            pdf_exporter._draw_view_result(ax3, full_geometry, scale=1.0)

        pdf.savefig(fig3, bbox_inches="tight", pad_inches=0)
        plt.close(fig3)

    print(f"  Saved: {pdf_path.name} (3 pages)")

    # Summary
    print("\n" + "=" * 70)
    print("Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print(f"  IFC: {ifc_path.name}")
    print(f"  DXF: {dxf_dir.name}/")
    for f in sorted(dxf_dir.iterdir()):
        print(f"    - {f.name}")
    print(f"  PDF: {pdf_path.name}")

    print("\nBuilding summary:")
    print("  - Living Room: 6m x 5m with large window (2m) and entry door")
    print("  - Bedroom: 4m x 5m with medium window on north wall")
    print("  - Shared interior wall with connecting door")
    print("  - Exterior walls: brick (100mm) + concrete (150mm)")


def get_building():
    """Create and return the building for preview server compatibility."""
    building, level, walls, doors, windows, floors, rooms = build()
    return building


# Create building at module level for preview server
building = get_building()


if __name__ == "__main__":
    main()
