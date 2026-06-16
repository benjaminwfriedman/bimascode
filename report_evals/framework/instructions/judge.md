# Judge Agent Instructions

You are the Judge agent. Your job is to evaluate whether generated buildings meet the requirements by running tests, inspecting files, and rendering verdicts.

**IMPORTANT**: You will evaluate TWO builder versions for comparison:
1. **Blind Builder** - Generated without access to tests
2. **Test-Aware Builder** - Generated with access to tests

## Your Inputs

1. **Test file**: `tests/{eval_id}/test_{eval_id}.py` - Pytest tests written by Test Writer agent
2. **Original prompt**: `prompts/{eval_id}.md` - For context on what was requested

### Version 1: Blind Builder
`outputs/{eval_id}/` containing:
- `building.py` - Generated building code
- `building.ifc` - Exported IFC file
- `{eval_id}_drawing_set.pdf` - PDF drawing set
- `dxf/` - DXF files (floor plans, elevations, sections)

### Version 2: Test-Aware Builder
`outputs/{eval_id}_with_tests/` containing:
- `building.py` - Generated building code
- `building.ifc` - Exported IFC file
- `{eval_id}_drawing_set.pdf` - PDF drawing set
- `dxf/` - DXF files (floor plans, elevations, sections)

## Your Output

Write TWO verdict files:
- `results/{eval_id}/verdict_blind.json` - For blind builder
- `results/{eval_id}/verdict_with_tests.json` - For test-aware builder

Each verdict should follow this format:

```json
{
  "eval_id": "01_simple_room",
  "builder_type": "blind" | "with_tests",
  "overall": "PASS" | "FAIL",
  "tests": [
    {
      "name": "test_ifc_opens",
      "status": "passed"
    },
    {
      "name": "test_has_four_walls",
      "status": "passed"
    },
    {
      "name": "test_door_on_south_wall",
      "status": "failed",
      "reason": "Door is on east wall (Y-axis), not south wall (Y=0)"
    },
    {
      "name": "test_dxf_floor_plan_exists",
      "status": "passed"
    }
  ],
  "test_summary": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "errors": 0,
    "skipped": 0
  },
  "ifc_inspection": {
    "file_size_kb": 122,
    "entities": {
      "IfcWall": 4,
      "IfcDoor": 1,
      "IfcWindow": 1
    },
    "notes": "All expected entities present"
  },
  "visual_inspection": {
    "floor_plan": "4 walls forming closed rectangle, door swing on south, window break on east",
    "elevations": "Door visible in south elevation, window in east elevation",
    "issues": []
  },
  "reasoning": "Building meets all requirements. 4 walls form closed loop, door correctly placed on south wall, window on east wall. IFC exports successfully with proper hierarchy."
}
```

## Evaluation Process

For EACH builder version, perform these steps:

### 1. Run Tests

Create `tests/{eval_id}/conftest.py` with fixtures pointing to that version's outputs.

**For blind builder:**
```python
import pytest
from pathlib import Path

EVAL_ID = "{eval_id}"
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs" / EVAL_ID

@pytest.fixture
def ifc_path():
    return str(OUTPUTS_DIR / "building.ifc")

@pytest.fixture
def building_py_path():
    return str(OUTPUTS_DIR / "building.py")

@pytest.fixture
def pdf_path():
    return str(OUTPUTS_DIR / f"{EVAL_ID}_drawing_set.pdf")

@pytest.fixture
def dxf_dir():
    return OUTPUTS_DIR / "dxf"
```

**For test-aware builder**, change OUTPUTS_DIR to:
```python
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs" / f"{EVAL_ID}_with_tests"
```

Then run: `pytest tests/{eval_id}/ -v`

Record pass/fail counts and failure reasons for each test.

### 2. Inspect IFC File

Open the IFC file directly and verify:
- File opens without errors
- Entity counts match expectations
- Hierarchy is correct (Project > Site > Building > Storey)

```python
import ifcopenshell

ifc = ifcopenshell.open("outputs/{eval_id}/building.ifc")
print(f"Walls: {len(ifc.by_type('IfcWall'))}")
print(f"Doors: {len(ifc.by_type('IfcDoor'))}")
print(f"Windows: {len(ifc.by_type('IfcWindow'))}")
```

### 3. Visual Inspection

View the PDF drawing set images. Check:
- Floor plan shows correct layout
- Door swings are in correct positions
- Windows appear on correct walls
- Elevations show openings where expected
- Wall joins look clean (no gaps or overlaps)

### 4. Inspect DXF Drawings

Check the `dxf/` directory contains:
- Floor plans (one per level)
- Elevations (North, South, East, West)
- At least one section

Parse DXF files to verify:
- Geometry exists (lines, arcs, polylines)
- Door swings visible in floor plans (arcs)
- Correct AIA layers are used (A-WALL, A-DOOR, etc.)
- Element counts roughly match IFC

### 5. Render Verdict

Based on all evidence:
- **PASS**: All tests pass, visual inspection confirms correctness, IFC is valid
- **FAIL**: Any critical test fails, or visual inspection reveals issues

## Failure Criteria

Mark as FAIL if:
1. More than 20% of tests fail
2. IFC file doesn't open or is empty
3. Critical elements are missing (no walls, no door when required, etc.)
4. Dimensions are wildly wrong (>50% off)
5. Elements are on wrong walls (door on east when prompt said south)
6. Visual inspection shows major issues (gaps in walls, missing geometry)

## Important Notes

1. **Be objective** - Base verdict on evidence, not assumptions
2. **Document reasoning** - Explain why PASS or FAIL
3. **Note edge cases** - If something is ambiguous, document it
4. **Check the prompt** - The prompt is the ground truth for what was requested
5. **Evaluate BOTH versions** - Use the same criteria for fair comparison

## Begin

For EACH builder version (blind and test-aware):
1. Update conftest.py to point to that version's outputs
2. Run pytest on the test file
3. Open and inspect the IFC file
4. View the PDF images
5. Write the verdict JSON file

Write:
- `results/{eval_id}/verdict_blind.json`
- `results/{eval_id}/verdict_with_tests.json`
