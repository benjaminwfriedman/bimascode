"""
Eval 05: Structural Grid Building

A warehouse-style building with exposed structure:
- Dimensions: 24m x 18m
- Structural grid: 6m x 6m (4 bays x 3 bays)
- Steel columns (400mm square) at each grid intersection
- Main beams spanning in X direction (300mm x 500mm)
- Secondary beams in Y direction (200mm x 400mm)
- Concrete exterior walls (200mm)
- Large loading door on south wall (4m wide x 4m high)
- Regular doors on east and west walls
- Clerestory windows along north wall (4 windows, each 2m wide)
"""
from datetime import datetime
from pathlib import Path

from bimascode.architecture import (
    Door,
    EndCapType,
    Floor,
    Wall,
    WallFunction,
    Window,
    detect_and_process_wall_joins,
)
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.floor_type import FloorType, LayerFunction
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
from bimascode.structure import (
    Beam,
    StructuralColumn,
    create_rectangular_beam_type,
    create_square_column_type,
)
from bimascode.utils.materials import MaterialLibrary

# Building dimensions (mm)
BUILDING_LENGTH = 24000  # 24m in X direction
BUILDING_WIDTH = 18000   # 18m in Y direction
FLOOR_HEIGHT = 6000      # 6m floor to ceiling for warehouse

# Structural grid (6m x 6m)
GRID_SPACING = 6000  # 6m
GRID_X = [0, 6000, 12000, 18000, 24000]  # 5 grid lines (4 bays)
GRID_Y = [0, 6000, 12000, 18000]          # 4 grid lines (3 bays)

# Element dimensions
COLUMN_SIZE = 400        # 400mm square
MAIN_BEAM_WIDTH = 300    # 300mm wide
MAIN_BEAM_HEIGHT = 500   # 500mm deep
SEC_BEAM_WIDTH = 200     # 200mm wide
SEC_BEAM_HEIGHT = 400    # 400mm deep
WALL_THICKNESS = 200     # 200mm concrete walls


def create_types():
    """Create all element types."""
    concrete = MaterialLibrary.concrete()
    steel = MaterialLibrary.steel()

    # Concrete exterior wall (200mm)
    exterior_wall_type = WallType("Exterior Wall - Concrete", function=WallFunction.EXTERIOR)
    exterior_wall_type.add_layer(concrete, WALL_THICKNESS, LayerFunction.STRUCTURE, structural=True)

    # Loading door (4m x 4m)
    loading_door_type = DoorType(name="Loading Door", width=4000, height=4000)

    # Regular doors (900mm x 2100mm)
    regular_door_type = DoorType(name="Regular Door", width=900, height=2100)

    # Clerestory windows (2m wide x 1.5m high, high sill)
    clerestory_window_type = WindowType(
        name="Clerestory Window",
        width=2000,
        height=1500,
        default_sill_height=4000,  # High sill for clerestory
    )

    # Floor slab
    floor_type = FloorType("Concrete Floor")
    floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

    # Structural elements
    column_type = create_square_column_type("Steel Column", size=COLUMN_SIZE, material=steel)
    main_beam_type = create_rectangular_beam_type(
        "Main Beam", width=MAIN_BEAM_WIDTH, height=MAIN_BEAM_HEIGHT, material=steel
    )
    secondary_beam_type = create_rectangular_beam_type(
        "Secondary Beam", width=SEC_BEAM_WIDTH, height=SEC_BEAM_HEIGHT, material=steel
    )

    return {
        "exterior_wall": exterior_wall_type,
        "loading_door": loading_door_type,
        "regular_door": regular_door_type,
        "clerestory_window": clerestory_window_type,
        "floor": floor_type,
        "column": column_type,
        "main_beam": main_beam_type,
        "secondary_beam": secondary_beam_type,
    }


