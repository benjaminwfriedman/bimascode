"""
Building visualization example using OCP CAD Viewer.

This demonstrates in-IDE 3D visualization of BIM models.
"""

from bimascode import Building, Level, Length, UnitSystem
from build123d import Box, Location, Align
from ocp_vscode import show, set_port, set_defaults

# Configure OCP Viewer
set_defaults(
    reset_camera=True,
    helper_scale=5,
    render_edges=True,
    render_normals=False,
    render_mates=False,
)

print("Creating building model...")

# Create a building with metric units
building = Building(
    name="Visualization Demo",
    address="123 Demo Street",
    unit_system=UnitSystem.METRIC
)

# Add levels
ground_floor = Level(
    building=building,
    name="Ground Floor",
    elevation=0.0
)

level_1 = Level(
    building=building,
    name="Level 1",
    elevation=4000.0  # 4m
)

level_2 = Level(
    building=building,
    name="Level 2",
    elevation=8000.0  # 8m
)

print(f"\nBuilding: {building.name}")
print(f"Levels: {len(building.levels)}")
for level in building.levels:
    print(f"  - {level.name}: {level.elevation.m}m")

# Create simple 3D geometry to represent the building
# (This is a placeholder - in future sprints we'll have actual walls, floors, etc.)
print("\nGenerating 3D visualization...")

# Create floor slabs at each level
floor_thickness = 200  # mm
floor_width = 10000  # 10m
floor_depth = 15000  # 15m

geometries = []
colors = ["lightgray", "lightblue", "lightyellow"]

for i, level in enumerate(building.levels):
    # Create a slab at each level
    slab = Box(
        floor_width,
        floor_depth,
        floor_thickness,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )

    # Position at level elevation
    elevation_mm = level.elevation_mm
    slab = slab.move(Location((0, 0, elevation_mm)))

    geometries.append((slab, level.name, colors[i % len(colors)]))
    print(f"  Created floor slab for {level.name}")

# Display in OCP Viewer
print("\nDisplaying in OCP CAD Viewer...")
print("(The 3D view should appear in VS Code's OCP CAD Viewer panel)")

# Show each floor with labels
for geom, label, color in geometries:
    show(geom, names=[label], options={"color": color})

# Export to IFC
ifc_path = "examples/visualization_demo.ifc"
building.export_ifc(ifc_path)
print(f"\nIFC exported to: {ifc_path}")

print("\n✓ Visualization complete!")
print("  - Check the OCP CAD Viewer panel in VS Code to see the 3D model")
print("  - You can rotate, pan, and zoom the view")
print("  - Each level is shown as a different colored floor slab")
