# Bimascode Agent Eval Instructions

You are being evaluated on your ability to generate building models using the bimascode library.

## Before You Begin

**Read these first to understand the library:**

1. **CLAUDE.md** (root) - Architecture overview, key patterns, common issues
2. **API Docs**: https://benjaminwfriedman.github.io/bimascode/bimascode.html
3. **Examples** - Study these working buildings:
   - `examples/example_office_building.py` - Multi-room layout, wall joins, view templates
   - `examples/example_residential_home.py` - Compound wall layers, multiple levels
   - `examples/sprint6_demo.py` - Simple starting point

**Key patterns to understand:**
- Type/Instance pattern (`WallType` → `Wall`, `DoorType` → `Door`)
- Wall joins via `WallJoinDetector` and `join_walls()`
- Doors/Windows are hosted in walls with `distance_along_wall` offset
- All dimensions in millimeters (5 meters = 5000)
- Coordinate system: X=East, Y=North, Z=Up

## Your Task

For each prompt in `prompts/`, you must:

1. **Read the prompt** - Understand the building requirements
2. **Generate Python code** - Write bimascode code that creates the building
3. **Execute the code** - Run it to verify it works
4. **Export outputs** - Save IFC file to `outputs/{eval_id}/`
5. **Self-verify** - Check your output against `requirements/{eval_id}.json`

## Eval Sequence

Work through these in order:

1. `01_simple_room` - Easy (single room, basic elements)
2. `02_two_room_house` - Medium (shared walls, compound layers)
3. `03_office_floor` - Hard (complex layout, circulation)
4. `04_two_story_building` - Hard (multi-level, vertical coordination)
5. `05_structural_grid` - Hard (columns, beams, structural logic)

## Output Format

For each eval, save your code to:
```
outputs/{eval_id}/building.py
```

Then run it to generate:
```
outputs/{eval_id}/building.ifc
```

## Verification

After generating each building, check against the requirements JSON:

- Did you create the right number of walls/doors/windows?
- Are dimensions within tolerance?
- Are elements on the correct walls/levels?
- Does the IFC export successfully?

Report your results as:
```
## Eval: {eval_id}
- Walls: {count} (expected: {expected})
- Doors: {count} (expected: {expected})
- Windows: {count} (expected: {expected})
- Dimensions: {actual} (expected: {expected})
- IFC Export: PASS/FAIL
- Overall: PASS/FAIL
```

## Begin

Start with `prompts/01_simple_room.md`. Read it, generate the code, execute it, and verify.

---

## Alternative: 3-Agent Eval Framework

For a more rigorous evaluation with separation of concerns, use `run_3agent_eval.py`:

```bash
# Run all phases for an eval
python run_3agent_eval.py 01_simple_room

# Run specific phase
python run_3agent_eval.py 01_simple_room --phase builder

# Check status
python run_3agent_eval.py --status
```

This orchestrates three isolated agents:
1. **Test Writer** - Generates pytest tests from the prompt (no access to building code)
2. **Builder** - Generates buildings from prompts (no access to tests)
3. **Judge** - Runs tests, inspects outputs, renders verdict

See `framework/instructions/` for per-agent instructions:
- `framework/instructions/builder.md` - Builder agent instructions + API reference
- `framework/instructions/test_writer.md` - Test writer instructions
- `framework/instructions/judge.md` - Judge instructions
