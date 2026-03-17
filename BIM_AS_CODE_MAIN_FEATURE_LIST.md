# BIM as Code — Master Feature Analysis
## Integrated Priority Roadmap

*Prepared by Benny Friedman | March 2026*

> **Purpose:** This document consolidates research from three prior briefs — landscape analysis, Revit feature parity, and drawing set production — into a single prioritized feature list. It is the working spec for library development sequencing.

---

## Priority Framework

| Label | Definition |
|---|---|
| **P0** | Blocking. The library cannot be used on real projects without this. Must ship in v1.0. |
| **P1** | Required for credible parity. AEC professionals expect this. Ship in v1.x. |
| **P2** | Roadmap. Completes the picture but does not block adoption. Post v1. |
| **Out** | Deliberately out of scope. Either handled by downstream tools or irrelevant to a code-first approach. |

Each feature also carries a **complexity rating** (engineering effort):

| Rating | Meaning |
|---|---|
| 🟢 Low | Straightforward wrapper over existing library. Days to weeks. |
| 🟡 Medium | Non-trivial design or integration work. Weeks to a month. |
| 🔴 High | Significant R&D, geometry algorithm work, or cross-cutting concern. Months. |

---

## Summary Table

| # | Feature | Domain | Priority | Complexity | Underlying Library |
|---|---|---|---|---|---|
| 1 | Wall (straight, compound layers) | Architecture | P0 | 🟡 | build123d + IfcOpenShell |
| 2 | Floor / slab | Architecture | P0 | 🟡 | build123d + IfcOpenShell |
| 3 | Roof (flat, pitched, shed) | Architecture | P0 | 🟡 | build123d + IfcOpenShell |
| 4 | Door (hosted in wall) | Architecture | P0 | 🟡 | build123d + IfcOpenShell |
| 5 | Window (hosted in wall) | Architecture | P0 | 🟡 | build123d + IfcOpenShell |
| 6 | Ceiling | Architecture | P0 | 🟢 | IfcOpenShell |
| 7 | Stair (straight, L-shape, U-shape) | Architecture | P0 | 🔴 | build123d + IfcOpenShell |
| 8 | Ramp | Architecture | P1 | 🟡 | build123d + IfcOpenShell |
| 9 | Railing / guardrail | Architecture | P1 | 🟡 | build123d + IfcOpenShell |
| 10 | Curtain wall | Architecture | P1 | 🔴 | build123d + IfcOpenShell |
| 11 | Column (architectural) | Architecture | P1 | 🟢 | build123d + IfcOpenShell |
| 12 | Room / Space | Spatial | P0 | 🟡 | shapely + IfcOpenShell |
| 13 | Room boundary detection (from walls) | Spatial | P1 | 🔴 | shapely + OCCT |
| 14 | Area plan / area scheme | Spatial | P2 | 🟡 | shapely + IfcOpenShell |
| 15 | Level / Building storey | Spatial | P0 | 🟢 | IfcOpenShell |
| 16 | Building / Site hierarchy | Spatial | P0 | 🟢 | IfcOpenShell |
| 17 | Grid lines | Spatial | P0 | 🟢 | IfcOpenShell + ezdxf |
| 18 | WallType (compound layer stack) | Parametric | P0 | 🟡 | IfcOpenShell |
| 19 | Type / instance parameter model | Parametric | P0 | 🟡 | Python dataclasses |
| 20 | Formula-driven parameters | Parametric | P1 | 🟡 | Python @property |
| 21 | Custom component (family equivalent) | Parametric | P1 | 🟡 | Python @component decorator |
| 22 | Shared / project parameters | Parametric | P2 | 🟢 | IfcOpenShell property sets |
| 23 | Material definition (render + physical) | Materials | P0 | 🟢 | IfcOpenShell |
| 24 | Material layer assignment | Materials | P0 | 🟢 | IfcOpenShell |
| 25 | Structural column | Structural | P0 | 🟡 | build123d + IfcOpenShell |
| 26 | Beam | Structural | P0 | 🟡 | build123d + IfcOpenShell |
| 27 | Structural wall | Structural | P0 | 🟢 | IfcOpenShell |
| 28 | Structural floor / slab | Structural | P0 | 🟢 | IfcOpenShell |
| 29 | Foundation (isolated, strip, mat) | Structural | P1 | 🟡 | build123d + IfcOpenShell |
| 30 | Brace / diagonal | Structural | P1 | 🟡 | build123d + IfcOpenShell |
| 31 | Truss | Structural | P2 | 🟡 | build123d + IfcOpenShell |
| 32 | Rebar set | Structural | P2 | 🔴 | build123d + IfcOpenShell |
| 33 | Steel connection detail | Structural | P2 | 🔴 | build123d + IfcOpenShell |
| 34 | Section profile library (W, HSS, L…) | Structural | P1 | 🟢 | STEP profile catalog |
| 35 | Duct (rectangular, round, oval) | MEP / HVAC | P1 | 🟡 | IfcOpenShell MEP |
| 36 | Duct fitting (elbow, tee, reducer) | MEP / HVAC | P1 | 🟡 | IfcOpenShell MEP |
| 37 | Mechanical equipment (AHU, fan, FCU) | MEP / HVAC | P1 | 🟢 | IfcOpenShell MEP |
| 38 | Air terminal (diffuser, grille, VAV) | MEP / HVAC | P1 | 🟢 | IfcOpenShell MEP |
| 39 | HVAC system definition | MEP / HVAC | P1 | 🟡 | IfcOpenShell MEP |
| 40 | Pipe (straight, elbow, tee) | MEP / Plumbing | P1 | 🟡 | IfcOpenShell MEP |
| 41 | Sloped pipe (gravity drainage) | MEP / Plumbing | P1 | 🟡 | IfcOpenShell MEP |
| 42 | Plumbing fixture (sink, toilet, drain) | MEP / Plumbing | P1 | 🟢 | IfcOpenShell MEP |
| 43 | Cable tray / conduit | MEP / Electrical | P1 | 🟡 | IfcOpenShell MEP |
| 44 | Electrical panel | MEP / Electrical | P1 | 🟡 | IfcOpenShell MEP |
| 45 | Circuit / branch wiring | MEP / Electrical | P1 | 🟡 | IfcOpenShell MEP |
| 46 | Lighting fixture | MEP / Electrical | P1 | 🟢 | IfcOpenShell MEP |
| 47 | Floor plan view generation | Drawing | P0 | 🔴 | OCCT BRepAlgoAPI_Section |
| 48 | Section view generation | Drawing | P0 | 🔴 | OCCT HLR |
| 49 | Elevation view generation | Drawing | P0 | 🔴 | OCCT HLR |
| 50 | Reflected ceiling plan | Drawing | P1 | 🟡 | OCCT BRepAlgoAPI_Section |
| 51 | Detail view (cropped region) | Drawing | P1 | 🟢 | ezdxf viewport |
| 52 | 3D axonometric / perspective | Drawing | P2 | 🟡 | OCCT + ezdxf |
| 53 | View crop region | Drawing | P0 | 🟢 | ezdxf |
| 54 | View scale | Drawing | P0 | 🟢 | ezdxf viewport |
| 55 | View range / cut height | Drawing | P0 | 🟡 | OCCT section plane |
| 56 | Linear dimension | Annotation | P0 | 🟡 | ezdxf DIMENSION |
| 57 | Chain / continuous dimensioning | Annotation | P0 | 🟡 | ezdxf DIMENSION |
| 58 | Angular dimension | Annotation | P1 | 🟢 | ezdxf DIMENSION |
| 59 | Radial / diameter dimension | Annotation | P1 | 🟢 | ezdxf DIMENSION |
| 60 | Spot elevation marker | Annotation | P1 | 🟢 | ezdxf TEXT + leader |
| 61 | Level datum annotation | Annotation | P1 | 🟢 | ezdxf |
| 62 | Room tag | Annotation | P0 | 🟡 | ezdxf BLOCK + ATTRIB |
| 63 | Door / window tag | Annotation | P0 | 🟡 | ezdxf BLOCK + ATTRIB |
| 64 | General tag (any element) | Annotation | P1 | 🟡 | ezdxf BLOCK + ATTRIB |
| 65 | Keynote tag | Annotation | P1 | 🟡 | ezdxf BLOCK + ATTRIB |
| 66 | Text note | Annotation | P0 | 🟢 | ezdxf MTEXT |
| 67 | Leader line | Annotation | P1 | 🟢 | ezdxf MULTILEADER |
| 68 | Section symbol / cut mark | Annotation | P0 | 🟡 | ezdxf BLOCK |
| 69 | Elevation symbol | Annotation | P1 | 🟡 | ezdxf BLOCK |
| 70 | Detail callout bubble | Annotation | P1 | 🟡 | ezdxf BLOCK |
| 71 | North arrow | Annotation | P0 | 🟢 | ezdxf BLOCK |
| 72 | Hatch / filled region | Annotation | P1 | 🟡 | ezdxf HATCH |
| 73 | Detail line (2D only) | Annotation | P1 | 🟢 | ezdxf LINE |
| 74 | AIA / NCS layer scheme | Annotation | P1 | 🟡 | ezdxf layer table |
| 75 | Sheet (DXF paperspace) | Sheets | P0 | 🟡 | ezdxf |
| 76 | Viewport placement on sheet | Sheets | P0 | 🟡 | ezdxf VIEWPORT |
| 77 | Title block (parametric) | Sheets | P0 | 🟡 | ezdxf BLOCK + ATTDEF |
| 78 | Sheet number / name | Sheets | P0 | 🟢 | ezdxf ATTRIB |
| 79 | Schedule on sheet | Sheets | P1 | 🟡 | ezdxf TABLE |
| 80 | General notes on sheet | Sheets | P1 | 🟢 | ezdxf MTEXT |
| 81 | Revision cloud | Sheets | P1 | 🟡 | ezdxf SPLINE |
| 82 | Revision table in title block | Sheets | P1 | 🟡 | ezdxf ATTRIB |
| 83 | Sheet list / drawing index | Sheets | P1 | 🟢 | Python + ezdxf |
| 84 | Export to DXF | Export | P0 | 🟢 | ezdxf |
| 85 | Export to PDF | Export | P0 | 🟢 | ezdxf + matplotlib |
| 86 | Export to IFC (IFC4) | Export | P0 | 🟢 | IfcOpenShell |
| 87 | Export to STEP | Export | P0 | 🟢 | build123d |
| 88 | Export to GLB / glTF | Export | P1 | 🟢 | IfcConvert CLI |
| 89 | Export to SVG | Export | P1 | 🟢 | ezdxf drawing add-on |
| 90 | Export to OBJ | Export | P2 | 🟢 | IfcConvert CLI |
| 91 | Import IFC (read existing model) | Import | P0 | 🟢 | IfcOpenShell |
| 92 | Link IFC (federated model ref) | Import | P1 | 🟡 | IfcOpenShell |
| 93 | Import STEP geometry | Import | P2 | 🟢 | build123d |
| 94 | Import DWG/DXF as underlay | Import | P2 | 🟡 | ezdxf |
| 95 | Schedule: door / window | Schedules | P1 | 🟢 | Python + pandas |
| 96 | Schedule: room finish | Schedules | P1 | 🟢 | Python + pandas |
| 97 | Schedule: structural member | Schedules | P1 | 🟢 | Python + pandas |
| 98 | Material takeoff | Schedules | P1 | 🟢 | IfcOpenShell quantity sets |
| 99 | Custom schedule (any category) | Schedules | P1 | 🟢 | Python + pandas |
| 100 | Schedule filters / sorting / grouping | Schedules | P1 | 🟢 | pandas |
| 101 | Phase: assign to element | Phasing | P1 | 🟢 | IfcOpenShell |
| 102 | Phase: demolish in phase | Phasing | P1 | 🟢 | IfcOpenShell |
| 103 | Phase filter on view | Phasing | P1 | 🟡 | IfcOpenShell |
| 104 | 2D representation caching (IFC) | Performance | P0 | 🟡 | IfcOpenShell contexts |
| 105 | Bounding box pre-filter for section cuts | Performance | P0 | 🟡 | OCCT BVH |
| 106 | Multicore section cutting | Performance | P1 | 🟡 | Python multiprocessing |
| 107 | Topography / site surface | Site | P2 | 🟡 | scipy Delaunay + IfcOpenShell |
| 108 | Building pad | Site | P2 | 🟢 | IfcOpenShell |
| 109 | Massing volume | Conceptual | P2 | 🟡 | build123d + IfcOpenShell |
| 110 | Surface panelization (from mass) | Conceptual | P2 | 🟡 | build123d |
| 111 | Point cloud import (.e57, .las) | Scan | P2 | 🟡 | laspy / open3d |
| 112 | Energy model export (gbXML) | Analysis | P2 | 🟡 | gbxml library |
| 113 | Speckle export | Collaboration | P1 | 🟢 | specklepy |
| 114 | Speckle import / versioning | Collaboration | P2 | 🟡 | specklepy |
| 115 | Clash detection | Coordination | P2 | 🟡 | IfcClash |

