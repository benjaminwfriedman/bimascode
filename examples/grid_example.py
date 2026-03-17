"""
Example: Creating grid lines for architectural coordination.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.grid import GridLine, create_orthogonal_grid
from bimascode.utils.units import Length

# Create a building
building = Building(
    name="Grid Example Building",
    address="123 Grid Street",
    unit_system="metric"
)

# Create levels
level_1 = Level(building, "Level 1", Length(0, "mm"))
level_2 = Level(building, "Level 2", Length(4000, "mm"))

# Method 1: Create individual grid lines
# Vertical grid lines (A, B, C) - parallel to Y axis
grid_a = GridLine(
    building,
    label="A",
    start_point=(0, 0),
    end_point=(0, 12000)
)

grid_b = GridLine(
    building,
    label="B",
    start_point=(6000, 0),
    end_point=(6000, 12000)
)

grid_c = GridLine(
    building,
    label="C",
    start_point=(12000, 0),
    end_point=(12000, 12000)
)

# Horizontal grid lines (1, 2, 3) - parallel to X axis
grid_1 = GridLine(
    building,
    label="1",
    start_point=(0, 0),
    end_point=(12000, 0)
)

grid_2 = GridLine(
    building,
    label="2",
    start_point=(0, 6000),
    end_point=(12000, 6000)
)

grid_3 = GridLine(
    building,
    label="3",
    start_point=(0, 12000),
    end_point=(12000, 12000)
)

# Print grid information
print(f"Building: {building.name}")
print(f"Grid lines: {len(building.grids)}")
print()

for grid in building.grids:
    print(f"  {grid}")
    print(f"    Length: {grid.length.mm:.0f}mm")
    print(f"    Vertical: {grid.is_vertical()}")
    print(f"    Horizontal: {grid.is_horizontal()}")
    print()

# Export to IFC
output_file = Path(__file__).parent / "output" / "grid_example.ifc"
output_file.parent.mkdir(exist_ok=True)
building.export_ifc(str(output_file))
print(f"✓ Exported to: {output_file}")
print()

# Method 2: Create orthogonal grid using helper function
building2 = Building(
    name="Grid Example 2",
    unit_system="metric"
)

Level(building2, "Ground Floor", Length(0, "mm"))

# Create a 4x3 orthogonal grid
grids = create_orthogonal_grid(
    building2,
    x_grid_labels=["A", "B", "C", "D"],
    x_grid_positions=[0, 6000, 12000, 18000],
    y_grid_labels=["1", "2", "3"],
    y_grid_positions=[0, 8000, 16000],
    x_extent=(0, 18000),
    y_extent=(0, 16000)
)

print(f"Building 2: {building2.name}")
print(f"Grid lines created with helper: {len(grids)}")
print(f"Total grids in building: {len(building2.grids)}")

# Export second building
output_file2 = Path(__file__).parent / "output" / "grid_example_2.ifc"
building2.export_ifc(str(output_file2))
print(f"✓ Exported to: {output_file2}")
