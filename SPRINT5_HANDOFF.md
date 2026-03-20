# Sprint 5 Handoff Document

## Summary

Sprints 1-4 are **100% complete**. All 267 tests pass with 86% coverage. The codebase now includes:
- Building/Level/Grid hierarchy
- Walls, Floors, Roofs with compound layers
- Doors, Windows with hosted element support
- Floor/Roof openings
- Wall join detection and processing
- Rooms with area/volume calculations
- Ceilings
- Structural columns and beams
- Structural flags for walls/floors
- Room schedule generation
- Full IFC export for all elements

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
- Material layer assignment per wall layer

### Sprint 4: Spatial + Structural
- `Room` with boundary polygon, area/volume, finishes
- `Ceiling` with height parameter
- `StructuralColumn` with rectangular profile
- `Beam` spanning between 3D points
- `structural` flag for Wall (SHEAR) and Floor (BASESLAB)
- `building.room_schedule()` returning pandas DataFrame

---

## Sprint 5: Performance Infrastructure

**Theme:** Spatial indexing and 2D representation caching for scalable floor plan generation.

**Duration:** 2 weeks

**Why This Matters:** Without performance infrastructure, generating floor plans for realistic projects (500+ elements) becomes prohibitively slow. Sprint 6 (Views) depends on this work.

### Features to Implement

#### 1. Bounding Box Pre-Filter (Issue #26)

**Purpose:** Filter elements by AABB intersection before expensive section cuts.

```python
# Spatial index automatically built
building.add_element(wall1)
building.add_element(wall2)
# ... add 1000 elements

# Only elements intersecting cut plane are processed
floor_plan = FloorPlanView(level=ground, cut_height=1200)
floor_plan.generate()  # Fast - pre-filtered to relevant elements
```

**Requirements:**
- BVH (Bounding Volume Hierarchy) or R-tree spatial index
- AABB calculation for each element type
- Intersection test before section cut
- Index update on element modification

**Performance Targets:**
- 1000-element model: filter to ~100 elements for typical floor plan
- Intersection test: <1ms per query
- Index build time: <100ms for 1000 elements

**Files:**
- `src/bimascode/performance/spatial_index.py` (NEW)
- `src/bimascode/performance/bounding_box.py` (NEW)
- `src/bimascode/performance/__init__.py` (NEW)

#### 2. 2D Representation Caching (Issue #25)

**Purpose:** Store computed 2D linework to avoid redundant section cuts.

```python
# First floor plan generation: computes and caches
floor_plan.generate()  # Slower - computes sections

# Second generation: uses cache
floor_plan.generate()  # Fast - uses cached 2D

# After modification: cache invalidates
wall.start_point = (100, 0)  # Cache invalidates for this wall
floor_plan.generate()  # Recomputes only modified wall
```

**Requirements:**
- IFC context for 2D representations (`Plan`, `Annotation`)
- Cached 2D linework storage per element
- Cache invalidation on geometry change
- Timestamp-based modification tracking

**Performance Targets:**
- 90% reduction in section cut computation time
- 1000-wall model exports in <30 seconds
- Memory overhead: <10% increase for cached data

**Files:**
- `src/bimascode/performance/representation_cache.py` (NEW)
- `src/bimascode/core/element.py` (MODIFY - add modification timestamp)

---

## Deliverables

- [ ] Spatial index with BVH or R-tree
- [ ] AABB calculation for all element types (Wall, Floor, Roof, Door, Window, Column, Beam, Ceiling, Room)
- [ ] 2D representation cache with invalidation
- [ ] Modification timestamp on Element base class
- [ ] Performance benchmarks showing targets met
- [ ] Integration tests with 1000+ element models
- [ ] All new tests passing

---

## Technical Notes

### Spatial Indexing Options

**Option 1: rtree library (Recommended)**
```python
from rtree import index

class SpatialIndex:
    def __init__(self):
        self._idx = index.Index()

    def insert(self, element_id: int, bbox: tuple):
        # bbox = (min_x, min_y, min_z, max_x, max_y, max_z)
        self._idx.insert(element_id, bbox)

    def intersects(self, bbox: tuple) -> List[int]:
        return list(self._idx.intersection(bbox))
```

**Option 2: Custom BVH**
```python
class BVHNode:
    def __init__(self, bbox, left=None, right=None, element=None):
        self.bbox = bbox
        self.left = left
        self.right = right
        self.element = element  # Leaf node only
```

### AABB Calculation

Each element type needs `get_bounding_box()`:

```python
class Wall:
    def get_bounding_box(self) -> BoundingBox:
        """Return axis-aligned bounding box."""
        # Calculate from start_point, end_point, height, and type width
        min_x = min(self.start_point[0], self.end_point[0]) - self.type.total_width / 2
        max_x = max(self.start_point[0], self.end_point[0]) + self.type.total_width / 2
        min_y = min(self.start_point[1], self.end_point[1]) - self.type.total_width / 2
        max_y = max(self.start_point[1], self.end_point[1]) + self.type.total_width / 2
        min_z = self.level.elevation_mm
        max_z = min_z + self.height
        return BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)
```

### Cache Invalidation Strategy

