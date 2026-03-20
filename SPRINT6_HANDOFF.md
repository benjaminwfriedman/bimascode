# Sprint 6 Handoff: Drawing Generation

**Sprint Duration:** 3 weeks
**Complexity:** 🔴 High
**Epoch:** 2 - Production
**Prerequisites:** Sprint 5 (Performance Infrastructure) ✅

---

## Overview

Sprint 6 is the start of Epoch 2: Production. This sprint implements the core drawing engine that generates 2D views from 3D BIM geometry. It leverages the spatial indexing and caching infrastructure from Sprint 5 to achieve acceptable performance on large models.

**Key Deliverables:**
- Floor plan view generation with horizontal section cuts
- Building section view generation with HLR
- Exterior elevation view generation
- Line weight and line type standards
- View visibility controls and templates

---

## Issues to Implement

### Core View Generation (High Complexity)

#### Issue #47: Floor Plan View Generation 🔴
```python
class FloorPlanView:
    """Horizontal section cut view for floor plans."""

    def __init__(
        self,
        level: Level,
        cut_height: float = 1200,  # mm above level
        view_depth_below: float = 0,
        view_depth_above: float = 2400,
        crop_region: Optional[BoundingBox] = None,
        scale: str = "1:100"
    ):
        pass

    def generate(self) -> ViewResult:
        """Generate 2D linework from 3D model."""
        pass
```

**Algorithm:**
1. Filter elements by bounding box intersection with cut plane (use SpatialIndex)
2. Check RepresentationCache for cached 2D linework
3. For uncached elements, compute OCCT section cut
4. Organize linework by category and line weight
5. Apply view range filtering (above/below cut plane)

**Line Classification:**
- **Cut lines** (thick): Elements intersected by cut plane (walls, columns)
- **Below lines** (medium): Elements below cut plane but visible (floors, furniture)
- **Above lines** (thin/dashed): Elements above cut plane (ceilings, beams)

#### Issue #48: Section View Generation 🔴
```python
class SectionView:
    """Vertical section cut view."""

    def __init__(
        self,
        cut_plane: Plane,  # Defined by point + normal
        depth: float,      # How far to look beyond cut
        height: float,     # View height extent
        crop_region: Optional[BoundingBox] = None,
        scale: str = "1:50"
    ):
        pass
```

**Algorithm:**
1. Filter elements by bounding box intersection with section volume
2. Compute OCCT section cut for elements at cut plane
3. Run Hidden Line Removal (HLR) for elements beyond cut
4. Classify lines: cut (thick), visible (medium), hidden (thin dashed)

#### Issue #49: Elevation View Generation 🔴
```python
class ElevationView:
    """Orthographic projection view (no section cut)."""

    def __init__(
        self,
        direction: Tuple[float, float, float],  # View direction vector
        crop_region: Optional[BoundingBox] = None,
        scale: str = "1:100"
    ):
        pass
```

**Algorithm:**
1. Filter elements by bounding box intersection with view frustum
2. Run HLR from view direction
3. Classify lines: visible (medium), hidden (thin dashed)

---

### View Parameters (Low-Medium Complexity)

#### Issue #53: View Crop Region 🟢
```python
@dataclass
class CropRegion:
    """Rectangular boundary that clips view extent."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def clip(self, linework: List[Line]) -> List[Line]:
        """Clip linework to crop region."""
        pass
```

#### Issue #30: View Scale 🟢
```python
class ViewScale:
    """Scale factor for views."""

    SCALES = {
        "1:1": 1.0,
        "1:10": 0.1,
        "1:20": 0.05,
        "1:50": 0.02,
        "1:100": 0.01,
        "1:200": 0.005,
    }

    def __init__(self, scale_str: str):
        self.factor = self.SCALES[scale_str]
```

#### Issue #31: View Range / Cut Height 🟡
```python
@dataclass
class ViewRange:
    """Controls what's visible in a floor plan view."""
    cut_plane_elevation: float  # Section cut height (typically 1200mm)
    view_depth_below: float     # How far below cut to show (typically 0)
    view_depth_above: float     # How far above cut to show (typically 2400mm)
    bottom_clip: float          # Absolute bottom of visible range
    top_clip: float             # Absolute top of visible range
```

