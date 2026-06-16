"""
Geometric audit for the eval buildings:

  1. Wall joins  -- detect L/T/cross joins and report whether each wall has a
     non-zero trim adjustment applied (i.e. joins were actually processed).
  2. Opening overlaps -- for every wall, check that hosted doors/windows stay
     within the wall, keep clear of the ends/corners, and do not overlap one
     another along the wall.

Run:  python audit.py
"""

import importlib.util
import math
from pathlib import Path

from bimascode.architecture import Wall
from bimascode.architecture.wall_joins import WallJoinDetector

ROOT = Path(__file__).parent
EVALS = [
    "01_simple_room",
    "02_two_room_house",
    "03_office_floor",
    "04_two_story_building",
    "05_structural_grid",
]
END_CLEARANCE = 100.0  # mm an opening must stay clear of a wall end / corner


def load_building(eval_id):
    path = ROOT / "outputs" / eval_id / "building.py"
    spec = importlib.util.spec_from_file_location(f"a_{eval_id}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.build()
    return res[0] if isinstance(res, tuple) else res["building"]


def opening_width(el):
    t = el.type
    return getattr(t, "overall_width", None) or el.width


def audit_eval(eval_id):
    building = load_building(eval_id)
    problems = []
    join_info = []

    for level in building.levels:
        walls = [e for e in level.elements if isinstance(e, Wall)]

        # --- joins ---
        detector = WallJoinDetector(walls, tolerance=50.0)
        joins = detector.detect_joins()
        trimmed = sum(
            1
            for w in walls
            if getattr(w, "_trim_adjustments", None)
            and any(abs(v) > 1e-9 for v in w._trim_adjustments.values())
        )
        join_info.append((level.name, len(walls), len(joins), trimmed))

        # --- openings per wall ---
        for w in walls:
            length = w.length
            spans = []
            for el in w.hosted_elements:
                ow = opening_width(el)
                start = el.offset
                end = el.offset + ow
                spans.append((start, end, type(el).__name__, el.name))
                if start < END_CLEARANCE:
                    problems.append(
                        f"[{eval_id}/{w.name}] {el.name} starts {start:.0f}mm from wall "
                        f"start (< {END_CLEARANCE:.0f}mm corner clearance)"
                    )
                if end > length - END_CLEARANCE:
                    problems.append(
                        f"[{eval_id}/{w.name}] {el.name} ends {length - end:.0f}mm from wall "
                        f"end (< {END_CLEARANCE:.0f}mm corner clearance); wall len {length:.0f}"
                    )
            # pairwise overlap
            spans.sort()
            for i in range(len(spans) - 1):
                a_s, a_e, a_t, a_n = spans[i]
                b_s, b_e, b_t, b_n = spans[i + 1]
                if b_s < a_e:
                    problems.append(
                        f"[{eval_id}/{w.name}] OVERLAP: {a_n} [{a_s:.0f}-{a_e:.0f}] "
                        f"& {b_n} [{b_s:.0f}-{b_e:.0f}] (overlap {a_e - b_s:.0f}mm)"
                    )

    return join_info, problems


def main():
    total_problems = 0
    for eval_id in EVALS:
        join_info, problems = audit_eval(eval_id)
        print(f"\n=== {eval_id} ===")
        for lvl, nwalls, njoins, ntrim in join_info:
            status = "APPLIED" if ntrim > 0 else "NOT APPLIED"
            print(f"  joins[{lvl}]: walls={nwalls} joins_detected={njoins} trims_{status}={ntrim}")
        if problems:
            for p in problems:
                print(f"  PROBLEM: {p}")
            total_problems += len(problems)
        else:
            print("  openings: OK (no overlaps / off-wall / corner-clash)")
    print(f"\nTOTAL OPENING PROBLEMS: {total_problems}")


if __name__ == "__main__":
    main()