def create_structural_grid(level, types):
    """Create columns and beams for the warehouse."""
    columns = []
    beams = []

    column_type = types["column"]
    main_beam = types["main_beam"]
    secondary_beam = types["secondary_beam"]

    # Columns at all grid intersections (5 x 4 = 20 columns)
    for i, x in enumerate(GRID_X):
        for j, y in enumerate(GRID_Y):
            col = StructuralColumn(
                column_type,
                level,
                position=(x, y),
                height=FLOOR_HEIGHT,
                rotation=0,
                name=f"Col_{chr(65+i)}{j+1}",
            )
            columns.append(col)

    # Main beams in X direction (along each Y gridline)
    beam_z = FLOOR_HEIGHT - MAIN_BEAM_HEIGHT / 2
    for j, y in enumerate(GRID_Y):
        for i in range(len(GRID_X) - 1):
            beam = Beam(
                main_beam,
                level,
                start_point=(GRID_X[i], y, beam_z),
                end_point=(GRID_X[i + 1], y, beam_z),
                name=f"MainBeam_X_{chr(65+i)}{j+1}",
            )
            beams.append(beam)

    # Secondary beams in Y direction (along each X gridline)
    sec_beam_z = beam_z - MAIN_BEAM_HEIGHT / 2 - SEC_BEAM_HEIGHT / 2
    for i, x in enumerate(GRID_X):
        for j in range(len(GRID_Y) - 1):
            beam = Beam(
                secondary_beam,
                level,
                start_point=(x, GRID_Y[j], sec_beam_z),
                end_point=(x, GRID_Y[j + 1], sec_beam_z),
                name=f"SecBeam_Y_{chr(65+i)}{j+1}",
            )
            beams.append(beam)

    return columns, beams


def create_building_envelope(level, types):
    """Create exterior walls, doors, and windows."""
    walls = []
    doors = []
    windows = []

    ext_wall = types["exterior_wall"]

    # Exterior walls (height matches floor height so walls reach beams)
    wall_south = Wall(
        ext_wall, (0, 0), (BUILDING_LENGTH, 0), level, height=FLOOR_HEIGHT, name="Ext_South"
    )
    wall_east = Wall(
        ext_wall, (BUILDING_LENGTH, 0), (BUILDING_LENGTH, BUILDING_WIDTH), level,
        height=FLOOR_HEIGHT, name="Ext_East"
    )
    wall_north = Wall(
        ext_wall, (BUILDING_LENGTH, BUILDING_WIDTH), (0, BUILDING_WIDTH), level,
        height=FLOOR_HEIGHT, name="Ext_North"
    )
    wall_west = Wall(
        ext_wall, (0, BUILDING_WIDTH), (0, 0), level, height=FLOOR_HEIGHT, name="Ext_West"
    )
    walls.extend([wall_south, wall_east, wall_north, wall_west])

    # Loading door on south wall (4m x 4m)
    # Columns are at X = 0, 6000, 12000, 18000, 24000 (400mm square)
    # Center door in bay 6000-12000: bay center is 9000
    # Door width ~4100mm, so offset = 9000 - 2050 = 6950 ≈ 7000
    # Door spans 7000-11100, geometrically clear of columns at 6000 and 12000
    loading_door = Door(
        types["loading_door"],
        wall_south,
        offset=7000,  # Geometrically centered in bay
        name="Loading_Door",
        mark="D-01",
    )
    doors.append(loading_door)

    # Regular door on east wall
    # Ensure 300mm clearance from corners
    # Wall runs from Y=0 to Y=18000, door width 900mm
    # Place door at Y=3000 (well clear of corner at Y=0)
    east_door = Door(
        types["regular_door"],
        wall_east,
        offset=3000,  # 3m from south corner
        name="East_Door",
        mark="D-02",
    )
    doors.append(east_door)

    # Regular door on west wall
    # Wall runs from Y=18000 to Y=0 (direction matters for offset)
    # Place door at offset 3000 from start (Y=18000 side), so door is near north end
    west_door = Door(
        types["regular_door"],
        wall_west,
        offset=3000,  # 3m from north corner
        name="West_Door",
        mark="D-03",
    )
    doors.append(west_door)

    # 4 clerestory windows on north wall (each 2m wide)
    # North wall runs from X=24000 to X=0 (direction matters)
    # Wall length 24m, 4 windows of 2m each = 8m total
    # Remaining space: 16m, distribute evenly
    # Start first window at offset to ensure 300mm clearance from corner
    # Window spacing: (24000 - 4*2000 - 2*300) / 3 = (24000 - 8000 - 600) / 3 = 5133mm between windows
    # Or simpler: place at grid bay centers for industrial look
    # Place windows centered between grid lines
    # Grid X = 0, 6000, 12000, 18000, 24000
    # Window centers at: 3000, 9000, 15000, 21000 (centers of each bay)
    # Since north wall goes from X=24000 to X=0, offset is from X=24000
    # Window center at X=21000 -> offset = 24000 - 21000 - 1000 = 2000
    # Window center at X=15000 -> offset = 24000 - 15000 - 1000 = 8000
    # Window center at X=9000 -> offset = 24000 - 9000 - 1000 = 14000
    # Window center at X=3000 -> offset = 24000 - 3000 - 1000 = 20000
    window_width = types["clerestory_window"].width
    bay_centers = [3000, 9000, 15000, 21000]  # X positions of bay centers
    for i, center_x in enumerate(bay_centers):
        # North wall runs from (24000, 18000) to (0, 18000)
        # Offset is distance from start point (24000, 18000)
        offset = BUILDING_LENGTH - center_x - window_width / 2
        win = Window(
            types["clerestory_window"],
            wall_north,
            offset=offset,
            name=f"Clerestory_Window_{i+1}",
            mark=f"W-{i+1:02d}",
        )
        windows.append(win)

    return walls, doors, windows


