# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BIM as Code (bimascode) is a Python library for programmatic Building Information Modeling. It enables creating buildings through code, generating documentation drawings, and exporting to IFC and DXF formats. Built on build123d (CAD geometry), IfcOpenShell (IFC), and ezdxf (DXF).

## Development Commands

### Setup
```bash
# Development installation with all dependencies
pip install -e ".[dev,viz]"
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_walls.py

# Run specific test class or function
pytest tests/test_walls.py::TestWall::test_wall_creation

# Run tests matching a pattern
pytest -k "wall_join"
```

### Code Quality
```bash
# Format code (100 char line length)
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type check with mypy
mypy src/
```

### Running Examples
```bash
# Run example scripts from project root
python examples/sprint6_demo.py
python examples/school_floor_plan.py
python examples/office_world_geometry_demo.py
```

## Architecture Overview

### Core Design Patterns

**Type/Instance Pattern**: All architectural and structural elements use a parametric type/instance system similar to Revit/BIM systems.

- `ElementType` (base class in `core/type_instance.py`): Defines shared parameters for all instances
  - Examples: `WallType`, `FloorType`, `DoorType`, `ColumnType`
  - When type parameters change, all instances are notified
  - Type holds reference to all its instances

- `ElementInstance` (base class in `core/type_instance.py`): Individual placed elements
  - Examples: `Wall`, `Floor`, `Door`, `Column`
  - Can override type parameters with instance-specific values
  - Geometry is cached and regenerated only when parameters change
  - All instances inherit from both `ElementInstance` and a geometry mixin

**World Geometry Mixins**: Two mixin classes handle transformation from local to world coordinates:

- `FreestandingElementMixin` (`core/world_geometry.py`): For elements positioned directly in world space
  - Used by: Wall, Floor, Ceiling, Column, Beam
  - Subclasses implement `_get_world_position()` and `_get_world_rotation()`

- `HostedElementMixin` (`core/world_geometry.py`): For elements positioned relative to a host
  - Used by: Door, Window
  - Subclasses implement `_get_host_transform()` and `_get_local_transform()`

### Critical build123d Behaviors

**IMPORTANT**: build123d has non-intuitive transformation behavior that causes subtle bugs:

1. **`locate()` modifies geometry IN PLACE** - Always `copy.copy()` before transforming:
   ```python
   # WRONG - corrupts cached geometry
   return self.get_geometry().locate(transform)

   # CORRECT - copy first
   import copy
   geom_copy = copy.copy(self.get_geometry())
   return geom_copy.locate(transform)
   ```

2. **`locate()` REPLACES transforms, doesn't chain** - Compose transforms using multiplication:
   ```python
   # WRONG - second locate() loses first transform
   box.locate(local_transform)
   box.locate(world_transform)

   # CORRECT - compose with multiplication before locate()
   combined = world_transform * local_transform
   box.locate(combined)
   ```

3. **`Polygon()` auto-centers at centroid** - Created polygons shift vertices to center at origin

See `docs/build123d_behavior.md` for detailed explanations and examples.

### Module Organization