---

### Line Standards (Medium Complexity)

#### Issue #61: Line Weights and Line Types 🟡
```python
from enum import Enum

class LineWeight(Enum):
    """Standard line weights per AIA/NCS standards."""
    EXTRA_FINE = 0.13  # mm
    FINE = 0.18
    THIN = 0.25
    MEDIUM = 0.35
    THICK = 0.50
    EXTRA_THICK = 0.70

class LineType(Enum):
    """Standard line types."""
    CONTINUOUS = "Continuous"
    DASHED = "Dashed"
    DOTTED = "Dotted"
    DASH_DOT = "Dash-Dot"
    HIDDEN = "Hidden"
    CENTER = "Center"

@dataclass
class LineStyle:
    """Complete line styling."""
    weight: LineWeight
    type: LineType
    color: Optional[Tuple[int, int, int]] = None  # RGB, None = ByLayer
```

**Default Line Assignments:**
| Element State | Weight | Type |
|---------------|--------|------|
| Cut (section) | THICK | CONTINUOUS |
| Visible | MEDIUM | CONTINUOUS |
| Hidden | THIN | DASHED |
| Above cut plane | FINE | CONTINUOUS |
| Annotation | THIN | CONTINUOUS |

#### Issue #62: View Visibility and View Templates 🟡
```python
class CategoryVisibility(Enum):
    """Visibility states for element categories."""
    VISIBLE = "visible"
    HIDDEN = "hidden"
    HALFTONE = "halftone"

@dataclass
class GraphicOverride:
    """Override graphics for a category."""
    visibility: CategoryVisibility = CategoryVisibility.VISIBLE
    line_weight: Optional[LineWeight] = None
    line_color: Optional[Tuple[int, int, int]] = None
    halftone: bool = False

class ViewTemplate:
    """Reusable view settings."""

    def __init__(self, name: str):
        self.name = name
        self.category_overrides: Dict[str, GraphicOverride] = {}
        self.default_line_weights: Dict[str, LineWeight] = {}

    @classmethod
    def architectural(cls) -> "ViewTemplate":
        """Standard architectural floor plan template."""
        template = cls("Architectural")
        template.category_overrides["Structure"] = GraphicOverride(
            visibility=CategoryVisibility.HALFTONE
        )
        return template

    @classmethod
    def structural(cls) -> "ViewTemplate":
        """Standard structural plan template."""
        template = cls("Structural")
        template.category_overrides["Architecture"] = GraphicOverride(
            visibility=CategoryVisibility.HALFTONE
        )
        return template
```

---

## Data Structures

### ViewResult
```python
@dataclass
class ViewResult:
    """Output from view generation."""
    linework: List[Line2D]
    annotations: List[Annotation]  # Added in Sprint 7
    crop_region: CropRegion
    scale: ViewScale

    def to_dxf_entities(self) -> List[DXFEntity]:
        """Convert to DXF entities for export."""
        pass

@dataclass
class Line2D:
    """2D line segment with styling."""
    start: Tuple[float, float]
    end: Tuple[float, float]
    style: LineStyle
    layer: str

@dataclass
class Arc2D:
    """2D arc segment with styling."""
    center: Tuple[float, float]
    radius: float
    start_angle: float
    end_angle: float
    style: LineStyle
    layer: str
```

### Element 2D Representation Protocol
```python
class Has2DRepresentation(Protocol):
    """Protocol for elements that can generate 2D representations."""

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: ViewRange
    ) -> List[Line2D | Arc2D]:
        """Generate floor plan linework."""
        ...

    def get_section_representation(
        self,
        cut_plane: Plane
    ) -> List[Line2D | Arc2D]:
        """Generate section cut linework."""
        ...
```

---

## Implementation Strategy

### Phase 1: Core Infrastructure (Week 1)
1. Create `src/bimascode/drawing/` module structure
2. Implement `LineWeight`, `LineType`, `LineStyle` enums
3. Implement `Line2D`, `Arc2D`, `ViewResult` data classes
4. Implement `ViewScale`, `ViewRange`, `CropRegion`

### Phase 2: Floor Plan Generation (Week 2)
1. Implement `FloorPlanView` class
2. Add `get_plan_representation()` to Wall, Door, Window
3. Integrate with SpatialIndex for element filtering
4. Integrate with RepresentationCache for caching
5. Implement line clipping for crop region

