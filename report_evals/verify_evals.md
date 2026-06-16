# Eval Verification Instructions

You are an LLM judge evaluating whether an agent successfully generated buildings from natural language prompts using bimascode.

## Your Task

For each eval in `outputs/`, you must:

1. **Read the original prompt** from `prompts/{eval_id}.md`
2. **Read the requirements** from `requirements/{eval_id}.json`
3. **Read the generated code** from `outputs/{eval_id}/building.py`
4. **View the visual outputs**:
   - PDF drawing set: `outputs/{eval_id}/{eval_id}_drawing_set.pdf`
   - DXF files in: `outputs/{eval_id}/dxf/`
   - IFC file: `outputs/{eval_id}/building.ifc` (check file size > 0)
5. **Judge pass/fail** based on the criteria below

## Evaluation Criteria

For each eval, assess:

### 1. Code Quality
- Does the code run without errors?
- Does it use bimascode APIs correctly?
- Is the code readable and well-structured?

### 2. Dimensional Accuracy
- Are building dimensions within tolerance of requirements?
- Are rooms/spaces approximately the right size?

### 3. Element Counts
- Correct number of walls?
- Correct number of doors and windows?
- Elements on the correct walls/levels?

### 4. Spatial Logic
- Do walls form closed polygons?
- Are doors hosted in walls?
- Are windows on the specified walls (south, east, etc.)?
- For multi-room buildings: do rooms share walls correctly?

### 5. Visual Verification (from PDFs/DXFs)
- Does the floor plan show the described layout?
- Are door swings visible and in correct locations?
- Do elevations show windows/doors at correct positions?
- For structural grids: are columns visible at grid intersections?

### 6. Export Success
- IFC file exists and has reasonable size (>10KB)?
- PDF drawing set generated?

## Verification Process

Work through each eval directory:

```
outputs/
├── 01_simple_room/
├── 02_two_room_house/
├── 03_office_floor/
├── 04_two_story_building/
└── 05_structural_grid/
```

For each one:

1. Read the prompt and requirements
2. Read the generated `building.py`
3. View the PDF drawing set (floor plans, elevations, sections)
4. Check IFC file exists

## Output Format

For each eval, report:

```
## Eval: {eval_id}

### Prompt Summary
[1-2 sentence summary of what was requested]

### Visual Inspection
- Floor Plan: [describe what you see - walls, doors, windows, rooms]
- Elevations: [describe - door/window positions, heights]
- Sections: [describe - if applicable]

### Requirements Check
- Dimensions: PASS/FAIL - [actual vs expected]
- Wall Count: PASS/FAIL - [actual vs expected]
- Door Count: PASS/FAIL - [actual vs expected]
- Window Count: PASS/FAIL - [actual vs expected]
- Door Placement: PASS/FAIL - [which wall]
- Window Placement: PASS/FAIL - [which wall]
- Special Requirements: PASS/FAIL - [e.g., curtain wall, structural grid]

### Exports
- IFC: PASS/FAIL ({file_size}KB)
- PDF: PASS/FAIL

### Overall: PASS / FAIL

### Notes
[Any issues, edge cases, or observations]
```

## Begin

Start with `01_simple_room`. Read the prompt, view the outputs, and judge.