```python
class Element:
    def __init__(self, ...):
        self._modified_timestamp = time.time()
        self._cached_2d = None
        self._cache_timestamp = 0

    def _invalidate_cache(self):
        """Call this when geometry changes."""
        self._modified_timestamp = time.time()
        self._cached_2d = None

    def get_2d_representation(self, cut_height: float):
        if self._cache_timestamp < self._modified_timestamp:
            self._cached_2d = self._compute_2d_section(cut_height)
            self._cache_timestamp = time.time()
        return self._cached_2d
```

### Property Setters for Cache Invalidation

```python
class Wall:
    @property
    def start_point(self):
        return self._start_point

    @start_point.setter
    def start_point(self, value):
        self._start_point = value
        self._invalidate_cache()  # Triggers recalculation
```

---

## File Structure

```
src/bimascode/
├── performance/
│   ├── __init__.py           # NEW: Module exports
│   ├── bounding_box.py       # NEW: BoundingBox class
│   ├── spatial_index.py      # NEW: SpatialIndex class (R-tree wrapper)
│   └── representation_cache.py # NEW: 2D caching logic
├── core/
│   └── element.py            # MODIFY: Add timestamp, cache invalidation
├── architecture/
│   ├── wall.py               # MODIFY: Add get_bounding_box(), property setters
│   ├── floor.py              # MODIFY: Add get_bounding_box()
│   ├── roof.py               # MODIFY: Add get_bounding_box()
│   ├── door.py               # MODIFY: Add get_bounding_box()
│   ├── window.py             # MODIFY: Add get_bounding_box()
│   └── ceiling.py            # MODIFY: Add get_bounding_box()
├── structure/
│   ├── column.py             # MODIFY: Add get_bounding_box()
│   └── beam.py               # MODIFY: Add get_bounding_box()
└── spatial/
    └── room.py               # MODIFY: Add get_bounding_box()

tests/
├── test_bounding_box.py      # NEW
├── test_spatial_index.py     # NEW
├── test_representation_cache.py # NEW
└── test_performance.py       # NEW: Benchmark tests
```

---

## Dependencies

**New Dependencies:**
- `rtree`: R-tree spatial indexing (already installed via `Rtree`)

**Existing Dependencies:**
- `build123d`: For geometry bounding box calculation
- `time`: For modification timestamps

---

## Performance Benchmarks

Create `tests/test_performance.py`:

```python
import pytest
import time
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import Wall, WallType

class TestPerformance:
    def test_spatial_index_query_time(self):
        """Spatial query should be <1ms."""
        building = Building("Benchmark")
        level = Level(building, "Ground", 0)
        wall_type = WallType("Standard")

        # Add 1000 walls
        for i in range(1000):
            Wall(wall_type, (i*100, 0), (i*100+50, 0), level, height=3000)

        # Query time
        start = time.time()
        for _ in range(100):
            building.spatial_index.intersects((5000, -100, 0, 5500, 100, 3000))
        elapsed = (time.time() - start) / 100

        assert elapsed < 0.001  # <1ms per query

    def test_cache_speedup(self):
        """Second floor plan generation should be 90% faster."""
        # Setup building with walls
        # First generation: measure time
        # Second generation: should be <10% of first time
        pass
```

---

## IFC 2D Representation Context

For IFC export of cached 2D representations:

```python
# Create 2D representation context
context_2d = ifc_file.createIfcGeometricRepresentationContext(
    ContextIdentifier="Plan",
    ContextType="Plan",
    CoordinateSpaceDimension=2,
    Precision=1.0e-5,
    WorldCoordinateSystem=axis2placement,
    TrueNorth=None
)

# Create 2D shape representation
shape_2d = ifc_file.createIfcShapeRepresentation(
    context_2d,
    "Annotation",
    "Curve2D",
    [polyline_2d]
)
```

---

## Current Test Status

```
267 passed, 11 warnings
Coverage: 86%
```

All existing tests must continue to pass after Sprint 5 implementation.

---

## Testing Commands

```bash
# Activate virtual environment
cd /Users/benjaminfriedman/repos/bimcode
source venv/bin/activate

# Run all tests
pytest

# Run performance tests
pytest tests/test_performance.py -v

# Run with coverage
pytest --cov=src/bimascode

# Run specific test file
pytest tests/test_spatial_index.py -v
```

---

## Demo Script Location

Create a demo at `examples/sprint5_demo.py` showing:
- Building with 500+ elements
- Spatial index query performance
- Cache hit/miss demonstration
- Performance comparison with/without caching

---

## Git Branch

Work on `main` branch. Commit message format:
```
Complete Sprint 5: Performance Infrastructure

- Spatial index with R-tree for element filtering
- AABB calculation for all element types
- 2D representation caching with invalidation
- Modification timestamps for cache control
- Performance benchmarks meeting targets

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Related Issues

| Issue | Title | Status |
|-------|-------|--------|
| #25 | 2D Representation Caching | Open |
| #26 | Bounding Box Pre-Filter | Open |

---

## Sprint 6 Preview

Sprint 5 enables Sprint 6 (Drawing/Views):
- FloorPlanView using spatial index for element filtering
- Section View using cached 2D representations
- Elevation View
- View Scale, Crop, Range
