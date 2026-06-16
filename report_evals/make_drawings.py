"""
Generate DXF drawings (plans, elevations, sections) and a PDF drawing set for
each eval. Reuses each eval's build() to construct the model, then runs the
shared drawing generator in outputs/_drawings.py.

Usage:
    python make_drawings.py            # all evals
    python make_drawings.py 01 05      # selected evals (by id prefix)
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "outputs"))
from _drawings import generate_drawing_set  # noqa: E402

EVALS = [
    ("01_simple_room", "Eval 01 - Simple Room", "A"),
    ("02_two_room_house", "Eval 02 - Two Room House", "A"),
    ("03_office_floor", "Eval 03 - Office Floor", "A"),
    ("04_two_story_building", "Eval 04 - Two Story Building", "A"),
    ("05_structural_grid", "Eval 05 - Structural Grid", "S"),
]


def load_building(eval_id):
    path = ROOT / "outputs" / eval_id / "building.py"
    spec = importlib.util.spec_from_file_location(f"bld_{eval_id}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.build()
    return res[0] if isinstance(res, tuple) else res["building"]


def main():
    selected = sys.argv[1:]
    for eval_id, project, prefix in EVALS:
        if selected and not any(eval_id.startswith(s) for s in selected):
            continue
        print(f"\n=== Drawings for {eval_id} ===")
        building = load_building(eval_id)
        out_dir = ROOT / "outputs" / eval_id
        counts = generate_drawing_set(building, out_dir, eval_id, project, sheet_prefix=prefix)
        print(
            f"  plans={counts['plans']} elevations={counts['elevations']} "
            f"sections={counts['sections']} | DXFs={counts['dxf_files']} | "
            f"sheets={counts['sheet_pdfs']} @ {counts['scale']} | set={counts['set_pdf']}"
        )


if __name__ == "__main__":
    main()
