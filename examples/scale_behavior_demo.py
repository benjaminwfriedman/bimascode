"""Scale Behavior Demo

Demonstrates the scale-dependent rendering system for creating
construction documents at different scales. Shows how views
automatically adjust detail levels, line weights, and visibility
based on the selected scale.

This example creates the same building model and generates floor
plans at three different scales to show how the system adapts:
- 1:50 (high detail) - Shows all elements with full detail
- 1:100 (medium detail) - Standard architectural scale
- 1:500 (low detail) - Site plan scale, hides small details
"""

from datetime import datetime
from pathlib import Path

from bimascode.architecture import create_basic_wall_type
from bimascode.architecture.door import Door
from bimascode.architecture.door_type import DoorType, DoorOperationType
from bimascode.architecture.floor import Floor
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.architecture.wall import Wall
from bimascode.architecture.window import Window
from bimascode.architecture.window_type import WindowType
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.export.ifc_exporter import IFCExporter
from bimascode.drawing.scale_helpers import (
    ScaleConfigurator,
    create_multi_scale_template_set,
)
from bimascode.drawing.view_base import DetailLevel, ViewScale
from bimascode.drawing.view_templates import ViewTemplate
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.materials import MaterialLibrary


def create_sample_building() -> tuple[Building, Level]:
    """Create a 3-bedroom, 2-bathroom ranch style home for demonstration.

    Layout (approximately 15m x 12m):
    - Living/Dining area (open plan)
    - Kitchen
    - 3 Bedrooms
    - 2 Bathrooms
    - Hallway connecting rooms
    """
    # Create building and level
    building = Building("Ranch Style Home - 3BR/2BA")
    ground = Level(building, "Ground Floor", 0.0)

    # Create wall types
    concrete = MaterialLibrary.concrete()
    exterior_wall = create_basic_wall_type("Exterior Wall", 200.0, concrete)
    interior_wall = create_basic_wall_type("Interior Wall", 100.0, concrete)

    # Dimensions (in mm)
    # Overall: 15000mm (15m) x 12000mm (12m)

    # Exterior walls (perimeter)
    Wall(exterior_wall, (0, 0), (15000, 0), ground, 2700)  # South wall
    Wall(exterior_wall, (15000, 0), (15000, 12000), ground, 2700)  # East wall
    Wall(exterior_wall, (15000, 12000), (0, 12000), ground, 2700)  # North wall
    Wall(exterior_wall, (0, 12000), (0, 0), ground, 2700)  # West wall

    # Interior walls - Main horizontal divisions
    # Separates living area from bedrooms
    Wall(interior_wall, (0, 6000), (5000, 6000), ground, 2700)  # Living area north wall (partial)
    Wall(interior_wall, (7000, 6000), (15000, 6000), ground, 2700)  # Hallway/bedroom divider

    # Interior walls - Vertical divisions
    # Kitchen wall
    Wall(interior_wall, (5000, 0), (5000, 6000), ground, 2700)  # Kitchen east wall

    # Hallway walls
    Wall(interior_wall, (7000, 6000), (7000, 12000), ground, 2700)  # Hallway west wall
    Wall(interior_wall, (11000, 6000), (11000, 12000), ground, 2700)  # Hallway east wall

    # Bedroom 1 (Master) walls
    Wall(interior_wall, (7000, 9000), (11000, 9000), ground, 2700)  # Master bedroom south wall

    # Bathroom 1 (Master ensuite) walls
    Wall(interior_wall, (9000, 9000), (9000, 12000), ground, 2700)  # Master bath divider

    # Bedroom 2 walls
    Wall(interior_wall, (11000, 9000), (15000, 9000), ground, 2700)  # Bedroom 2 south wall

    # Bathroom 2 walls
    Wall(interior_wall, (13000, 6000), (13000, 9000), ground, 2700)  # Bathroom 2 divider

    # Create door and window types
    glass = MaterialLibrary.glass()
    wood = MaterialLibrary.timber()

    # Standard single swing door (900mm wide x 2100mm high)
    interior_door_type = DoorType(
        "Interior Door",
        width=900.0,
        height=2100.0,
        operation_type=DoorOperationType.SINGLE_SWING_RIGHT,
        frame_material=wood,
        panel_material=wood
    )

    # Exterior door (1000mm wide x 2100mm high)
    exterior_door_type = DoorType(
        "Exterior Door",
        width=1000.0,
        height=2100.0,
        operation_type=DoorOperationType.SINGLE_SWING_RIGHT,
        frame_material=wood,
        panel_material=wood
    )

    # Standard window (1200mm wide x 1200mm high)
    standard_window_type = WindowType(
        "Standard Window",
        width=1200.0,
        height=1200.0,
        frame_material=wood,
        glazing_material=glass
    )

    # Large window (2400mm wide x 1500mm high)
    large_window_type = WindowType(
        "Large Window",
        width=2400.0,
        height=1500.0,
        frame_material=wood,
        glazing_material=glass
    )

    # Add doors
    # Wall 0: South wall (0,0) to (15000,0)
    # - Kitchen wall intersects at x=5000
    # Main entrance (centered in living area, well clear of kitchen wall)
    Door(exterior_door_type, ground.get_walls()[0], 2000.0, sill_height=0.0)

    # Wall 4: Living area north (0,6000) to (5000,6000)
    # - No intersections, can place door anywhere
    # Living/Dining to hallway passage (centered)
    Door(interior_door_type, ground.get_walls()[4], 2050.0, sill_height=0.0)

    # Wall 6: Kitchen wall (5000,0) to (5000,6000) - vertical
    # - Intersects south wall at y=0 and wall 4 at y=6000
    # Kitchen door (centered, well clear of both ends)
    Door(interior_door_type, ground.get_walls()[6], 3000.0, sill_height=0.0)

    # Wall 7: Hallway west (7000,6000) to (7000,12000) - vertical
    # - Intersects wall 5 at y=6000 and wall 9 at y=9000
    # Bedroom 3 door (between y=6000 and y=9000, centered)
    Door(interior_door_type, ground.get_walls()[7], 1050.0, sill_height=0.0)

    # Wall 8: Hallway east (11000,6000) to (11000,12000) - vertical
    # - Intersects wall 5 at y=6000 and wall 9 at y=9000
    # Master bedroom door (between y=6000 and y=9000, centered)
    Door(interior_door_type, ground.get_walls()[8], 1050.0, sill_height=0.0)

    # Wall 9: Master bedroom south (7000,9000) to (11000,9000) - horizontal
    # - Intersects walls 7, 10, and 8 at x=7000, x=9000, x=11000
    # Master bathroom door (between x=9000 and x=11000, centered)
    Door(interior_door_type, ground.get_walls()[9], 1050.0, sill_height=0.0)

    # Wall 10: Master bath divider (9000,9000) to (9000,12000) - vertical
    # - Intersects wall 9 at y=9000 and north wall at y=12000
    # No door needed here (already have door in wall 9)

    # Wall 11: Bedroom 2 south (11000,9000) to (15000,9000) - horizontal
    # - Intersects walls 8 and 12 at x=11000 and x=13000
    # Bedroom 2 door (between x=11000 and x=13000, centered)
    Door(interior_door_type, ground.get_walls()[11], 1050.0, sill_height=0.0)

    # Wall 12: Bathroom 2 divider (13000,6000) to (13000,9000) - vertical
    # - Intersects wall 5 at y=6000 and wall 11 at y=9000
    # Bathroom 2 door (centered between y=6000 and y=9000)
    Door(interior_door_type, ground.get_walls()[12], 1050.0, sill_height=0.0)

    # Add windows
    # Wall 0: South wall (0,0) to (15000,0)
    # - Kitchen wall at x=5000, door at x=2000-3000
    # Living room windows (between x=0 and x=5000, avoiding door)
    Window(standard_window_type, ground.get_walls()[0], 600.0, sill_height=900.0)
    Window(standard_window_type, ground.get_walls()[0], 3800.0, sill_height=900.0)

    # Kitchen windows (between x=5000 and x=15000)
    Window(standard_window_type, ground.get_walls()[0], 6000.0, sill_height=900.0)
    Window(standard_window_type, ground.get_walls()[0], 7500.0, sill_height=900.0)

    # Wall 1: East wall (15000,0) to (15000,12000)
    # - Wall 5 intersects at y=6000
    # - Wall 11 intersects at y=9000
    # Bedroom 3 window (between y=6000 and y=9000)
    Window(standard_window_type, ground.get_walls()[1], 7500.0, sill_height=900.0)

    # Bedroom 2 window (between y=9000 and y=12000)
    Window(standard_window_type, ground.get_walls()[1], 10500.0, sill_height=900.0)

    # Wall 2: North wall (15000,12000) to (0,12000) - goes right to left
    # - Wall 8 intersects at x=11000 (offset from right = 4000)
    # - Wall 10 intersects at x=9000 (offset from right = 6000)
    # - Wall 7 intersects at x=7000 (offset from right = 8000)
    # Master bedroom window (between x=9000 and x=11000, offset from right edge)
    Window(large_window_type, ground.get_walls()[2], 5000.0, sill_height=900.0)

    # Bedroom 2 window (between x=11000 and x=15000, offset from right edge)
    Window(standard_window_type, ground.get_walls()[2], 2000.0, sill_height=900.0)

    # Wall 3: West wall (0,12000) to (0,0) - goes top to bottom
    # - Wall 4 intersects at y=6000 (offset from top = 6000)
    # Living room window (between y=6000 and y=0, offset from top)
    Window(standard_window_type, ground.get_walls()[3], 9000.0, sill_height=900.0)

    # Create floor slab
    floor_type = FloorType("Concrete Slab")
    floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
    Floor(
        floor_type,
        [(0, 0), (15000, 0), (15000, 12000), (0, 12000)],
        ground
    )

    return building, ground


