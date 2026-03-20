# Sprint 3: Hosted Elements + Wall Joins - Implementation Plan

## Overview

Sprint 3 implements doors, windows, wall joins, and openings. This is marked **HIGH RISK** due to wall join complexity.

## Implementation Order (Lowest → Highest Risk)

| Phase | Feature | Days | Risk |
|-------|---------|------|------|
| 1 | Door + DoorType | 3 | Low |
| 2 | Window + WindowType | 2 | Low |
| 3 | Non-Hosted Openings | 2 | Medium |
| 4 | Wall Joins | 5 | High |
| 5 | Integration Testing | 2 | Medium |

**Total: ~14 days (3 weeks)**

---

## Phase 1: Doors (Days 1-3)

### New Files

**`src/bimascode/architecture/door_type.py`**
```python
class DoorType(ElementType):
    # Parameters: width, height, frame_width, frame_depth, swing_direction
    def create_geometry(instance) -> Compound  # Frame + panel
    def create_opening_geometry(instance) -> Box  # Void for wall cut
    def to_ifc(ifc_file) -> IfcDoorType
```

**`src/bimascode/architecture/door.py`**
```python
class Door(ElementInstance):
    # Parameters: door_type, host_wall, offset (along wall), sill_height
    def __init__()  # Registers with host wall
    def get_opening_geometry() -> Box  # In wall's local coordinates
    def to_ifc(ifc_file, storey, ifc_wall)  # Creates IfcDoor + IfcOpeningElement
```

### Modifications

**`src/bimascode/architecture/wall.py`** - Add:
- `_hosted_elements: List` - Track doors/windows
- `add_hosted_element(element)` - Register + invalidate geometry
- `remove_hosted_element(element)`
- `openings` property - Returns opening geometries

**`src/bimascode/architecture/wall_type.py`** - Modify `create_geometry()`:
```python
# After creating layer boxes, apply boolean subtraction:
if instance.openings:
    wall_compound = Compound(children=layer_solids)
    for opening in instance.openings:
        wall_compound = cut(wall_compound, opening)
    return wall_compound
```

### IFC Relationships
- `IfcOpeningElement` - The void
- `IfcRelVoidsElement` - Links opening → wall
- `IfcDoor` - The door element
- `IfcRelFillsElement` - Links door → opening

---

## Phase 2: Windows (Days 4-5)

### New Files

**`src/bimascode/architecture/window_type.py`**
- Same pattern as DoorType
- Additional: `sill_height` default, `mullion_count`

**`src/bimascode/architecture/window.py`**
- Same pattern as Door
- `sill_height` typically > 0 (e.g., 900mm)
- Maps to `IfcWindow`

### Shared Logic

**`src/bimascode/architecture/hosted_element.py`** (optional mixin)
```python
class HostedElementMixin:
    def validate_position() -> bool  # Check element fits in wall
    def get_opening_box() -> Box  # Generate void geometry
```

---

## Phase 3: Non-Hosted Openings (Days 6-7)

### New Files

**`src/bimascode/architecture/opening.py`**
```python
class Opening(ElementInstance):
    # For floor/roof penetrations (stairs, shafts, skylights)
    # Parameters: host_element, boundary (polygon), depth
```

### Modifications

**`src/bimascode/architecture/floor.py`** - Replace stub:
```python
def add_opening(self, boundary, depth=None) -> Opening:
    opening = Opening(host_element=self, boundary=boundary, depth=depth)
    self._openings.append(opening)
    self.invalidate_geometry()
    return opening
```

**`src/bimascode/architecture/floor_type.py`** - Modify `create_geometry()`:
- Apply boolean subtraction for each opening polygon

Same pattern for **`roof.py`** and **`roof_type.py`**

---

## Phase 4: Wall Joins (Days 8-12) - HIGH RISK

### New Files

**`src/bimascode/architecture/wall_joins.py`**

```python
class JoinType(Enum):
    L_JUNCTION = "L"  # Corner
    T_JUNCTION = "T"  # Wall meets another's side
    CROSS = "X"       # Walls crossing

class EndCapType(Enum):
    FLUSH = "flush"       # Cut at centerline
    EXTERIOR = "exterior" # Extend to outer face
    INTERIOR = "interior" # Cut at inner face

@dataclass
class WallJoin:
    wall_a, wall_b: Wall
    join_type: JoinType
    intersection_point: Tuple[float, float]

class WallJoinDetector:
    def detect_joins(walls: List[Wall]) -> List[WallJoin]
    # Algorithm:
    # 1. For each wall pair on same level
    # 2. Compute centerline intersection
    # 3. Classify: L (both endpoints), T (one endpoint), X (neither)

class WallJoinProcessor:
    def process_joins(joins, end_cap_type) -> Dict[Wall, trim_adjustments]
    # Priority rules:
    # 1. Structural > non-structural
    # 2. Thicker > thinner
```

