# Elevation View Door Issue

## Problem Summary

Doors are not appearing in elevation views even though they exist in the model and export correctly to IFC.

## Root Cause

**Walls do not have door/window openings cut from their 3D geometry.**

When HLR (Hidden Line Removal) processes combined wall + door geometry:
- Walls only: 42 lines
- Doors only: 36 lines
- Combined: 35 lines (LESS than walls alone!)

The solid wall geometry is occluding the door geometry because the wall doesn't have a void where the door should be.

## Technical Details

### Wall Geometry
- `Wall.get_geometry()` returns a solid box without openings
- `Wall.openings` property exists and collects `get_opening_geometry()` from hosted elements
- But openings are NOT subtracted from wall geometry

### Door Positioning (Fixed)
The door's `get_world_geometry()` was fixed to:
1. Use transform composition: `world_transform * local_position` (not chained `locate()` calls)
2. Center door in wall thickness: `y_offset = -frame_depth / 2`

Door world geometry is now correct:
- West Girls Bathroom door: X=[-50, 50], Y=[16050, 17050]
- Centered in 300mm wall thickness (100mm frame depth)

### Verification
```python
# Tested with school_views_demo.py
# Door HLR works correctly when processed alone
hlr.process_elements(doors_only, direction)  # Returns 36 lines

# But when combined with walls, door lines disappear
hlr.process_elements(walls + doors, direction)  # Returns 35 lines (fewer!)
```

## Solution Required

Modify `Wall.get_geometry()` or `Wall.get_world_geometry()` to subtract door/window openings:

```python
def get_world_geometry(self):
    """Get wall geometry with openings cut."""
    wall_geom = ... # existing wall solid

    for element in self._hosted_elements:
        if hasattr(element, 'get_opening_geometry'):
            opening = element.get_opening_geometry()
            # Transform opening to wall coordinates
            # Subtract from wall_geom using boolean cut
            wall_geom = wall_geom - opening

    return wall_geom
```

This is the architecturally correct approach - walls should represent their actual shape with voids for doors/windows.

## Files Involved

- `/src/bimascode/architecture/wall.py` - Needs opening subtraction
- `/src/bimascode/architecture/door.py` - `get_world_geometry()` fixed, `get_opening_geometry()` exists
- `/src/bimascode/drawing/hlr_processor.py` - HLR processing works correctly
- `/src/bimascode/drawing/elevation_view.py` - View generation works correctly

## IFC Export Note

User confirmed IFC export shows correct geometry with openings. This is because IFC export may handle openings differently (via IfcOpeningElement relationships) rather than boolean geometry.

## Test Case

West Elevation of school building should show door on "West Girls Bathroom West" wall at X=0.
- Wall runs from (0, 13500) to (0, 18500) at 90 degrees
- Door at offset 2550mm, width 1000mm, height 2150mm
- Door should appear in elevation at Y position ~16050-17050 (projected to 2D X ~ -16000 to -17000)