def demo_basic_scale_aware_templates():
    """Demo 1: Using pre-built scale-aware templates."""
    print("=" * 70)
    print("DEMO 1: Scale-Aware Templates")
    print("=" * 70)

    building, ground = create_sample_building()

    # Build spatial index
    spatial_index = SpatialIndex()
    for wall in ground.get_walls():
        spatial_index.insert(wall)
        # Also insert hosted elements (doors and windows)
        for hosted_element in wall.hosted_elements:
            spatial_index.insert(hosted_element)

    cache = RepresentationCache()

    # Create views at different scales using factory methods
    scales = [
        (ViewScale.SCALE_1_50, "High Detail"),
        (ViewScale.SCALE_1_100, "Standard"),
        (ViewScale.SCALE_1_500, "Site Plan"),
    ]

    for scale, description in scales:
        # Use the factory method that automatically configures for scale
        template = ViewTemplate.floor_plan_scaled(scale)

        view = FloorPlanView(
            f"Ground Floor @ {scale.name}",
            ground,
            scale=scale,
            template=template,
        )

        result = view.generate(spatial_index, cache)

        print(f"\n{description} ({scale.name}):")
        print(f"  Detail Level: {scale.get_default_detail_level().value}")
        print(f"  Elements: {result.element_count}")
        print(f"  Lines: {len(result.lines)}")
        print(f"  Generation time: {result.generation_time:.3f}s")


