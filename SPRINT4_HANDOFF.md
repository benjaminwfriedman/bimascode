# Sprint 4 Handoff Document

## Summary

Sprints 1-3 are **100% complete**. All 196 tests pass. The codebase has a solid foundation with walls, floors, roofs, doors, windows, openings, and wall joins. IFC export is working correctly with proper BIM semantics.

---

## Completed Work

### Sprint 1: Project Skeleton
- Building/Site/Level hierarchy with IFC export
- Grid lines
- Materials with IFC export
- Units management (metric/imperial)
- IFC import capability

### Sprint 2: Core Architecture
- Type/Instance parameter model (`ElementType`, `ElementInstance`)
- `WallType` with compound layer stacks
- `Wall` with straight geometry
- `Floor` with boundary polygon and slope
- `Roof` (flat) with slope parameter

### Sprint 3: Hosted Elements + Wall Joins
- `Door` and `DoorType` with frame/panel geometry
- `Window` and `WindowType` with frame/glazing/mullion
- `Opening` for floor/roof penetrations
- `WallJoinDetector` and `WallJoinProcessor`
- Proper IFC export with `IfcDoorLiningProperties`, `IfcDoorPanelProperties`, etc.
- `IfcShellBasedSurfaceModel` for multi-solid geometry (door assemblies)

---

## Sprint 4: Spatial + Structural

**Theme:** Rooms for program definition and structural elements for engineering.

**Duration:** 2 weeks

### Features to Implement

#### 1. Room / Space (P0)
```python
Room(name, number, boundary_polygon, level)
```
- Compute area via shapely
- Volume from floor-to-ceiling height
- Finish parameters: floor_finish, wall_finish, ceiling_finish
- Export to IFC `IfcSpace` with property sets

**File:** `src/bimascode/spatial/room.py`

#### 2. Ceiling (P0)
```python
Ceiling(type, boundary, height, level)
```
- Simple horizontal plane at defined height
- Required for room volume calculations
- Export to IFC `IfcCovering` with `CEILING` predefined type

**File:** `src/bimascode/architecture/ceiling.py`

#### 3. Structural Column (P0)
```python
StructuralColumn(section_profile, level, grid_intersection)
```
- Extrude section profile (rectangular for now)
- Export to IFC `IfcColumn` with structural classification

**File:** `src/bimascode/structure/column.py`

#### 4. Beam (P0)
```python
Beam(section_profile, start_point, end_point, level)
```
- Extrude profile along path
- Export to IFC `IfcBeam`

**File:** `src/bimascode/structure/beam.py`

#### 5. Structural Wall (P0)
- Reuse existing `Wall` class with `structural=True` flag
- Export to IFC `IfcWall` with `SHEAR` predefined type

**Modification:** `src/bimascode/architecture/wall.py`

#### 6. Structural Floor / Slab (P0)
- Reuse existing `Floor` class with `structural=True` flag
- Export to IFC `IfcSlab` with `BASESLAB` predefined type

**Modification:** `src/bimascode/architecture/floor.py`

---

## Deliverables

- [ ] Multi-room floor plan with named spaces
- [ ] Room.area and Room.volume properties working
- [ ] Structural grid with columns at intersections
- [ ] Beams spanning between columns
- [ ] Room schedule via `building.room_schedule()` returning pandas DataFrame
- [ ] IFC export distinguishes architectural vs. structural elements
- [ ] All new tests passing

---

## Technical Notes

### Existing Patterns to Follow

1. **Type/Instance Model**: Use `ElementType` and `ElementInstance` base classes
   - See `door_type.py` and `door.py` for reference

2. **Geometry Creation**: Types create geometry, instances provide parameters
   ```python
   class ColumnType(ElementType):
       def create_geometry(self, instance: 'Column') -> Solid:
           # Return build123d geometry
   ```

3. **IFC Export**: Each element has `to_ifc()` method
   ```python
   def to_ifc(self, ifc_file, ifc_building_storey):
       # Create IFC entity and return it
   ```