---

## P0 Features — Full Detail

*Must ship in v1.0. Grouped by implementation dependency.*

---

### Group A: Project Skeleton
*These are prerequisites for everything else. Zero complexity individually, but must exist before any element can be placed.*

**15. Level / Building Storey**
Every element in a BIM model is associated with a level. `Level` is a horizontal datum with a name and elevation. In IFC it is `IfcBuildingStorey`. This is the simplest entity in the library but must exist before walls, floors, or rooms can be instantiated.
```python
ground = Level(name="Ground Floor", elevation=0)
level_1 = Level(name="Level 1", elevation=4200)
```

**16. Building / Site hierarchy**
`Building` creates the IFC project hierarchy: `IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey`. Every exported IFC file requires this scaffolding. In BIM as Code it is created automatically when you instantiate `Building()` — zero boilerplate.
```python
b = Building(name="One Harbor Place", address="100 Harbor Blvd")
```

**17. Grid lines**
Column grids are established at project outset. They appear on every drawing as bubble-annotated lines. `GridLine` stores the 2D line, label, and bubble position, and is referenced by structural elements and annotations.

---

### Group B: Architecture Core

**1. Wall (straight, compound layers)**
The most fundamental architectural element. A wall has a start point, end point, height, and a `WallType` defining its layer stack. Walls host doors and windows (they own openings that are boolean-subtracted from the wall body). Wall-to-wall joins (T-junctions, L-junctions) must clean up correctly — the end cap of one wall meets the face of another.