def demo_scale_configurator():
    """Demo 2: Using ScaleConfigurator for custom configurations."""
    print("\n" + "=" * 70)
    print("DEMO 2: ScaleConfigurator API")
    print("=" * 70)

    building, ground = create_sample_building()

    spatial_index = SpatialIndex()
    for wall in ground.get_walls():
        spatial_index.insert(wall)
        # Also insert hosted elements (doors and windows)
        for hosted_element in wall.hosted_elements:
            spatial_index.insert(hosted_element)

    cache = RepresentationCache()

    # Use ScaleConfigurator for programmatic template creation
    configurator = ScaleConfigurator()

    # Example 1: Create template with custom settings
    template_1 = configurator.create_template_for_scale(
        ViewScale.SCALE_1_200,
        view_type="floor_plan",
        hide_small_details=True,
        reduce_line_weights=True,
    )

    view_1 = FloorPlanView(
        "Custom Config 1:200",
        ground,
        scale=ViewScale.SCALE_1_200,
        template=template_1,
    )

    result_1 = view_1.generate(spatial_index, cache)

    print("\nCustom Configuration (1:200):")
    print(f"  Small details hidden: Yes")
    print(f"  Line weights reduced: Yes")
    print(f"  Lines generated: {len(result_1.lines)}")

    # Example 2: Override detail level
    template_2 = configurator.create_template_for_scale(
        ViewScale.SCALE_1_100,
        view_type="floor_plan",
        custom_detail_level=DetailLevel.LOW,  # Force low detail at 1:100
    )

    view_2 = FloorPlanView(
        "Forced Low Detail 1:100",
        ground,
        scale=ViewScale.SCALE_1_100,
        template=template_2,
    )

    result_2 = view_2.generate(spatial_index, cache)

    print("\nForced Low Detail (1:100):")
    print(f"  Normal detail level: {ViewScale.SCALE_1_100.get_default_detail_level().value}")
    print(f"  Forced detail level: {DetailLevel.LOW.value}")
    print(f"  Lines generated: {len(result_2.lines)}")


def demo_scale_recommendation():
    """Demo 3: Intelligent scale recommendation."""
    print("\n" + "=" * 70)
    print("DEMO 3: Scale Recommendation")
    print("=" * 70)

    configurator = ScaleConfigurator()

    # Recommend scale based on content size and paper
    building_width = 50000  # 50 meters

    recommended = configurator.recommend_scale(
        "floor_plan",
        content_size=building_width,
        target_paper_size="A3",
    )

    print(f"\nBuilding width: {building_width/1000}m")
    print(f"Target paper: A3 (420mm)")
    print(f"Recommended scale: {recommended.name}")
    print(f"  Detail level: {recommended.get_default_detail_level().value}")

    # Get visibility thresholds for this scale
    thresholds = configurator.get_visibility_thresholds(recommended)
    print(f"\nVisibility thresholds at {recommended.name}:")
    for element_type, threshold in thresholds.items():
        if threshold > 0:
            print(f"  {element_type}: {threshold}mm minimum")


