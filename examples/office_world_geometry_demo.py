"""
Office Building Demo - Line Weight and View Template Demonstration

This example creates a realistic office floor with:
- Private offices along North and East walls (L-shaped arrangement)
- Open bullpen area with exposed structural grid (columns/beams visible)
- Professional line weights per AIA/NCS standards

The demo generates architectural and structural floor plans to show
how line weights differentiate between disciplines.
"""

from datetime import datetime
from pathlib import Path

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import (
    Wall, create_basic_wall_type, detect_and_process_wall_joins, EndCapType
)
from bimascode.architecture.door import Door
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.window import Window
from bimascode.architecture.window_type import WindowType
from bimascode.architecture.floor import Floor
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.architecture.ceiling import Ceiling
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.structure import (
    ColumnType,
    StructuralColumn,
    create_square_column_type,
    BeamType,
    Beam,
    create_rectangular_beam_type,
)
from bimascode.utils.materials import MaterialLibrary
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.elevation_view import ElevationView, ElevationDirection
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.drawing.view_templates import ViewTemplate, GraphicOverride, CategoryVisibility
from bimascode.drawing.line_styles import LineWeight
from bimascode.drawing.dxf_exporter import DXFExporter


def create_office_building():
    """Create an office floor with private offices and open bullpen.

    Layout (24m x 18m):

        North (windows)
    +--+--+--+--+--+--+------+
    |O1|O2|O3|O4|O5|O6|CORNER| <- 6 offices (3mx4m) + corner (6mx4m)
    +--+--+--+--+--+--+------+
    |                    | E1|  E
    |                    +---+  a
    |    OPEN BULLPEN    | E2|  s  <- 4 East offices
    |    (exposed        +---+  t
    |     structure)     | E3|
    |                    +---+  (windows)
    |                    | E4|
    +--------------------+---+
        South

    The bullpen has no interior walls - just columns and beams visible.
    Private offices are along North and East walls with windows.
    """
    print("Creating office building with private offices and open bullpen...")

    # Create building and levels
    building = Building("Office with Bullpen")
    ground = Level(building, "Ground Floor", elevation=0)

    # Materials
    concrete = MaterialLibrary.concrete()
    steel = MaterialLibrary.steel()

    # =========================================================================
    # BUILDING DIMENSIONS
    # =========================================================================

    building_length = 24000  # mm (X direction) - 24m
    building_width = 18000   # mm (Y direction) - 18m
    floor_height = 4000      # mm
    ceiling_height = 2700    # mm
    wall_thickness = 200     # mm (interior walls)
    ext_wall_thickness = 300 # mm (exterior walls)

    # Office dimensions
    office_depth = 4000      # 4m deep offices
    office_width = 3000      # 3m wide offices

    # Structural grid - 6m spacing
    grid_spacing = 6000
    grid_x = [0, 6000, 12000, 18000, 24000]  # 5 gridlines
    grid_y = [0, 6000, 12000, 18000]          # 4 gridlines

    # =========================================================================
    # TYPES
    # =========================================================================

    # Wall types
    exterior_wall_type = create_basic_wall_type("Exterior Wall", ext_wall_thickness, concrete)
    interior_wall_type = create_basic_wall_type("Interior Wall", wall_thickness, concrete)

    # Door types
    office_door_type = DoorType(name="Office Door", width=900, height=2100)
    entry_door_type = DoorType(name="Entry Door", width=1800, height=2400)  # Double door

    # Window types
    office_window_type = WindowType(
        name="Office Window",
        width=1800,
        height=1500,
        default_sill_height=900,
    )

    # Floor and ceiling types
    floor_type = FloorType("Concrete Slab")
    floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
    ceiling_type = CeilingType("Suspended Ceiling", thickness=20)

    # Structural types
    column_type = create_square_column_type("Steel Column", size=350, material=steel)
    beam_type = create_rectangular_beam_type("Steel Beam", width=250, height=450, material=steel)

    # Calculate wall height (below beams)
    beam_height = beam_type.height
    wall_height = floor_height - beam_height  # Walls stop at bottom of beams

    # Storage for all elements
    all_walls = []
    all_doors = []
    all_windows = []
    all_floors = []
    all_ceilings = []
    all_columns = []
    all_beams = []

    level = ground
    level_name = "Ground"

    # =========================================================================
    # EXTERIOR WALLS
    # =========================================================================
    print(f"\n  Creating exterior walls...")

    wall_south = Wall(exterior_wall_type,
                     (0, 0), (building_length, 0),
                     level, height=wall_height, name="Ext_South")
    wall_east = Wall(exterior_wall_type,
                    (building_length, 0), (building_length, building_width),
                    level, height=wall_height, name="Ext_East")
    wall_north = Wall(exterior_wall_type,
                     (building_length, building_width), (0, building_width),
                     level, height=wall_height, name="Ext_North")
    wall_west = Wall(exterior_wall_type,
                    (0, building_width), (0, 0),
                    level, height=wall_height, name="Ext_West")

    exterior_walls = [wall_south, wall_east, wall_north, wall_west]
    all_walls.extend(exterior_walls)
    print(f"    4 exterior walls")

    # =========================================================================
    # MAIN ENTRY DOOR (south wall, between Col_B1 and Col_C1)
    # =========================================================================
    # Col_B1 is at x=6000, Col_C1 is at x=12000 (grid spacing = 6000)
    # Center the entry door between them
    entry_door_center_x = (grid_x[1] + grid_x[2]) / 2  # (6000 + 12000) / 2 = 9000
    entry_door = Door(entry_door_type, wall_south,
                     offset=entry_door_center_x - entry_door_type.width / 2,
                     name="Main_Entry")
    all_doors.append(entry_door)
    print(f"    1 main entry door (1.8m wide double door)")

    # =========================================================================
    # NORTH OFFICES (along north wall)
    # =========================================================================
    # North offices go from x=0 to x=(building_length - office_depth)
    # This leaves room for east offices in the corner
    north_offices_length = building_length - office_depth  # 20m available
    num_north_offices = int(north_offices_length / office_width)  # 6 offices at 3m each = 18m

    print(f"\n  Creating North offices ({num_north_offices} offices, 3m x 4m each)...")

    north_office_y = building_width - office_depth  # Y coordinate of office front wall

    # Corridor wall along north offices (from west wall to east corridor)
    wall_north_corridor = Wall(interior_wall_type,
                               (0, north_office_y), (num_north_offices * office_width, north_office_y),
                               level, height=wall_height, name="North_Corridor")
    all_walls.append(wall_north_corridor)

    # Create offices along north wall
    for i in range(num_north_offices):
        office_x = i * office_width

        # Partition wall between offices (skip first one - exterior wall)
        if i > 0:
            partition = Wall(interior_wall_type,
                           (office_x, north_office_y), (office_x, building_width),
                           level, height=wall_height, name=f"North_Partition_{i}")
            all_walls.append(partition)

        # Door in corridor wall
        door = Door(office_door_type, wall_north_corridor,
                   offset=office_x + office_width / 2 - office_door_type.width / 2,
                   name=f"North_Office_{i+1}_Door")
        all_doors.append(door)

        # Window in north exterior wall (wall runs right to left, so offset from right)
        win = Window(office_window_type, wall_north,
                    offset=building_length - office_x - office_width + (office_width - office_window_type.width) / 2,
                    name=f"North_Office_{i+1}_Window")
        all_windows.append(win)

    # Final partition wall to close off last north office from corner area
    final_partition_x = num_north_offices * office_width
    wall_north_end = Wall(interior_wall_type,
                         (final_partition_x, north_office_y), (final_partition_x, building_width),
                         level, height=wall_height, name="North_End_Partition")
    all_walls.append(wall_north_end)

    print(f"    {num_north_offices} offices with doors and windows")

    # =========================================================================
    # CORNER OFFICE (northeast corner - larger executive office)
    # =========================================================================
    print(f"\n  Creating Corner office (executive, 6m x 4m)...")

    corner_office_x = num_north_offices * office_width  # Where north offices end
    corner_office_y = north_office_y

    # Corner office corridor wall (connects north corridor to east corridor)
    wall_corner_corridor = Wall(interior_wall_type,
                                (corner_office_x, corner_office_y),
                                (building_length - office_depth, corner_office_y),
                                level, height=wall_height, name="Corner_Corridor")
    all_walls.append(wall_corner_corridor)

    # Door to corner office
    corner_door = Door(office_door_type, wall_corner_corridor,
                      offset=(building_length - office_depth - corner_office_x) / 2 - office_door_type.width / 2,
                      name="Corner_Office_Door")
    all_doors.append(corner_door)

    # Windows in corner office (one on north, one on east)
    corner_win_north = Window(office_window_type, wall_north,
                             offset=(office_depth - office_window_type.width) / 2,
                             name="Corner_Office_Window_N")
    all_windows.append(corner_win_north)

    corner_win_east = Window(office_window_type, wall_east,
                            offset=north_office_y + (office_depth - office_window_type.width) / 2,
                            name="Corner_Office_Window_E")
    all_windows.append(corner_win_east)

    print(f"    1 corner office with door and 2 windows")

    # =========================================================================
    # EAST OFFICES (along east wall, below corner office)
    # =========================================================================
    east_office_x = building_length - office_depth  # X coordinate of office front wall
    east_offices_start_y = 0  # Start from south
    east_offices_end_y = north_office_y  # End at corner office

    # Calculate how many offices fit
    num_east_offices = int(east_offices_end_y / office_width)  # Use office_width for consistency
    east_office_height = east_offices_end_y / num_east_offices

    print(f"\n  Creating East offices ({num_east_offices} offices, 4m x {east_office_height/1000:.1f}m each)...")

    # Corridor wall along east offices
    wall_east_corridor = Wall(interior_wall_type,
                              (east_office_x, east_offices_start_y),
                              (east_office_x, east_offices_end_y),
                              level, height=wall_height, name="East_Corridor")
    all_walls.append(wall_east_corridor)

    for i in range(num_east_offices):
        office_y = i * east_office_height

        # Partition wall between offices (skip first one - exterior wall)
        if i > 0:
            partition = Wall(interior_wall_type,
                           (east_office_x, office_y), (building_length, office_y),
                           level, height=wall_height, name=f"East_Partition_{i}")
            all_walls.append(partition)

        # Door in corridor wall
        door = Door(office_door_type, wall_east_corridor,
                   offset=office_y + east_office_height / 2 - office_door_type.width / 2,
                   name=f"East_Office_{i+1}_Door")
        all_doors.append(door)

        # Window in east exterior wall
        win = Window(office_window_type, wall_east,
                    offset=office_y + (east_office_height - office_window_type.width) / 2,
                    name=f"East_Office_{i+1}_Window")
        all_windows.append(win)

    print(f"    {num_east_offices} offices with doors and windows")

    # =========================================================================
    # FLOOR SLAB
    # =========================================================================
    print(f"\n  Creating floor slab...")

    floor_boundary = [
        (0, 0),
        (building_length, 0),
        (building_length, building_width),
        (0, building_width),
    ]
    floor = Floor(floor_type, floor_boundary, level, name="Floor_Slab")
    all_floors.append(floor)
    print(f"    1 floor slab")

    # =========================================================================
    # CEILING (only over offices, bullpen has exposed structure)
    # =========================================================================
    print(f"\n  Creating ceilings (offices only - bullpen exposed)...")

    # North offices ceiling
    north_ceiling = Ceiling(ceiling_type,
                           [(0, north_office_y), (building_length - office_depth, north_office_y),
                            (building_length - office_depth, building_width), (0, building_width)],
                           level, height=ceiling_height, name="North_Offices_Ceiling")
    all_ceilings.append(north_ceiling)

    # East offices ceiling
    east_ceiling = Ceiling(ceiling_type,
                          [(east_office_x, 0), (building_length, 0),
                           (building_length, north_office_y), (east_office_x, north_office_y)],
                          level, height=ceiling_height, name="East_Offices_Ceiling")
    all_ceilings.append(east_ceiling)

    print(f"    2 ceilings (offices only)")

    # =========================================================================
    # STRUCTURAL COLUMNS - Full grid
    # =========================================================================
    print(f"\n  Creating structural columns...")

    column_height = floor_height

    for i, x in enumerate(grid_x):
        for j, y in enumerate(grid_y):
            col = StructuralColumn(
                column_type, level,
                position=(x, y),
                height=column_height,
                rotation=0,
                name=f"Col_{chr(65+i)}{j+1}"
            )
            all_columns.append(col)

    print(f"    {len(grid_x) * len(grid_y)} columns at 6m grid")

    # =========================================================================
    # STRUCTURAL BEAMS - Full grid (visible in bullpen)
    # =========================================================================
    print(f"\n  Creating structural beams...")

    # Beam Z position - top of beam at floor_height
    beam_z = floor_height - beam_height / 2

    # Primary beams in X direction (along Y gridlines)
    for j, y in enumerate(grid_y):
        for i in range(len(grid_x) - 1):
            beam = Beam(
                beam_type, level,
                start_point=(grid_x[i], y, beam_z),
                end_point=(grid_x[i+1], y, beam_z),
                name=f"Beam_X_{chr(65+i)}{j+1}"
            )
            all_beams.append(beam)

    # Secondary beams in Y direction (along X gridlines)
    secondary_beam_z = beam_z - beam_height  # Below primary beams
    for i, x in enumerate(grid_x):
        for j in range(len(grid_y) - 1):
            beam = Beam(
                beam_type, level,
                start_point=(x, grid_y[j], secondary_beam_z),
                end_point=(x, grid_y[j+1], secondary_beam_z),
                name=f"Beam_Y_{chr(65+i)}{j+1}"
            )
            all_beams.append(beam)

    # Infill beams at mid-span (especially visible in bullpen)
    infill_beam_type = create_rectangular_beam_type(
        "Infill Beam", width=200, height=350, material=steel
    )

    for i in range(len(grid_x) - 1):
        mid_x = (grid_x[i] + grid_x[i + 1]) / 2
        for j in range(len(grid_y) - 1):
            # X-direction infill
            mid_y = (grid_y[j] + grid_y[j + 1]) / 2
            beam = Beam(
                infill_beam_type, level,
                start_point=(grid_x[i], mid_y, secondary_beam_z),
                end_point=(grid_x[i + 1], mid_y, secondary_beam_z),
                name=f"Infill_X_{chr(65+i)}{j+1}"
            )
            all_beams.append(beam)

            # Y-direction infill
            beam = Beam(
                infill_beam_type, level,
                start_point=(mid_x, grid_y[j], secondary_beam_z),
                end_point=(mid_x, grid_y[j + 1], secondary_beam_z),
                name=f"Infill_Y_{chr(65+i)}{j+1}"
            )
            all_beams.append(beam)

    print(f"    {len(all_beams)} beams (primary, secondary, and infill)")

    # =========================================================================
    # PROCESS WALL JOINS
    # =========================================================================
    print(f"\n  Processing wall joins...")
    adjustments = detect_and_process_wall_joins(all_walls, end_cap_type=EndCapType.EXTERIOR)
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n  Total elements created:")
    print(f"    Walls: {len(all_walls)}")
    print(f"    Doors: {len(all_doors)}")
    print(f"    Windows: {len(all_windows)}")
    print(f"    Floors: {len(all_floors)}")
    print(f"    Ceilings: {len(all_ceilings)}")
    print(f"    Columns: {len(all_columns)}")
    print(f"    Beams: {len(all_beams)}")

    return (building, ground,
            all_walls, all_doors, all_windows, all_floors, all_ceilings,
            all_columns, all_beams,
            {"length": building_length, "width": building_width, "height": floor_height})


