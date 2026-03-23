"""
Sprint 6 Demo: Drawing Generation

Creates a simple building with walls, doors, and windows,
then generates:
1. IFC export for 3D viewing
2. Floor plan DXF for 2D viewing
"""

from pathlib import Path

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import Wall, create_basic_wall_type, detect_and_process_wall_joins, EndCapType
from bimascode.architecture.door import Door
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.window import Window
from bimascode.architecture.window_type import WindowType
from bimascode.architecture.floor import Floor
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.utils.materials import MaterialLibrary
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.view_base import ViewRange
from bimascode.drawing.dxf_exporter import DXFExporter


def create_simple_house():
    """Create a simple house with rooms, doors, and windows."""
    print("Creating building...")

    # Create building and level
    building = Building("Demo House")
    ground = Level(building, "Ground Floor", elevation=0)

    # Materials
    concrete = MaterialLibrary.concrete()

    # Wall types
    exterior_wall_type = create_basic_wall_type("Exterior Wall", 300, concrete)
    interior_wall_type = create_basic_wall_type("Interior Wall", 150, concrete)

    # Door types
    entry_door_type = DoorType(
        name="Entry Door",
        width=900,
        height=2100,
    )
    interior_door_type = DoorType(
        name="Interior Door",
        width=800,
        height=2100,
    )

    # Window type
    window_type = WindowType(
        name="Standard Window",
        width=1200,
        height=1500,
        default_sill_height=900,
    )

    # Floor type
    floor_type = FloorType("Concrete Slab")
    floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

    # Create exterior walls (10m x 8m house)
    # South wall
    wall_south = Wall(exterior_wall_type, (0, 0), (10000, 0), ground)
    # East wall
    wall_east = Wall(exterior_wall_type, (10000, 0), (10000, 8000), ground)
    # North wall
    wall_north = Wall(exterior_wall_type, (10000, 8000), (0, 8000), ground)
    # West wall
    wall_west = Wall(exterior_wall_type, (0, 8000), (0, 0), ground)

    # Interior wall dividing house (at x=5000)
    wall_interior = Wall(interior_wall_type, (5000, 0), (5000, 8000), ground)

    exterior_walls = [wall_south, wall_east, wall_north, wall_west]
    interior_walls = [wall_interior]
    all_walls = exterior_walls + interior_walls

    # Process wall joins to get proper corner connections
    # Use EXTERIOR end cap so walls extend to outer face of joining wall
    adjustments = detect_and_process_wall_joins(all_walls, end_cap_type=EndCapType.EXTERIOR)
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj
    print(f"  Processed {len(adjustments)} wall join adjustments")

    # Add entry door on south wall
    entry_door = Door(
        door_type=entry_door_type,
        host_wall=wall_south,
        offset=2000,  # 2m from left corner
    )

    # Add interior door in the dividing wall
    interior_door = Door(
        door_type=interior_door_type,
        host_wall=wall_interior,
        offset=4000,  # 4m from south
    )

    doors = [entry_door, interior_door]

    # Add windows
    # Window on south wall (right side)
    window_south = Window(
        window_type=window_type,
        host_wall=wall_south,
        offset=7000,  # 7m from left corner
    )

    # Windows on east wall
    window_east_1 = Window(
        window_type=window_type,
        host_wall=wall_east,
        offset=2000,
    )
    window_east_2 = Window(
        window_type=window_type,
        host_wall=wall_east,
        offset=5500,
    )

    # Window on north wall
    window_north = Window(
        window_type=window_type,
        host_wall=wall_north,
        offset=2500,
    )

    # Window on west wall
    window_west = Window(
        window_type=window_type,
        host_wall=wall_west,
        offset=4000,
    )

    windows = [window_south, window_east_1, window_east_2, window_north, window_west]

    # Create floor
    floor_boundary = [
        (0, 0),
        (10000, 0),
        (10000, 8000),
        (0, 8000),
    ]
    floor = Floor(floor_type, floor_boundary, ground)

    floors = [floor]

    print(f"  Created {len(all_walls)} walls")
    print(f"  Created {len(doors)} doors")
    print(f"  Created {len(windows)} windows")
    print(f"  Created {len(floors)} floor")

    return building, ground, all_walls, doors, windows, floors


def export_ifc(building, output_path):
    """Export building to IFC format."""
    print(f"\nExporting to IFC: {output_path}")

    # The building.export_ifc() method handles all registered elements
    building.export_ifc(str(output_path))
    print(f"  IFC export complete: {output_path}")


def generate_floor_plan(level, walls, doors, windows, floors, output_path):
    """Generate floor plan DXF."""
    print(f"\nGenerating floor plan: {output_path}")

    # Create spatial index and populate with elements
    spatial_index = SpatialIndex()
    all_elements = walls + doors + windows + floors

    for element in all_elements:
        spatial_index.insert(element)

    print(f"  Indexed {len(all_elements)} elements")

    # Create representation cache
    cache = RepresentationCache()

    # Create floor plan view with Revit-style view range
    view_range = ViewRange(
        cut_height=1200,  # Cut at 1.2m above floor (4')
        top=2700,  # Top of view at 2.7m (typical ceiling)
        bottom=0,  # Bottom at floor level
        view_depth=0,  # View depth at floor level
    )

    floor_plan = FloorPlanView(
        name="Ground Floor Plan",
        level=level,
        view_range=view_range,
    )

    # Generate the view
    result = floor_plan.generate(spatial_index, cache)

    print(f"  Generated {result.element_count} elements")
    print(f"  Total geometry: {result.total_geometry_count} items")
    print(f"    - Lines: {len(result.lines)}")
    print(f"    - Arcs: {len(result.arcs)}")
    print(f"    - Polylines: {len(result.polylines)}")
    print(f"    - Hatches: {len(result.hatches)}")
    print(f"  Generation time: {result.generation_time*1000:.1f}ms")
    print(f"  Cache hits: {result.cache_hits}")

    # Export to DXF
    exporter = DXFExporter()
    exporter.export(result, str(output_path))
    print(f"  DXF export complete: {output_path}")


def main():
    """Run the demo."""
    print("=" * 60)
    print("Sprint 6 Demo: Drawing Generation")
    print("=" * 60)

    # Create output directory
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Create building
    building, level, walls, doors, windows, floors = create_simple_house()

    # Export IFC
    ifc_path = output_dir / "sprint6_demo.ifc"
    export_ifc(building, ifc_path)

    # Generate floor plan
    dxf_path = output_dir / "sprint6_floor_plan.dxf"
    generate_floor_plan(level, walls, doors, windows, floors, dxf_path)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print(f"\nOutput files:")
    print(f"  IFC: {ifc_path}")
    print(f"  DXF: {dxf_path}")
    print("\nTo view:")
    print("  - IFC: Open in BIM Collab ZOOM, FreeCAD, or any IFC viewer")
    print("  - DXF: Open in AutoCAD, LibreCAD, or any DXF viewer")
    print("=" * 60)


if __name__ == "__main__":
    main()
