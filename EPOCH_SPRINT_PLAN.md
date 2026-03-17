# BIM as Code v1.0 — Epoch & Sprint Plan

**Repository:** benjaminwfriedman/bimascode
**Target Release:** v1.0
**Planning Date:** March 2026

---

## Overview

This document defines the implementation sequence for BIM as Code v1.0 across **3 epochs** and **10 sprints**. Each sprint is 2-3 weeks, delivering testable increments toward a complete code-first BIM authoring and drawing production system.

### Epoch Structure

| Epoch | Sprints | Focus | Deliverable |
|---|---|---|---|
| **Epoch 1: Foundation** | 1-5 | Core geometry, parametric model, performance | Modeled building with optimization |
| **Epoch 2: Production** | 6-8 | Drawing generation, annotation, sheets | Complete drawing set (DXF/PDF) |
| **Epoch 3: Completeness** | 9-10 | Schedules, export formats, complex geometry | Production-ready v1.0 |

---

## Epoch 1: Foundation (Sprints 1-5)

**Goal:** Establish the core BIM authoring capability with a parametric type/instance model, essential building elements, and performance infrastructure for large models.

---

### Sprint 1: Project Skeleton (2 weeks)

**Theme:** Zero-to-model foundation. Create the minimal IFC project structure and demonstrate end-to-end IFC export.

#### Features (P0)
- **#15: Level / Building Storey** 🟢
  - `Level(name, elevation)` class
  - Automatic `IfcBuildingStorey` generation
  - Validates that every element must belong to a level

- **#16: Building / Site Hierarchy** 🟢
  - `Building(name, address)` creates full IFC scaffolding
  - `IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey` hierarchy
  - Automatic GUID generation and ownership relationships

- **#17: Grid Lines** 🟢
  - `GridLine(axis_label, geometry)` for column grids
  - Store as 2D line + bubble position
  - Export to IFC `IfcGrid` and DXF representation

- **#23: Material Definition** 🟢
  - `Material(name, render_color, physical_properties)` class
  - Export to IFC `IfcMaterial` with property sets

- **#86: Export to IFC (IFC4)** 🟢
  - `building.export_ifc(filepath)` method
  - Validate output with ifcopenshell.validate
  - Include geometric and spatial representations

- **#91: Import IFC (Read Existing Model)** 🟢
  - `Building.import_ifc(filepath)` class method
  - Parse IFC4 into BIM as Code object model
  - Preserve element properties, materials, spatial hierarchy
  - Enable consultant coordination and renovation workflows

- **Units Management** 🟢
  - Project-level units configuration (metric/imperial)
  - Length, area, volume unit classes with conversion
  - Unit-aware geometric inputs
  - IFC export with correct unit declarations

#### Deliverables
- ✅ Empty building exports valid IFC4 file
- ✅ Import existing IFC and modify
- ✅ Grid lines appear in Bonsai viewer
- ✅ Materials defined and queryable
- ✅ Project units configurable (metric/imperial)
- ✅ Unit tests for IFC hierarchy and import/export round-trip

#### Dependencies
- IfcOpenShell installation and API familiarity
- build123d integration pattern established

---

### Sprint 2: Core Architecture (3 weeks)

**Theme:** Walls and floors—the fundamental building blocks. Establish the type/instance parametric model.

#### Features (P0)
- **#19: Type / Instance Parameter Model** 🟡
  - Base classes: `ElementType`, `Element`
  - Type parameters propagate to all instances
  - Instance parameters override per-element
  - Property change notification system

- **#18: WallType (Compound Layer Stack)** 🟡
  - `WallType(name, layers=[])` defining material layers
  - `Layer(material, thickness, structural=False, function)`
  - Export to IFC `IfcMaterialLayerSet`

- **#1: Wall (Straight, No Joins)** 🟡
  - `Wall(type, start_point, end_point, height, base_level)` class
  - Extrude compound profile from layer stack
  - Export body geometry to IFC `IfcWall`
  - **No wall join logic yet** (Sprint 3)

