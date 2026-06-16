"""Pytest fixtures for Eval 03: Office Floor tests."""
import pytest
from pathlib import Path

EVAL_ID = "03_office_floor"
# Default to blind builder version - change to test with_tests version
OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs" / EVAL_ID


@pytest.fixture
def output_dir():
    """Path to the output directory for this eval."""
    return OUTPUTS_DIR


@pytest.fixture
def ifc_path(output_dir):
    """Path to the IFC file."""
    return output_dir / "building.ifc"


@pytest.fixture
def dxf_dir(output_dir):
    """Path to the DXF output directory."""
    return output_dir / "dxf"


@pytest.fixture
def pdf_path(output_dir):
    """Path to the PDF drawing set."""
    return output_dir / "03_office_floor_drawing_set.pdf"
