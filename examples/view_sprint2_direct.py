"""
View Sprint 2 geometry directly from build123d (not from IFC).

This script creates the building model and displays the geometry directly.
"""

try:
    from ocp_vscode import show
    from bimascode import Building, Level, WallType, Wall, FloorType, Floor, Roof, Length, LayerFunction
    from bimascode.utils.materials import MaterialLibrary

    print("Creating Sprint 2 building model...")

    # Create building
    building = Building("Sprint 2 Demo Building", address="456 Demo Street")

    # Create levels
    ground = Level(building, "Ground Floor", elevation=0)
    first = Level(building, "First Floor", elevation=Length(3, "m"))
    roof_level = Level(building, "Roof", elevation=Length(6, "m"))

    # Create materials
    concrete = MaterialLibrary.concrete("C30/37")
    brick = MaterialLibrary.brick()
    insulation = MaterialLibrary.insulation_mineral_wool()

    # Create wall type
    ext_wall_type = WallType("Exterior Wall - 310mm")
    ext_wall_type.add_layer(brick, 110, LayerFunction.FINISH_EXTERIOR)
    ext_wall_type.add_layer(insulation, 100, LayerFunction.THERMAL_INSULATION)
    ext_wall_type.add_layer(concrete, 100, LayerFunction.STRUCTURE, structural=True)

    # Create floor type
    floor_type = FloorType("Concrete Floor - 250mm")
    floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
    floor_type.add_layer(concrete, 50, LayerFunction.FINISH_INTERIOR)

    # Create roof type
    roof_type = FloorType("Flat Roof - 300mm")
    roof_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
    roof_type.add_layer(insulation, 80, LayerFunction.THERMAL_INSULATION)
    roof_type.add_layer(concrete, 20, LayerFunction.MEMBRANE)

    # Create walls on ground floor
    print("Creating walls...")
    walls = [
        Wall(ext_wall_type, (0, 0), (10000, 0), ground, name="South Wall"),
        Wall(ext_wall_type, (10000, 0), (10000, 8000), ground, name="East Wall"),
        Wall(ext_wall_type, (10000, 8000), (0, 8000), ground, name="North Wall"),
        Wall(ext_wall_type, (0, 8000), (0, 0), ground, name="West Wall"),
    ]

    # Create walls on first floor
    first_walls = [
        Wall(ext_wall_type, (0, 0), (10000, 0), first),
        Wall(ext_wall_type, (10000, 0), (10000, 8000), first),
        Wall(ext_wall_type, (10000, 8000), (0, 8000), first),
        Wall(ext_wall_type, (0, 8000), (0, 0), first),
    ]

    # Create floors
    boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
    ground_floor = Floor(floor_type, boundary, ground, name="Ground Floor Slab")
    first_floor = Floor(floor_type, boundary, first, name="First Floor Slab")

    # Create roof
    roof = Roof(roof_type, boundary, roof_level, slope=2.0, name="Flat Roof")

    print(f"Created {len(walls) + len(first_walls)} walls, 2 floors, 1 roof")

    # Collect all geometry
    print("\nExtracting build123d geometry...")
    shapes = []

    # Get geometry from all elements
    all_elements = []
    for level in building.levels:
        all_elements.extend(level.elements)

    for element in all_elements:
        try:
            geom = element.get_geometry()
            if geom:
                shapes.append(geom)
                print(f"  ✓ {element.__class__.__name__}: {element.name}")
        except Exception as e:
            print(f"  ✗ Failed for {element.name}: {e}")

    if shapes:
        print(f"\nDisplaying {len(shapes)} elements in OCP CAD Viewer...")
        show(*shapes)
        print("✓ Geometry displayed in viewer!")
    else:
        print("\n⚠ No geometry found to display")

except ImportError as e:
    print(f"Error: {e}")
    print("\nRequired packages:")
    print("  - ocp-vscode (for viewer)")
    print("\nInstall with: pip install ocp-vscode")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
