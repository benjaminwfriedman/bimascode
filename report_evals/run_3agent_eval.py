#!/usr/bin/env python3
"""
4-Agent Eval Runner

Orchestrates the evaluation of bimascode building generation using four phases:
1. Test Writer - Generates tests by interpreting the prompt
2. Builder (blind) - Generates buildings from prompts only (no test access)
3. Builder (with tests) - Generates buildings with access to tests
4. Judge - Runs tests and renders verdict for BOTH builder versions

Each agent is invoked as a separate Claude Code session with specific instructions.

Usage:
    # Run all phases for an eval
    python run_3agent_eval.py 01_simple_room

    # Run specific phase
    python run_3agent_eval.py 01_simple_room --phase test_writer
    python run_3agent_eval.py 01_simple_room --phase builder
    python run_3agent_eval.py 01_simple_room --phase builder_with_tests
    python run_3agent_eval.py 01_simple_room --phase judge

    # Run all evals
    python run_3agent_eval.py --all

    # Run with a named eval version (creates report_evals_{name}/ directory)
    python run_3agent_eval.py 01_simple_room --name v2
    python run_3agent_eval.py --all --name experiment_1
"""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent

# Shared resources (prompts and framework instructions)
FRAMEWORK = SCRIPT_DIR / "framework"
INSTRUCTIONS = FRAMEWORK / "instructions"
PROMPTS = SCRIPT_DIR / "prompts"

# Default output locations (in report_evals/)
DEFAULT_TESTS = SCRIPT_DIR / "tests"
DEFAULT_OUTPUTS = SCRIPT_DIR / "outputs"
DEFAULT_RESULTS = SCRIPT_DIR / "results"

EVAL_IDS = [
    "01_simple_room",
    "02_two_room_house",
    "03_office_floor",
    "04_two_story_building",
    "05_structural_grid",
]

PHASES = ["test_writer", "builder", "builder_with_tests", "judge"]


def get_paths(name: str | None = None) -> tuple[Path, Path, Path]:
    """Get paths for tests, outputs, and results based on optional name."""
    if name:
        base = REPO_ROOT / f"report_evals_{name}"
        return base / "tests", base / "outputs", base / "results"
    return DEFAULT_TESTS, DEFAULT_OUTPUTS, DEFAULT_RESULTS


def ensure_dirs(eval_id: str, name: str | None = None):
    """Create output directories if they don't exist."""
    tests, outputs, results = get_paths(name)
    (tests / eval_id).mkdir(parents=True, exist_ok=True)
    (outputs / eval_id).mkdir(parents=True, exist_ok=True)
    (outputs / f"{eval_id}_with_tests").mkdir(parents=True, exist_ok=True)
    (results / eval_id).mkdir(parents=True, exist_ok=True)


def print_agent_instructions(phase: str, eval_id: str, name: str | None = None):
    """Print instructions for manually running an agent."""
    tests, outputs, results = get_paths(name)
    prompt_file = PROMPTS / f"{eval_id}.md"

    print(f"\n{'='*60}")
    print(f"PHASE: {phase.upper()}")
    print(f"EVAL: {eval_id}")
    if name:
        print(f"VERSION: {name}")
    print(f"{'='*60}\n")

    if phase == "test_writer":
        instructions_file = INSTRUCTIONS / "test_writer.md"
        print("Run Claude Code with this prompt:\n")
        print("-" * 40)
        print(f"""You are the Test Writer agent.

Read these files:
- Instructions: {instructions_file}
- Prompt: {prompt_file}

Write pytest tests to: {tests / eval_id / f'test_{eval_id}.py'}

Interpret the prompt and write tests for what it asks. DO NOT look at any generated building code.
""")
        print("-" * 40)

    elif phase == "builder":
        instructions_file = INSTRUCTIONS / "builder.md"
        print("Run Claude Code with this prompt:\n")
        print("-" * 40)
        print(f"""You are the Builder agent (BLIND - no test access).

Read these files:
- Instructions: {instructions_file}
- Prompt: {prompt_file}

Write building code to: {outputs / eval_id / 'building.py'}

DO NOT read test files - generate based only on the natural language prompt.
Then run the building.py to generate the IFC, DXF, and PDF exports.
""")
        print("-" * 40)

    elif phase == "builder_with_tests":
        instructions_file = INSTRUCTIONS / "builder_with_tests.md"
        test_file = tests / eval_id / f"test_{eval_id}.py"
        print("Run Claude Code with this prompt:\n")
        print("-" * 40)
        print(f"""You are the Builder agent (WITH TEST ACCESS).

Read these files:
- Instructions: {instructions_file}
- Prompt: {prompt_file}
- Tests: {test_file}

Write building code to: {outputs / f'{eval_id}_with_tests' / 'building.py'}

You CAN read the test files! Use them to ensure your building passes all tests.
Then run the building.py to generate the IFC, DXF, and PDF exports.
""")
        print("-" * 40)

    elif phase == "judge":
        instructions_file = INSTRUCTIONS / "judge.md"
        print("Run Claude Code with this prompt:\n")
        print("-" * 40)
        print(f"""You are the Judge agent. You will evaluate BOTH builder versions.

Read these files:
- Instructions: {instructions_file}
- Tests: {tests / eval_id / f'test_{eval_id}.py'}
- Prompt (for reference): {prompt_file}

## Version 1: Builder (blind - no test access)
- Generated code: {outputs / eval_id / 'building.py'}
- IFC: {outputs / eval_id / 'building.ifc'}
- PDF: {outputs / eval_id / f'{eval_id}_drawing_set.pdf'}
- DXF files in: {outputs / eval_id / 'dxf/'}

## Version 2: Builder (with test access)
- Generated code: {outputs / f'{eval_id}_with_tests' / 'building.py'}
- IFC: {outputs / f'{eval_id}_with_tests' / 'building.ifc'}
- PDF: {outputs / f'{eval_id}_with_tests' / f'{eval_id}_drawing_set.pdf'}
- DXF files in: {outputs / f'{eval_id}_with_tests' / 'dxf/'}

For EACH version:
1. Create conftest.py with fixtures pointing to that version's outputs
2. Run pytest on the tests
3. Inspect the IFC file
4. View the PDF images
5. Write verdict

Write verdicts to:
- {results / eval_id / 'verdict_blind.json'} (for blind builder)
- {results / eval_id / 'verdict_with_tests.json'} (for test-aware builder)
""")
        print("-" * 40)


