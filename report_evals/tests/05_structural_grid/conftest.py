"""Pytest fixtures for Eval 05: Structural Grid Building tests."""
import pytest
from pathlib import Path


@pytest.fixture
def output_dir():
    """Path to the output directory for this eval."""
    return Path(__file__).parent.parent.parent / "outputs" / "05_structural_grid"


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