```
src/bimascode/
├── core/               # Base classes and patterns
│   ├── element.py      # Element base class with GUID, properties, cache
│   ├── type_instance.py # ElementType/ElementInstance parametric pattern
│   └── world_geometry.py # Freestanding/Hosted geometry transformation mixins
├── spatial/            # Project hierarchy
│   ├── building.py     # Building (IFC project root), unit system management
│   ├── level.py        # Building storeys with elevation tracking
│   ├── grid.py         # Layout axes (numeric/alphabetic)
│   └── room.py         # Spatial zones with area/volume
├── architecture/       # Architectural elements
│   ├── wall.py, wall_type.py       # Straight walls with layer stacks
│   ├── wall_joins.py               # Automatic corner/T/cross joins
│   ├── door.py, door_type.py       # Doors hosted in walls
│   ├── window.py, window_type.py   # Windows with sill height
│   ├── floor.py, floor_type.py     # Slabs with layer stacks
│   ├── roof.py                     # Flat roofs
│   ├── ceiling.py, ceiling_type.py # Suspended ceilings
│   └── opening.py                  # Voids in floors/roofs
├── structure/          # Structural elements
│   ├── column.py, column_type.py   # Vertical members
│   ├── beam.py, beam_type.py       # Horizontal/sloped members
│   └── profile.py                  # Section profiles (RHS, I-beam, etc)
├── drawing/            # 2D view generation
│   ├── protocols.py        # Drawable2D protocol for elements
│   ├── view_base.py        # Base view class with ViewRange
│   ├── floor_plan_view.py  # Horizontal section cuts
│   ├── elevation_view.py   # Exterior projections
│   ├── section_view.py     # Vertical section cuts
│   ├── view_templates.py   # Visibility/graphic overrides
│   ├── line_styles.py      # LineWeight, LineType, Layer definitions
│   ├── primitives.py       # Line2D, Arc2D, Polyline2D, Hatch2D
│   ├── hlr_processor.py    # Hidden line removal
│   └── dxf_exporter.py     # Export to DXF with AIA layers
├── export/             # IFC import/export
│   ├── ifc_exporter.py     # Building → IFC4/2x3
│   ├── ifc_importer.py     # IFC → Building (planned)
│   └── ifc_geometry.py     # Geometry conversion helpers
├── performance/        # Optimization
│   ├── spatial_index.py        # R-tree for fast element queries
│   ├── representation_cache.py # Cached 2D linework
│   └── bounding_box.py         # AABB for spatial queries
└── utils/
    ├── units.py        # Length class, UnitSystem (metric/imperial)
    └── materials.py    # Material library (concrete, steel, wood, etc)
```

### 2D Drawing System

Elements implement the `Drawable2D` protocol (`drawing/protocols.py`) to provide 2D representations:

- `get_plan_representation(cut_height, view_range)` - Returns list of Line2D/Arc2D/Polyline2D/Hatch2D
- `get_section_representation(section_plane, view_direction)` - For elevations/sections

Views use representation caching (`performance/representation_cache.py`) to avoid regenerating geometry when elements haven't changed (timestamp-based invalidation).

### IFC Export

IFC export follows professional standards matching Bonsai BIM:
- Header set to `ViewDefinition[DesignTransferView]`, implementation level `2;1`
- Full hierarchy: IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey
- Proper material layers, property sets, and geometric representations
- See `src/bimascode/export/ifc_exporter.py`

## Key Implementation Patterns

### Adding a New Element Type

1. Create type class inheriting from `ElementType`:
   ```python
   from bimascode.core.type_instance import ElementType

   class MyElementType(ElementType):
       def __init__(self, name: str, width: float, height: float):
           super().__init__(name)
           self.set_parameter("width", width)
           self.set_parameter("height", height)

       def create_geometry(self, instance):
           # Return build123d geometry
           pass
   ```

2. Create instance class inheriting from `ElementInstance` + geometry mixin:
   ```python
   from bimascode.core.type_instance import ElementInstance
   from bimascode.core.world_geometry import FreestandingElementMixin

   class MyElement(ElementInstance, FreestandingElementMixin):
       def __init__(self, element_type, level, location, name=None):
           super().__init__(element_type, name)
           self.level = level
           self.location = location

       def _get_world_position(self):
           x, y = self.location
           z = self.level.elevation_mm
           return (x, y, z)

       def _get_world_rotation(self):
           return 0.0  # or calculate from parameters
   ```

3. Implement `Drawable2D` protocol for 2D views (optional but recommended):
   ```python
   def get_plan_representation(self, cut_height, view_range):
       # Return list of Line2D, Arc2D, etc.
       return [Line2D(...), ...]
   ```

4. Add tests in `tests/test_myelement.py`

