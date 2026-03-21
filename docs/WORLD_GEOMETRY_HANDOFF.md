# World Geometry Transformation Handoff

## Summary

All BIM elements in bimascode create their geometry in **local coordinates**. For proper rendering in elevation views, section views, and HLR (Hidden Line Removal) processing, each element needs a `get_world_geometry()` method that transforms local geometry to world coordinates.

**Current Status**: Only 3 of 7 element types have `get_world_geometry()` implemented.

## Element Coordinate Systems

| Element | Local Origin | Local Axes | Has get_world_geometry() |
|---------|-------------|------------|--------------------------|
| **Wall** | Wall start point | X=along length, Y=perpendicular, Z=up | YES |
| **Door** | Bottom-left corner | X=width, Y=depth, Z=up | YES |
| **Window** | Bottom-left corner | X=width, Y=depth, Z=up | **NO** |
| **Floor** | Boundary corner, Z=0 | XY=boundary plane, Z=up | YES |
| **Ceiling** | (0,0,0), XY plane | XY=boundary, Z=down from height | **NO** |
| **Column** | Base center | X=width, Y=depth, Z=up | **NO** |
| **Beam** | Start point | X=length, Y=width, Z=height | **NO** |

## Task: Implement Missing get_world_geometry() Methods

### Window (Highest Priority - similar to Door)

Location: `src/bimascode/architecture/window.py`

Windows are hosted in walls, just like doors. Copy the pattern from `door.py`:

```python
def get_world_geometry(self):
    """Get window geometry transformed to world coordinates."""
    from build123d import Location

    local_geom = self.get_geometry()
    if local_geom is None:
        return None

    if self.host_wall is None:
        return local_geom

    # Get wall's world transform
    wall = self.host_wall
    start = wall.start_point
    angle_deg = wall.angle_degrees
    level_z = wall.level.elevation_mm

    # Position along wall
    offset = self.offset
    wall_angle = wall.angle
    import math
    pos_x = start[0] + offset * math.cos(wall_angle)
    pos_y = start[1] + offset * math.sin(wall_angle)
    pos_z = level_z + self.sill_height  # Note: windows have sill_height, doors don't

    # Apply transform
    world_geom = local_geom.locate(Location(
        (pos_x, pos_y, pos_z),
        (0, 0, 1),
        angle_deg
    ))

    return world_geom
```

### Column

Location: `src/bimascode/structure/column.py`

Columns have a placement point and extend upward:

```python
def get_world_geometry(self):
    """Get column geometry transformed to world coordinates."""
    from build123d import Location

    local_geom = self.get_geometry()
    if local_geom is None:
        return None

    # Column placement is at base center
    x, y = self.location  # Assuming column has location property
    z = self.level.elevation_mm if self.level else 0

    # Apply rotation if column has angle
    angle = getattr(self, 'rotation', 0)

    world_geom = local_geom.locate(Location(
        (x, y, z),
        (0, 0, 1),
        angle
    ))

    return world_geom
```

### Beam

Location: `src/bimascode/structure/beam.py`

Beams have start/end points similar to walls:

```python
def get_world_geometry(self):
    """Get beam geometry transformed to world coordinates."""
    from build123d import Location
    import math

    local_geom = self.get_geometry()
    if local_geom is None:
        return None

    start = self.start_point
    end = self.end_point

    # Calculate angle from start to end
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle_deg = math.degrees(math.atan2(dy, dx))

    # Z position
    z = self.level.elevation_mm + self.elevation_offset if hasattr(self, 'elevation_offset') else 0

    world_geom = local_geom.locate(Location(
        (start[0], start[1], z),
        (0, 0, 1),
        angle_deg
    ))

    return world_geom
```

### Ceiling

Location: `src/bimascode/architecture/ceiling.py`

Ceilings are placed at a height above a level:

```python
def get_world_geometry(self):
    """Get ceiling geometry transformed to world coordinates."""
    from build123d import Location

    local_geom = self.get_geometry()
    if local_geom is None:
        return None

    # Ceiling is at level elevation + ceiling height
    z = self.level.elevation_mm + self.height if self.level else self.height

    world_geom = local_geom.locate(Location((0, 0, z)))

    return world_geom
```

## CRITICAL: build123d locate() Behavior

### Issue 1: locate() modifies IN PLACE

**`shape.locate()` modifies the geometry IN PLACE and returns the same object.**

Since `get_geometry()` returns cached geometry, calling `locate()` on it corrupts the cache!

```python
# WRONG - corrupts cached geometry
def get_world_geometry(self):
    local_geom = self.get_geometry()  # Returns cached geometry
    return local_geom.locate(transform)  # CORRUPTS the cache!

# CORRECT - copy before transforming
def get_world_geometry(self):
    import copy
    local_geom = self.get_geometry()
    geom_copy = copy.copy(local_geom)  # Make a copy first!
    return geom_copy.locate(transform)
```

### Issue 2: locate() REPLACES transforms, doesn't chain

**`shape.locate()` REPLACES the shape's transform - it does NOT compose/chain transforms.**

```python
# WRONG - second locate() replaces the first, losing the height shift
box = Box(300, 300, 3000)                    # centered at origin, Z=[-1500, 1500]
box = box.locate(Location((0, 0, 1500)))     # shift base to Z=0, now Z=[0, 3000]
box = box.locate(Location((x, y, z)))        # REPLACES! Back to Z=[-1500, 1500] + z

# CORRECT - compose transforms using multiplication BEFORE calling locate()
local_transform = Location((0, 0, 1500))     # shift to put base at Z=0
world_transform = Location((x, y, z), (0,0,1), angle_deg)
combined = world_transform * local_transform
geom_copy.locate(combined)
```

**When implementing get_world_geometry():**
1. ALWAYS use `copy.copy(local_geom)` before calling `locate()`
2. If `create_geometry()` applies an internal transform, compose transforms with multiplication
3. See Door.get_world_geometry() for the correct pattern

## How HLR Uses World Geometry

In `src/bimascode/drawing/hlr_processor.py`, the `process_elements()` method:

```python
for element in elements:
    # Prefer world geometry if available
    if hasattr(element, "get_world_geometry"):
        geometry = element.get_world_geometry()
    elif hasattr(element, "get_geometry"):
        geometry = element.get_geometry()
    else:
        geometry = None
```

Without `get_world_geometry()`, elements will render at the wrong position in elevation/section views.

## Testing

After implementing, test with:

1. Add windows to the school demo
2. Run `python examples/school_views_demo.py`
3. Check elevation DXFs - windows should appear in correct positions on facade
4. Check section DXFs - windows should appear where walls are cut

## Files to Modify

1. `src/bimascode/architecture/window.py` - Add get_world_geometry()
2. `src/bimascode/structure/column.py` - Add get_world_geometry()
3. `src/bimascode/structure/beam.py` - Add get_world_geometry()
4. `src/bimascode/architecture/ceiling.py` - Add get_world_geometry()

## Reference Implementations

- Wall: `src/bimascode/architecture/wall.py` lines 137-166
- Door: `src/bimascode/architecture/door.py` lines 119-178
- Floor: `src/bimascode/architecture/floor.py` lines 152-175