This is the single most complex P0 feature. Key sub-problems:
- Compound layer stack: core + finish layers, each with material and thickness
- Wall joins: automatic intersection cleanup when walls meet at corners and T-intersections
- Hosted openings: boolean subtraction of door/window voids from wall body
- 2D plan representation: two parallel lines with end caps (stored explicitly, not computed at runtime)

**18. WallType (compound layer stack)**
```python
concrete_200 = WallType("200mm Concrete", layers=[
    Layer("plaster", 12),
    Layer("concrete", 176, structural=True),
    Layer("plaster", 12),
])
```

**2. Floor / slab**
A horizontal planar element defined by a boundary polygon and thickness, associated with a level. Floors have a `FloorType` with layer stacks (finish floor, structural slab, drop ceiling, etc.). Sub-problems: floors with openings (stair cores, shafts) require boolean subtractions; sloped floors require a slope vector.

**3. Roof (flat, pitched, shed)**
A roof is defined by a boundary and either a flat extrusion or a pitch angle + ridge geometry. Flat roofs are trivial (floor with positive slope = 0). Pitched roofs require generating the ridge, hip, and valley geometry from the boundary — this is non-trivial for complex footprints.

**4. Door (hosted in wall)**
A door is parametric: width, height, swing direction, frame width. It is *hosted by* a wall — it cannot exist without a wall, and it lives at a position along the wall's axis. The door creates an `IfcOpeningElement` (a void) in the host wall, then fills it with door geometry. In 2D plan view, the door shows as an arc (swing) and a thin rectangle (door panel).