### Wall Joins

Wall joins are detected and applied automatically via `wall_joins.py`:
- Corner joins: Two walls meeting at an endpoint
- T-junctions: Wall endpoint touching another wall's midpoint
- Crosses: Two walls intersecting

Joins modify wall geometry by trimming/extending at intersection points. The system uses `_trim_adjustments` dict on walls to cache trim geometry.

### Material Layer Stacks

Walls, floors, and ceilings use compound layer systems:
```python
from bimascode.architecture import Layer, LayerFunction
from bimascode.utils.materials import MaterialLibrary

layers = [
    Layer(MaterialLibrary.gypsum(), 12.5, LayerFunction.FINISH),
    Layer(MaterialLibrary.concrete(), 200, LayerFunction.STRUCTURE, structural=True),
    Layer(MaterialLibrary.insulation(), 50, LayerFunction.THERMAL),
]
wall_type = WallType("Exterior Wall", layers)
```

Layers have:
- `material`: Material reference
- `thickness`: In mm
- `function`: STRUCTURE, THERMAL, FINISH, etc.
- `structural`: Boolean flag for load-bearing layers

## Common Issues and Solutions

### Issue: Elements not appearing in elevation/section views

**Cause**: Missing or incorrect `get_world_geometry()` implementation.

**Solution**: Ensure element inherits from `FreestandingElementMixin` or `HostedElementMixin` and implements required abstract methods. See `docs/WORLD_GEOMETRY_HANDOFF.md` for detailed guidance.

### Issue: Geometry corruption or incorrect transforms

**Cause**: Violating build123d `locate()` rules (not copying, chaining locate calls).

**Solution**: Always `copy.copy()` before transforming. Compose multiple transforms with `*` operator before calling `locate()` once. See `docs/build123d_behavior.md`.

### Issue: Tests failing with geometry differences

**Cause**: Cached geometry not invalidated after parameter changes.

**Solution**: Call `invalidate_geometry()` or `_invalidate_cache()` when modifying geometric parameters in setters.

### Issue: Slow drawing generation

**Cause**: Representation cache not being used, or too many OCCT section cuts.

**Solution**:
1. Implement `Drawable2D` protocol on elements to avoid OCCT cutting
2. Ensure `RepresentationCache` is enabled and elements have proper timestamp tracking
3. Use spatial index to filter elements before processing

## Testing Patterns

Tests follow pytest conventions:
- Test files: `tests/test_*.py`
- Test classes: `class Test*`
- Test functions: `def test_*`

Common test fixtures:
```python
@pytest.fixture
def building():
    return Building("Test Building")

@pytest.fixture
def level(building):
    return Level(building, "Ground", elevation=0)

@pytest.fixture
def wall_type():
    material = MaterialLibrary.concrete()
    return create_basic_wall_type("Test Wall", 200, material)
```

Run specific test: `pytest tests/test_walls.py::TestWall::test_wall_creation -v`

## Export Workflows

### IFC Export
```python
building = Building("My Building")
# ... add levels, walls, etc.
building.export_ifc("output.ifc")
```

### DXF Export (via views)
```python
from bimascode.drawing import FloorPlanView
from bimascode.drawing.dxf_exporter import DXFExporter

# Create view
plan = FloorPlanView(level, cut_height=1200)
result = plan.generate()

# Export to DXF
exporter = DXFExporter()
exporter.export(result, "floor_plan.dxf")
```

## Committing
- We run
    - black
    - ruff
    - tests

- We don't credit claude

## Notes

- All dimensions internally stored in millimeters
- Coordinate system: X=East, Y=North, Z=Up
- Angles in degrees (build123d convention)
- IFC export supports both IFC4 and IFC2x3 schemas
- DXF exports use AIA-compliant layer naming (A-WALL, A-DOOR, etc.)
- Line weights follow AIA/NCS standards (0.13mm to 0.70mm)
