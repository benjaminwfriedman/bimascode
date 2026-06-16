"""Pytest fixtures for Eval 03: Office Floor tests."""
import pytest
from pathlib import Path


@pytest.fixture
def output_dir():
    """Path to the output directory for this eval."""
    # Testing TEST-AWARE builder outputs
    return Path(__file__).parent.parent.parent / "outputs" / "03_office_floor_with_tests"


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