**5. Window (hosted in wall)**
Similar to door: hosted by a wall, creates an opening void, has a sill height in addition to width and height. In 2D plan view, a window shows as three parallel lines (two jambs + glass line).

**6. Ceiling**
A horizontal plane at a defined height within a room or space. Simpler than floor — no structural layer, typically just a finish material and height. Required for reflected ceiling plans (P1) but the entity itself is P0 because it drives ceiling height and room volume calculations.

**7. Stair (straight, L-shape, U-shape)**
The most complex single architectural element. A stair connects two levels. It requires: tread/riser calculation from the vertical rise and target number of risers, landing geometry at changes of direction, railing hosts. Stair geometry is complex enough to deserve its own sub-module. Start with straight-run stairs in v1.0; L-shape and U-shape can follow.

---

### Group C: Spatial Elements

**12. Room / Space**
A `Room` is a named spatial volume bounded by walls, floors, and ceilings. It has: name, number, level, boundary polygon (explicit or auto-detected), computed area and volume, finish parameters (floor finish, wall finish, ceiling finish), and base elevation. In IFC it is `IfcSpace`. Area is computed from the boundary polygon via `shapely`. Rooms are the primary object for room schedules and room tags.

---

### Group D: Structural Core

**25–28. Structural column, beam, structural wall, structural slab**
These are the same entities as their architectural counterparts (`Wall`, `Floor`, `Column`) but with structural IFC classification (`IfcColumn`, `IfcBeam`, `IfcWall` with `SHEAR` or `BEARING` function, `IfcSlab` with `BASESLAB` function). They carry structural analysis properties (section profile, material grade, connection data) in addition to geometry. The clean separation between `StructuralColumn` and architectural `Column` mirrors Revit's discipline model.

