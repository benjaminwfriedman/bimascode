"""
Basic building example demonstrating Building, Level, and Units.
"""

from bimascode import Building, Level, Length, UnitSystem

# Create a building with metric units
building = Building(
    name="Sample Building",
    address="123 Main Street",
    unit_system=UnitSystem.METRIC
)

# Add levels
ground_floor = Level(
    building=building,
    name="Ground Floor",
    elevation=0.0  # Interpreted as mm (building's default unit)
)

level_1 = Level(
    building=building,
    name="Level 1",
    elevation=4200.0  # 4200mm = 4.2m
)

level_2 = Level(
    building=building,
    name="Level 2",
    elevation=Length(8.4, "m")  # Explicit unit
)

# Print building info
print(f"Building: {building.name}")
print(f"Unit System: {building.unit_system.value}")
print(f"Levels:")
for level in building.levels:
    print(f"  - {level.name}: {level.elevation_mm}mm ({level.elevation.m}m)")

# Export to IFC
output_path = "examples/basic_building.ifc"
try:
    building.export_ifc(output_path)
    print(f"\nIFC exported to: {output_path}")
except ImportError as e:
    print(f"\nCannot export IFC: {e}")
except Exception as e:
    print(f"\nError exporting IFC: {e}")


# Example with imperial units
print("\n" + "="*50)
print("Imperial Example:\n")

imperial_building = Building(
    name="Imperial Building",
    address="456 Oak Ave",
    unit_system=UnitSystem.IMPERIAL
)

ground = Level(
    building=imperial_building,
    name="Ground Floor",
    elevation=0.0  # Interpreted as inches (imperial default)
)

level_1_imperial = Level(
    building=imperial_building,
    name="Level 1",
    elevation=Length(14, "ft")  # 14 feet
)

print(f"Building: {imperial_building.name}")
print(f"Unit System: {imperial_building.unit_system.value}")
print(f"Levels:")
for level in imperial_building.levels:
    print(f"  - {level.name}: {level.elevation.feet}ft ({level.elevation.inches}in)")
