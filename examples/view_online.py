"""
Create a building and view it online.

This exports to IFC format which you can view at:
https://ifcviewer.com
"""

from bimascode import Building, Level, Length

# Create a simple 3-story building
building = Building(
    name="My Building",
    address="123 Main Street"
)

# Add 3 levels (elevations in mm)
ground = Level(building, "Ground Floor", 0)
first = Level(building, "Level 1", 4000)  # 4m above ground
second = Level(building, "Level 2", 8000)  # 8m above ground

print(f"\n{'='*60}")
print(f"Building: {building.name}")
print(f"Address: {building.address}")
print(f"{'='*60}\n")

print("Levels:")
for level in building.levels:
    print(f"  • {level.name:20s} elevation: {level.elevation.m:>6.2f}m ({level.elevation_mm:>8.1f}mm)")

# Export to IFC
ifc_file = "examples/my_building.ifc"
building.export_ifc(ifc_file)

print(f"\n{'='*60}")
print(f"✓ IFC file exported: {ifc_file}")
print(f"{'='*60}\n")

print("To view the 3D model:")
print("  1. Go to: https://ifcviewer.com")
print("  2. Click 'Choose File' or drag and drop")
print(f"  3. Select: {ifc_file}")
print("  4. View your building in 3D!\n")

print("What you'll see:")
print("  • 3 building levels/stories")
print("  • Proper elevation hierarchy")
print("  • IFC4-compliant structure")
print("  • Project → Site → Building → Storeys\n")
