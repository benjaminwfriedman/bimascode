"""
Quick visualization example - minimal code to see a building in 3D.

Run this script and the 3D view will appear in VS Code's OCP CAD Viewer panel.
"""

from bimascode import Building, Level
from build123d import Box, Location, Align
from ocp_vscode import show

# Create a simple 3-story building
building = Building(name="My Building")

# Add 3 levels (elevations in mm)
ground = Level(building, "Ground", 0)
first = Level(building, "First Floor", 4000)
second = Level(building, "Second Floor", 8000)

# Visualize as simple floor plates
floors = []
for level in building.levels:
    floor = Box(10000, 15000, 200, align=(Align.CENTER, Align.CENTER, Align.MIN))
    floor = floor.move(Location((0, 0, level.elevation_mm)))
    floors.append(floor)

# Show all floors at once with proper names
show(*floors, names=[level.name for level in building.levels])

# Export to IFC
building.export_ifc("examples/my_building.ifc")
print(f"✓ Created {building.name} with {len(building.levels)} levels")
print("✓ Check the OCP CAD Viewer panel in VS Code to see the 3D model")