- **#2: Floor / Slab** 🟡
  - `Floor(type, boundary_polygon, level)` class
  - `FloorType` with layer stacks (structural, finish)
  - Extrude 2D boundary into 3D solid
  - **Slope parameter** for drainage (flat roofs, accessibility ramps)
  - Export to IFC `IfcSlab`

- **#3: Roof (Flat Only)** 🟡
  - `Roof(type, boundary, slope=0)` for flat roofs
  - Slope parameter for drainage (typical 2% slope)
  - **Pitched roof deferred to P1 (v1.1)** - decision made
  - Export to IFC `IfcRoof`

#### Deliverables
- ✅ Simple rectangular building with walls and floor
- ✅ Change `WallType` thickness updates all wall instances
- ✅ IFC export shows correct layer assignments
- ✅ 3D visualization via `building.show()` in OCP CAD Viewer

#### Dependencies
- build123d for BRep extrusion
- shapely for 2D polygon operations
- Type/instance architecture must be solid before Sprint 3

---

### Sprint 3: Hosted Elements + Wall Joins (3 weeks)

**Theme:** Doors, windows, and clean wall intersections. The most geometrically complex architectural sprint.

#### Features (P0)
- **#4: Door (Hosted in Wall)** 🟡
  - `Door(type, host_wall, offset, level)` class
  - Creates `IfcOpeningElement` (void) in host wall
  - Boolean subtraction from wall geometry
  - 2D plan representation: swing arc + panel rectangle

- **#5: Window (Hosted in Wall)** 🟡
  - `Window(type, host_wall, offset, sill_height)` class
  - Same hosting/voiding logic as door
  - 2D plan representation: three parallel lines (jambs + glass)

- **#24: Material Layer Assignment** 🟢
  - Assign materials to wall layers, floor finishes
  - IFC `IfcRelAssociatesMaterial` relationships

- **#1 (Enhanced): Wall-to-Wall Joins** 🔴
  - Automatic T-junction and L-junction cleanup
  - Trim wall end caps where walls intersect
  - **Wall end cap types**: flush, exterior, interior
  - Priority rules: structural > non-structural, thicker > thinner
  - **HIGH RISK**: Complex geometry; extensive testing required

- **Non-Hosted Openings** 🟡
  - `Opening(host_element, boundary, depth)` for arbitrary voids
  - Floor penetrations (stairs, elevators, shafts)
  - Wall passthrough openings
  - Roof openings (skylights, hatches)
  - Export to IFC `IfcOpeningElement`

#### Deliverables
- ✅ Walls with doors and windows (voids correctly cut)
- ✅ Wall corners meet cleanly (no overlaps/gaps)
- ✅ Wall end caps properly terminated
- ✅ T-intersections where corridor walls meet room walls
- ✅ Floor openings for stairs/shafts
- ✅ 2D plan view shows correct door/window symbols
- ✅ Comprehensive regression tests for wall join cases

#### Technical Risks
- Wall join algorithm performance on large models
- Edge cases: three-way intersections, curved walls (defer curved to P1)
- OCCT boolean operations stability

---

### Sprint 4: Spatial + Structural (2 weeks)

**Theme:** Rooms for program definition and structural elements for engineering.

#### Features (P0)
- **#12: Room / Space** 🟡
  - `Room(name, number, boundary_polygon, level)` class
  - Compute area via shapely, volume from floor-to-ceiling height
  - Finish parameters: floor finish, wall finish, ceiling finish
  - Export to IFC `IfcSpace` with properties

- **#6: Ceiling** 🟢
  - `Ceiling(type, boundary, height, level)` class
  - Simple horizontal plane at defined height
  - Required for room volume calculations

- **#25: Structural Column** 🟡
  - `StructuralColumn(section_profile, level, grid_intersection)` class
  - Extrude section profile (rectangular for now; full library in Sprint 10)
  - Export to IFC `IfcColumn` with `COLUMN` function