---

### Group E: Type/Instance Parameter Model

**19. Type / instance parameter model**
This is the architectural decision that shapes the entire API. Every element in BIM as Code has two levels of parameterization:
- **Type parameters** — shared across all instances of a type. Stored on the `WallType`, `DoorType`, etc. Changing a type parameter updates all walls of that type.
- **Instance parameters** — unique to a placed element. Position, hosting wall, mark number. Changing an instance parameter updates only that element.

```python
# Type-level: all D-01 doors get the same geometry
door_type_D01 = DoorType("D-01", width=900, height=2100, material="solid_core_wood")

# Instance-level: this particular door is at position 3400 on wall W-05
d_101 = Door(type=door_type_D01, host=wall_W05, offset=3400, mark="101")
d_102 = Door(type=door_type_D01, host=wall_W12, offset=1200, mark="102")

# Change type → both instances update
door_type_D01.width = 1000   # d_101 and d_102 both become 1000mm wide
```

---

### Group F: Drawing Production

**47. Floor plan view generation**
The most computationally intensive P0 feature. A floor plan is a horizontal section cut through the building at a defined height (typically 1200mm above the level datum). The algorithm:
1. Filter elements to those that intersect the cut plane (bounding box pre-filter)
2. For elements with stored 2D `PLAN_VIEW` representations: use them directly
3. For elements without: compute section cut via OCCT `BRepAlgoAPI_Section`
4. Output: 2D polylines, arcs, and hatches organized by layer

**48. Section view generation**
A vertical cut plane through the building. Uses OCCT's Hidden Line Removal (HLR) renderer to generate: cut elements (foreground, thick line weight), visible elements behind the cut (medium line weight), and hidden elements (dashed, thin). The cut line is defined in plan; the section depth and height determine what is visible.

**49. Elevation view generation**
An orthographic projection onto a vertical plane facing a compass direction (north, south, east, west) or a defined direction vector. OCCT HLR renders visible and hidden edges. No section cut — the entire building face is projected.