### Key Algorithm: Centerline Intersection
```python
def line_intersection(p1, p2, p3, p4):
    # Parametric line intersection
    denom = (p1.x-p2.x)*(p3.y-p4.y) - (p1.y-p2.y)*(p3.x-p4.x)
    if abs(denom) < 1e-10: return None  # Parallel
    t = ((p1.x-p3.x)*(p3.y-p4.y) - (p1.y-p3.y)*(p3.x-p4.x)) / denom
    return (p1.x + t*(p2.x-p1.x), p1.y + t*(p2.y-p1.y))
```

### Modifications

**`src/bimascode/architecture/wall.py`** - Add:
- `is_structural` property
- `_trim_adjustments` dict for join processing

**`src/bimascode/architecture/wall_type.py`** - Modify `create_geometry()`:
- Apply trim offsets when `_trim_adjustments` present

**`src/bimascode/spatial/level.py`** - Add:
```python
def process_wall_joins(self, end_cap_type=EndCapType.FLUSH):
    walls = [e for e in self.elements if isinstance(e, Wall)]
    joins = WallJoinDetector(walls).detect_joins()
    adjustments = WallJoinProcessor(joins).process_joins(end_cap_type)
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj
        wall.invalidate_geometry()
```

---

## Phase 5: Integration (Days 13-14)

### Update Exports

**`src/bimascode/architecture/__init__.py`**
```python
from .door_type import DoorType
from .door import Door
from .window_type import WindowType
from .window import Window
from .opening import Opening
from .wall_joins import WallJoinDetector, WallJoinProcessor, EndCapType
```

**`src/bimascode/__init__.py`** - Add public exports

### Test Files

**`tests/test_doors.py`**
- Door creation, positioning, wall geometry void
- Multiple doors on wall
- IFC export with proper relationships

**`tests/test_windows.py`**
- Window creation with sill height
- IFC export

**`tests/test_openings.py`**
- Floor/roof openings
- Boolean geometry validation

**`tests/test_wall_joins.py`**
- L-junction detection and trimming
- T-junction detection and trimming
- Priority rules (structural, thickness)
- End cap types
- Multiple joins on single wall

**`tests/test_sprint3_integration.py`**
- Full building with walls, doors, windows
- Wall joins processed
- IFC export validation

---

## Critical Files Summary

| File | Action |
|------|--------|
| `architecture/door_type.py` | Create |
| `architecture/door.py` | Create |
| `architecture/window_type.py` | Create |
| `architecture/window.py` | Create |
| `architecture/opening.py` | Create |
| `architecture/wall_joins.py` | Create |
| `architecture/wall.py` | Modify (add hosted elements) |
| `architecture/wall_type.py` | Modify (boolean ops, trimming) |
| `architecture/floor.py` | Modify (implement add_opening) |
| `architecture/floor_type.py` | Modify (boolean ops) |
| `spatial/level.py` | Modify (add process_wall_joins) |
| `export/ifc_exporter.py` | Modify (export doors/windows) |
| `architecture/__init__.py` | Modify (exports) |

---

## Risk Mitigation

1. **Boolean operation failures**: Wrap in try/except, add small offset to opening depth
2. **3+ walls meeting at point**: Process joins iteratively
3. **Performance on large models**: Pre-filter by bounding box
4. **Curved walls**: Detect and skip with warning (defer to P1)

---

## Verification

1. Run `pytest tests/test_doors.py tests/test_windows.py tests/test_openings.py tests/test_wall_joins.py -v`
2. Run `python examples/sprint3_demo.py` (to be created)
3. Open exported IFC in Bonsai/Autodesk Viewer - verify:
   - Door/window voids visible in walls
   - Wall corners meet cleanly
   - No overlapping geometry
4. Check IFC structure: `IfcDoor`, `IfcWindow`, `IfcOpeningElement`, `IfcRelVoidsElement`, `IfcRelFillsElement` present

---

## Existing Code References

### Type/Instance Pattern (follow this)
- `src/bimascode/core/type_instance.py` - ElementType, ElementInstance base classes
- `src/bimascode/architecture/wall_type.py` - WallType example (lines 73-296)
- `src/bimascode/architecture/wall.py` - Wall example (lines 15-283)

### Geometry Creation (follow this pattern)
- Wall geometry uses LOCAL coordinates (X=along length, Y=thickness, Z=height)
- IFC placement handles world positioning
- `create_geometry()` returns `build123d.Compound`

### IFC Export (follow this pattern)
- `wall.py:182-276` - `to_ifc()` method example
- Uses `build123d_to_ifc_brep()` for geometry conversion
- Creates `IfcLocalPlacement` relative to building storey

### Boolean Operations (build123d)
```python
from build123d import Box, cut, Compound

# Subtract opening from wall
wall_solid = cut(wall_solid, opening_box)
```

### Existing Stubs to Implement
- `floor.py:147-160` - `add_opening()` stub
- `roof.py:149-161` - `add_opening()` stub