def build():
    """Create the warehouse building."""
    building = Building("Structural Grid Warehouse")
    types = create_types()

    # Create level
    level = Level(building, "Ground Floor", elevation=0)

    # Create structural grid
    columns, beams = create_structural_grid(level, types)

    # Create building envelope
    walls, doors, windows = create_building_envelope(level, types)

    # Process wall joins
    adjustments = detect_and_process_wall_joins(walls, end_cap_type=EndCapType.EXTERIOR)
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj

    # Create floor slab
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["floor"], floor_boundary, level, name="Floor_Slab")

    return building


def main():
    """Create building and export all outputs."""
    print("=" * 70)
    print("Eval 05: Structural Grid Building")
    print("=" * 70)

    out_dir = Path(__file__).parent
    dxf_dir = out_dir / "dxf"
    dxf_dir.mkdir(parents=True, exist_ok=True)

    # Create building
    print("\nCreating building...")
    building = Building("Structural Grid Warehouse")
    types = create_types()

    # Create level
    level = Level(building, "Ground Floor", elevation=0)

    # Create structural grid
    print("  Creating structural grid (5x4 columns, beams)...")
    columns, beams = create_structural_grid(level, types)

    # Create building envelope
    print("  Creating building envelope (walls, doors, windows)...")
    walls, doors, windows = create_building_envelope(level, types)

    # Process wall joins
    print("  Processing wall joins...")
    adjustments = detect_and_process_wall_joins(walls, end_cap_type=EndCapType.EXTERIOR)
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj

    # Create floor slab
    floor_boundary = [
        (0, 0),
        (BUILDING_LENGTH, 0),
        (BUILDING_LENGTH, BUILDING_WIDTH),
        (0, BUILDING_WIDTH),
    ]
    floor = Floor(types["floor"], floor_boundary, level, name="Floor_Slab")

    # Summary
    all_elements = walls + doors + windows + columns + beams + [floor]
    print(f"\n  Total elements: {len(all_elements)}")
    print(f"    Walls: {len(walls)}")
    print(f"    Doors: {len(doors)}")
    print(f"    Windows: {len(windows)}")
    print(f"    Columns: {len(columns)}")
    print(f"    Beams: {len(beams)}")
    print(f"    Floors: 1")

    # Export IFC
    print("\n" + "-" * 70)
    print("Exporting IFC...")
    ifc_path = out_dir / "building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Saved: {ifc_path.name}")

    # Create spatial index
    print("\n" + "-" * 70)
    print("Generating drawings...")

    spatial_index = SpatialIndex()
    for elem in all_elements:
        spatial_index.insert(elem)

    cache = RepresentationCache()
    exporter = DXFExporter()

    # Floor plan
    print("  Generating floor plan...")
    view_range = ViewRange(cut_height=1200, top=FLOOR_HEIGHT, bottom=0, view_depth=0)
    floor_plan = FloorPlanView(name="Floor Plan", level=level, view_range=view_range)
    floor_result = floor_plan.generate(spatial_index, cache)
    exporter.export(floor_result, str(dxf_dir / "floor_plan.dxf"))
    print(f"    Saved: floor_plan.dxf")

    # Elevations
    print("  Generating elevations...")
    height_range = (0, FLOOR_HEIGHT + 500)

    north_elev = ElevationView(
        "North Elevation",
        direction=ElevationDirection.NORTH,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    north_result = north_elev.generate(spatial_index, cache)
    exporter.export(north_result, str(dxf_dir / "elevation_north.dxf"))
    print(f"    Saved: elevation_north.dxf")

    south_elev = ElevationView(
        "South Elevation",
        direction=ElevationDirection.SOUTH,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    south_result = south_elev.generate(spatial_index, cache)
    exporter.export(south_result, str(dxf_dir / "elevation_south.dxf"))
    print(f"    Saved: elevation_south.dxf")

    east_elev = ElevationView(
        "East Elevation",
        direction=ElevationDirection.EAST,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    east_result = east_elev.generate(spatial_index, cache)
    exporter.export(east_result, str(dxf_dir / "elevation_east.dxf"))
    print(f"    Saved: elevation_east.dxf")

    west_elev = ElevationView(
        "West Elevation",
        direction=ElevationDirection.WEST,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    west_result = west_elev.generate(spatial_index, cache)
    exporter.export(west_result, str(dxf_dir / "elevation_west.dxf"))
    print(f"    Saved: elevation_west.dxf")

    # Section
    print("  Generating section...")
    section = SectionView(
        name="Section A",
        plane_point=(BUILDING_LENGTH / 2, BUILDING_WIDTH / 2, 0),
        plane_normal=(0, 1, 0),  # Looking north
        depth=BUILDING_WIDTH,
        height_range=height_range,
        scale=ViewScale.SCALE_1_100,
    )
    section_result = section.generate(spatial_index, cache)
    exporter.export(section_result, str(dxf_dir / "section_a.dxf"))
    print(f"    Saved: section_a.dxf")

    # Create PDF drawing set
    print("\n" + "-" * 70)
    print("Creating PDF drawing set...")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        import math
        from matplotlib.patches import Arc as MplArc

        pdf_path = out_dir / "05_structural_grid_drawing_set.pdf"
        with PdfPages(str(pdf_path)) as pdf:
            views = [
                ("Floor Plan", floor_result),
                ("North Elevation", north_result),
                ("South Elevation", south_result),
                ("East Elevation", east_result),
                ("West Elevation", west_result),
                ("Section A", section_result),
            ]

            for idx, (view_name, view_result) in enumerate(views):
                sheet = Sheet(
                    size=SheetSize.ARCH_D,
                    number=f"A-{idx + 101}",
                    name=view_name,
                    metadata=SheetMetadata(
                        project="Structural Grid Warehouse",
                        drawn_by="BIMasCode",
                        date=datetime.now().strftime("%Y-%m-%d"),
                    ),
                )

                sheet.add_viewport(
                    view_result,
                    position=(sheet.size.width / 2, sheet.size.height / 2 + 50),
                    scale=ViewScale.SCALE_1_100,
                    name=view_name,
                )

                title_block = TitleBlock.from_template(
                    "standard_arch_d",
                    fields={
                        TitleBlockField.PROJECT_NAME.value: "Structural Grid Warehouse",
                        TitleBlockField.SHEET_NAME.value: sheet.name,
                        TitleBlockField.SHEET_NUMBER.value: sheet.number,
                        TitleBlockField.DRAWN_BY.value: "BIMasCode",
                        TitleBlockField.DATE.value: datetime.now().strftime("%Y-%m-%d"),
                        TitleBlockField.SCALE.value: "1:100",
                    },
                    position=(sheet.size.width - 210, 10),
                )
                sheet.set_title_block(title_block)

                fig_width = sheet.size.width / 25.4
                fig_height = sheet.size.height / 25.4

                fig, ax = plt.subplots(figsize=(fig_width, fig_height))
                fig.patch.set_facecolor("white")
                ax.set_facecolor("white")
                ax.set_aspect("equal")
                ax.axis("off")
                ax.set_xlim(0, sheet.size.width)
                ax.set_ylim(0, sheet.size.height)

                border = plt.Rectangle(
                    (0, 0),
                    sheet.size.width,
                    sheet.size.height,
                    fill=False,
                    edgecolor=(0.7, 0.7, 0.7),
                    linewidth=0.5,
                )
                ax.add_patch(border)

                bounds = view_result.get_bounds()
                if bounds:
                    model_center_x = (bounds[0] + bounds[2]) / 2
                    model_center_y = (bounds[1] + bounds[3]) / 2
                    scale = ViewScale.SCALE_1_100.ratio
                    offset_x = sheet.size.width / 2 - model_center_x * scale
                    offset_y = sheet.size.height / 2 + 50 - model_center_y * scale

                    for line in view_result.lines:
                        ax.plot(
                            [line.start.x * scale + offset_x, line.end.x * scale + offset_x],
                            [line.start.y * scale + offset_y, line.end.y * scale + offset_y],
                            color="black",
                            linewidth=0.5,
                        )

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

                    for polyline in view_result.polylines:
                        if len(polyline.points) >= 2:
                            xs = [p.x * scale + offset_x for p in polyline.points]
                            ys = [p.y * scale + offset_y for p in polyline.points]
                            if polyline.closed:
                                xs.append(xs[0])
                                ys.append(ys[0])
                            ax.plot(xs, ys, color="black", linewidth=0.5)

                ax.text(
                    sheet.size.width / 2,
                    30,
                    view_name,
                    fontsize=12,
                    ha="center",
                    va="bottom",
                    color="black",
                )

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
    pdf_file = out_dir / "05_structural_grid_drawing_set.pdf"
    if pdf_file.exists():
        print(f"  05_structural_grid_drawing_set.pdf")


if __name__ == "__main__":
    main()
