"""
Curtain wall demonstration.

This example shows how to create curtain walls with the bimascode library,
demonstrating the Revit-compatible curtain wall system.
"""

from pathlib import Path

from bimascode.spatial import Building, Level
from bimascode.architecture.curtain_wall import (
    MullionProfile,
    MullionType,
    GlazedPanelType,
    OpaquePanelType,
    GridLayout,
    GridJustification,
    CurtainWallType,
    CurtainWall,
)
from bimascode.architecture import (
    Wall,
    WallType,
    create_basic_wall_type,
)
from bimascode.utils.materials import MaterialLibrary


def create_mullion_types() -> dict[str, MullionType]:
    """Create standard mullion types."""
    # Standard interior mullion (50x100mm rectangular)
    interior_profile = MullionProfile(width=50, depth=100)
    interior_mullion = MullionType(
        name="Standard Interior",
        profile=interior_profile,
        material=MaterialLibrary.steel(),
        finish="anodized",
    )

    # Border mullion (larger, 75x120mm)
    border_profile = MullionProfile(width=75, depth=120)
    border_mullion = MullionType(
        name="Border Mullion",
        profile=border_profile,
        material=MaterialLibrary.steel(),
        finish="anodized",
    )

    # Corner mullion (L-section approximated with rectangular)
    corner_profile = MullionProfile(width=100, depth=100)
    corner_mullion = MullionType(
        name="Corner Mullion",
        profile=corner_profile,
        material=MaterialLibrary.steel(),
        thermal_break=True,
        finish="painted",
        color=(50, 50, 50),
    )

    return {
        "interior": interior_mullion,
        "border": border_mullion,
        "corner": corner_mullion,
    }


def create_panel_types() -> dict[str, GlazedPanelType | OpaquePanelType]:
    """Create standard panel types."""
    # Double glazed vision panel
    vision_panel = GlazedPanelType(
        name="Vision Panel",
        glazing_type="double",
        glass_thickness=6.0,
        air_gap=12.0,
        low_e=True,
        tint="clear",
    )

    # Triple glazed high-performance panel
    high_perf_panel = GlazedPanelType(
        name="High Performance",
        glazing_type="triple",
        glass_thickness=6.0,
        air_gap=12.0,
        low_e=True,
    )

    # Spandrel panel (opaque)
    spandrel_panel = OpaquePanelType(
        name="Spandrel",
        material=MaterialLibrary.steel(),
        insulation_thickness=50.0,
        face_thickness=6.0,
        backing_thickness=12.0,
    )

    return {
        "vision": vision_panel,
        "high_perf": high_perf_panel,
        "spandrel": spandrel_panel,
    }


def main():
    """Create a building with curtain walls."""
    # Create building and level
    building = Building("Curtain Wall Demo")
    ground = Level(building, "Ground Floor", elevation=0)

    # Create mullion and panel types
    mullion_types = create_mullion_types()
    panel_types = create_panel_types()

    # Create curtain wall type with fixed distance grid
    curtain_type_1 = CurtainWallType(
        name="Standard Curtain Wall",
        # Vertical grid: 1200mm spacing
        vertical_grid_layout=GridLayout.FIXED_DISTANCE,
        vertical_grid_spacing=1200.0,
        vertical_justification=GridJustification.CENTER,
        adjust_for_mullion_size_vertical=True,
        # Horizontal grid: 1500mm spacing
        horizontal_grid_layout=GridLayout.FIXED_DISTANCE,
        horizontal_grid_spacing=1500.0,
        horizontal_justification=GridJustification.CENTER,
        adjust_for_mullion_size_horizontal=True,
        # Vertical mullions
        vertical_interior_mullion_type=mullion_types["interior"],
        vertical_border_1_mullion_type=mullion_types["border"],
        vertical_border_2_mullion_type=mullion_types["border"],
        # Horizontal mullions
        horizontal_interior_mullion_type=mullion_types["interior"],
        horizontal_border_1_mullion_type=mullion_types["border"],
        horizontal_border_2_mullion_type=mullion_types["border"],
        # Default panel
        default_panel_type=panel_types["vision"],
    )

    # Create curtain wall type with fixed number of divisions
    curtain_type_2 = CurtainWallType(
        name="Fixed Grid Curtain Wall",
        vertical_grid_layout=GridLayout.FIXED_NUMBER,
        vertical_grid_number=4,
        horizontal_grid_layout=GridLayout.FIXED_NUMBER,
        horizontal_grid_number=3,
        vertical_interior_mullion_type=mullion_types["interior"],
        horizontal_interior_mullion_type=mullion_types["interior"],
        default_panel_type=panel_types["high_perf"],
    )

    # Place curtain walls
    # South facade - standard curtain wall
    cw_south = CurtainWall(
        curtain_wall_type=curtain_type_1,
        start_point=(0, 0),
        end_point=(12000, 0),
        level=ground,
        height=4000,
        name="South Facade",
    )

    # East facade - fixed grid
    cw_east = CurtainWall(
        curtain_wall_type=curtain_type_2,
        start_point=(12000, 0),
        end_point=(12000, 8000),
        level=ground,
        height=4000,
        name="East Facade",
    )

    # Override specific panels with spandrel (bottom row)
    for u in range(cw_south.grid.u_count):
        cw_south.set_panel_type(u, 0, panel_types["spandrel"])

    # Print summary
    print("Curtain Wall Demo")
    print("=" * 50)
    print(f"Building: {building.name}")
    print(f"Level: {ground.name}")
    print()
    print("Curtain Walls:")
    print(f"  - {cw_south.name}: {cw_south.width:.0f}mm x {cw_south.height:.0f}mm")
    print(f"    Grid: {cw_south.grid.u_count} x {cw_south.grid.v_count} cells")
    print(f"  - {cw_east.name}: {cw_east.width:.0f}mm x {cw_east.height:.0f}mm")
    print(f"    Grid: {cw_east.grid.u_count} x {cw_east.grid.v_count} cells")
    print()

    # Generate 3D geometry
    print("Generating geometry...")
    south_geom = cw_south.get_geometry()
    east_geom = cw_east.get_geometry()
    print(f"  South facade geometry: {type(south_geom).__name__}")
    print(f"  East facade geometry: {type(east_geom).__name__}")

    # Generate 2D plan representation
    print()
    print("Generating floor plan representation...")
    south_plan = cw_south.get_plan_representation(cut_height=1200)
    east_plan = cw_east.get_plan_representation(cut_height=1200)
    print(f"  South facade: {len(south_plan)} primitives")
    print(f"  East facade: {len(east_plan)} primitives")

    print()
    print("Demo complete!")

    return building


if __name__ == "__main__":
    main()
