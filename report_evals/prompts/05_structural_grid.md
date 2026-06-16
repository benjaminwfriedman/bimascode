# Eval 05: Structural Grid Building

## Prompt

Create a warehouse-style building with exposed structure:

Dimensions: 24m x 18m
Structural grid: 6m x 6m (4 bays x 3 bays)

Structure:
- Steel columns (400mm square) at each grid intersection
- Main beams spanning in the X direction (300mm x 500mm)
- Secondary beams in the Y direction (200mm x 400mm)

Envelope:
- Concrete exterior walls (200mm)
- Large loading door on the south wall (4m wide x 4m high)
- Regular doors on east and west walls
- Clerestory windows along the north wall (4 windows, each 2m wide)

Generate:
- IFC model
- DXF drawings (floor plan showing column grid, elevations, section)
- PDF drawing set

## Difficulty

Hard

## Skills Tested

- Structural grid layout
- Column placement at intersections
- Beam framing logic
- Large openings (loading doors)
- Structural vs architectural documentation
- DXF export with view templates

## Design Constraints

- Doors and windows must have at least 300mm clearance from wall corners/ends
- Doors and windows must have at least 300mm clearance from each other
- Columns and beams must not pass through doors or windows
- Interior walls must not connect to exterior walls at door/window locations
