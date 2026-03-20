# Sprint 3 Handoff Document

## Summary

Sprint 3 implementation is **95% complete**. All features (doors, windows, openings, wall joins) have been implemented and all 196 tests pass. There is one remaining issue: **door and window geometry is not exported to IFC files** - only their openings (voids) appear in walls.

---

## Completed Work

### Phase 1: Doors
- **door_type.py** - `DoorType` class with frame/panel geometry, swing direction, operation types
- **door.py** - `Door` class hosted in walls, creates openings, has `to_ifc()` method
- Helper functions: `create_standard_door_type()`, `create_double_door_type()`

### Phase 2: Windows
- **window_type.py** - `WindowType` class with frame/glazing/mullion geometry
- **window.py** - `Window` class hosted in walls with sill height support
- Helper functions: `create_standard_window_type()`, `create_double_window_type()`, `create_fixed_window_type()`

### Phase 3: Openings
- **opening.py** - `Opening` class for floor/roof penetrations (stair openings, skylights)
- Helper functions: `create_rectangular_opening()`, `create_circular_opening()`
- Modified **floor.py** and **roof.py** to support `add_opening()` and `remove_opening()`

### Phase 4: Wall Joins
- **wall_joins.py** - `WallJoinDetector` and `WallJoinProcessor` classes
- Enums: `JoinType` (L_JUNCTION, T_JUNCTION, CROSS), `EndCapType` (FLUSH, EXTERIOR, INTERIOR)
- Modified **level.py** with `process_wall_joins()` method

### Modified Files
- **wall.py** - Added `hosted_elements`, `add_hosted_element()`, `remove_hosted_element()`
- **wall_type.py** - Boolean subtraction for openings (uses `-` operator, not `cut()`)
- **floor_type.py** - Boolean subtraction for openings
- **architecture/__init__.py** - All Sprint 3 exports added

### Test Files Created
- `tests/test_doors.py` - 18 tests
- `tests/test_windows.py` - 20 tests
- `tests/test_openings.py` - 16 tests
- `tests/test_wall_joins.py` - 8 tests

### Demo
- `examples/sprint3_demo.py` - Full demo with all Sprint 3 features

---

## Remaining Issue

### Problem
Doors and windows create **openings (voids) in walls correctly**, but the **actual door/window geometry is not visible** in the exported IFC file.

### Root Cause
The `_export_elements()` method in `src/bimascode/export/ifc_exporter.py` (lines 375-403) only exports Wall, Floor, and Roof elements. It does **not** call `to_ifc()` on hosted elements (doors, windows).

### Current Code (lines 395-403)
```python
for level in building.levels:
    ifc_storey = ifc_storeys.get(level)
    if not ifc_storey or not level.elements:
        continue

    for element in level.elements:
        if isinstance(element, (Wall, Floor, Roof)):
            element.to_ifc(self._ifc_file, ifc_storey)
```

### Required Fix
```python
for level in building.levels:
    ifc_storey = ifc_storeys.get(level)
    if not ifc_storey or not level.elements:
        continue

    for element in level.elements:
        if isinstance(element, Wall):
            ifc_wall = element.to_ifc(self._ifc_file, ifc_storey)
            # Export hosted elements (doors, windows)
            for hosted in element.hosted_elements:
                if isinstance(hosted, Door):
                    hosted.to_ifc(self._ifc_file, ifc_storey, ifc_wall)
                elif isinstance(hosted, Window):
                    hosted.to_ifc(self._ifc_file, ifc_storey, ifc_wall)
        elif isinstance(element, (Floor, Roof)):
            element.to_ifc(self._ifc_file, ifc_storey)
```

Also update the import at line 382:
```python
from ..architecture import Wall, Floor, Roof, Door, Window
```

### Door/Window to_ifc() Signatures
- `Door.to_ifc(ifc_file, ifc_building_storey, ifc_wall)` - Returns `IfcDoor`
- `Window.to_ifc(ifc_file, ifc_building_storey, ifc_wall)` - Returns `IfcWindow`

Both methods create:
1. `IfcOpeningElement` (the void in the wall)
2. `IfcRelVoidsElement` (links opening to wall)
3. `IfcDoor` or `IfcWindow` (the element with geometry)
4. `IfcRelFillsElement` (links door/window to opening)

---

## Verification Steps

1. Apply the fix to `ifc_exporter.py`
2. Run the demo:
   ```bash
   cd /Users/benjaminfriedman/repos/bimcode
   source .venv/bin/activate
   python examples/sprint3_demo.py
   ```
3. Open `output/sprint3_demo.ifc` in an IFC viewer
4. Verify doors and windows are visible with geometry
5. Run tests:
   ```bash
   pytest tests/test_doors.py tests/test_windows.py -v
   ```

---

## Key Technical Notes

1. **Coordinate System**: All geometry is created in LOCAL coordinates (wall's local space)
2. **Boolean Operations**: Use `-` operator in build123d (NOT `cut()` which doesn't exist)
3. **Element Base Class**: Has `guid` property - don't set it manually
4. **Export Method**: Use `building.export_ifc(path)`, not `building.to_ifc()`
5. **Wall's `to_ifc()`**: Returns the `IfcWallStandardCase` entity, which is needed for hosted element export

---

## File Locations

| File | Path |
|------|------|
| IFC Exporter | `src/bimascode/export/ifc_exporter.py` |
| Door | `src/bimascode/architecture/door.py` |
| Window | `src/bimascode/architecture/window.py` |
| Demo | `examples/sprint3_demo.py` |
| Output | `output/sprint3_demo.ifc` |
