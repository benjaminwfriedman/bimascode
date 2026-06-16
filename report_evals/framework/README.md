# 4-Phase Eval Framework

This framework evaluates bimascode building generation using four phases with isolated agents. It compares a "blind" builder (no test access) against a "test-aware" builder to measure how much test visibility improves output quality.

## Phases

### 1. Test Writer Agent
- **Input**: `prompts/{eval_id}.md`
- **Output**: `tests/{eval_id}/test_{eval_id}.py`
- **Instructions**: `instructions/test_writer.md`

Writes pytest tests BEFORE seeing any generated code. Interprets the prompt to determine what "correct" means. Has access to:
- `ifcopenshell` for IFC verification
- `ezdxf` for DXF parsing
- `pymupdf` (fitz) for PDF inspection
- bimascode APIs for building inspection

### 2. Builder Agent (Blind)
- **Input**: `prompts/{eval_id}.md` ONLY (no tests)
- **Output**: `outputs/{eval_id}/building.py` + exports (IFC, DXF, PDF)
- **Instructions**: `instructions/builder.md`

Generates building code from natural language prompt only. Cannot see tests.

### 3. Builder Agent (With Tests)
- **Input**: `prompts/{eval_id}.md` + `tests/{eval_id}/test_{eval_id}.py`
- **Output**: `outputs/{eval_id}_with_tests/building.py` + exports (IFC, DXF, PDF)
- **Instructions**: `instructions/builder_with_tests.md`

Generates building code with access to tests. Can use tests to ensure output passes.

### 4. Judge Agent
- **Input**: Tests, both builder outputs, prompt
- **Output**:
  - `results/{eval_id}/verdict_blind.json`
  - `results/{eval_id}/verdict_with_tests.json`
- **Instructions**: `instructions/judge.md`

Evaluates BOTH builder versions using the same criteria:
- Runs pytest tests
- Inspects IFC files
- Views PDF images
- Checks DXF drawings
- Renders PASS/FAIL verdict for each

## Running

```bash
# Run all phases for an eval
python run_3agent_eval.py 01_simple_room

# Run specific phase
python run_3agent_eval.py 01_simple_room --phase test_writer
python run_3agent_eval.py 01_simple_room --phase builder
python run_3agent_eval.py 01_simple_room --phase builder_with_tests
python run_3agent_eval.py 01_simple_room --phase judge

# Run all evals
python run_3agent_eval.py --all

# Check status
python run_3agent_eval.py --status
```

## Directory Structure

```
report_evals/
├── framework/
│   ├── README.md                    # This file
│   └── instructions/
│       ├── test_writer.md           # Test Writer agent prompt
│       ├── builder.md               # Builder (blind) agent prompt
│       ├── builder_with_tests.md    # Builder (with tests) agent prompt
│       └── judge.md                 # Judge agent prompt
├── prompts/                         # Natural language building prompts
├── tests/                           # Generated test files (by Test Writer)
├── outputs/
│   ├── {eval_id}/                   # Blind builder outputs
│   └── {eval_id}_with_tests/        # Test-aware builder outputs
├── results/
│   └── {eval_id}/
│       ├── verdict_blind.json       # Verdict for blind builder
│       └── verdict_with_tests.json  # Verdict for test-aware builder
└── run_3agent_eval.py               # Orchestrator script
```

## Expected Outcome

The test-aware builder should generally perform better than the blind builder, since it can see exactly what will be tested. Comparing the two verdicts shows:
- How much test visibility helps
- Whether the prompt alone is sufficient
- Where the blind builder commonly fails