def run_phase(phase: str, eval_id: str, name: str | None = None):
    """Run a specific phase for an eval."""
    ensure_dirs(eval_id, name)
    print_agent_instructions(phase, eval_id, name)

    # In a full implementation, this would invoke claude-code programmatically
    # For now, we print instructions for manual execution
    print("\nTo run this phase, start a new Claude Code session with the prompt above.")
    print("Each agent should run in isolation to prevent information leakage.\n")


def check_phase_complete(phase: str, eval_id: str, name: str | None = None) -> bool:
    """Check if a phase has been completed."""
    tests, outputs, results = get_paths(name)
    if phase == "test_writer":
        return (tests / eval_id / f"test_{eval_id}.py").exists()
    elif phase == "builder":
        return (outputs / eval_id / "building.ifc").exists()
    elif phase == "builder_with_tests":
        return (outputs / f"{eval_id}_with_tests" / "building.ifc").exists()
    elif phase == "judge":
        blind_done = (results / eval_id / "verdict_blind.json").exists()
        tests_done = (results / eval_id / "verdict_with_tests.json").exists()
        return blind_done and tests_done
    return False


def print_status(eval_id: str, name: str | None = None):
    """Print completion status for an eval."""
    version_str = f" ({name})" if name else ""
    print(f"\nStatus for {eval_id}{version_str}:")
    for phase in PHASES:
        complete = check_phase_complete(phase, eval_id, name)
        status = "DONE" if complete else "PENDING"
        print(f"  {phase}: {status}")


def main():
    parser = argparse.ArgumentParser(description="Run 4-agent eval framework")
    parser.add_argument("eval_id", nargs="?", help="Eval ID (e.g., 01_simple_room)")
    parser.add_argument("--phase", choices=PHASES, help="Run specific phase")
    parser.add_argument("--all", action="store_true", help="Run all evals")
    parser.add_argument("--status", action="store_true", help="Show completion status")
    parser.add_argument(
        "--name",
        help="Version name (creates report_evals_{name}/ directory for outputs)",
    )

    args = parser.parse_args()

    if args.name:
        tests, outputs, results = get_paths(args.name)
        print(f"Using output directory: {tests.parent}")

    if args.status:
        for eval_id in EVAL_IDS:
            print_status(eval_id, args.name)
        return

    if args.all:
        eval_ids = EVAL_IDS
    elif args.eval_id:
        if args.eval_id not in EVAL_IDS:
            print(f"Unknown eval: {args.eval_id}")
            print(f"Valid evals: {', '.join(EVAL_IDS)}")
            sys.exit(1)
        eval_ids = [args.eval_id]
    else:
        parser.print_help()
        sys.exit(1)

    phases = [args.phase] if args.phase else PHASES

    for eval_id in eval_ids:
        for phase in phases:
            run_phase(phase, eval_id, args.name)
            if not args.phase:
                # In sequential mode, wait for user to complete each phase
                input(f"\nPress Enter when {phase} phase is complete...")


if __name__ == "__main__":
    main()
