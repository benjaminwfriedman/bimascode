"""
Sprint 3 Demo: Doors, Windows, Openings, and Wall Joins

This example demonstrates all Sprint 3 features:
- Doors with automatic wall openings
- Windows with sill heights
- Floor/roof openings
- Wall join detection and processing

The model creates a simple building with:
- Four walls forming a room (with wall joins)
- Entry door
- Two windows
- Floor with stair opening
- Roof with skylight
"""

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import (
    # Wall components
    WallType,
    Wall,
    LayerFunction,
    create_basic_wall_type,
    # Floor components
    FloorType,
    Floor,
    create_concrete_floor_type,
    # Roof
    Roof,
    # Doors (Sprint 3)
    DoorType,
    Door,
    create_standard_door_type,
    create_double_door_type,
    # Windows (Sprint 3)
    WindowType,
    Window,
    create_standard_window_type,
    create_double_window_type,
    # Openings (Sprint 3)
    Opening,
    create_rectangular_opening,
    # Wall joins (Sprint 3)
    EndCapType,
)
from bimascode.utils.materials import MaterialLibrary


def main():
    """Create a building demonstrating Sprint 3 features."""

    print("=" * 60)
    print("Sprint 3 Demo: Doors, Windows, Openings, and Wall Joins")
    print("=" * 60)

    # =========================================================================
    # 1. Create Building and Level
    # =========================================================================

    print("\n1. Creating building and level...")
    building = Building("Sprint 3 Demo Building")
    ground_floor = Level(building, "Ground Floor", elevation=0)

    print(f"   Building: {building.name}")
    print(f"   Level: {ground_floor.name} at {ground_floor.elevation_mm}mm")

    # =========================================================================
    # 2. Create Wall Type
    # =========================================================================

    print("\n2. Creating wall type...")
    wall_type = WallType("Exterior Wall")
    concrete = MaterialLibrary.concrete()
    brick = MaterialLibrary.brick()

    # Add layers (exterior to interior)
    wall_type.add_layer(brick, 100, LayerFunction.FINISH_EXTERIOR)
    wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
    wall_type.add_layer(MaterialLibrary.gypsum_board(), 12.5, LayerFunction.FINISH_INTERIOR)

    print(f"   Wall type: {wall_type.name}")
    print(f"   Total width: {wall_type.total_width_mm}mm")
    print(f"   Layers: {wall_type.layer_count}")

    # =========================================================================
    # 3. Create Walls (forming a room)
    # =========================================================================

    print("\n3. Creating walls...")

    # Room dimensions: 6m x 5m
    room_length = 6000  # mm
    room_width = 5000   # mm
    wall_height = 3000  # mm

    # Create four walls
    wall_south = Wall(wall_type, (0, 0), (room_length, 0), ground_floor, height=wall_height, name="South Wall")
    wall_east = Wall(wall_type, (room_length, 0), (room_length, room_width), ground_floor, height=wall_height, name="East Wall")
    wall_north = Wall(wall_type, (room_length, room_width), (0, room_width), ground_floor, height=wall_height, name="North Wall")
    wall_west = Wall(wall_type, (0, room_width), (0, 0), ground_floor, height=wall_height, name="West Wall")

    walls = [wall_south, wall_east, wall_north, wall_west]
    for wall in walls:
        print(f"   {wall.name}: {wall.length:.0f}mm x {wall.height:.0f}mm")

    # =========================================================================
    # 4. Create Door Types
    # =========================================================================

    print("\n4. Creating door types...")

    entry_door_type = create_standard_door_type(
        "Entry Door",
        width=900,
        height=2100
    )

    double_door_type = create_double_door_type(
        "Double Entry",
        width=1800,
        height=2100
    )

    print(f"   {entry_door_type.name}: {entry_door_type.width}mm x {entry_door_type.height}mm")
    print(f"   {double_door_type.name}: {double_door_type.width}mm x {double_door_type.height}mm")

    # =========================================================================
    # 5. Create Doors
    # =========================================================================

    print("\n5. Creating doors...")

    # Place entry door on south wall (centered)
    door_offset = (room_length - entry_door_type.overall_width) / 2
    entry_door = Door(entry_door_type, wall_south, offset=door_offset, name="Main Entry")

    print(f"   {entry_door.name} on {entry_door.host_wall.name}")
    print(f"     Offset: {entry_door.offset:.0f}mm")
    print(f"     Dimensions: {entry_door.width:.0f}mm x {entry_door.height:.0f}mm")
    print(f"     Valid position: {entry_door.validate_position()}")

    # =========================================================================
    # 6. Create Window Types
    # =========================================================================

    print("\n6. Creating window types...")

    standard_window_type = create_standard_window_type(
        "Standard Window",
        width=1200,
        height=1500,
        sill_height=900
    )

    large_window_type = create_double_window_type(
        "Large Window",
        width=2400,
        height=1500,
        sill_height=900
    )

    print(f"   {standard_window_type.name}: {standard_window_type.width}mm x {standard_window_type.height}mm")
    print(f"   {large_window_type.name}: {large_window_type.width}mm x {large_window_type.height}mm (with mullion)")

    # =========================================================================
    # 7. Create Windows
    # =========================================================================

    print("\n7. Creating windows...")

    # Place windows on east and west walls
    window1 = Window(standard_window_type, wall_east, offset=1000, name="East Window")
    window2 = Window(large_window_type, wall_west, offset=1000, name="West Window")

    for window in [window1, window2]:
        print(f"   {window.name} on {window.host_wall.name}")
        print(f"     Offset: {window.offset:.0f}mm, Sill: {window.sill_height:.0f}mm")
        print(f"     Valid position: {window.validate_position()}")

    # =========================================================================
    # 8. Process Wall Joins
    # =========================================================================

    print("\n8. Processing wall joins...")

    # Process wall joins on the level
    ground_floor.process_wall_joins(end_cap_type=EndCapType.FLUSH)

    print(f"   Processed joins for {len(ground_floor.get_walls())} walls")

    # =========================================================================
    # 9. Create Floor
    # =========================================================================

    print("\n9. Creating floor...")

    floor_type = create_concrete_floor_type("Ground Floor Slab", slab_thickness=200)

    # Floor boundary (slightly larger than room to show foundation)
    floor_boundary = [
        (-200, -200),
        (room_length + 200, -200),
        (room_length + 200, room_width + 200),
        (-200, room_width + 200),
    ]
    ground_slab = Floor(floor_type, floor_boundary, ground_floor, name="Ground Slab")

    print(f"   {ground_slab.name}: {ground_slab.area_m2:.2f}m²")

    # =========================================================================
    # 10. Create Floor Opening (for stairs)
    # =========================================================================

    print("\n10. Creating floor opening...")

    # Stair opening in corner
    stair_opening = ground_slab.add_opening(
        [
            (4500, 3500),
            (5800, 3500),
            (5800, 4800),
            (4500, 4800),
        ],
        name="Stair Opening"
    )

    print(f"   {stair_opening.name}: {stair_opening.area_m2:.2f}m²")

    # =========================================================================
    # 11. Create Roof
    # =========================================================================

    print("\n11. Creating roof...")

    roof_level = Level(building, "Roof Level", elevation=wall_height)

    roof_type = create_concrete_floor_type("Flat Roof", slab_thickness=150)

    # Roof boundary (matches room with small overhang)
    roof_boundary = [
        (-100, -100),
        (room_length + 100, -100),
        (room_length + 100, room_width + 100),
        (-100, room_width + 100),
    ]
    roof = Roof(roof_type, roof_boundary, roof_level, slope=1.5, name="Flat Roof")

    print(f"   {roof.name}: {roof.area_m2:.2f}m², slope: {roof.slope:.1f}°")

    # =========================================================================
    # 12. Create Roof Opening (skylight)
    # =========================================================================

    print("\n12. Creating roof opening (skylight)...")

    skylight = roof.add_opening(
        [
            (2500, 2000),
            (3500, 2000),
            (3500, 3000),
            (2500, 3000),
        ],
        name="Skylight"
    )

    print(f"   {skylight.name}: {skylight.area_m2:.2f}m²")

    # =========================================================================
    # 13. Export to IFC
    # =========================================================================

    print("\n13. Exporting to IFC...")

    output_path = "output/sprint3_demo.ifc"
    building.export_ifc(output_path)

    print(f"   Exported to: {output_path}")

    # =========================================================================
    # Summary
    # =========================================================================

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    print(f"\nBuilding: {building.name}")
    print(f"Levels: {len(building.levels)}")

    print(f"\nGround Floor elements:")
    print(f"  - Walls: {len(ground_floor.get_walls())}")

    total_doors = sum(len(w.hosted_elements) for w in walls if hasattr(w, 'hosted_elements'))
    door_count = len([e for w in walls for e in w.hosted_elements if hasattr(e, 'sill_height') and e.sill_height == 0])
    window_count = total_doors - door_count

    print(f"  - Doors: {door_count}")
    print(f"  - Windows: {window_count}")
    print(f"  - Floor openings: {len(ground_slab.openings)}")
    print(f"\nRoof Level elements:")
    print(f"  - Roof openings: {len(roof.openings)}")

    print("\n" + "=" * 60)
    print("Sprint 3 Demo Complete!")
    print("=" * 60)
    print("\nOpen output/sprint3_demo.ifc in Bonsai or Autodesk Viewer to verify:")
    print("  ✓ Door/window voids visible in walls")
    print("  ✓ Wall corners meet cleanly")
    print("  ✓ Floor has stair opening")
    print("  ✓ Roof has skylight opening")


if __name__ == "__main__":
    main()
