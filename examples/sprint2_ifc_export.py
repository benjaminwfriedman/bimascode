"""
Sprint 2 IFC Export Example

Demonstrates IFC export with all Sprint 2 features:
- Walls with compound layer stacks
- Floors/slabs
- Flat roofs
- Material assignments
"""

from bimascode import Building, Level, WallType, Wall, FloorType, Floor, Roof, Length, LayerFunction
from bimascode.utils.materials import MaterialLibrary

# Create building
building = Building("Sprint 2 Demo Building", address="456 Demo Street")
print(f"Created: {building.name}")

# Create levels
ground = Level(building, "Ground Floor", elevation=0)
first = Level(building, "First Floor", elevation=Length(3, "m"))
roof_level = Level(building, "Roof", elevation=Length(6, "m"))
print(f"Created {len(building.levels)} levels")

# Create materials
concrete = MaterialLibrary.concrete("C30/37")
brick = MaterialLibrary.brick()
insulation = MaterialLibrary.insulation_mineral_wool()
gypsum = MaterialLibrary.gypsum_board()

# Create wall type (exterior wall: brick + insulation + concrete)
ext_wall_type = WallType("Exterior Wall - 310mm")
ext_wall_type.add_layer(brick, 110, LayerFunction.FINISH_EXTERIOR)
ext_wall_type.add_layer(insulation, 100, LayerFunction.THERMAL_INSULATION)
ext_wall_type.add_layer(concrete, 100, LayerFunction.STRUCTURE, structural=True)
print(f"\nCreated wall type: {ext_wall_type.name} ({ext_wall_type.total_width_mm}mm)")

# Create floor type (concrete slab + topping)
floor_type = FloorType("Concrete Floor - 250mm")
floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
floor_type.add_layer(concrete, 50, LayerFunction.FINISH_INTERIOR)  # Screed
print(f"Created floor type: {floor_type.name} ({floor_type.total_thickness_mm}mm)")

# Create roof type
roof_type = FloorType("Flat Roof - 300mm")
roof_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
roof_type.add_layer(insulation, 80, LayerFunction.THERMAL_INSULATION)
roof_type.add_layer(concrete, 20, LayerFunction.MEMBRANE)
print(f"Created roof type: {roof_type.name} ({roof_type.total_thickness_mm}mm)")

# Create perimeter walls on ground floor (10m x 8m building)
print(f"\nCreating walls on {ground.name}...")
walls = [
    Wall(ext_wall_type, (0, 0), (10000, 0), ground, name="South Wall"),
    Wall(ext_wall_type, (10000, 0), (10000, 8000), ground, name="East Wall"),
    Wall(ext_wall_type, (10000, 8000), (0, 8000), ground, name="North Wall"),
    Wall(ext_wall_type, (0, 8000), (0, 0), ground, name="West Wall"),
]
print(f"Created {len(walls)} walls")

# Create walls on first floor
print(f"Creating walls on {first.name}...")
first_walls = [
    Wall(ext_wall_type, (0, 0), (10000, 0), first),
    Wall(ext_wall_type, (10000, 0), (10000, 8000), first),
    Wall(ext_wall_type, (10000, 8000), (0, 8000), first),
    Wall(ext_wall_type, (0, 8000), (0, 0), first),
]
print(f"Created {len(first_walls)} walls")

# Create floors
boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
print(f"\nCreating floors...")
ground_floor = Floor(floor_type, boundary, ground, name="Ground Floor Slab")
first_floor = Floor(floor_type, boundary, first, name="First Floor Slab")
print(f"Ground floor: {ground_floor.area_m2:.1f}m²")
print(f"First floor: {first_floor.area_m2:.1f}m²")

# Create roof with drainage slope
print(f"\nCreating roof...")
roof = Roof(roof_type, boundary, roof_level, slope=2.0, name="Flat Roof")
print(f"Roof: {roof.area_m2:.1f}m² with {roof.slope}° slope")

# Export to IFC
output_file = "examples/output/sprint2_demo.ifc"
print(f"\n{'='*60}")
print(f"Exporting to IFC: {output_file}")
print(f"{'='*60}")

building.export_ifc(output_file)

print(f"\n✓ Export complete!")
print(f"\nBuilding Summary:")
print(f"  Levels: {len(building.levels)}")
print(f"  Total walls: {sum(len([e for e in level.elements if isinstance(e, Wall)]) for level in building.levels)}")
print(f"  Total floors: {sum(len([e for e in level.elements if isinstance(e, Floor)]) for level in building.levels)}")
print(f"  Total roofs: {sum(len([e for e in level.elements if isinstance(e, Roof)]) for level in building.levels)}")

print(f"\nIFC file created: {output_file}")
print(f"Open in: Bonsai, FreeCAD, Revit, or any IFC viewer")
