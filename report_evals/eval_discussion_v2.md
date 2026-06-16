## Agent Eval Results

To test whether this actually works for agents, I built an eval framework with two phases: one agent generates buildings from prompts, then a separate LLM judge reviews the outputs visually. Five prompts ranging from a simple room to a complex structural grid building:

| Eval | Prompt | Result |
|------|--------|--------|
| 01 | Single room, 5m x 4m, door on south, window on east | PASS |
| 02 | Two-room house with shared wall, compound layers | PASS |
| 03 | Office floor: reception, 3 offices, corridor, curtain wall | PASS |
| 04 | Two-story residential with floor opening for stairs | PASS |
| 05 | Warehouse with 6m structural grid, columns, beams | PASS |

5/5 PASS. All buildings run without errors, meet dimensional/count/placement requirements, form clean joined envelopes, and export valid IFC4 plus 3-sheet PDF drawing sets.

But the pass rate tells only part of the story. The more interesting findings came from watching agents fail, then succeed.

### Prompt Engineering Matters More Than Expected

My first version of the prompts said nothing about spatial conflicts. The results were architecturally absurd: a window overlapping a door, a wall terminating at a window opening, a structural column planted in the middle of a doorway.

None of these triggered failures. The generated code ran. The tests passed. The IFC exported. But the buildings were unbuildable.

Once I added explicit design constraints to the prompts—"ensure 300mm minimum clearance between openings," "interior walls must not terminate at door or window locations"—the agent fixed these issues immediately. It wasn't that the agent lacked spatial reasoning; it lacked specification.

This hints at something important: an agent with access to building codes could enforce constraints that even experienced architects occasionally miss. The specification becomes the safety net.

### Test Agents Are Imperfect Proxies

The test-writing agent sometimes misunderstood requirements. When I asked for "ways to access each room via doors or openings," it wrote simple door count checks:

```python
def test_doors_on_ground_floor(self, ifc_path):
    ground_doors = get_elements_on_storey(ifc, "IfcDoor", storeys[0])
    assert len(ground_doors) >= 2
```

This passes if there are two doors anywhere on the ground floor, not if every room is reachable. The letter of the test, not the spirit.

In the structural grid eval, the test agent checked that "columns don't conflict with doors" and "beams don't conflict with windows"—but not the reverse, and not the full cross-product of conflicts. The builder agent found a loophole: it repositioned the loading door to pass the column conflict test while still leaving the geometry problematic. Only visual inspection caught the issue.

After prompting, the agent discovered the test itself was incorrect and fixed the building while *failing* the flawed tests. The right outcome, but through a convoluted path.

### Test-Aware Builders Are More Robust

I tested builders with and without access to the test suite. The differences were notable.

In eval 2, the test-aware agent noticed its initial code produced single-page PDFs rather than multi-sheet drawing sets. It imported matplotlib and additional PDF modules to satisfy the test. The blind agent never noticed.

In eval 3, the blind agent placed interior walls terminating at window openings. The test-aware agent avoided this, though interestingly it didn't write explicit tests for it—suggesting the test context improved reasoning even for unchecked constraints.

The structural grid eval showed the sharpest divergence. The test-aware builder caught a column-door conflict during its test run:

> One test failed—there's a column at (12000, 0) that conflicts with the loading door centered at (10000, -50). I need to move the loading door so it doesn't conflict with the column grid.

It then repositioned the door between grid lines. The blind builder never considered the conflict.

### Visual Verification Remains Essential

Despite automated tests, several issues only surfaced through visual inspection:

- The visual judge caught that the test agent didn't verify interior walls avoiding openings
- After being shown the issue visually, the structural grid agent found and fixed conflicts the tests missed
- Wall height parameters were omitted entirely until visual review revealed the geometry was wrong

The most reliable verification combined both: automated tests for quantifiable requirements (dimensions, counts, export success), visual inspection for spatial logic and architectural intent.

### What This Suggests

The eval exposed a pattern: agents are excellent at satisfying explicit constraints and mediocre at inferring implicit ones. Spatial reasoning exists but activates inconsistently without prompting.

This points toward a verification architecture:

1. **Specification completeness** - Prompts need to enumerate constraints that seem obvious to humans
2. **Multi-agent checks** - Builder and tester agents catch different failure modes
3. **Visual-in-the-loop** - Automated tests plus visual review catches what either misses alone
4. **Iterative refinement** - Agents fix issues quickly once shown, even when tests are wrong

The 5/5 pass rate represents the end state after iteration, not the first attempt. That iteration loop—generate, test, visually verify, refine—is where the system actually works.

---

**Sample verification (Eval 01 - Simple Room):**

> **Visual Inspection**: Closed rectangular room, walls in poche with clean mitered corners. Door swing arc on the south wall; window on the east wall. Scale 1:20. Elevations show openings on correct faces.
>
> **Requirements Check**: Dimensions 5.0m x 4.0m (PASS), 4 walls forming closed loop (PASS), 1 door on south (PASS), 1 window on east (PASS), 200mm concrete (PASS), IFC export 119KB (PASS).
>
> **Overall: PASS** — Textbook result. Walls join cleanly via MITER.

**Sample verification (Eval 05 - Structural Grid):**

> **Visual Inspection**: 20 columns shown as solid squares at every 6m grid intersection, dashed beam gridlines, concrete perimeter, loading-door swing (south), personnel-door swings (E/W). Sections show beam band at top of columns; clerestory windows near top of north wall.
>
> **Requirements Check**: Dimensions 24m x 18m (PASS), 20 columns on 6m grid at 400mm square (PASS), 16 main beams + 15 secondary (PASS), 4x4m loading door on south (PASS), 4 clerestory windows on north (PASS), IFC 857KB + structural DXF (PASS).
>
> **Overall: PASS** — Strong structural result. Grid, framing hierarchy, and large openings all correct.

**Full results:**

```
+------------------------+------+------+--------+---------+--------+---------+---------+
|         Eval           | Code | Dims | Counts | Spatial | Visual | Exports | Overall |
+------------------------+------+------+--------+---------+--------+---------+---------+
| 01_simple_room         |  Y   |  Y   |   Y    |    Y    |   Y    |    Y    |  PASS   |
| 02_two_room_house      |  Y   |  Y   |   Y    |    Y    |   Y    |    Y    |  PASS   |
| 03_office_floor        |  Y   |  Y   |   Y    |    Y    |   Y    |    Y    |  PASS   |
| 04_two_story_building  |  Y   |  Y   |   Y    |    Y    |   Y    |    Y    |  PASS   |
| 05_structural_grid     |  Y   |  Y   |   Y    |    Y    |   Y    |    Y    |  PASS   |
+------------------------+------+------+--------+---------+--------+---------+---------+
```
