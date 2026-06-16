# Bimascode Agent Evals

Evaluation framework for testing how well AI agents can generate buildings from natural language prompts using [bimascode](https://github.com/benjaminwfriedman/bimascode).

**Documentation**: [API Docs](https://benjaminwfriedman.github.io/bimascode/bimascode.html)

## Structure

```
report_evals/
├── README.md           # This file
├── run_evals.md        # Instructions for the agent being evaluated
├── verify_evals.md     # Instructions for LLM judge to verify outputs
├── prompts/            # Natural language building prompts (5 evals)
├── requirements/       # Expected outputs for each prompt (JSON)
└── outputs/            # Generated code and artifacts
```

## Workflow

### 1. Run Evals

Open a coding agent in this directory and point it to `run_evals.md`. The agent will:

1. Read each prompt in `prompts/`
2. Generate bimascode Python to create the building
3. Execute the code and export IFC + drawings
4. Save outputs to `outputs/{eval_id}/`

### 2. Verify Results

Open a fresh agent and point it to `verify_evals.md`. This agent acts as an LLM judge:

1. Reads the original prompts and requirements
2. Views the generated PDFs and DXFs as images
3. Compares visual output against requirements
4. Reports pass/fail for each eval

## Eval Difficulty

| Eval | Difficulty | Skills Tested |
|------|------------|---------------|
| 01_simple_room | Easy | Basic walls, door, window |
| 02_two_room_house | Medium | Shared walls, compound layers |
| 03_office_floor | Hard | Complex layout, circulation |
| 04_two_story_building | Hard | Multi-level, vertical coordination |
| 05_structural_grid | Hard | Columns, beams, structural logic |

## Adding New Evals

1. Add a prompt file in `prompts/{id}.md`
2. Add corresponding requirements in `requirements/{id}.json`