- **#26: Beam** 🟡
  - `Beam(section_profile, start_point, end_point, level)` class
  - Extrude profile along path
  - Export to IFC `IfcBeam`

- **#27: Structural Wall** 🟢
  - Reuse `Wall` with structural classification flag
  - Export to IFC `IfcWall` with `SHEAR` predefined type

- **#28: Structural Floor / Slab** 🟢
  - Reuse `Floor` with structural flag
  - Export to IFC `IfcSlab` with `FLOOR` or `BASESLAB` type

#### Deliverables
- ✅ Multi-room floor plan with named spaces
- ✅ Structural grid with columns at intersections
- ✅ Beam spanning between columns
- ✅ Room schedule (name, number, area) via pandas query
- ✅ IFC export distinguishes architectural vs. structural elements

#### Dependencies
- Room boundary detection (auto-generate from walls) is P1; manual boundary input for v1.0
- Section profile library minimal (rectangles only); full AISC catalog in Sprint 10

---

### Sprint 5: Performance Infrastructure (2 weeks)

**Theme:** Optimize for realistic project scale. Caching and spatial indexing before drawing generation.

#### Features (P0)
- **#104: 2D Representation Caching (IFC)** 🟡
  - Store computed 2D linework in IFC `Plan/Annotation` context
  - Walls, doors, windows export cached plan representation
  - Invalidate cache only when geometry changes
  - Reduces section cut computation time by ~90%

- **#105: Bounding Box Pre-Filter** 🟡
  - BVH (Bounding Volume Hierarchy) tree for spatial indexing
  - Filter elements by AABB intersection before OCCT section cuts
  - Critical for floor plan performance on 500+ element models

#### Deliverables
- ✅ Benchmark: 1000-wall model exports in <30 seconds
- ✅ Floor plan section cut pre-filtered to relevant elements
- ✅ IFC file size optimization via cached 2D representations
- ✅ Performance test suite with large models

#### Technical Notes
- Use `rtree` or custom AABB tree for spatial queries
- Cache invalidation strategy: track element modification timestamps
- Memory vs. speed tradeoff: cache in memory during script execution, persist in IFC for export

---

## Epoch 2: Production (Sprints 6-8)

**Goal:** Deliver automated drawing set generation with floor plans, sections, elevations, annotations, and sheets with title blocks.

---

### Sprint 6: Drawing Generation (3 weeks)

**Theme:** The core drawing engine. Section cuts, HLR, and view parameters.

#### Features (P0)
- **#47: Floor Plan View Generation** 🔴
  - `FloorPlanView(level, cut_height, view_range)` class
  - Horizontal section cut at 1200mm above level
  - Algorithm:
    1. Filter elements by bounding box intersection with cut plane
    2. Use cached 2D representations where available
    3. Compute OCCT section for uncached elements
    4. Organize linework by layer (walls, doors, windows, annotations)
  - Output: 2D polylines + arcs ready for DXF export
  - **HIGH RISK**: Performance and correctness on complex models

- **#48: Section View Generation** 🔴
  - `SectionView(cut_plane, depth, height)` class
  - OCCT Hidden Line Removal (HLR) algorithm
  - Three line types: cut (thick), visible (medium), hidden (dashed)
  - Output: 2D polylines with line type metadata

- **#49: Elevation View Generation** 🔴
  - `ElevationView(direction, crop_region)` class
  - Orthographic projection + HLR
  - No section cut, just visible/hidden edge rendering

- **#53: View Crop Region** 🟢
  - Rectangular bounding box clips view extent
  - Applied at DXF export time

- **#54: View Scale** 🟢
  - Store scale as property (1:100, 1:50, etc.)
  - Applied when placing viewport on sheet

- **#55: View Range / Cut Height** 🟡
  - `cut_plane_elevation`: horizontal section cut height
  - `view_depth_below` and `view_depth_above`: control what's visible
  - Affects element filtering logic

- **Line Weights and Line Types** 🟡
  - Standard line weights: fine, thin, medium, thick, extra thick
  - Line types: solid, dashed, dotted, dash-dot
  - Automatic assignment: cut=thick, visible=medium, hidden=thin+dashed
  - Per-category line weight configuration
  - DXF export with correct line weights

