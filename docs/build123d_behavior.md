# build123d Behavior Notes

This document captures important build123d behaviors discovered during development that affect geometry creation and transformation.

## 1. `locate()` REPLACES Transforms (Does NOT Chain)

**Critical:** Calling `shape.locate(transform)` **replaces** the shape's existing transform - it does NOT compose/chain transforms.

```python
# WRONG - second locate() replaces the first, losing the initial shift
box = Box(6000, 200, 400)                     # centered at origin
box = box.locate(Location((3000, 0, 0)))      # shift so X goes 0->6000
box = box.locate(Location((0, 0, 100)))       # REPLACES! Box is back centered at origin, just shifted Z

# CORRECT - compose transforms using multiplication BEFORE calling locate()
local_transform = Location((3000, 0, 0))      # internal positioning
world_transform = Location((0, 0, 100))       # world positioning
combined = world_transform * local_transform  # multiply to compose
box.locate(combined)                          # apply once
```

### Implications for `get_world_geometry()`

When `create_geometry()` applies an internal transform (e.g., shifting a centered Box to start at origin), and `get_world_geometry()` needs to apply a world transform, you MUST compose them:

```python
def get_world_geometry(self):
    import copy
    from build123d import Location

    local_geom = self.get_geometry()
    geom_copy = copy.copy(local_geom)  # Always copy first!

    # Compose the internal transform with world transform
    local_transform = Location((length/2, 0, 0))  # what create_geometry() applied
    world_transform = Location((x, y, z), (0, 0, 1), angle_deg)
    combined = world_transform * local_transform

    return geom_copy.locate(combined)
```

## 2. `locate()` Modifies Geometry IN PLACE

**Critical:** `shape.locate()` modifies the geometry in place AND returns the same object.

Since `get_geometry()` typically returns cached geometry, calling `locate()` on it corrupts the cache!

```python
# WRONG - corrupts cached geometry
def get_world_geometry(self):
    local_geom = self.get_geometry()      # Returns cached geometry
    return local_geom.locate(transform)   # CORRUPTS the cache!

# CORRECT - copy before transforming
def get_world_geometry(self):
    import copy
    local_geom = self.get_geometry()
    geom_copy = copy.copy(local_geom)     # Make a copy first!
    return geom_copy.locate(transform)
```

## 3. `Polygon()` Automatically Centers Vertices at Centroid

**Critical:** When creating a `Polygon` from a list of points, build123d automatically shifts all vertices so the polygon's centroid is at the origin.

```python
from build123d import Polygon

# Input boundary with corner at origin
boundary = [(0, 0), (6000, 0), (6000, 12000), (0, 12000)]
poly = Polygon(boundary)

# Centroid is at (3000, 6000)
# Polygon vertices are SHIFTED to center at origin:
for v in poly.vertices():
    print(f'({v.X}, {v.Y})')
# Output:
#   (-3000, -6000)
#   (3000, -6000)
#   (3000, 6000)
#   (-3000, 6000)
```

### Implications for Floor/Ceiling Geometry

When using `Polygon` + `extrude` for floors and ceilings, the resulting geometry is centered at the origin, not at the original boundary coordinates.

In `get_world_geometry()`, you must translate by the centroid to restore correct positioning:

```python
def get_world_geometry(self):
    import copy
    from build123d import Location

    local_geom = self.get_geometry()
    geom_copy = copy.copy(local_geom)

    # Polygon centers at origin, so translate by centroid to restore position
    cx, cy = self.get_centroid()
    z = self.level.elevation_mm

    return geom_copy.locate(Location((cx, cy, z)))
```

## 4. `Box()` is Centered at Origin

A `Box(length, width, height)` is created centered at the origin, spanning:
- X: `-length/2` to `+length/2`
- Y: `-width/2` to `+width/2`
- Z: `-height/2` to `+height/2`

To position a Box so its corner is at the origin (or base at Z=0), you need to apply a translation:

```python
# Box with base at Z=0 and centered in XY
box = Box(100, 100, 300)
box = box.locate(Location((0, 0, 150)))  # shift up by half height

# Box with corner at origin
box = Box(100, 100, 300)
box = box.locate(Location((50, 50, 150)))  # shift by half in each dimension
```

## Summary: Safe Pattern for `get_world_geometry()`

1. **Always copy** the cached local geometry before transforming
2. **Identify internal transforms** applied by `create_geometry()`
3. **Compose transforms** using multiplication if there are internal transforms
4. **Account for Polygon centering** when using extruded polygons

```python
def get_world_geometry(self):
    import copy
    from build123d import Location

    local_geom = self.get_geometry()
    if local_geom is None:
        return None

    # 1. Copy to avoid corrupting cache
    geom_copy = copy.copy(local_geom)

    # 2. Determine transforms
    # - internal_transform: what create_geometry() applied (if any)
    # - world_transform: position in world coordinates

    # 3. Compose if needed
    # combined = world_transform * internal_transform

    # 4. Apply once
    return geom_copy.locate(combined_or_world_transform)
```
