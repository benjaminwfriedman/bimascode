"""
ViewRange Demo - Sprint 6 Issue #31

Demonstrates the Revit-style ViewRange implementation with different scenarios:
1. Standard floor plan (default range)
2. Showing basement elements (extended view_depth)
3. Showing upper level elements (raised top)
4. Focus on specific room types (custom ranges)
"""

from pathlib import Path

from bimascode.architecture import (
    Wall, Door, DoorType,
    WallType, Layer, LayerFunction,
    detect_and_process_wall_joins, EndCapType
)
from bimascode.utils.materials import Material
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, LengthUnit


def create_multi_level_house():
    """Create a simple house with basement, ground floor, and upper floor."""
    print("Creating multi-level house...")

    building = Building("Multi-Level House Demo")

    # Create levels (using millimeters directly for simplicity)
    basement = Level(building, "Basement", elevation=Length(-2400, LengthUnit.MILLIMETER))  # -2.4m below grade
    ground = Level(building, "Ground Floor", elevation=Length(0, LengthUnit.MILLIMETER))
    upper = Level(building, "Upper Floor", elevation=Length(3000, LengthUnit.MILLIMETER))  # 3m above ground

    # Materials
    brick = Material("Brick")
    insulation = Material("Insulation")
    gypsum = Material("Gypsum Board")

    # Exterior wall type (250mm total)
    ext_wall_type = WallType("Exterior Wall - 250mm")
    ext_wall_type.add_layer(brick, 110, LayerFunction.FINISH_EXTERIOR, structural=False)
    ext_wall_type.add_layer(insulation, 60, LayerFunction.THERMAL_INSULATION, structural=False)
    ext_wall_type.add_layer(gypsum, 80, LayerFunction.STRUCTURE, structural=True)

    # Interior wall type (150mm total)
    int_wall_type = WallType("Interior Wall - 150mm")
    int_wall_type.add_layer(gypsum, 75, LayerFunction.STRUCTURE, structural=True)

    # Door type
    door_type = DoorType("Standard Door")

    # BASEMENT: Foundation walls (2400mm tall)
    basement_height = 2400

    # Basement perimeter (9m x 12m)
    basement_walls = [
        # South wall
        Wall(ext_wall_type, (0, 0), (12000, 0), basement, basement_height),
        # East wall
        Wall(ext_wall_type, (12000, 0), (12000, 9000), basement, basement_height),
        # North wall
        Wall(ext_wall_type, (12000, 9000), (0, 9000), basement, basement_height),
        # West wall
        Wall(ext_wall_type, (0, 9000), (0, 0), basement, basement_height),
    ]

    # Basement storage room (4.5m x 3m in southwest corner)
    basement_walls.extend([
        Wall(int_wall_type, (0, 0), (4500, 0), basement, basement_height),
        Wall(int_wall_type, (4500, 0), (4500, 3000), basement, basement_height),
        Wall(int_wall_type, (4500, 3000), (0, 3000), basement, basement_height),
    ])

    # GROUND FLOOR: Living spaces (2700mm ceilings)
    ground_height = 2700

    # Ground floor perimeter (same footprint as basement)
    south_wall = Wall(ext_wall_type, (0, 0), (12000, 0), ground, ground_height)

    ground_walls = [
        south_wall,
        # East wall
        Wall(ext_wall_type, (12000, 0), (12000, 9000), ground, ground_height),
        # North wall
        Wall(ext_wall_type, (12000, 9000), (0, 9000), ground, ground_height),
        # West wall
        Wall(ext_wall_type, (0, 9000), (0, 0), ground, ground_height),
    ]

    # Front door in south wall
    front_door = Door(door_type, south_wall, offset=5400)

    # Interior walls - Living room (6m x 4.5m), Kitchen (6m x 4.5m)
    ground_walls.extend([
        # Dividing wall between living and kitchen
        Wall(int_wall_type, (6000, 0), (6000, 3600), ground, ground_height),
        Wall(int_wall_type, (6000, 4500), (6000, 9000), ground, ground_height),
    ])

    # Bathroom (3m x 2.4m in NW corner)
    ground_walls.extend([
        Wall(int_wall_type, (0, 6600), (3000, 6600), ground, ground_height),
        Wall(int_wall_type, (3000, 6600), (3000, 9000), ground, ground_height),
    ])

    # UPPER FLOOR: Bedrooms (2400mm ceilings)
    upper_height = 2400

    # Upper floor perimeter (slightly smaller - setback roof)
    upper_walls = [
        # South wall
        Wall(ext_wall_type, (600, 0), (11400, 0), upper, upper_height),
        # East wall
        Wall(ext_wall_type, (11400, 0), (11400, 8400), upper, upper_height),
        # North wall
        Wall(ext_wall_type, (11400, 8400), (600, 8400), upper, upper_height),
        # West wall
        Wall(ext_wall_type, (600, 8400), (600, 0), upper, upper_height),
    ]

    # Two bedrooms (5.4m x 4.2m each)
    upper_walls.extend([
        # Center dividing wall
        Wall(int_wall_type, (6000, 0), (6000, 8400), upper, upper_height),
    ])

    # Process wall joins for all walls
    all_walls = basement_walls + ground_walls + upper_walls
    detect_and_process_wall_joins(all_walls, end_cap_type=EndCapType.EXTERIOR)

    print(f"  Created {len(basement_walls)} basement walls")
    print(f"  Created {len(ground_walls)} ground floor walls")
    print(f"  Created 1 door")
    print(f"  Created {len(upper_walls)} upper floor walls")

    # Collect all elements
    all_elements = all_walls + [front_door]

    return building, basement, ground, upper, all_elements