- **View Visibility and View Templates** 🟡
  - Show/hide elements by category (Architecture, Structure, MEP)
  - Show/hide by type or custom filter
  - View templates for standard views (Architectural, Structural, RCP)
  - Graphic overrides (line weight, color, halftone per category)
  - Critical for professional drawing standards

#### Deliverables
- ✅ Floor plan view with walls, doors, windows
- ✅ Building section showing multiple levels
- ✅ Exterior elevation view
- ✅ View crop and scale correctly applied
- ✅ **Line weights meet AIA/NCS standards**
- ✅ **View templates for arch/struct separation**
- ✅ Regression tests with known-good DXF outputs

#### Technical Risks
- OCCT HLR performance on detailed models
- Correct handling of overlapping elements in 2D projection
- Edge case: curved walls, circular elements in section

---

### Sprint 7: Annotation Core (2 weeks)

**Theme:** Dimensions, tags, and symbols that make drawings readable.

#### Features (P0)
- **#56: Linear Dimension** 🟡
  - `LinearDimension(start_point, end_point, offset)` class
  - Dynamic text (reads from geometry, not static value)
  - DXF `DIMENSION` entity with proper extension lines

- **#57: Chain / Continuous Dimensioning** 🟡
  - String multiple dimensions end-to-end
  - `ChainDimension(points, offset)` helper

- **#62: Room Tag** 🟡
  - `RoomTag(room, position)` class
  - DXF `BLOCK` reference with `ATTRIB` for room name and number
  - Bound to room parameter (updates when room renamed)

- **#63: Door / Window Tag** 🟡
  - `DoorTag(door, position)` class
  - Displays door mark (e.g., "101", "D-01")
  - Similar BLOCK + ATTRIB mechanism

- **#66: Text Note** 🟢
  - `TextNote(content, position, height, justification)` class
  - DXF `MTEXT` entity with word wrapping

- **#68: Section Symbol / Cut Mark** 🟡
  - Shows where section cuts are taken in plan view
  - Line with arrow heads and reference bubbles
  - `SectionSymbol(view_reference, cut_line)` class

- **#71: North Arrow** 🟢
  - Simple DXF `BLOCK` for north arrow symbol
  - Placed on sheet or in plan view

**Note:** All annotations are **view-specific**. When added to a view, they appear only in that view, allowing different dimensions/notes per drawing.

