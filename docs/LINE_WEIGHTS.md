# Line Weights and Line Types Reference

This document describes the professional line weight and line type system implemented in BimasCode, which follows **AIA/NCS (US National CAD Standard)** and **ISO 128** specifications.

## Industry Standards Compliance

BimasCode's line weight system adheres to:

- **AIA CAD Layer Guidelines** - American Institute of Architects layer naming and line weight conventions
- **US National CAD Standard (NCS) v7** - Comprehensive CAD standards including plotting guidelines
- **ISO 128** - International standard for technical drawing line conventions

### ISO Line Weight Progression

Per ISO/DIN standards, line weights follow a mathematical progression based on √2 (approximately 1.414):

```
0.13 × √2 = 0.18
0.18 × √2 = 0.25
0.25 × √2 = 0.35
0.35 × √2 = 0.50
0.50 × √2 = 0.70
0.70 × √2 = 1.00
```

This progression ensures visual clarity and proper hierarchy when printed or displayed.

## Line Weight Definitions

BimasCode implements six standard line weights:

| Weight | Value (mm) | DXF Index | Use Case |
|--------|------------|-----------|----------|
| **HEAVY** | 0.70 | 70 | Primary cut elements (walls, columns) |
| **WIDE** | 0.50 | 50 | Secondary cut elements (doors, windows) |
| **MEDIUM** | 0.35 | 35 | Detail lines, projection lines |
| **NARROW** | 0.25 | 25 | Visible projection lines (default) |
| **FINE** | 0.18 | 18 | Patterns, hidden lines, above-cut elements |
| **EXTRA_FINE** | 0.13 | 13 | Annotations, dimension lines, center lines |

### Visual Hierarchy

The line weight hierarchy follows the industry-standard 3:2:1 ratio principle:

```
HEAVY (0.70) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  Cut walls/structure
WIDE  (0.50) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         Secondary cut
MEDIUM(0.35) ━━━━━━━━━━━━━━━━━━━━━━━               Details
NARROW(0.25) ━━━━━━━━━━━━━━━━━                     Visible projection
FINE  (0.18) ━━━━━━━━━━━━━                         Hidden/patterns
EXTRA (0.13) ━━━━━━━━━                             Annotations
```

## Line Type Definitions

Seven standard line types are available for different drawing conventions:

| Line Type | Pattern (mm) | Visual | Use Case |
|-----------|--------------|--------|----------|
| **CONTINUOUS** | Solid | ─────────── | Cut lines, visible edges |
| **DASHED** | 6.0 dash, 3.0 gap | ── ── ── ── | Long dash hidden lines |
| **HIDDEN** | 3.0 dash, 1.5 gap | ─ ─ ─ ─ ─ | Hidden below cut plane |
| **CENTER** | 12-3-3-3 | ───── ─ ───── ─ | Center lines, axes |
| **PHANTOM** | 12-3-3-3-3-3 | ───── ─ ─ ───── | Alternate positions |
| **DEMOLISH** | 3-1.5-1.5-1.5 | ─ . ─ . ─ . | Demolition elements |
| **ABOVE_CUT** | 4.0 dash, 2.0 gap | ── ── ── | Elements above cut plane |

## Element Line Weight Assignments

### Floor Plans

| Element | Cut Condition | Line Weight | Line Type |
|---------|---------------|-------------|-----------|
| Walls | Cut by plan | HEAVY (0.70) | CONTINUOUS |
| Walls | Below cut plane | NARROW (0.25) | CONTINUOUS |
| Columns | Cut by plan | HEAVY (0.70) | CONTINUOUS |
| Doors | Cut by plan | WIDE (0.50) | CONTINUOUS |
| Windows | Cut by plan | WIDE (0.50) | CONTINUOUS |
| Floors | Visible | NARROW (0.25) | CONTINUOUS |
| Ceilings | Above cut | FINE (0.18) | ABOVE_CUT |
| Furniture | Projection | NARROW (0.25) | CONTINUOUS |

### Sections and Elevations

| Element | Visibility | Line Weight | Line Type |
|---------|------------|-------------|-----------|
| Cut walls | Section cut | HEAVY (0.70) | CONTINUOUS |
| Cut floors/slabs | Section cut | HEAVY (0.70) | CONTINUOUS |
| Visible walls | Beyond section | NARROW (0.25) | CONTINUOUS |
| Hidden elements | Behind visible | FINE (0.18) | HIDDEN |
| Ground line | Reference | MEDIUM (0.35) | CONTINUOUS |

### Annotations

| Element | Line Weight | Line Type |
|---------|-------------|-----------|
| Dimension lines | EXTRA_FINE (0.13) | CONTINUOUS |
| Leader lines | EXTRA_FINE (0.13) | CONTINUOUS |
| Center lines | EXTRA_FINE (0.13) | CENTER |
| Grid lines | FINE (0.18) | CONTINUOUS |
| Section marks | MEDIUM (0.35) | CONTINUOUS |