def create_spatial_index(walls, doors, windows, floors, ceilings, columns, beams):
    """Create and populate spatial index with all elements."""
    spatial_index = SpatialIndex()
    all_elements = walls + doors + windows + floors + ceilings + columns + beams

    for element in all_elements:
        spatial_index.insert(element)

    return spatial_index, all_elements


def create_architectural_floor_plan_template() -> ViewTemplate:
    """Create a professional architectural floor plan template.

    Line weight assignments per AIA/NCS standards:
    - HEAVY (0.70mm): Primary cut elements - walls
    - WIDE (0.50mm): Secondary cut elements - doors, windows
    - MEDIUM (0.35mm): Detail lines, floor patterns
    - NARROW (0.25mm): Visible projection lines
    - FINE (0.18mm): Hidden lines, elements above cut plane
    - EXTRA_FINE (0.13mm): Annotations, dimensions
    """
    template = ViewTemplate("Architectural Floor Plan")

    # Wall settings - primary cut elements use heavy line weight
    template.set_category_override("Wall", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        cut_line_weight=LineWeight.HEAVY,      # 0.70mm for cut walls
        projection_line_weight=LineWeight.NARROW,
    ))

    # Door settings - secondary cut elements
    template.set_category_override("Door", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        cut_line_weight=LineWeight.WIDE,       # 0.50mm for cut doors
    ))

    # Window settings - secondary cut elements
    template.set_category_override("Window", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        cut_line_weight=LineWeight.WIDE,       # 0.50mm for cut windows
    ))

    # Column settings - halftone in architectural plans
    template.set_category_override("StructuralColumn", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        cut_line_weight=LineWeight.MEDIUM,     # 0.35mm (reduced from heavy)
        halftone=True,  # Gray to de-emphasize
    ))

    # Beam settings - above cut plane, halftone
    template.set_category_override("Beam", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        line_weight=LineWeight.FINE,           # 0.18mm for above-cut beams
        halftone=True,
    ))

    template.visibility.ceilings = False

    return template