**53–55. View crop region, view scale, view range / cut height**
Supporting parameters for all view types. The crop region clips the view to a bounding rectangle. Scale is stored on the view and applied when placing a viewport on a sheet. Cut height is the horizontal plane elevation for floor plans; view range depth controls how far below the cut plane elements are shown.

**56–57. Linear dimension, chain dimensioning**
The most important annotation type. A `LinearDimension` spans between two points (or element references) at a defined offset, and displays the computed distance at the current view scale. Chain dimensioning strings multiple dimensions end-to-end across a wall run. Dimension text is dynamic — it reads from the geometry, not from a static value. Both are DXF `DIMENSION` entities.

**62–63. Room tag, door/window tag**
Tags are annotation symbols that display element parameter values. A `RoomTag` displays room name and number at the room centroid. A `DoorTag` displays the door mark at the door location. Tags are DXF `BLOCK` references with `ATTRIB` entities bound to element parameters. When the underlying parameter changes, the tag value updates at export time.

**66. Text note**
Freestanding text annotation. DXF `MTEXT` with wrapping, justification, and font support.

**68. Section symbol / cut mark**
The symbol that appears in plan views indicating where a section cut is taken. Comprises a line (the cut plane) with arrow heads at each end and circles containing the sheet/view reference numbers. This is a DXF `BLOCK` with `ATTRIB` fields for the view reference.

**71. North arrow**
Required on all floor plan sheets. A simple DXF `BLOCK` definition for the firm's north arrow symbol, placed on the sheet or in the view.

**75–78. Sheet, viewport, title block, sheet number**
The sheet is a DXF paperspace layout. Viewports are `VIEWPORT` entities that are scaled windows into the modelspace. The title block is a `BLOCK` definition with `ATTDEF` entities for each text field (project name, sheet number, date, etc.), instantiated as a `BLOCKREF` with `ATTRIB` values filled from the project and sheet metadata.

**84–87. Export to DXF, PDF, IFC, STEP**
The four primary deliverable formats. DXF and PDF are the drawing set. IFC is the model exchange format. STEP is geometry exchange with structural/fabrication engineers.

---

### Group G: Performance Infrastructure

**104–105. 2D representation caching, bounding box pre-filter**
Without these, floor plan generation on a realistic project will be unusably slow. The bounding box pre-filter eliminates elements that don't intersect the cut plane before any OCCT operations are attempted. 2D representation caching stores computed plan linework in the IFC `Plan/Annotation/PLAN_VIEW` context so subsequent exports skip recomputation for unchanged elements. Both must be in v1.0.

---

## P1 Features — Summary

*Required for credible parity with Revit. No individual feature here is a blocker, but collectively their absence makes the library feel incomplete to an AEC professional.*

### Architecture
- **Ramp** — essentially a stair without treads/risers; a sloped slab with landings
- **Railing / guardrail** — path-based element that follows a stair or slab edge; the hardest part is the hosted-path geometry
- **Curtain wall** — a gridded wall type with mullions and glass panels; the most complex architectural element after stairs; deserves a dedicated sub-module
- **Architectural column** — a non-structural column (decorative, cladding); simpler than a structural column

### Structural
- **Foundation types** — isolated (pad), strip (continuous), mat slab; all are slabs with different IFC classification and structural properties
- **Bracing / diagonal** — a structural member connecting two points that aren't horizontally aligned; geometry is simple, connection logic is the complexity
- **Section profile library** — a catalog of standard steel sections (W, HSS, WT, L, C, S for AISC; UB, UC, RHS for BS; IPE, HEA for Eurocode); each section is a build123d 2D profile used to extrude beams and columns

### MEP
Full MEP (HVAC, plumbing, electrical) is P1 as a block. The key design constraint is that MEP elements require *routing* — a duct or pipe has a path, not just endpoints. Auto-routing (finding the optimal path around obstacles) is P2; manual path specification is P1. Each discipline has the same structure: elements (ducts, pipes, cables), fittings (elbows, tees, reducers), equipment (AHUs, panels, tanks), and terminals (diffusers, fixtures, luminaires).

