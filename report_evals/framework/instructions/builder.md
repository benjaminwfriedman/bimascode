# Builder Agent Instructions

You are the Builder agent. Your job is to generate a building using bimascode based on a natural language prompt.

## Before You Begin

**Read these first to understand the library:**

1. **CLAUDE.md** (project root) - Architecture overview, key patterns, common issues
2. **API Docs**: https://benjaminwfriedman.github.io/bimascode/bimascode.html
3. **Examples** - Study these working buildings:
   - `examples/example_office_building.py` - Multi-room layout, wall joins
   - `examples/example_residential_home.py` - Compound wall layers, multiple levels
   - `examples/sprint6_demo.py` - Simple starting point

## Your Input

**Prompt file**: `prompts/{eval_id}.md` - A natural language description of the building to create

That's it. You do NOT have access to:
- Requirements JSON files
- Test files
- Any other eval infrastructure

## Your Output

Write a Python file to: `outputs/{eval_id}/building.py`

This file must:
1. Define a `build()` function that creates and returns the building
2. Have a `main()` function that calls `build()` and exports:
   - IFC file: `building.ifc`
   - DXF drawings in `dxf/` directory:
     - Floor plans (one per level)
     - Elevations (North, South, East, West)
     - Sections (at least one)
   - PDF drawing set: `{eval_id}_drawing_set.pdf` (all views combined)
3. Be runnable as `python building.py`

## Available bimascode APIs

```python
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room import Room

from bimascode.architecture import (
    Wall, Door, Window, Floor, Ceiling, Roof,
    WallFunction, LayerFunction,
    create_basic_wall_type,
)
from bimascode.architecture.wall_type import WallType
from bimascode.architecture.door_type import DoorType, create_double_door_type
from bimascode.architecture.window_type import WindowType
from bimascode.architecture.floor_type import FloorType
from bimascode.architecture.ceiling_type import CeilingType

from bimascode.architecture.wall_joins import (
    WallJoinDetector, WallJoinStyle, JoinType, join_walls
)

from bimascode.structure import (
    StructuralColumn, Beam,
    create_square_column_type, create_rectangular_beam_type,
)

from bimascode.utils.materials import MaterialLibrary
```

## Coordinate System

- X = East-West (positive X is East)
- Y = North-South (positive Y is North)
- Z = Up
- All dimensions in millimeters
- Angles in degrees

## Wall Directions

- **South wall**: runs along Y=0, from west to east (start X < end X)
- **North wall**: runs along Y=max, from east to west (start X > end X)
- **East wall**: runs along X=max, from south to north (start Y < end Y)
- **West wall**: runs along X=0, from north to south (start Y > end Y)

## Template

```python
"""
Eval {eval_id}: {Building Name}

{Brief description from prompt}
"""
from pathlib import Path

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import Wall, Door, Window, create_basic_wall_type
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.window_type import WindowType
from bimascode.architecture.wall_joins import (
    WallJoinDetector, WallJoinStyle, JoinType, join_walls
)
from bimascode.utils.materials import MaterialLibrary


def apply_wall_joins(walls, tolerance=50.0):
    """Join walls at corners and intersections."""
    for j in WallJoinDetector(list(walls), tolerance=tolerance).detect_joins():
        style = (
            WallJoinStyle.MITER if j.join_type == JoinType.L_JUNCTION
            else WallJoinStyle.BUTT
        )
        try:
            join_walls(style, j.wall_a, j.wall_b, tolerance=tolerance)
        except Exception:
            try:
                join_walls(WallJoinStyle.BUTT, j.wall_a, j.wall_b, tolerance=tolerance)
            except Exception:
                pass


def build():
    building = Building("Building Name")
    level = Level(building, "Ground Floor", elevation=0)

    # Create wall type
    material = MaterialLibrary.concrete()
    wall_type = create_basic_wall_type("Wall", 200, material)

    # Create walls
    walls = []
    # ... add walls ...

    # Join walls
    apply_wall_joins(walls)

    # Add doors and windows
    # ...

    return building


def main():
    out_dir = Path(__file__).parent
    building = build()

    # Export IFC
    ifc_path = out_dir / "building.ifc"
    building.export_ifc(str(ifc_path))
    print(f"Exported: {ifc_path}")

    # Export DXF and PDF - see examples for how to generate views and export


if __name__ == "__main__":
    main()
```

## Important Rules

1. **Read the prompt carefully** - it specifies dimensions, materials, element placement, and design constraints
2. **Use correct wall directions** - "door on south wall" means the wall at Y=0
3. **Apply wall joins** - use the `apply_wall_joins` helper for clean corners
4. **Export all outputs** - IFC, DXF floor plans, and PDF drawing set (see examples)
5. **Keep it simple** - implement what the prompt asks, nothing more
6. **Follow design constraints** - each prompt includes a "Design Constraints" section that must be followed

## Critical Rules
- **DO NOT** read any files in `outputs/` directories
- **DO NOT** read the test file to understand what will be checked
- **DO** reference `examples/` for patterns (especially example_office_building.py)


## Begin

Read the prompt file and generate `building.py` that creates the described building.
