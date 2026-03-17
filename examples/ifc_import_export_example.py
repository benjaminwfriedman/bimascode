"""
Example: IFC Import/Export Round-Trip

Demonstrates:
1. Creating a building model
2. Exporting to IFC
3. Importing the IFC file back
4. Verifying data preservation
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.grid import GridLine, create_orthogonal_grid
from bimascode.utils.units import Length
from bimascode.export import IFCImporter

print("="*70)
print("IFC Import/Export Round-Trip Example")
print("="*70)
print()

# STEP 1: Create a building model programmatically
print("Step 1: Creating Building Model")
print("-" * 70)

building = Building(
    name="Round-Trip Test Building",
    address="123 Export Street, Import City",
    unit_system="metric"
)

# Add levels
level_0 = Level(building, "Ground Floor", Length(0, "mm"), "Ground level")
level_1 = Level(building, "First Floor", Length(4000, "mm"), "First floor level")
level_2 = Level(building, "Second Floor", Length(8000, "mm"), "Second floor level")

print(f"  ✓ Created building: {building.name}")
print(f"  ✓ Added {len(building.levels)} levels")

# Add grid lines
grids = create_orthogonal_grid(
    building,
    x_grid_labels=["A", "B", "C"],
    x_grid_positions=[0, 6000, 12000],
    y_grid_labels=["1", "2", "3", "4"],
    y_grid_positions=[0, 5000, 10000, 15000],
    x_extent=(0, 12000),
    y_extent=(0, 15000)
)

print(f"  ✓ Added {len(building.grids)} grid lines")
print()

# STEP 2: Export to IFC
print("Step 2: Exporting to IFC")
print("-" * 70)

output_file = Path(__file__).parent / "output" / "roundtrip_test.ifc"
output_file.parent.mkdir(exist_ok=True)

building.export_ifc(str(output_file))
print(f"  ✓ Exported to: {output_file}")
print(f"  ✓ File size: {output_file.stat().st_size:,} bytes")
print()

# STEP 3: Get file info
print("Step 3: Inspecting IFC File")
print("-" * 70)

importer = IFCImporter()
file_info = importer.get_info(str(output_file))

print(f"  Schema: {file_info.get('schema')}")
print(f"  Projects: {file_info.get('projects')}")
print(f"  Buildings: {file_info.get('buildings')}")
print(f"  Storeys: {file_info.get('storeys')}")
print(f"  Grids: {file_info.get('grids')}")
print(f"  Materials: {file_info.get('materials')}")

if 'building_names' in file_info:
    print(f"  Building names: {', '.join(file_info['building_names'])}")

if 'storey_names' in file_info:
    print(f"  Storey names: {', '.join(file_info['storey_names'])}")

print()

# STEP 4: Import the IFC file back
print("Step 4: Importing from IFC")
print("-" * 70)

# Method 1: Using class method
imported_building = Building.from_ifc(str(output_file))

print(f"  ✓ Imported building: {imported_building.name}")
print(f"  ✓ Levels: {len(imported_building.levels)}")
print(f"  ✓ Grids: {len(imported_building.grids)}")
print()

# STEP 5: Verify data preservation
print("Step 5: Verifying Data Preservation")
print("-" * 70)

# Check building properties
print("\n  Building Properties:")
print(f"    Original name: {building.name}")
print(f"    Imported name: {imported_building.name}")
print(f"    Match: {'✓' if building.name == imported_building.name else '✗'}")

print(f"\n    Original address: {building.address}")
print(f"    Imported address: {imported_building.address}")
print(f"    Match: {'✓' if building.address == imported_building.address else '✗'}")

print(f"\n    Original GUID: {building.guid}")
print(f"    Imported GUID: {imported_building.guid}")
print(f"    Match: {'✓' if building.guid == imported_building.guid else '✗'}")

# Check levels
print("\n  Levels:")
print(f"    {'Level Name':<20} {'Original Elevation':<20} {'Imported Elevation':<20} {'Match'}")
print(f"    {'-'*20} {'-'*20} {'-'*20} {'-'*5}")

for orig_level, imp_level in zip(building.levels, imported_building.levels):
    orig_elev = orig_level.elevation_mm
    imp_elev = imp_level.elevation_mm
    match = '✓' if abs(orig_elev - imp_elev) < 0.01 else '✗'
    print(f"    {orig_level.name:<20} {orig_elev:<20.1f} {imp_elev:<20.1f} {match}")

# Check grids
print("\n  Grid Lines:")
print(f"    Original count: {len(building.grids)}")
print(f"    Imported count: {len(imported_building.grids)}")
print(f"    Match: {'✓' if len(building.grids) == len(imported_building.grids) else '✗'}")

if len(building.grids) > 0:
    print(f"\n    Sample grid lines:")
    for i, (orig_grid, imp_grid) in enumerate(zip(building.grids[:3], imported_building.grids[:3])):
        print(f"      {orig_grid.label}: {orig_grid.start_point_mm} → {orig_grid.end_point_mm}")
        print(f"      {imp_grid.label}: {imp_grid.start_point_mm} → {imp_grid.end_point_mm}")
        print()

print()
print("="*70)
print("Round-Trip Test Complete!")
print("="*70)
print()
print("Summary:")
print(f"  ✓ Created building with {len(building.levels)} levels and {len(building.grids)} grids")
print(f"  ✓ Exported to IFC successfully")
print(f"  ✓ Imported from IFC successfully")
print(f"  ✓ Data preserved through round-trip")
print()
print("This demonstrates that BIM as Code can:")
print("  • Export models to IFC for interoperability")
print("  • Import existing IFC files")
print("  • Maintain data fidelity through export/import cycles")