### Phase 3: Section/Elevation + Templates (Week 3)
1. Implement `SectionView` class with OCCT HLR
2. Implement `ElevationView` class
3. Implement `ViewTemplate` and `GraphicOverride`
4. Add comprehensive tests
5. Performance benchmarking

---

## File Structure

```
src/bimascode/drawing/
├── __init__.py
├── line_styles.py      # LineWeight, LineType, LineStyle
├── geometry_2d.py      # Line2D, Arc2D, Polyline2D
├── view_base.py        # Base View class, ViewResult, ViewRange
├── floor_plan.py       # FloorPlanView
├── section.py          # SectionView
├── elevation.py        # ElevationView
├── crop_region.py      # CropRegion with clipping
├── view_scale.py       # ViewScale
├── visibility.py       # CategoryVisibility, GraphicOverride, ViewTemplate
└── hlr.py              # Hidden Line Removal wrapper

tests/
├── test_line_styles.py
├── test_floor_plan.py
├── test_section.py
├── test_elevation.py
├── test_view_templates.py
└── test_drawing_performance.py
```

---

## Technical Notes

### OCCT Hidden Line Removal
```python
from OCC.Core.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCC.Core.HLRAlgo import HLRAlgo_Projector

def compute_hlr(shape, view_direction):
    """Compute hidden line removal for a shape."""
    hlr = HLRBRep_Algo()
    hlr.Add(shape)

    # Set up projector (orthographic)
    projector = HLRAlgo_Projector(
        gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*view_direction))
    )
    hlr.Projector(projector)
    hlr.Update()
    hlr.Hide()

    # Extract result
    hlr_shapes = HLRBRep_HLRToShape(hlr)
    visible_sharp = hlr_shapes.VCompound()
    hidden_sharp = hlr_shapes.HCompound()

    return visible_sharp, hidden_sharp
```

### Section Cut with OCCT
```python
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section

def compute_section(shape, plane):
    """Compute section cut of shape with plane."""
    section = BRepAlgoAPI_Section(shape, plane)
    section.Build()
    return section.Shape()
```

### Performance Targets
- Floor plan generation: <5 seconds for 500 elements
- Section view generation: <10 seconds for 500 elements
- Cache hit should reduce subsequent generation to <500ms

---

## Testing Strategy

### Unit Tests
- Line style enums and conversions
- View scale calculations
- Crop region clipping
- View range filtering

### Integration Tests
- Floor plan from simple building (4 walls, 1 door, 1 window)
- Section through multi-story building
- Elevation of building facade

### Visual Regression Tests
- Known-good DXF output comparisons
- Linework geometry verification

### Performance Tests
- 500-element floor plan benchmark
- Cache hit rate verification
- Memory usage profiling

---

## Acceptance Criteria

- [ ] Floor plan view generates correct 2D linework from walls/doors/windows
- [ ] Section view shows cut elements thick, visible elements medium, hidden dashed
- [ ] Elevation view shows visible/hidden edge distinction
- [ ] Line weights match AIA/NCS standards
- [ ] View templates correctly override category visibility
- [ ] Crop region clips linework correctly
- [ ] Performance meets targets (<5s for 500 elements)
- [ ] All existing tests continue to pass
- [ ] New tests achieve >85% coverage of drawing module

---

## Dependencies

- **build123d**: 3D geometry operations
- **OCC (OpenCASCADE)**: Section cuts and HLR
- **shapely**: 2D geometry operations (clipping)
- **Sprint 5**: SpatialIndex, RepresentationCache, BoundingBox

---

## Risk Mitigation

1. **HLR Performance**: May need to limit HLR to visible elements only; use bounding box pre-filter aggressively
2. **Complex Geometry**: Curved walls and irregular shapes may produce excessive line segments; implement simplification
3. **Line Classification**: Ensuring correct cut/visible/hidden classification requires careful Z-coordinate tracking

---

## Notes

- Sprint 6 is blocking for Sprints 7-8 (annotations and sheets depend on views)
- View generation will be enhanced in Sprint 7 with annotation support
- DXF export (Sprint 8) will consume ViewResult objects
