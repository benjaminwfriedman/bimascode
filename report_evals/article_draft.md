# Bimascode: Architecture as Code

I've been thinking about what it might mean to bring BIM and AEC into the agentic world coding has been living in. In code we're pretty comfortable with the idea that an agent can take our instructions and implement the core logic. BIM and AEC are still pretty far from that.

There are many reasons for this. Legal consideration being a major barior. Beyond that, a key barrior is that most AEC work is done in UI-bound software. Point and click, point and click. When I think about what enables agents in coding, a good comp for AEC's current positioning is cloud software teams that only use their cloud provider's web-ui. That was how work was done on many teams, but about five years ago a movement to take cloud implementation from the UI to code took hold. Software packages like Terraform made it simple to implement cloud infrastructure in code. The technology was coined infrastructure as code (IaC).

I think there could be a similar movement in AEC, where building designs could be specified via code and then quickly compiled into industry standard 3D and 2D representations. The driving force behind this I'd imagine will be agentic workflows. Modern LLMs are magnificent at writing code, but less efficient at clicking buttons. Even when they are good at clicking buttons in a particular usecase, it usually requires providing full computer access which then creates a litany of security concerns. Developing an architecture as code authoring system opens up architecture to coding agents.

To experiment with this, I developed [bimascode](https://github.com/benjaminwfriedman/bimascode).

---

## What Is Bimascode?

Bimascode is a Python library for programmatic Building Information Modeling. You write Python code to describe a building—walls, doors, windows, floors, columns—and the library handles geometry generation, automatic coordination (wall joins, door openings), and export to industry-standard formats like IFC and DXF.

The simplest possible building:

```python
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import Wall, Door, create_basic_wall_type, DoorType
from bimascode.utils.materials import MaterialLibrary

# Create building and level
building = Building("My Building")
ground = Level(building, "Ground Floor", elevation=0)

# Define a wall type
concrete = MaterialLibrary.concrete()
wall_type = create_basic_wall_type("Exterior Wall", 300, concrete)
door_type = DoorType(name="Entry Door", width=900, height=2100)

# Create walls (10m x 8m building)
wall_south = Wall(wall_type, (0, 0), (10000, 0), ground)
wall_east = Wall(wall_type, (10000, 0), (10000, 8000), ground)
wall_north = Wall(wall_type, (10000, 8000), (0, 8000), ground)
wall_west = Wall(wall_type, (0, 8000), (0, 0), ground)

# Add a door
door = Door(door_type, wall_south, offset=2000)

# Export to IFC
building.export_ifc("my_building.ifc")
```

That's it. The IFC file opens in Revit, Bonsai, or any other BIM viewer. No clicking required.

---

## The Type/Instance Pattern

The library borrows a key abstraction from how Revit thinks about elements: the type/instance pattern.

A `WallType` defines the layer stack—materials, thicknesses, functions. A `Wall` is an instance placed at a specific location. Change the type, and all instances update automatically.

```python
# Define a compound wall type with multiple layers
exterior_wall = WallType("Exterior Wall - Compound", function=WallFunction.EXTERIOR)
exterior_wall.add_layer(brick, 100, LayerFunction.FINISH_EXTERIOR)
exterior_wall.add_layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
exterior_wall.add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)
exterior_wall.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)

# Every wall using this type gets all four layers
wall_1 = Wall(exterior_wall, (0, 0), (10000, 0), ground)
wall_2 = Wall(exterior_wall, (10000, 0), (10000, 8000), ground)
```

This pattern runs through everything: `DoorType`/`Door`, `ColumnType`/`Column`, `FloorType`/`Floor`. It's the right abstraction for buildings because buildings are fundamentally repetitive—that repetition should be captured in code, not clicks.

---

## Automatic Coordination

Buildings have rules. Walls that meet at corners should join properly. Doors should cut openings in their host walls. T-junctions should trim correctly.

Bimascode handles this automatically:

```python
from bimascode.architecture import detect_and_process_wall_joins, EndCapType

# Create walls that form an L-shape
wall_1 = Wall(wall_type, (0, 0), (5000, 0), ground)
wall_2 = Wall(wall_type, (5000, 0), (5000, 5000), ground)

# Detect and process joins
adjustments = detect_and_process_wall_joins([wall_1, wall_2], end_cap_type=EndCapType.EXTERIOR)
for wall, adj in adjustments.items():
    wall._trim_adjustments = adj
```

The system detects corners, T-junctions, and crosses. It calculates trim geometry so walls meet cleanly. No manual adjustment needed.

---

## 2D Documentation

3D geometry is only half the story. Buildings need documentation: floor plans, sections, elevations. Bimascode includes a drawing system that generates 2D representations with proper line weights, hatching, and AIA-compliant layers.

```python
from bimascode.drawing import FloorPlanView
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.drawing.view_base import ViewRange

# Create a floor plan view
view_range = ViewRange(cut_height=1200, top=3000, bottom=0, view_depth=0)
floor_plan = FloorPlanView(name="Ground Floor", level=ground, view_range=view_range)
result = floor_plan.generate(spatial_index, cache)

# Export to DXF
exporter = DXFExporter()
exporter.export(result, "ground_floor.dxf")
```

The output is production-ready DXF that opens in AutoCAD with proper layer organization (A-WALL, A-DOOR, A-GLAZ), line weights following NCS standards, and material hatching in cut sections.

---

## Agent Eval Results

To test whether this actually works for agents, I built a 4-phase eval framework with three agent roles:

1. **Test Writer** — Interprets the prompt and writes pytest tests *before* seeing any generated code
2. **Builder** — Generates buildings from prompts (run twice: once blind, once with test access)
3. **Judge** — Runs tests, inspects IFC files, views PDF drawings, and renders verdicts

The key comparison: does a builder with access to tests outperform a blind builder working from the prompt alone?

| Eval | Prompt | Blind | With Tests |
|------|--------|-------|------------|
| 01 | Single room, 5m×4m, door on south, window on east | PASS | PASS |
| 02 | Two-room house with shared wall, compound layers | PASS | PASS |
| 03 | Office floor: reception, 3 offices, corridor, curtain wall | PASS | PASS |
| 04 | Two-story residential with floor opening for stairs | PASS | PASS |
| 05 | Warehouse with 6m structural grid, columns, beams | PASS | PASS |

All buildings run without errors, meet dimensional/count/placement requirements, and export valid IFC4 plus 3-sheet PDF drawing sets.

But the pass rate tells only part of the story. The more interesting findings came from watching agents fail, then succeed.

### Prompt Engineering Matters More Than Expected

My first version of the prompts said nothing about spatial conflicts. The results were architecturally absurd: a window overlapping a door, a wall terminating at a window opening, a structural column planted in the middle of a doorway.

None of these triggered failures. The generated code ran. The tests passed. The IFC exported. But the buildings were unbuildable.

The Test Writer agent didn't catch these either—it wrote tests for what was explicitly specified, not for implicit architectural constraints. Since both the tests and the generation were conditioned on the same underspecified prompt, spatial conflicts slipped through.

Once I added explicit design constraints—"ensure 300mm minimum clearance between openings," "interior walls must not terminate at door or window locations"—both agents fixed these issues. It wasn't that they lacked spatial reasoning; they lacked specification.

This hints at something important: an agent with access to building codes could enforce constraints that even experienced architects occasionally miss. The specification becomes the safety net.

### Test Writer Agents Are Imperfect Proxies

The Test Writer agent sometimes misunderstood requirements. When the prompt asked for "ways to access each room via doors or openings," it wrote simple door count checks:

```python
def test_doors_on_ground_floor(self, ifc_path):
    ground_doors = get_elements_on_storey(ifc, "IfcDoor", storeys[0])
    assert len(ground_doors) >= 2
```

This passes if there are two doors anywhere on the ground floor, not if every room is reachable. The letter of the test, not the spirit.

In the structural grid eval, the Test Writer checked that "columns don't conflict with doors" and "beams don't conflict with windows"—but not the reverse, and not the full cross-product of conflicts. The test-aware Builder found a loophole: it repositioned the loading door to pass the column conflict test while still leaving the geometry problematic. Only visual inspection by the Judge caught the issue.

After prompting, the Builder discovered the test itself was incorrect and fixed the building while *failing* the flawed tests. The right outcome, but through a convoluted path.

### Test-Aware Builders Are More Robust

Comparing the blind and test-aware Builders revealed notable differences.

In eval 2, the test-aware Builder noticed its initial code produced single-page PDFs rather than multi-sheet drawing sets. It imported matplotlib and additional PDF modules to satisfy the test. The blind Builder never noticed.

In eval 3, the blind Builder placed interior walls terminating at window openings. The test-aware Builder avoided this, though interestingly the Test Writer didn't write explicit tests for it—suggesting the test context improved reasoning even for unchecked constraints.

The structural grid eval showed the sharpest divergence. The test-aware Builder caught a column-door conflict during its test run:

> One test failed—there's a column at (12000, 0) that conflicts with the loading door centered at (10000, -50). I need to move the loading door so it doesn't conflict with the column grid.

It then repositioned the door between grid lines. The blind Builder never considered the conflict.

### Visual Verification Remains Essential

Despite automated tests from the Test Writer, several issues only surfaced through the Judge's visual inspection:

- The Judge caught that tests didn't verify interior walls avoiding openings
- After being shown the issue visually, the structural grid Builder found and fixed conflicts the tests missed
- Wall height parameters were omitted entirely until visual review revealed the geometry was wrong

The most reliable verification combined both: automated tests for quantifiable requirements (dimensions, counts, export success), visual inspection for spatial logic and architectural intent.

### What This Suggests

The eval exposed a pattern: agents are excellent at satisfying explicit constraints and mediocre at inferring implicit ones. Spatial reasoning exists but activates inconsistently without prompting.

This points toward a verification architecture:

1. **Specification completeness** — Prompts need to enumerate constraints that seem obvious to humans
2. **Multi-agent checks** — Test Writer, Builder, and Judge agents catch different failure modes
3. **Visual-in-the-loop** — Automated tests plus visual review catches what either misses alone
4. **Iterative refinement** — Agents fix issues quickly once shown, even when tests are wrong

The PASS verdicts represent the end state after iteration, not the first attempt. That iteration loop—generate, test, visually verify, refine—is where the system actually works.

**What the agent produced:**

For the simplest case (5m×4m room), the generated code is clean and correct:

```python
LENGTH = 5000  # 5m
WIDTH = 4000   # 4m
WALL_THICKNESS = 200

def build():
    building = Building("Simple Room")
    level = Level(building, "Ground Floor", elevation=0)

    concrete = MaterialLibrary.concrete()
    wall_type = create_basic_wall_type(
        "Concrete Wall", WALL_THICKNESS, concrete, function=WallFunction.EXTERIOR
    )

    # Four walls forming a closed rectangle
    south = Wall(wall_type, (0, 0), (LENGTH, 0), level, name="South")
    east = Wall(wall_type, (LENGTH, 0), (LENGTH, WIDTH), level, name="East")
    north = Wall(wall_type, (LENGTH, WIDTH), (0, WIDTH), level, name="North")
    west = Wall(wall_type, (0, WIDTH), (0, 0), level, name="West")

    # Door on south wall, centered
    door_type = DoorType(name="Entry Door", width=900, height=2100)
    door = Door(door_type, south, offset=LENGTH/2 - door_type.overall_width/2)

    # Window on east wall, centered
    window_type = WindowType(name="Window", width=1200, height=1000, default_sill_height=900)
    window = Window(window_type, east, offset=WIDTH/2 - window_type.width/2)

    apply_wall_joins([south, east, north, west])
    return building
```

For the hardest case (structural grid warehouse), the agent correctly placed 20 columns at 6m grid intersections, framed main and secondary beams at proper elevations, sized the 4m×4m loading door, and positioned clerestory windows on the north wall:

```python
GRID_X = [0, 6000, 12000, 18000, 24000]  # 4 bays
GRID_Y = [0, 6000, 12000, 18000]          # 3 bays

# Columns at all grid intersections
for x in GRID_X:
    for y in GRID_Y:
        StructuralColumn(col_type, level, position=(x, y), height=WALL_HEIGHT)

# Main beams span X, along each Y gridline
for y in GRID_Y:
    for i in range(len(GRID_X) - 1):
        Beam(main_beam_type, level,
             start_point=(GRID_X[i], y, main_z),
             end_point=(GRID_X[i+1], y, main_z))
```

The drawings show the agent understood not just geometry but architectural conventions: door swings, wall joins at corners, window placement on correct walls, and structural grid logic.

---

## Why This Matters for Agents

Three reasons I think this work connects to where AI is heading:

**1. Code is the right interface for LLMs.**

LLMs are excellent at writing code. They're less excellent at navigating spatial UIs, clicking the right buttons in the right sequence, handling modal dialogs. A code-based building definition is something an LLM can read, understand, and modify directly.

Ask an agent to "add a door to the south wall" and it can:
```python
door = Door(door_type, wall_south, offset=5000, name="New_Door")
```

No screen recording, no computer vision, no fragile UI automation.

**2. Verification becomes possible.**

When a building is code, you can write tests:

```python
def test_all_rooms_have_doors():
    for room in building.rooms:
        doors_in_room = [d for d in building.doors if d.host.level == room.level]
        assert len(doors_in_room) > 0, f"Room {room.name} has no door"

def test_egress_width():
    for door in building.doors:
        if door.is_egress:
            assert door.width >= 900, f"Egress door {door.name} too narrow"
```

Building code compliance, accessibility requirements, space program validation—all become assertions that run automatically.

**3. Parametric exploration at scale.**

Want to generate 100 floor plan variations? Loop over parameters:

```python
for corridor_width in [1200, 1500, 1800]:
    for office_depth in [3500, 4000, 4500]:
        building = generate_office(corridor_width, office_depth)
        building.export_ifc(f"variant_{corridor_width}_{office_depth}.ifc")
```

This is impractical in a UI. In code, it's trivial.

---

## What's Working

The library currently handles:
- **Walls**: Straight walls with compound layer stacks, automatic corner/T/cross joins
- **Doors and Windows**: Hosted in walls, automatic opening cuts
- **Floors, Roofs, Ceilings**: Horizontal elements with layer systems
- **Columns and Beams**: Structural elements with section profiles
- **Floor Plans**: 2D views with cut lines, projections, hatching
- **Sections and Elevations**: Vertical cuts and exterior projections
- **IFC Export**: IFC4/IFC2x3 with full hierarchy, materials, property sets
- **DXF Export**: AIA-compliant layers, line weights, material hatching
- **PDF Sheets**: Drawing sets with title blocks

The preview server provides a live development experience—edit your Python, save, and the browser refreshes with 2D floor plans and 3D model synchronized.

---

## What's Missing

Plenty:
- Curved walls
- Stairs and railings
- MEP systems (ducts, pipes, electrical)
- Parametric families (think: Revit families with adjustable dimensions)
- Clash detection
- Quantity takeoffs
- Round-trip with existing BIM models

This is alpha software. The API will change. But the foundation—type/instance pattern, automatic coordination, code-first workflow—is solid enough to build on.

---

## Try It

```bash
pip install bimascode
```

Or clone and run an example:

```bash
git clone https://github.com/benjaminwfriedman/bimascode
cd bimascode
pip install -e ".[dev,viz]"
python examples/example_office_building.py
```

The preview server gives you interactive 2D/3D views:

```bash
bimascode serve examples/example_office_building.py
```

---

## The Bet

The bet here is that the same forces that moved infrastructure from web consoles to Terraform will move building design from Revit to code. Not for all use cases—complex organic forms, renovation of existing buildings, late-stage coordination—but for the generative phase where you're exploring layouts, testing program fit, producing documentation.

Agents are the forcing function. When your design partner is an LLM that thinks in code, you need a design medium that speaks code.

This is an experiment in that direction.

---

*If you're working on spatial AI, procedural generation, or building systems, I'd like to hear from you. The repo is open, the code is messy in places, and there's plenty to build.*