def generate_floor_plans(building, basement, ground, upper, all_elements):
    """Generate multiple floor plans with different view ranges."""

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Build spatial index
    spatial_index = SpatialIndex()
    for element in all_elements:
        spatial_index.insert(element)

    print(f"\n  Indexed {len(all_elements)} elements")

    cache = RepresentationCache()

    print("\n" + "="*60)
    print("Generating Floor Plans with Different View Ranges")
    print("="*60)

    # ========================================================================
    # 1. STANDARD GROUND FLOOR PLAN
    # ========================================================================
    print("\n1. Standard Ground Floor Plan")
    print("   ViewRange: cut=1200mm, top=2400mm, bottom=0mm, view_depth=0mm")
    print("   Shows: Walls cut at 1.2m, up to 2.4m ceiling")

    standard_range = ViewRange(
        cut_height=1200,  # Cut at 4' (1.2m)
        top=2400,         # Show up to 8' (2.4m)
        bottom=0,         # Bottom at floor level
        view_depth=0,     # No extended depth
    )

    ground_plan = FloorPlanView(
        "Ground Floor - Standard",
        ground,
        view_range=standard_range,
        scale=ViewScale.SCALE_1_50,
    )

    result = ground_plan.generate(spatial_index, cache)
    output_path = output_dir / "house_ground_standard.dxf"

    exporter = DXFExporter()
    exporter.export(result, output_path)

    print(f"   ✓ Generated: {output_path.name}")
    print(f"     Elements: {result.element_count}, Geometry: {len(result.lines) + len(result.polylines) + len(result.hatches)}")

    # ========================================================================
    # 2. GROUND FLOOR SHOWING BASEMENT
    # ========================================================================
    print("\n2. Ground Floor - Extended View Depth (Show Basement)")
    print("   ViewRange: cut=1200mm, top=2400mm, bottom=0mm, view_depth=-2400mm")
    print("   Shows: Ground floor PLUS basement walls below (dashed lines)")

    extended_depth_range = ViewRange(
        cut_height=1200,
        top=2400,
        bottom=0,
        view_depth=-2400,  # Extend 8' below floor to see basement
    )

    ground_with_basement = FloorPlanView(
        "Ground Floor - With Basement",
        ground,
        view_range=extended_depth_range,
        scale=ViewScale.SCALE_1_50,
    )

    result = ground_with_basement.generate(spatial_index, cache)
    output_path = output_dir / "house_ground_with_basement.dxf"

    exporter.export(result, output_path)

    print(f"   ✓ Generated: {output_path.name}")
    print(f"     Elements: {result.element_count}, Geometry: {len(result.lines) + len(result.polylines) + len(result.hatches)}")

    # ========================================================================
    # 3. GROUND FLOOR WITH HIGH TOP (Show upper floor framing)
    # ========================================================================
    print("\n3. Ground Floor - High Top (Show Upper Floor Above)")
    print("   ViewRange: cut=1200mm, top=4000mm, bottom=0mm, view_depth=0mm")
    print("   Shows: Ground floor + upper floor walls above (lighter lines)")

    high_top_range = ViewRange(
        cut_height=1200,
        top=4000,         # Extend to 13' to see upper floor
        bottom=0,
        view_depth=0,
    )

    ground_with_upper = FloorPlanView(
        "Ground Floor - With Upper",
        ground,
        view_range=high_top_range,
        scale=ViewScale.SCALE_1_50,
    )

    result = ground_with_upper.generate(spatial_index, cache)
    output_path = output_dir / "house_ground_with_upper.dxf"

    exporter.export(result, output_path)

    print(f"   ✓ Generated: {output_path.name}")
    print(f"     Elements: {result.element_count}, Geometry: {len(result.lines) + len(result.polylines) + len(result.hatches)}")

    # ========================================================================
    # 4. BASEMENT PLAN
    # ========================================================================
    print("\n4. Basement Floor Plan")
    print("   ViewRange: cut=1200mm, top=2400mm, bottom=0mm, view_depth=0mm")
    print("   Shows: Basement walls only")

    basement_range = ViewRange(
        cut_height=1200,
        top=2400,
        bottom=0,
        view_depth=0,
    )

    basement_plan = FloorPlanView(
        "Basement Plan",
        basement,
        view_range=basement_range,
        scale=ViewScale.SCALE_1_50,
    )

    result = basement_plan.generate(spatial_index, cache)
    output_path = output_dir / "house_basement.dxf"

    exporter.export(result, output_path)

    print(f"   ✓ Generated: {output_path.name}")
    print(f"     Elements: {result.element_count}, Geometry: {len(result.lines) + len(result.polylines) + len(result.hatches)}")

    # ========================================================================
    # 5. UPPER FLOOR PLAN
    # ========================================================================
    print("\n5. Upper Floor Plan")
    print("   ViewRange: cut=1200mm, top=2400mm, bottom=0mm, view_depth=0mm")
    print("   Shows: Upper floor bedrooms only")

    upper_range = ViewRange(
        cut_height=1200,
        top=2400,
        bottom=0,
        view_depth=0,
    )

    upper_plan = FloorPlanView(
        "Upper Floor Plan",
        upper,
        view_range=upper_range,
        scale=ViewScale.SCALE_1_50,
    )

    result = upper_plan.generate(spatial_index, cache)
    output_path = output_dir / "house_upper.dxf"

    exporter.export(result, output_path)

    print(f"   ✓ Generated: {output_path.name}")
    print(f"     Elements: {result.element_count}, Geometry: {len(result.lines) + len(result.polylines) + len(result.hatches)}")

    # ========================================================================
    # 6. ROOM FOCUS: Bathroom Detail
    # ========================================================================
    print("\n6. Room Focus - Bathroom Detail (High Detail)")
    print("   ViewRange: cut=1000mm, top=2700mm, bottom=-100mm, view_depth=-100mm")
    print("   Shows: Lower cut height for fixtures, extended range for pipes")

    bathroom_range = ViewRange(
        cut_height=1000,   # Lower cut to show fixtures/counters
        top=2700,          # Show full ceiling height
        bottom=-100,       # Show slightly below floor
        view_depth=-100,   # Catch any below-floor elements (pipes, etc.)
    )

    bathroom_focus = FloorPlanView(
        "Ground Floor - Bathroom Detail",
        ground,
        view_range=bathroom_range,
        scale=ViewScale.SCALE_1_20,  # Larger scale for detail
    )

    result = bathroom_focus.generate(spatial_index, cache)
    output_path = output_dir / "house_bathroom_detail.dxf"

    exporter.export(result, output_path)

    print(f"   ✓ Generated: {output_path.name}")
    print(f"     Elements: {result.element_count}, Geometry: {len(result.lines) + len(result.polylines) + len(result.hatches)}")

    print("\n" + "="*60)
    print("All floor plans generated successfully!")
    print("="*60)