def demo_multi_scale_export():
    """Demo 4: Export to DXF at multiple scales."""
    print("\n" + "=" * 70)
    print("DEMO 4: Multi-Scale DXF Export")
    print("=" * 70)

    building, ground = create_sample_building()

    spatial_index = SpatialIndex()
    for wall in ground.get_walls():
        spatial_index.insert(wall)
        # Also insert hosted elements (doors and windows)
        for hosted_element in wall.hosted_elements:
            spatial_index.insert(hosted_element)

    cache = RepresentationCache()

    # Create template set for all standard scales
    templates = create_multi_scale_template_set("floor_plan")

    print(f"\nCreated {len(templates)} templates for standard scales:")
    for scale in templates.keys():
        print(f"  - {scale.name}")

    # Generate views at multiple scales
    views = []
    for scale, template in templates.items():
        view = FloorPlanView(
            f"Ground Floor {scale.name}",
            ground,
            scale=scale,
            template=template,
        )
        result = view.generate(spatial_index, cache)
        views.append((view.name, result))

    # Export all to single DXF file with offsets
    exporter = DXFExporter()

    # Create output directory if it doesn't exist
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"scale_demo_multi_scale_{timestamp}.dxf"

    # Create views with offsets
    spacing = 25000
    views_with_offsets = [
        (result, (i * spacing, 0.0))
        for i, (_, result) in enumerate(views)
    ]
    exporter.export_multiple(views_with_offsets, str(output_path))

    print(f"\nExported {len(views)} views to: {output_path}")
    print("Each view shows the same building at different scales")

    # Also export the building model to IFC
    ifc_exporter = IFCExporter()
    ifc_path = output_dir / f"scale_demo_building_{timestamp}.ifc"
    ifc_exporter.export(building, str(ifc_path))
    print(f"Exported 3D building model to: {ifc_path}")


def demo_manual_configuration():
    """Demo 5: Manual fine-grained control."""
    print("\n" + "=" * 70)
    print("DEMO 5: Manual Configuration")
    print("=" * 70)

    building, ground = create_sample_building()

    spatial_index = SpatialIndex()
    for wall in ground.get_walls():
        spatial_index.insert(wall)
        # Also insert hosted elements (doors and windows)
        for hosted_element in wall.hosted_elements:
            spatial_index.insert(hosted_element)

    cache = RepresentationCache()

    # Manual configuration with full control
    template = ViewTemplate("Custom Template")

    # Set scale behavior with custom thresholds
    from bimascode.drawing.view_base import ScaleBehaviorConfig

    custom_config = ScaleBehaviorConfig(
        detail_level=DetailLevel.MEDIUM,
        min_element_size=75.0,  # Custom threshold
        min_line_length=30.0,  # Custom threshold
        line_weight_factor=0.85,  # Custom line weight reduction
        show_small_details=True,
    )

    template.set_scale_behavior(
        ViewScale.SCALE_1_100, DetailLevel.MEDIUM, custom_config
    )

    view = FloorPlanView(
        "Custom Manual Config",
        ground,
        scale=ViewScale.SCALE_1_100,
        template=template,
    )

    result = view.generate(spatial_index, cache)

    print("\nManual Configuration:")
    print(f"  Min element size: {custom_config.min_element_size}mm")
    print(f"  Min line length: {custom_config.min_line_length}mm")
    print(f"  Line weight factor: {custom_config.line_weight_factor}")
    print(f"  Show small details: {custom_config.show_small_details}")
    print(f"  Lines generated: {len(result.lines)}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SCALE-DEPENDENT RENDERING DEMONSTRATION")
    print("=" * 70)
    print(
        "\nThis demo shows how the view system automatically adapts"
        "\nrendering based on scale to maintain visual clarity and"
        "\nappropriate level of detail for construction documents.\n"
    )

    # Run all demos
    demo_basic_scale_aware_templates()
    demo_scale_configurator()
    demo_scale_recommendation()
    demo_multi_scale_export()
    demo_manual_configuration()

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. Use ViewTemplate.floor_plan_scaled() for quick setup")
    print("  2. Use ScaleConfigurator for programmatic control")
    print("  3. System automatically adjusts detail based on scale")
    print("  4. Full manual control available when needed")
    print("  5. All scales maintain backward compatibility")
    print("=" * 70 + "\n")