def create_structural_floor_plan_template() -> ViewTemplate:
    """Create a structural floor plan template.

    Emphasizes structural elements, shows architecture in halftone.
    This is ideal for showing the bullpen's exposed structure.
    """
    template = ViewTemplate("Structural Floor Plan")

    # Structure at full weight - columns prominent
    template.set_category_override("StructuralColumn", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        cut_line_weight=LineWeight.HEAVY,      # 0.70mm - primary element
    ))

    # Beams clearly visible
    template.set_category_override("Beam", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        line_weight=LineWeight.MEDIUM,         # 0.35mm
    ))

    # Architecture in halftone with reduced weight
    template.set_category_override("Wall", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        line_weight=LineWeight.FINE,           # 0.18mm
        halftone=True,
    ))

    template.set_category_override("Door", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        line_weight=LineWeight.FINE,
        halftone=True,
    ))

    template.set_category_override("Window", GraphicOverride(
        visibility=CategoryVisibility.VISIBLE,
        line_weight=LineWeight.FINE,
        halftone=True,
    ))

    return template


def generate_floor_plan(level, spatial_index, cache, output_path, template=None):
    """Generate floor plan DXF with professional line weights."""
    print(f"\n  Generating floor plan: {output_path.name}")

    view_range = ViewRange(
        cut_height=1200,
        top_clip=3500,     # Show beams above
        bottom_clip=0,
    )

    floor_plan = FloorPlanView(
        name=f"{level.name} Plan",
        level=level,
        view_range=view_range,
        template=template,
    )

    result = floor_plan.generate(spatial_index, cache)
    print(f"    Elements: {result.element_count}, Geometry: {result.total_geometry_count}")

    # Report line weight usage
    weights_used = set()
    for line in result.lines:
        weights_used.add(f"{line.style.weight.name}")
    for arc in result.arcs:
        weights_used.add(f"{arc.style.weight.name}")
    for polyline in result.polylines:
        weights_used.add(f"{polyline.style.weight.name}")
    print(f"    Line weights: {', '.join(sorted(weights_used))}")

    exporter = DXFExporter()
    exporter.export(result, str(output_path))