### Drawing
- **Reflected ceiling plan (RCP)** — same as floor plan but viewed from below looking up; shows ceiling grid, light fixtures, HVAC diffusers, and sprinklers
- **Detail view** — a cropped region at large scale (1:5, 1:10, 1:20); no new section cut logic; just a viewport with a tight crop and high scale
- **Angular/radial dimensions** — required for curved walls, circular elements, and structural connections
- **Spot elevations** — spot level markers at finished floor, top of concrete, and similar references; a text annotation with a leader line
- **Tags: general, keynote** — same mechanism as room/door tags but for arbitrary element categories
- **Elevation symbol** — interior elevation reference marks in floor plans
- **Detail callout bubble** — circular or rectangular callout symbol pointing to the detail view sheet reference
- **Hatch / filled region** — material hatching (concrete, insulation, earth) and solid filled regions for graphic emphasis
- **AIA/NCS layer scheme** — standard layer naming convention applied automatically to DXF output; required for deliverables to most US clients
- **Revision cloud + table** — revision clouds mark changed regions; the title block revision table is populated with revision number, date, and description
- **Schedule on sheet** — placing a schedule (door list, room list, etc.) directly on a drawing sheet as a table

### Schedules
All schedule types are low complexity because they are Python queries over model objects returning pandas DataFrames. The implementation is the same for all schedule types: define the element category and fields, filter, sort, and export. The main variation is the set of fields available per element type.

### Phasing
Phase assignment and phase-filtered views are moderately complex to implement correctly but straightforward in concept. Every element gets a `phase_created` and optionally a `phase_demolished`. Views are filtered to show only elements relevant to a given phase.

### Speckle export
specklepy is a Python SDK; wrapping it as a `building.export_speckle()` method is low complexity once the library's object model is stable.

---

## P2 Features — Summary

*Completes long-term parity. Not required for initial adoption.*

| Feature | Notes |
|---|---|
| Area plans / area schemes | Rentable vs. gross area; custom area boundaries |
| Truss | Parametric truss from chord/web profiles |
| Rebar set | 3D bent bar geometry is complex; requires OCCT sweep along bent path |
| Steel connection detail | Bolted/welded connection geometry from AISC connection tables |
| 3D axonometric / perspective view | OCCT isometric projection; useful for client communication |
| Drafting view (pure 2D) | A blank canvas for hand-drafted 2D detail work; no model geometry |
| Topography / site surface | TIN from survey points via scipy Delaunay; IfcSite |
| Building pad | A cut in the topography for the building footprint |
| Massing volume | Free-form volume for conceptual design; hosts curtain wall / roof |
| Surface panelization | Divides a massing face into a regular panel grid |
| Point cloud import | .e57 / .las import via laspy or open3d |
| Energy model export (gbXML) | Export for EnergyPlus or IES-VE analysis |
| Speckle import / versioning | Pull model state from a Speckle branch |
| Clash detection | Wraps IfcClash for MEP coordination |
| DWG/DXF import as underlay | For referencing existing as-built CAD drawings |
| Import STEP geometry | For incorporating structural / fabrication geometry |

---

## Out of Scope — Final

| Feature | Rationale |
|---|---|
| GUI / visual authoring | BIM as Code is headless by design. Visualization is Speckle viewer / Bonsai. |
| Rendering (Twinmotion, V-Ray) | Output IFC/GLB to any renderer. |
| Cloud worksharing (real-time multi-user) | v1 is single-user, git-backed. Speckle handles multi-user in v2. |
| Mobile app | Not applicable to a Python library. |
| Fabrication MEP (LOD 400) | Niche manufacturing workflow; specialized tools (Trimble, Victaulic) |
| Sheet PDF annotation / markup | Post-design; handled by Bluebeam / Acrobat. |
| Structural analysis (FEA) | Export to analysis tools; not a solver. |
| DWG binary format write | ezdxf writes DXF only; ODA FileConverter handles DXF → DWG if needed. |
| .rfa / .rvt import | Revit proprietary formats; no open-source reader exists. |

