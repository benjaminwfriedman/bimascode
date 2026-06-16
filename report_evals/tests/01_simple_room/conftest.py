"""Pytest fixtures for Eval 01: Simple Room tests."""
import pytest
from pathlib import Path


@pytest.fixture
def output_dir():
    """Path to the output directory for this eval."""
    # Testing TEST-AWARE builder outputs
    return Path(__file__).parent.parent.parent / "outputs" / "01_simple_room_with_tests"


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
    return output_dir / "01_simple_room_drawing_set.pdf"
