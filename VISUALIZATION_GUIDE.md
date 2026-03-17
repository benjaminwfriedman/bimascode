# BIM as Code - Visualization Guide

This guide shows you how to visualize your BIM models in VS Code using OCP CAD Viewer.

## Prerequisites

Make sure you have:
1. **VS Code** installed
2. **OCP CAD Viewer extension** installed in VS Code
   - Search for "OCP CAD Viewer" in VS Code extensions
   - Install the extension by `bernhard-42`
3. **Python packages** installed:
   ```bash
   pip install ocp-vscode build123d
   ```

## Quick Start

### Step 1: Enable OCP CAD Viewer in VS Code

1. Open VS Code
2. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
3. Type "OCP CAD Viewer: Show"
4. The 3D viewer panel should appear

### Step 2: Run a Visualization Script

Run any of the example scripts:

```bash
python examples/quick_viz.py
```

The 3D model will appear in the OCP CAD Viewer panel in VS Code.

## Visualization Methods

### Method 1: Simple Geometry (Current)

Since we're in Sprint 1 and haven't built walls/floors yet, we visualize using simple placeholder geometry:

```python
from bimascode import Building, Level
from build123d import Box, Location
from ocp_vscode import show

# Create building
building = Building(name="Demo Building")
ground = Level(building, "Ground", 0)
first = Level(building, "First Floor", 4000)

# Visualize levels as floor plates
for level in building.levels:
    # Create a simple box to represent the floor
    floor = Box(10000, 15000, 200, align=(0, 0, 0))

    # Move it to the level elevation
    floor = floor.move(Location((0, 0, level.elevation_mm)))

    # Show it in the viewer with a label
    show(floor, name=level.name)
```

### Method 2: With Colors and Options

```python
from ocp_vscode import show, set_defaults

# Configure viewer defaults
set_defaults(
    reset_camera=True,
    helper_scale=5,
    render_edges=True,
)

# Show geometry with custom colors
show(floor, name="Ground Floor", options={"color": "lightgray"})
show(floor2, name="Level 1", options={"color": "lightblue"})
```

### Method 3: Future (After Sprint 2+)

Once we implement walls and floors, visualization will be built-in:

```python
# This will be available in Sprint 2+
building = Building(name="My Building")
level = Level(building, "Ground", 0)

# Create actual walls
wall = Wall(level, start=(0, 0), end=(10000, 0), height=4000)

# Direct visualization (to be implemented)
building.show()  # Shows entire building
wall.show()      # Shows just the wall
```

## Viewer Controls

Once the model is displayed in OCP CAD Viewer:

- **Rotate**: Left mouse button + drag
- **Pan**: Right mouse button + drag (or Shift + left drag)
- **Zoom**: Mouse wheel
- **Reset View**: Click the "Reset Camera" button in the viewer
- **Toggle Edges**: Use viewer options panel

## Example Outputs

### Current Capabilities (Sprint 1)
- ✅ Visualize building levels as floor plates
- ✅ Show spatial hierarchy
- ✅ Export to IFC for viewing in external tools
- ✅ Verify elevations and positions

### Coming Soon
- Sprint 2: Walls, doors, windows, roofs
- Sprint 3: Wall joins, openings
- Sprint 4: Rooms, columns, beams
- Sprint 6+: 2D drawing generation with matplotlib

## Verification Workflow

The intended workflow for verification:

1. **Write code** to create your building
2. **Visualize in 3D** using `show()` to verify geometry
3. **Export to IFC** to check interoperability
4. **Generate drawings** (later sprints) for documentation

## Troubleshooting

### OCP CAD Viewer not showing
1. Make sure the extension is installed
2. Press `Cmd+Shift+P` > "OCP CAD Viewer: Show"
3. Try restarting VS Code

### "No connection to kernel"
- Make sure you're running the Python script from the terminal
- The viewer connects automatically when you call `show()`

### Geometry not appearing
- Check that your coordinates are reasonable (not too large/small)
- Use `reset_camera=True` in set_defaults()
- Verify the geometry was created successfully

## External IFC Viewers (Alternative)

You can also export to IFC and view in external tools:

```python
building.export_ifc("my_building.ifc")
```

Then open `my_building.ifc` in:
- **Blender** (with BlenderBIM add-on)
- **FreeCAD** (with IFC support)
- **Online**: https://ifcviewer.com or https://3dviewer.net

## Examples

All visualization examples are in the `examples/` directory:

- `quick_viz.py` - Minimal 3D visualization
- `visualize_building.py` - Full example with colors and options
- `basic_building.py` - Building creation without visualization

## Next Steps

As we implement more features in upcoming sprints:
- Sprint 2: Wall and roof visualization
- Sprint 3: Complete building assemblies
- Sprint 6: 2D drawing generation
- Sprint 10: Full v1.0 feature set

The visualization approach will evolve to match the implemented features!
