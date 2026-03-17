"""
Example: Creating and using materials with physical properties.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.units import Length
from bimascode.utils.materials import Material, MaterialCategory, MaterialLibrary

# Create a building
building = Building(
    name="Materials Example Building",
    unit_system="metric"
)

# Create a level
level_1 = Level(building, "Ground Floor", Length(0, "mm"))

print("="*70)
print("Material Definition Examples")
print("="*70)
print()

# Example 1: Create custom material from scratch
print("1. Custom Material (High-Performance Concrete)")
print("-" * 70)

custom_concrete = Material(
    name="High-Performance Concrete C50/60",
    category=MaterialCategory.CONCRETE,
    description="High-strength concrete for structural applications",
    density=2500,  # kg/m³
    thermal_conductivity=1.7,  # W/(m·K)
    specific_heat=900,  # J/(kg·K)
    sound_transmission_class=53,
    color=(180, 180, 180),  # Gray
    cost_per_unit=350.0,  # dollars per m³
    embodied_carbon=0.18,  # kgCO2e/kg
    recyclable=True
)

# Add custom properties
custom_concrete.set_property("Compressive_Strength", "50 MPa")
custom_concrete.set_property("Manufacturer", "Acme Concrete Co.")
custom_concrete.set_property("Fire_Rating", "R120")

print(f"  {custom_concrete}")
print(f"  Description: {custom_concrete.description}")
print(f"  Density: {custom_concrete.density} kg/m³")
print(f"  Thermal conductivity: {custom_concrete.thermal_conductivity} W/(m·K)")
print(f"  STC Rating: {custom_concrete.sound_transmission_class}")
print(f"  Embodied carbon: {custom_concrete.embodied_carbon} kgCO2e/kg")
print(f"  Recyclable: {custom_concrete.recyclable}")
print(f"  Custom properties: {custom_concrete.properties}")
print()

# Example 2: Use material library for common materials
print("2. Materials from Library")
print("-" * 70)

materials = {
    "concrete": MaterialLibrary.concrete("C30/37"),
    "steel": MaterialLibrary.steel("S355"),
    "timber": MaterialLibrary.timber("Pine"),
    "brick": MaterialLibrary.brick(),
    "glass": MaterialLibrary.glass("low-e"),
    "insulation": MaterialLibrary.insulation_mineral_wool(),
    "gypsum": MaterialLibrary.gypsum_board()
}

for name, material in materials.items():
    print(f"  {material}")

print()

# Example 3: Compare thermal properties
print("3. Thermal Performance Comparison")
print("-" * 70)

thermal_materials = [
    ("Concrete", MaterialLibrary.concrete()),
    ("Steel", MaterialLibrary.steel()),
    ("Timber", MaterialLibrary.timber()),
    ("Insulation", MaterialLibrary.insulation_mineral_wool()),
    ("Brick", MaterialLibrary.brick())
]

print(f"  {'Material':<20} {'k [W/(m·K)]':<15} {'Performance'}")
print(f"  {'-'*20} {'-'*15} {'-'*30}")

for name, mat in thermal_materials:
    k = mat.thermal_conductivity
    if k < 0.1:
        performance = "Excellent insulator"
    elif k < 1.0:
        performance = "Good insulator"
    elif k < 5.0:
        performance = "Moderate conductor"
    else:
        performance = "High conductor"

    print(f"  {name:<20} {k:<15.2f} {performance}")

print()

# Example 4: Sustainability comparison
print("4. Embodied Carbon Comparison")
print("-" * 70)

carbon_materials = [
    ("Timber (stores CO2)", MaterialLibrary.timber()),
    ("Concrete", MaterialLibrary.concrete()),
    ("Brick", MaterialLibrary.brick()),
    ("Glass", MaterialLibrary.glass()),
    ("Insulation", MaterialLibrary.insulation_mineral_wool()),
    ("Steel", MaterialLibrary.steel())
]

print(f"  {'Material':<25} {'Embodied Carbon [kgCO2e/kg]':<30} {'Rating'}")
print(f"  {'-'*25} {'-'*30} {'-'*20}")

for name, mat in carbon_materials:
    carbon = mat.embodied_carbon
    if carbon < 0:
        rating = "Carbon negative ✓"
    elif carbon < 0.5:
        rating = "Low carbon"
    elif carbon < 1.0:
        rating = "Medium carbon"
    else:
        rating = "High carbon"

    print(f"  {name:<25} {carbon:>10.2f}                      {rating}")

print()

# Example 5: Export materials to IFC
print("5. IFC Export with Materials")
print("-" * 70)

# Create a simple IFC file with materials
# Note: In Sprint 2, we'll assign materials to walls/floors
# For now, we're just exporting the material definitions

try:
    import ifcopenshell

    # Create IFC file
    ifc_file = ifcopenshell.file(schema="IFC4")

    # Export all materials to IFC
    ifc_materials = []
    for name, material in materials.items():
        ifc_mat = material.to_ifc(ifc_file)
        ifc_materials.append(ifc_mat)
        print(f"  ✓ Exported: {material.name}")

    # Also export custom concrete
    custom_concrete.to_ifc(ifc_file)
    print(f"  ✓ Exported: {custom_concrete.name}")

    # Save IFC file
    output_file = Path(__file__).parent / "output" / "materials_example.ifc"
    output_file.parent.mkdir(exist_ok=True)

    # We need to create minimal project structure for valid IFC
    # (IFC files need at least a project entity)
    building.export_ifc(str(output_file))

    print()
    print(f"  ✓ Exported to: {output_file}")
    print(f"  ✓ Total materials: {len(materials) + 1}")

except ImportError:
    print("  ⚠ ifcopenshell not available, skipping IFC export")

print()
print("="*70)
print("Material examples complete!")
print("="*70)
print()
print("Note: In Sprint 2, materials will be assigned to walls, floors, etc.")
print("      For now, they're defined but not yet associated with elements.")