def main():
    """Run the ViewRange demo."""
    print("="*60)
    print("ViewRange Demo - Sprint 6 Issue #31")
    print("Revit-Style View Range Implementation")
    print("="*60)

    # Create building
    building, basement, ground, upper, all_elements = create_multi_level_house()

    # Generate various floor plans
    generate_floor_plans(building, basement, ground, upper, all_elements)

    print("\n" + "="*60)
    print("Demo Summary")
    print("="*60)
    print()
    print("ViewRange Parameters (Revit-style):")
    print("  • cut_height: Where horizontal section cuts (typically 1200mm / 4')")
    print("  • top: Maximum height to show (elements above are hidden)")
    print("  • bottom: Lower limit for standard visibility")
    print("  • view_depth: Extended visibility below bottom (for basement, etc.)")
    print()
    print("Display Behavior:")
    print("  • Elements CUT by plane → Heavy lines (1.4mm)")
    print("  • Elements between cut and bottom → Medium lines (0.7mm)")
    print("  • Elements between bottom and view_depth → Light lines (0.35mm)")
    print("  • Elements above top or below view_depth → Hidden")
    print()
    print("Use Cases Demonstrated:")
    print("  1. Standard floor plan (typical architectural drawings)")
    print("  2. Show elements below (basement visible from ground floor)")
    print("  3. Show elements above (upper floor visible from ground floor)")
    print("  4. Individual level plans (basement, ground, upper)")
    print("  5. Room detail focus (bathroom with custom range)")
    print()
    print("="*60)


if __name__ == "__main__":
    main()
