"""
Sprint 1 Complete Demo - All Features Together

This example demonstrates all Sprint 1 completed features:
1. Building & Level hierarchy
2. Grid Lines (orthogonal layout)
3. Material Definition with properties
4. Units Management (metric/imperial)
5. IFC Export
6. IFC Import (round-trip)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.grid import GridLine, create_orthogonal_grid
from bimascode.utils.units import Length, UnitSystem
from bimascode.utils.materials import Material, MaterialCategory, MaterialLibrary
from bimascode.export import IFCExporter, IFCImporter

print("="*80)
print(" BIM as Code v1.0 - Sprint 1 Complete Demonstration")
print("="*80)
print()

# ============================================================================
# PART 1: Create Building Hierarchy
# ============================================================================
print("PART 1: Building Hierarchy")
print("-" * 80)

building = Building(
    name="Sprint 1 Demo Building",
    address="123 BIM Street, Code City, 12345",
    description="Demonstration of all Sprint 1 features",
    unit_system=UnitSystem.METRIC
)

print(f"✓ Created: {building.name}")
print(f"  Address: {building.address}")
print(f"  Unit System: {building.unit_system.value}")
print(f"  GUID: {building.guid}")
print()

# ============================================================================
# PART 2: Add Levels (Building Storeys)
# ============================================================================
print("PART 2: Building Levels")
print("-" * 80)

levels = [
    Level(building, "Basement", Length(-3000, "mm"), "Underground parking"),
    Level(building, "Ground Floor", Length(0, "mm"), "Main entrance and lobby"),
    Level(building, "First Floor", Length(4000, "mm"), "Office spaces"),
    Level(building, "Second Floor", Length(8000, "mm"), "Office spaces"),
    Level(building, "Roof", Length(12000, "mm"), "Mechanical and roof access")
]

print(f"✓ Created {len(building.levels)} levels:")
for level in building.levels:
    elevation_m = level.elevation.m
    print(f"  • {level.name:<15} Elevation: {elevation_m:>6.1f}m ({level.elevation_mm:.0f}mm)")
print()

# ============================================================================
# PART 3: Create Grid System
# ============================================================================
print("PART 3: Architectural Grid System")
print("-" * 80)

# Create a 5x4 orthogonal grid
# Vertical grids: A, B, C, D, E (@ 6m spacing)
# Horizontal grids: 1, 2, 3, 4 (@ 8m spacing)

grids = create_orthogonal_grid(
    building,
    x_grid_labels=["A", "B", "C", "D", "E"],
    x_grid_positions=[0, 6000, 12000, 18000, 24000],  # mm
    y_grid_labels=["1", "2", "3", "4"],
    y_grid_positions=[0, 8000, 16000, 24000],  # mm
    x_extent=(0, 24000),
    y_extent=(0, 24000)
)

print(f"✓ Created {len(building.grids)} grid lines:")
print(f"  Vertical grids (A-E): 5 lines @ 6m spacing")
print(f"  Horizontal grids (1-4): 4 lines @ 8m spacing")
print(f"  Building footprint: 24m x 24m")
print()

# Show some grid details
print("  Sample grid lines:")
for grid in building.grids[:3]:
    start_m = (grid.start_point[0].m, grid.start_point[1].m)
    end_m = (grid.end_point[0].m, grid.end_point[1].m)
    orient = "Vertical" if grid.is_vertical() else "Horizontal"
    print(f"    Grid {grid.label}: {start_m} → {end_m} ({orient})")
print()

# ============================================================================
# PART 4: Define Materials
# ============================================================================
print("PART 4: Material Library")
print("-" * 80)

# Use pre-defined materials from library
materials = {
    "Structure": {
        "concrete": MaterialLibrary.concrete("C30/37"),
        "steel": MaterialLibrary.steel("S355"),
    },
    "Envelope": {
        "brick": MaterialLibrary.brick(),
        "glass": MaterialLibrary.glass("low-e"),
        "insulation": MaterialLibrary.insulation_mineral_wool(),
    },
    "Interior": {
        "gypsum": MaterialLibrary.gypsum_board(),
        "timber": MaterialLibrary.timber("Oak"),
    }
}

print("✓ Material library loaded:")
for category, mats in materials.items():
    print(f"\n  {category}:")
    for name, mat in mats.items():
        props = []
        if mat.density:
            props.append(f"ρ={mat.density}kg/m³")
        if mat.thermal_conductivity:
            props.append(f"k={mat.thermal_conductivity}W/(m·K)")
        if mat.embodied_carbon:
            props.append(f"CO2={mat.embodied_carbon:+.2f}kgCO2e/kg")

        props_str = ", ".join(props)
        print(f"    • {mat.name:<30} ({props_str})")
print()

# Create a custom material
custom_concrete = Material(
    name="High-Performance Concrete HPС60",
    category=MaterialCategory.CONCRETE,
    description="Ultra-high performance concrete for main columns",
    density=2600,
    thermal_conductivity=1.9,
    specific_heat=920,
    cost_per_unit=450.0,
    embodied_carbon=0.20,
    recyclable=True
)
custom_concrete.set_property("compressive_strength", "60 MPa")
custom_concrete.set_property("fire_rating", "R180")

print("✓ Custom material created:")
print(f"  {custom_concrete.name}")
print(f"  Properties: {custom_concrete.properties}")
print()

# ============================================================================
# PART 5: Export to IFC
# ============================================================================
print("PART 5: IFC Export")
print("-" * 80)

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

ifc_file = output_dir / "sprint1_demo.ifc"
building.export_ifc(str(ifc_file))

file_size_kb = ifc_file.stat().st_size / 1024
print(f"✓ Exported to: {ifc_file}")
print(f"  File size: {file_size_kb:.1f} KB")
print(f"  Schema: IFC4")
print()

# Validate the export
exporter = IFCExporter()
validation = exporter.validate_export(str(ifc_file))

if validation.get("valid"):
    print("✓ IFC file validation successful:")
    entities = validation.get("entities", {})
    for entity_type, count in entities.items():
        if count > 0:
            print(f"  • {entity_type}: {count}")
else:
    print(f"✗ Validation failed: {validation.get('error')}")
print()

# ============================================================================
# PART 6: Import from IFC (Round-Trip Test)
# ============================================================================
print("PART 6: IFC Import (Round-Trip Verification)")
print("-" * 80)

# Import the file we just exported
imported_building = Building.from_ifc(str(ifc_file))

print(f"✓ Imported building: {imported_building.name}")
print()

# Verify data preservation
print("Data preservation check:")
checks = [
    ("Building name", building.name, imported_building.name),
    ("Address", building.address, imported_building.address),
    ("GUID", building.guid, imported_building.guid),
    ("Number of levels", len(building.levels), len(imported_building.levels)),
    ("Number of grids", len(building.grids), len(imported_building.grids)),
]

all_passed = True
for check_name, original, imported in checks:
    match = "✓" if original == imported else "✗"
    if original != imported:
        all_passed = False
    print(f"  {match} {check_name}: {original} == {imported}")

print()

# Check level elevations
print("Level elevation preservation:")
for orig_level, imp_level in zip(building.levels, imported_building.levels):
    elevation_match = abs(orig_level.elevation_mm - imp_level.elevation_mm) < 0.01
    match = "✓" if elevation_match else "✗"
    if not elevation_match:
        all_passed = False
    print(f"  {match} {orig_level.name}: {orig_level.elevation_mm:.0f}mm == {imp_level.elevation_mm:.0f}mm")

print()

if all_passed:
    print("✓ All round-trip checks PASSED - data preserved perfectly!")
else:
    print("✗ Some checks FAILED - data may have been lost")

print()

# ============================================================================
# PART 7: Summary
# ============================================================================
print("="*80)
print(" Sprint 1 Feature Summary")
print("="*80)
print()

features = [
    ("Building Hierarchy", "Building + Site structure with metadata", "✓ Complete"),
    ("Building Storeys", f"{len(building.levels)} levels with elevations", "✓ Complete"),
    ("Grid Lines", f"{len(building.grids)} orthogonal grid axes", "✓ Complete"),
    ("Material System", f"{sum(len(m) for m in materials.values()) + 1} materials defined", "✓ Complete"),
    ("Units Management", "Metric/Imperial with auto-conversion", "✓ Complete"),
    ("IFC Export", f"IFC4 schema ({file_size_kb:.1f}KB file)", "✓ Complete"),
    ("IFC Import", "Round-trip with data preservation", "✓ Complete"),
]

for feature, description, status in features:
    print(f"{status} {feature:<20} {description}")

print()
print("="*80)
print(f" Sprint 1 Development: COMPLETE")
print("="*80)
print()
print("Next Steps (Sprint 2):")
print("  • Walls (straight, curved, complex profiles)")
print("  • Flat roofs")
print("  • Doors and windows")
print("  • Material assignment to elements")
print("  • 3D visualization with OCP CAD Viewer")
print()
print("For more information, see:")
print(f"  • Documentation: /Users/benjaminfriedman/repos/bimcode/README.md")
print(f"  • Examples: /Users/benjaminfriedman/repos/bimcode/examples/")
print(f"  • Sprint Plan: /Users/benjaminfriedman/repos/bimcode/EPOCH_SPRINT_PLAN.md")
print()