## AIA Layer Naming

BimasCode uses AIA-standard layer names:

### Architecture (A-)
| Layer | Description |
|-------|-------------|
| `A-WALL` | General walls |
| `A-WALL-FIRE` | Fire-rated walls |
| `A-WALL-CORE` | Core/shaft walls |
| `A-DOOR` | Doors |
| `A-GLAZ` | Windows and glazing |
| `A-FLOR` | Floor elements |
| `A-CLNG` | Ceiling elements |
| `A-ROOF` | Roof elements |
| `A-STRS` | Stairs |
| `A-FURN` | Furniture |

### Structure (S-)
| Layer | Description |
|-------|-------------|
| `S-COLS` | Columns |
| `S-BEAM` | Beams |
| `S-SLAB` | Slabs |
| `S-FNDN` | Foundation |

### General (G-)
| Layer | Description |
|-------|-------------|
| `G-ANNO` | Annotations |
| `G-ANNO-DIMS` | Dimensions |
| `G-ANNO-SYMB` | Symbols |
| `G-GRID` | Grids |

## Code Usage

### Using Pre-defined Line Styles

```python
from bimascode.drawing.line_styles import LineStyle, LineWeight, LineType

# Pre-defined factory methods
cut_wall_style = LineStyle.cut_heavy()      # 0.70mm, solid, cut=True
door_style = LineStyle.cut_wide()           # 0.50mm, solid, cut=True
visible_style = LineStyle.visible()         # 0.25mm, solid
hidden_style = LineStyle.hidden()           # 0.18mm, dashed
above_style = LineStyle.above_cut()         # 0.18mm, above-cut dashed
center_style = LineStyle.center()           # 0.13mm, center line pattern
```

### Creating Custom Line Styles

```python
# Custom style with specific weight and type
custom_style = LineStyle(
    weight=LineWeight.MEDIUM,
    type=LineType.DASHED,
    color=(255, 0, 0),  # Optional RGB color
    is_cut=False
)

# Modify existing style
red_cut = LineStyle.cut_heavy().with_color((255, 0, 0))
thicker_hidden = LineStyle.hidden().with_weight(LineWeight.NARROW)
```

### Getting Line Weight for Elements

```python
# For cut elements (structural vs non-structural)
weight = LineWeight.for_cut_element(is_structural=True)   # Returns HEAVY
weight = LineWeight.for_cut_element(is_structural=False)  # Returns WIDE

# For projection elements
weight = LineWeight.for_projection(is_hidden=False)  # Returns NARROW
weight = LineWeight.for_projection(is_hidden=True)   # Returns FINE
```

## DXF Export

Line weights are automatically mapped to DXF lineweight indices during export:

```python
# Mapping in dxf_exporter.py
DXF_LINEWEIGHT_MAP = {
    LineWeight.EXTRA_FINE: 13,   # 0.13mm
    LineWeight.FINE: 18,         # 0.18mm
    LineWeight.NARROW: 25,       # 0.25mm
    LineWeight.MEDIUM: 35,       # 0.35mm
    LineWeight.WIDE: 50,         # 0.50mm
    LineWeight.HEAVY: 70,        # 0.70mm
}
```

Line type patterns are also exported:

```python
DXF_LINETYPES = {
    LineType.CONTINUOUS: None,                        # Solid
    LineType.DASHED: [6.0, -3.0],                    # Long dash
    LineType.HIDDEN: [3.0, -1.5],                    # Short dash
    LineType.CENTER: [12.0, -3.0, 3.0, -3.0],        # Center
    LineType.PHANTOM: [12.0, -3.0, 3.0, -3.0, 3.0, -3.0],
    LineType.DEMOLISH: [3.0, -1.5, 0.5, -1.5],
    LineType.ABOVE_CUT: [4.0, -2.0],
}
```

## View Templates

View templates can override line weights per element category:

```python
from bimascode.drawing.view_templates import ViewTemplate

# Pre-defined templates
floor_plan = ViewTemplate.floor_plan_default()
rcp = ViewTemplate.reflected_ceiling_plan()
section = ViewTemplate.section_default()
elevation = ViewTemplate.elevation_default()
structural = ViewTemplate.structural_plan()  # Architecture halftoned
```

## References

- [US National CAD Standard v7](https://www.nationalcadstandard.org/ncs7/content.php)
- [AIA CAD Layer Guidelines](https://www.cadcam.org/blog/what-are-the-aia-layering-standards-for-cad-drawings)
- [ISO 128 Line Weight Standards](https://caddrafter.us/line-weights-and-annotation-standards/)
- [Technical Drawing Line Types](https://cadsetterout.com/drawing-standards/line-type-definitions/)
- [Standard CAD Lineweights](https://www.cad-standard.com/cad-lines/standard-cad-lineweight)