def generate_section(name, spatial_index, cache, point, normal, output_path, height_range):
    """Generate section view DXF."""
    print(f"\n  Generating section: {name}")

    section = SectionView(
        name=name,
        plane_point=point,
        plane_normal=normal,
        depth=30000,
        height_range=height_range,
        scale=ViewScale.SCALE_1_50,
        show_hidden_lines=False,
    )

    result = section.generate(spatial_index, cache)
    print(f"    Elements: {result.element_count}, Geometry: {result.total_geometry_count}")

    exporter = DXFExporter()
    exporter.export(result, str(output_path))


def main():
    """Run the demo."""
    print("=" * 70)
    print("Office Building Demo - Line Weights & View Templates")
    print("=" * 70)

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / "output" / f"office_demo_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # =========================================================================
    # CREATE BUILDING
    # =========================================================================

    (building, ground,
     walls, doors, windows, floors, ceilings, columns, beams,
     dims) = create_office_building()

    # =========================================================================
    # CREATE SPATIAL INDEX
    # =========================================================================

    spatial_index, all_elements = create_spatial_index(
        walls, doors, windows, floors, ceilings, columns, beams
    )
    print(f"\nSpatial index created with {len(all_elements)} elements")

    cache = RepresentationCache()

    # =========================================================================
    # EXPORT IFC
    # =========================================================================

    print("\n" + "=" * 70)
    print("Exporting IFC")
    print("=" * 70)

    ifc_path = output_dir / "office_building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"  Exported to: {ifc_path}")

    # =========================================================================
    # GENERATE FLOOR PLANS
    # =========================================================================

    print("\n" + "=" * 70)
    print("Generating Floor Plans (Architectural vs Structural)")
    print("=" * 70)

    arch_template = create_architectural_floor_plan_template()
    struct_template = create_structural_floor_plan_template()

    print("\n  Line weight standards (AIA/NCS):")
    print("    HEAVY   = 0.70mm - Primary cut elements")
    print("    WIDE    = 0.50mm - Secondary cut elements")
    print("    MEDIUM  = 0.35mm - Detail lines")
    print("    NARROW  = 0.25mm - Visible projection")
    print("    FINE    = 0.18mm - Hidden/above-cut")
    print("    X-FINE  = 0.13mm - Annotations")

    # Architectural floor plan - walls prominent, structure subdued
    generate_floor_plan(ground, spatial_index, cache,
                       output_dir / "floor_plan_architectural.dxf",
                       template=arch_template)

    # Structural floor plan - columns/beams prominent, walls subdued
    generate_floor_plan(ground, spatial_index, cache,
                       output_dir / "floor_plan_structural.dxf",
                       template=struct_template)

    # =========================================================================
    # GENERATE SECTIONS
    # =========================================================================

    print("\n" + "=" * 70)
    print("Generating Sections")
    print("=" * 70)

    center_x = dims["length"] / 2
    center_y = dims["width"] / 2

    # Section through bullpen (showing exposed beams)
    generate_section(
        "Section A-A (Through Bullpen)",
        spatial_index, cache,
        (center_x, center_y / 2, 0),  # Cut through bullpen area
        (0, 1, 0),
        output_dir / "section_bullpen.dxf",
        height_range=(0, 4500)
    )

    # Section through offices
    generate_section(
        "Section B-B (Through Offices)",
        spatial_index, cache,
        (center_x, dims["width"] - 2000, 0),  # Cut through north offices
        (0, 1, 0),
        output_dir / "section_offices.dxf",
        height_range=(0, 4500)
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)

    print("\nGenerated files:")
    for f in sorted(output_dir.iterdir()):
        print(f"  {f.name}")

    print(f"\nOutput directory: {output_dir}")

    print("\nKey differences to observe:")
    print("  - Architectural plan: Walls are HEAVY (0.70mm), columns are MEDIUM halftone")
    print("  - Structural plan: Columns are HEAVY (0.70mm), walls are FINE halftone")
    print("  - Bullpen area shows exposed beam grid clearly in structural plan")
    print("  - Private offices show wall layout clearly in architectural plan")

    print("=" * 70)


if __name__ == "__main__":
    main()
