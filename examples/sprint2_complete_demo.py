"""
Sprint 2 Complete Demo - Walls, Floors, and Roofs

This example demonstrates all Sprint 2 features:
- Type/Instance parameter model
- Wall types with compound layer stacks
- Straight walls (no joins yet - Sprint 3)
- Floor/slab types and instances
- Flat roofs with drainage slope

Creates a simple 2-story building with walls, floors, and a roof.
"""

from bimascode import (
    Building, Level,
    WallType, Wall, FloorType, Floor, Roof,
    Layer, LayerFunction,
    Length
)
from bimascode.utils.materials import MaterialLibrary
from bimascode.architecture import (
    create_basic_wall_type,
    create_stud_wall_type,
    create_basic_floor_type,
    create_concrete_floor_type
)


def main():
    print("=" * 70)
    print("Sprint 2 Complete Demo: Walls, Floors, and Roofs")
    print("=" * 70)

    # Create building
    building = Building("Residential Building", address="123 Main St, Springfield")
    print(f"\n✓ Created building: {building.name}")

    # Create levels
    ground_floor = Level(building, "Ground Floor", elevation=0)
    first_floor = Level(building, "First Floor", elevation=Length(3, "m"))
    second_floor = Level(building, "Second Floor", elevation=Length(6, "m"))
    roof_level = Level(building, "Roof", elevation=Length(9, "m"))

    print(f"✓ Created {len(building.levels)} levels")
    for level in building.levels:
        print(f"  - {level.name} @ {level.elevation.m:.1f}m")

    # ========================================================================
    # PART 1: Wall Types
    # ========================================================================
    print("\n" + "=" * 70)
    print("PART 1: Wall Types with Compound Layer Stacks")
    print("=" * 70)

    # Create materials
    concrete = MaterialLibrary.concrete("C30/37")
    brick = MaterialLibrary.brick()
    insulation = MaterialLibrary.insulation_mineral_wool()
    gypsum = MaterialLibrary.gypsum_board()
    timber = MaterialLibrary.timber()

    # Exterior wall type (brick + insulation + gypsum)
    exterior_wall_type = WallType("Exterior Wall - 290mm")
    exterior_wall_type.add_layer(brick, 110, LayerFunction.FINISH_EXTERIOR, structural=False)
    exterior_wall_type.add_layer(insulation, 100, LayerFunction.THERMAL_INSULATION, structural=False)
    exterior_wall_type.add_layer(gypsum, 80, LayerFunction.STRUCTURE, structural=True)

    print(f"\n✓ Created {exterior_wall_type}")
    print(f"  Layers: {exterior_wall_type.layer_count}")
    print(f"  Total width: {exterior_wall_type.total_width_mm}mm")
    for i, layer in enumerate(exterior_wall_type.layers):
        print(f"    {i+1}. {layer}")

    # Interior wall type (using helper function)
    interior_wall_type = create_stud_wall_type(
        "Interior Wall - 115mm",
        stud_material=timber,
        stud_depth=90,
        interior_finish=gypsum,
        interior_finish_thickness=12.5,
        exterior_finish=gypsum,
        exterior_finish_thickness=12.5
    )

    print(f"\n✓ Created {interior_wall_type}")
    print(f"  Layers: {interior_wall_type.layer_count}")
    print(f"  Total width: {interior_wall_type.total_width_mm}mm")

    # Simple concrete wall type
    concrete_wall_type = create_basic_wall_type("Concrete Wall - 200mm", 200, concrete)
    print(f"\n✓ Created {concrete_wall_type}")

    # ========================================================================
    # PART 2: Walls
    # ========================================================================
    print("\n" + "=" * 70)
    print("PART 2: Creating Walls")
    print("=" * 70)

    # Create exterior walls (rectangular perimeter) on ground floor
    # Building is 12m x 8m
    ext_wall_1 = Wall(exterior_wall_type, (0, 0), (12000, 0), ground_floor, name="South Wall")
    ext_wall_2 = Wall(exterior_wall_type, (12000, 0), (12000, 8000), ground_floor, name="East Wall")
    ext_wall_3 = Wall(exterior_wall_type, (12000, 8000), (0, 8000), ground_floor, name="North Wall")
    ext_wall_4 = Wall(exterior_wall_type, (0, 8000), (0, 0), ground_floor, name="West Wall")

    print(f"\n✓ Created 4 exterior walls on {ground_floor.name}")
    for wall in [ext_wall_1, ext_wall_2, ext_wall_3, ext_wall_4]:
        print(f"  - {wall.name}: length={wall.length_length.m:.2f}m, width={wall.width_length.mm:.1f}mm, height={wall.height_length.m:.1f}m")

    # Create interior partition wall
    int_wall_1 = Wall(interior_wall_type, (6000, 0), (6000, 8000), ground_floor, name="Interior Partition")
    print(f"\n✓ Created interior wall: {int_wall_1.name}")
    print(f"  Length: {int_wall_1.length_length.m:.2f}m")
    print(f"  Width: {int_wall_1.width_length.mm:.1f}mm")

    # Create walls on first floor (reuse same wall types)
    first_ext_walls = [
        Wall(exterior_wall_type, (0, 0), (12000, 0), first_floor),
        Wall(exterior_wall_type, (12000, 0), (12000, 8000), first_floor),
        Wall(exterior_wall_type, (12000, 8000), (0, 8000), first_floor),
        Wall(exterior_wall_type, (0, 8000), (0, 0), first_floor),
    ]
    print(f"\n✓ Created 4 exterior walls on {first_floor.name}")

    # Demonstrate type/instance parameter model
    print("\n" + "-" * 70)
    print("Demonstrating Type/Instance Parameter Model:")
    print("-" * 70)
    print(f"Exterior wall type has {exterior_wall_type.instance_count} instances")
    print(f"All exterior walls have width: {ext_wall_1.width_length.mm:.1f}mm")

    # Change the type parameter - all instances update
    print("\nAdding 20mm finish layer to exterior wall type...")
    exterior_wall_type.add_layer(gypsum, 20, LayerFunction.FINISH_INTERIOR)
    print(f"Updated width: {exterior_wall_type.total_width_mm}mm")
    print(f"All walls now have width: {ext_wall_1.width_length.mm:.1f}mm")

    # ========================================================================
    # PART 3: Floor Types and Floors
    # ========================================================================
    print("\n" + "=" * 70)
    print("PART 3: Floors and Slabs")
    print("=" * 70)

    # Create floor type with layers
    floor_type = create_concrete_floor_type(
        "Concrete Floor - 250mm",
        slab_thickness=200,
        topping_thickness=50,
        topping_material=concrete
    )

    print(f"\n✓ Created {floor_type}")
    print(f"  Layers: {floor_type.layer_count}")
    print(f"  Total thickness: {floor_type.total_thickness_mm}mm")

    # Create ground floor slab
    floor_boundary = [(0, 0), (12000, 0), (12000, 8000), (0, 8000)]
    ground_slab = Floor(floor_type, floor_boundary, ground_floor, name="Ground Floor Slab")

    print(f"\n✓ Created {ground_slab.name}")
    print(f"  Area: {ground_slab.area_m2:.2f}m²")
    print(f"  Thickness: {ground_slab.thickness_length.mm:.1f}mm")
    print(f"  Centroid: ({ground_slab.get_centroid()[0]/1000:.1f}m, {ground_slab.get_centroid()[1]/1000:.1f}m)")

    # Create first floor slab
    first_slab = Floor(floor_type, floor_boundary, first_floor, name="First Floor Slab")
    print(f"\n✓ Created {first_slab.name}")
    print(f"  Area: {first_slab.area_m2:.2f}m²")

    # Create second floor slab
    second_slab = Floor(floor_type, floor_boundary, second_floor, name="Second Floor Slab")
    print(f"\n✓ Created {second_slab.name}")

    # ========================================================================
    # PART 4: Roof
    # ========================================================================
    print("\n" + "=" * 70)
    print("PART 4: Flat Roof with Drainage Slope")
    print("=" * 70)

    # Create roof type (similar to floor but with waterproofing)
    roof_type = FloorType("Flat Roof - 300mm")
    roof_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
    roof_type.add_layer(insulation, 80, LayerFunction.THERMAL_INSULATION)
    roof_type.add_layer(MaterialLibrary.concrete(), 20, LayerFunction.MEMBRANE)  # Waterproofing

    print(f"\n✓ Created {roof_type}")
    print(f"  Total thickness: {roof_type.total_thickness_mm}mm")

    # Create flat roof with 2% slope for drainage (typical for flat roofs)
    roof_boundary = [(0, 0), (12000, 0), (12000, 8000), (0, 8000)]
    roof = Roof(roof_type, roof_boundary, roof_level, slope=2.0, name="Flat Roof")

    print(f"\n✓ Created {roof.name}")
    print(f"  Area: {roof.area_m2:.2f}m²")
    print(f"  Slope: {roof.slope}° (for drainage)")
    print(f"  Thickness: {roof.thickness_length.mm:.1f}mm")

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 70)
    print("BUILDING SUMMARY")
    print("=" * 70)

    print(f"\nBuilding: {building.name}")
    print(f"Levels: {len(building.levels)}")

    for level in building.levels:
        print(f"\n{level.name} (Elevation: {level.elevation.m:.1f}m)")
        print(f"  Elements: {len(level.elements)}")

        # Count element types
        wall_count = sum(1 for e in level.elements if isinstance(e, Wall))
        floor_count = sum(1 for e in level.elements if isinstance(e, Floor))
        roof_count = sum(1 for e in level.elements if isinstance(e, Roof))

        if wall_count > 0:
            print(f"    Walls: {wall_count}")
        if floor_count > 0:
            print(f"    Floors: {floor_count}")
        if roof_count > 0:
            print(f"    Roofs: {roof_count}")

    # Type/Instance statistics
    print("\n" + "-" * 70)
    print("Type/Instance Statistics:")
    print("-" * 70)
    print(f"Exterior Wall Type: {exterior_wall_type.instance_count} instances")
    print(f"Interior Wall Type: {interior_wall_type.instance_count} instances")
    print(f"Floor Type: {floor_type.instance_count} instances")
    print(f"Roof Type: {roof_type.instance_count} instances")

    # Material usage
    print("\n" + "-" * 70)
    print("Material Usage:")
    print("-" * 70)
    print(f"Concrete: Structural walls, floors, roof")
    print(f"Brick: Exterior wall finish")
    print(f"Insulation: Exterior walls and roof")
    print(f"Gypsum Board: Interior finishes")
    print(f"Timber: Interior wall studs")

    # Parametric updates demonstration
    print("\n" + "-" * 70)
    print("Parametric Model Capabilities:")
    print("-" * 70)
    print("✓ Change wall type thickness → all wall instances update")
    print("✓ Change floor type layers → all floor instances update")
    print("✓ Individual elements can override type parameters")
    print("✓ Geometry automatically invalidates when parameters change")

    print("\n" + "=" * 70)
    print("Sprint 2 Demo Complete!")
    print("=" * 70)
    print("\nNext Sprint (Sprint 3):")
    print("  - Wall-to-wall joins (T-junctions, L-junctions)")
    print("  - Doors and windows with openings")
    print("  - Material layer assignment")
    print("  - Non-hosted openings")


if __name__ == "__main__":
    main()