4. **Level Association**: Elements belong to levels
   ```python
   column = Column(column_type, level, ...)
   level.add_element(column)  # Called automatically in __init__
   ```

### Section Profiles

For Sprint 4, implement simple rectangular profiles only:
```python
class RectangularProfile:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    def to_build123d(self) -> Face:
        return Rectangle(self.width, self.height)
```

Full AISC catalog is Sprint 10 scope.

### Room Boundaries

For v1.0, room boundaries are **manually specified** (not auto-detected from walls):
```python
room = Room(
    name="Office",
    number="101",
    boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
    level=ground_floor
)
```

Auto-detection from enclosing walls is P1 (v1.1).

---

## File Structure

```
src/bimascode/
├── spatial/
│   ├── room.py          # NEW: Room/Space class
│   └── ...
├── architecture/
│   ├── ceiling.py       # NEW: Ceiling class
│   ├── ceiling_type.py  # NEW: CeilingType class
│   └── ...
├── structure/
│   ├── __init__.py      # UPDATE: Add exports
│   ├── column.py        # NEW: StructuralColumn class
│   ├── column_type.py   # NEW: ColumnType class
│   ├── beam.py          # NEW: Beam class
│   ├── beam_type.py     # NEW: BeamType class
│   └── profile.py       # NEW: Section profiles
└── ...

tests/
├── test_rooms.py        # NEW
├── test_ceilings.py     # NEW
├── test_columns.py      # NEW
├── test_beams.py        # NEW
└── ...
```

---

## IFC Mappings

| BIM as Code | IFC Entity | PredefinedType |
|-------------|------------|----------------|
| Room | IfcSpace | SPACE |
| Ceiling | IfcCovering | CEILING |
| StructuralColumn | IfcColumn | COLUMN |
| Beam | IfcBeam | BEAM |
| Wall (structural=True) | IfcWall | SHEAR |
| Floor (structural=True) | IfcSlab | BASESLAB |

---

## Testing Commands

```bash
# Activate virtual environment
cd /Users/benjaminfriedman/repos/bimcode

# Run all tests
venv/bin/pytest

# Run specific test file
venv/bin/pytest tests/test_rooms.py -v

# Run with coverage
venv/bin/pytest --cov=src/bimascode
```

---

## Current Test Status

```
196 passed, 11 warnings
Coverage: 85%
```

All existing tests must continue to pass after Sprint 4 implementation.

---

## Dependencies

- **shapely**: For room boundary polygon operations (already installed)
- **pandas**: For room schedule generation (already installed)
- **build123d**: For geometry creation (already installed)
- **ifcopenshell**: For IFC export (already installed)

---

## Reference Files

| Purpose | File |
|---------|------|
| Type/Instance pattern | `src/bimascode/core/type_instance.py` |
| Door example (hosted element) | `src/bimascode/architecture/door.py` |
| Wall example (basic element) | `src/bimascode/architecture/wall.py` |
| IFC geometry export | `src/bimascode/export/ifc_geometry.py` |
| Sprint plan | `EPOCH_SPRINT_PLAN.md` |

---

## Key Decisions Already Made

1. **Pitched roofs** deferred to P1 (v1.1) - only flat roofs in v1.0
2. **Room auto-boundary detection** deferred to P1 - manual boundary input for v1.0
3. **Full section profile library** (100+ AISC sections) deferred to Sprint 10 - only 10-20 common sections needed
4. **Curved walls** deferred to P1

---

## Demo Script Location

Create a demo at `examples/sprint4_demo.py` showing:
- Building with multiple rooms
- Room schedule output
- Structural columns on grid
- Beams between columns
- IFC export with all elements

---

## Git Branch

Work on `main` branch. Commit message format:
```
Complete Sprint 4: Spatial + Structural

- Room/Space class with area/volume
- Ceiling class
- StructuralColumn and Beam classes
- Structural flags for walls/floors
- Room schedule generation

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
