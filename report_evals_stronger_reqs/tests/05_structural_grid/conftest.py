"""Pytest fixtures for Eval 05: Structural Grid Building tests."""
import pytest
from pathlib import Path

# Testing TEST-AWARE builder (version 2)
EVAL_ID = "05_structural_grid_with_tests"


@pytest.fixture
def output_dir():
    """Path to the output directory for this eval."""
    return Path(__file__).parent.parent.parent / "outputs" / EVAL_ID


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
    return output_dir / "05_structural_grid_drawing_set.pdf"