---

## Development Sequence Recommendation

Based on dependencies and blocking relationships, the recommended build order for v1.0:

```
Sprint 1 — Project skeleton
  Building, Level, Site hierarchy, Units, IFC project context

Sprint 2 — Core architecture
  WallType, Wall (no joins), Floor, Roof (flat only)
  Type/instance parameter model

Sprint 3 — Hosted elements + materials
  Door, Window (with opening voids), Material, MaterialType
  Wall-to-wall joins (T and L)

Sprint 4 — Spatial + structural
  Room, GridLine
  StructuralColumn, Beam, StructuralWall, StructuralSlab

Sprint 5 — Performance infrastructure
  2D representation storage (IFC Plan/Annotation contexts)
  Bounding box pre-filter

Sprint 6 — Drawing generation
  FloorPlan view (section cut)
  Section view (HLR)
  Elevation view (HLR)
  View crop, scale, range

Sprint 7 — Annotation core
  LinearDimension, ChainDimension
  RoomTag, DoorTag, TextNote
  SectionSymbol, NorthArrow, GridLine annotation

Sprint 8 — Sheet production
  Sheet (DXF paperspace)
  Viewport placement
  TitleBlock (parametric)
  DXF export, PDF export

Sprint 9 — Schedules + IFC/STEP export
  Door schedule, Room schedule, Material takeoff
  IFC4 export, STEP export

Sprint 10 — Stair + advanced architecture
  Stair (straight run)
  Section profile library
  Foundation types
```

This sequence ensures a working drawing-set-capable build by Sprint 8, with schedules and full model export completing v1.0 in Sprint 9. Stair is deliberately last among P0 features because it is the most complex and does not block the drawing production pipeline.

---

## Dependency Graph (Critical Path)

```
Building / Level
    ↓
WallType → Wall → Door / Window → Room
    ↓                              ↓
Floor / Roof              Room Tag / Area
    ↓                              ↓
StructuralColumn / Beam   Room Schedule
    ↓
IFC 2D representation storage
    ↓
FloorPlan / Section / Elevation  ←── GridLine, Section Symbol
    ↓
LinearDimension, RoomTag, DoorTag, TextNote
    ↓
Sheet → Viewport → TitleBlock
    ↓
DXF export → PDF export
    ↓
▶ DELIVERED DRAWING SET ◀
```

---

## Sources

| Source | URL |
|---|---|
| Autodesk Revit — Key Features (official) | https://www.autodesk.com/products/revit/features |
| Autodesk Revit — Wikipedia | https://en.wikipedia.org/wiki/Autodesk_Revit |
| IfcOpenShell — drawing generation issue #1153 | https://github.com/IfcOpenShell/IfcOpenShell/issues/1153 |
| IfcOpenShell — geometry creation docs | https://docs.ifcopenshell.org/ifcopenshell-python/geometry_creation.html |
| IfcOpenShell — official site | https://ifcopenshell.org |
| OSArch — 2D drawings from IFC discussion | https://community.osarch.org/discussion/1450/ |
| build123d — Python BRep CAD framework | https://github.com/gumyr/build123d |
| ezdxf — Python DXF library | https://github.com/mozman/ezdxf |
| ezdxf — paperspace / viewport docs | https://ezdxf.readthedocs.io/en/stable/usage_for_beginners.html |
| ezdxf — blocks / title block mechanism | https://ezdxf.readthedocs.io/en/stable/tutorials/blocks.html |
| specklepy — Python Speckle SDK | https://specklepy.io |
| ScienceDirect — automated 2D from BIM (2025) | https://www.sciencedirect.com/science/article/abs/pii/S0957417425006402 |
| MCP4IFC — LLM-driven BIM design (arXiv 2025) | https://arxiv.org/html/2511.05533v1 |
| Revit Parametric Families guide | https://blog.blocksrvt.com/en/parametric-families/ |

---

*BIM as Code — Master Feature Analysis | Benny Friedman | March 2026 | Not Magic, Just Math*