#### Deliverables
- ✅ Dimensioned floor plan (wall lengths, room dimensions)
- ✅ Room tags at room centroids
- ✅ Door tags at door locations
- ✅ Section symbols indicating cut planes
- ✅ North arrow on plan sheets
- ✅ **Annotations are view-bound** (don't appear globally)

#### Dependencies
- Views from Sprint 6 must be functional
- DXF BLOCK and ATTRIB export working

---

### Sprint 8: Sheet Production (2 weeks)

**Theme:** Assemble views into construction document sheets with title blocks.

#### Features (P0)
- **#75: Sheet (DXF Paperspace)** 🟡
  - `Sheet(size, number, name)` class (e.g., "A1", "A-101", "Level 1 Floor Plan")
  - DXF paperspace layout
  - Stores viewports, title block, annotations

- **#76: Viewport Placement on Sheet** 🟡
  - `Viewport(view, position, scale)` class
  - DXF `VIEWPORT` entity linking paperspace to modelspace view
  - Correct scale factor application

- **#77: Title Block (Parametric)** 🟡
  - `TitleBlock(template, fields)` class
  - DXF `BLOCK` definition with `ATTDEF` for text fields
  - Instantiated as `BLOCKREF` with values (project name, sheet number, date, etc.)

- **#78: Sheet Number / Name** 🟢
  - Store as attributes on sheet
  - Populate title block fields automatically

- **#84: Export to DXF** 🟢
  - `sheet.export_dxf(filepath)` method
  - Uses ezdxf to write complete DXF file

- **#85: Export to PDF** 🟢
  - `sheet.export_pdf(filepath)` method
  - ezdxf drawing add-on + matplotlib backend
  - Alternative: shell out to ODA FileConverter (DXF → PDF)

#### Deliverables
- ✅ Multi-sheet drawing set (3-5 sheets)
- ✅ Each sheet has title block with populated fields
- ✅ Viewports correctly scaled and positioned
- ✅ DXF export opens correctly in AutoCAD/BricsCAD
- ✅ PDF export suitable for printing/client review

#### Dependencies
- Views and annotations from Sprints 6-7
- ezdxf paperspace and BLOCK API mastery

---

## Epoch 3: Completeness (Sprints 9-10)

**Goal:** Schedules, multi-format export, and the most complex geometric feature (stairs).

---

### Sprint 9: Schedules + Export Formats (2 weeks)

**Theme:** Quantification and interoperability. Deliver full IFC/STEP export and schedule generation.

#### Features (P0)
- **#95: Door / Window Schedule** 🟢
  - `building.door_schedule()` returns pandas DataFrame
  - Fields: mark, type, width, height, material, location (room), count
  - Sortable, filterable, groupable

- **#96: Room Finish Schedule** 🟢
  - `building.room_schedule()` returns DataFrame
  - Fields: room number, name, area, floor finish, wall finish, ceiling finish

- **#98: Material Takeoff** 🟢
  - Query IFC quantity sets for material volumes
  - `building.material_takeoff()` aggregates by material type
  - Fields: material, volume, unit cost (if specified), total cost

- **#99: Custom Schedule (Any Category)** 🟢
  - Generic `building.schedule(element_type, fields)` method
  - Users define arbitrary element queries

- **#100: Schedule Filters / Sorting / Grouping** 🟢
  - Standard pandas operations: `sort_values()`, `groupby()`, `query()`

- **#86: Export to IFC (Enhanced)** 🟢
  - Full IFC4 export with all P0 elements
  - Validate against buildingSMART IFC4 spec

- **#87: Export to STEP** 🟢
  - `building.export_step(filepath)` method
  - Geometry-only export for structural/fabrication tools
  - Uses build123d STEP exporter

#### Deliverables
- ✅ Door schedule as DataFrame and CSV export
- ✅ Room finish schedule
- ✅ Material takeoff with quantities
- ✅ Complete IFC4 file passes validation
- ✅ STEP file opens in structural engineering tools (Tekla, Advance Steel)

#### Dependencies
- All P0 elements from Sprints 1-8 must export correctly
- IfcOpenShell quantity extraction API

---

### Sprint 10: Stair + Advanced Architecture (3 weeks)

**Theme:** The most geometrically complex P0 feature. Stairs with treads, risers, and landings.

#### Features (P0)
- **#7: Stair (Straight Run)** 🔴
  - `Stair(base_level, top_level, tread_depth, riser_height, width)` class
  - Algorithm:
    1. Compute number of risers from level-to-level height
    2. Generate tread geometry (3D solids)
    3. Generate stringer geometry (support structure)
    4. Optional: railing hosts (P1 feature, but stub interface in P0)
  - Export to IFC `IfcStair` with treads as `IfcStairFlight`
  - **HIGH RISK**: Complex geometry and many edge cases

- **#7 (Enhanced): L-Shape and U-Shape Stairs** 🔴
  - Landing geometry at direction changes
  - Multiple stair flights connected by landings
  - User specifies turn points and landing dimensions

- **#34: Section Profile Library (Basic)** 🟢
  - Catalog of standard steel sections: W, HSS, L, C (AISC)
  - `SectionProfile.load("W12x26")` returns build123d 2D profile
  - Used for structural columns and beams
  - Full catalog (100+ sections) in P1; 10-20 common sections in P0

#### Deliverables
- ✅ Straight-run stair connecting two levels
- ✅ L-shape stair with landing
- ✅ Stair exports to IFC with correct component breakdown
- ✅ 3D visualization shows treads, stringers, landings
- ✅ Section profile library usable for beam/column selection
- ✅ v1.0 release candidate ready

#### Technical Risks
- Stair geometry complexity: overlapping treads, non-standard riser heights
- Landing-to-flight transitions must be seamless
- Railing attachment points (defer full railing to P1, but geometry must support it)

---

## Sprint Summary Table

| Sprint | Duration | Features | Complexity | Milestone |
|---|---|---|---|---|
| Sprint 1 | 2 weeks | 7 | 🟢 Low | IFC import/export + units |
| Sprint 2 | 3 weeks | 5 | 🟡 Medium | Walls & floors modeled |
| Sprint 3 | 3 weeks | 5 | 🔴 High | Wall joins + openings |
| Sprint 4 | 2 weeks | 7 | 🟡 Medium | Rooms + structure |
| Sprint 5 | 2 weeks | 2 | 🟡 Medium | Performance baseline |
| Sprint 6 | 3 weeks | 8 | 🔴 High | Drawings with line weights |
| Sprint 7 | 2 weeks | 7 | 🟡 Medium | View-specific annotations |
| Sprint 8 | 2 weeks | 6 | 🟡 Medium | Sheets with title blocks |
| Sprint 9 | 2 weeks | 7 | 🟢 Low | Schedules + export |
| Sprint 10 | 3 weeks | 3 | 🔴 High | **v1.0 Release** |
| **Total** | **24 weeks** | **57 features** | — | Production ready |

---

## Critical Path

### Blocking Dependencies
1. **Sprints 1-2** must complete before any hosted elements (doors/windows)
2. **Sprint 5** (performance) must complete before Sprint 6 (drawing generation)
3. **Sprint 6** (views) must complete before Sprint 7 (annotations)
4. **Sprint 7** (annotations) must complete before Sprint 8 (sheets)

### Parallel Work Opportunities
- Structural elements (Sprint 4) can be developed in parallel with wall joins (Sprint 3)
- Schedule infrastructure (Sprint 9) can be prototyped during Sprint 4 (rooms)
- Section profile library (Sprint 10) can be started during Sprint 4 (beams/columns)

### Risk Mitigation Schedule
- Prototype wall join algorithm in Sprint 1 (proof-of-concept)
- Prototype OCCT HLR in Sprint 2 (validate feasibility)
- Prototype stair geometry in Sprint 5 (reduce Sprint 10 risk)

---

## Testing Strategy by Sprint

### Sprint 1-2: Unit Tests
- Test each element type individually
- Verify IFC export structure
- Parametric update propagation

### Sprint 3-4: Integration Tests
- Multi-element interactions (wall joins, door hosting)
- Room boundary calculations
- Structural element placement on grids

### Sprint 5: Performance Tests
- Large model benchmarks (1000+ elements)
- Cache hit rate measurements
- Memory profiling

### Sprint 6-8: Visual Regression Tests
- Known-good DXF output comparisons
- Screenshot diffing for drawing views
- PDF rendering validation

### Sprint 9-10: End-to-End Tests
- Full building model → complete drawing set workflow
- Schedule accuracy validation
- IFC compliance testing (buildingSMART validation suite)

---

## Release Criteria

v1.0 is ready to ship when:

✅ All 57 P0 features implemented and tested
✅ Complete drawing set generated from code (floor plans, sections, elevations, sheets)
✅ **Line weights and visibility controls meet professional standards**
✅ **IFC import/export round-trip works correctly**
✅ **Units management (metric/imperial) functional**
✅ IFC4 export passes buildingSMART validation
✅ DXF export opens correctly in AutoCAD and BricsCAD with correct line weights
✅ PDF export suitable for client review and permit submittal
✅ Schedules (door, room, material) generated accurately
✅ Documentation complete (API reference, user guide, examples)
✅ Performance benchmarks met (1000-element model in <60 seconds)
✅ No P0 bugs in issue tracker

---

**Prepared by:** Benny Friedman
**Last Updated:** March 2026
**Version:** 1.0
