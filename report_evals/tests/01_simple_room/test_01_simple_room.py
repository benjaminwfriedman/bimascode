"""Tests for Eval 01: Simple Room

Verifies a 5m x 4m room with:
- 4 concrete walls (200mm thick)
- 1 door on south wall
- 1 window on east wall
- IFC model, DXF drawings, PDF drawing set
"""
import pytest
import ifcopenshell
import ifcopenshell.util.element
import ezdxf
import fitz
from pathlib import Path


# =============================================================================
# IFC Basic Structure Tests
# =============================================================================


class TestIFCStructure:
    """Test that the IFC file has correct structure and hierarchy."""

    def test_ifc_opens(self, ifc_path):
        """IFC file should open without errors."""
        ifc = ifcopenshell.open(ifc_path)
        assert ifc is not None

    def test_has_project(self, ifc_path):
        """IFC should have exactly one project."""
        ifc = ifcopenshell.open(ifc_path)
        projects = ifc.by_type("IfcProject")
        assert len(projects) == 1, f"Expected 1 IfcProject, got {len(projects)}"

    def test_has_building(self, ifc_path):
        """IFC should have at least one building."""
        ifc = ifcopenshell.open(ifc_path)
        buildings = ifc.by_type("IfcBuilding")
        assert len(buildings) >= 1, f"Expected at least 1 IfcBuilding, got {len(buildings)}"

    def test_has_building_storey(self, ifc_path):
        """IFC should have at least one building storey."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) >= 1, f"Expected at least 1 IfcBuildingStorey, got {len(storeys)}"


# =============================================================================
# Wall Tests
# =============================================================================


class TestWalls:
    """Test wall count and properties."""

    def test_has_four_walls(self, ifc_path):
        """A rectangular room needs exactly 4 walls."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) == 4, f"Expected 4 walls for rectangular room, got {len(walls)}"

    def test_walls_have_geometry(self, ifc_path):
        """All walls should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        for wall in walls:
            assert wall.Representation is not None, f"Wall {wall.Name} has no representation"


# =============================================================================
# Door Tests
# =============================================================================


class TestDoors:
    """Test door count and placement."""

    def test_has_one_door(self, ifc_path):
        """Prompt specifies exactly one door."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) == 1, f"Expected 1 door, got {len(doors)}"

    def test_door_has_geometry(self, ifc_path):
        """Door should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 1, "No doors found"
        door = doors[0]
        assert door.Representation is not None, "Door has no representation"


# =============================================================================
# Window Tests
# =============================================================================


class TestWindows:
    """Test window count and placement."""

    def test_has_one_window(self, ifc_path):
        """Prompt specifies exactly one window."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) == 1, f"Expected 1 window, got {len(windows)}"

    def test_window_has_geometry(self, ifc_path):
        """Window should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) >= 1, "No windows found"
        window = windows[0]
        assert window.Representation is not None, "Window has no representation"


# =============================================================================
# Dimension Tests
# =============================================================================


class TestDimensions:
    """Test that room dimensions match prompt (5m x 4m)."""

    def test_room_dimensions_approximately_correct(self, ifc_path):
        """Room should be approximately 5m x 4m (±0.5m tolerance)."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        # Collect all wall placement coordinates to compute bounding box
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")

        for wall in walls:
            placement = wall.ObjectPlacement
            if placement and hasattr(placement, "RelativePlacement"):
                rel_placement = placement.RelativePlacement
                if rel_placement and hasattr(rel_placement, "Location"):
                    location = rel_placement.Location
                    if location and hasattr(location, "Coordinates"):
                        coords = location.Coordinates
                        x, y = coords[0], coords[1]
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)

        # If we couldn't extract coordinates, skip this test
        if min_x == float("inf"):
            pytest.skip("Could not extract wall coordinates from IFC")

        # Calculate dimensions (in meters, IFC uses mm or m depending on units)
        # Allow for tolerance and wall thickness
        width = max_x - min_x
        length = max_y - min_y

        # Dimensions should be roughly 5m x 4m (5000mm x 4000mm)
        # With tolerance for wall thickness and placement variations
        # The dimensions could be in either order (5x4 or 4x5)
        dims = sorted([width, length])

        # Convert to meters if values are in mm (>100)
        if dims[0] > 100:
            dims = [d / 1000 for d in dims]

        # Allow generous tolerance (±1m) since wall positions vary
        assert 3.0 <= dims[0] <= 5.0, f"Smaller dimension {dims[0]}m not in range 3-5m"
        assert 4.0 <= dims[1] <= 6.0, f"Larger dimension {dims[1]}m not in range 4-6m"


# =============================================================================
# DXF Drawing Tests
# =============================================================================


class TestDXFDrawings:
    """Test DXF drawing outputs."""

    def test_dxf_directory_exists(self, dxf_dir):
        """DXF output directory should exist."""
        assert dxf_dir.exists(), f"DXF directory not found: {dxf_dir}"

    def test_has_floor_plan(self, dxf_dir):
        """Should have at least one floor plan DXF."""
        dxf_files = list(dxf_dir.glob("*plan*.dxf")) + list(dxf_dir.glob("*floor*.dxf"))
        # Also check for level-named files
        dxf_files += list(dxf_dir.glob("*level*.dxf")) + list(dxf_dir.glob("*ground*.dxf"))
        assert len(dxf_files) >= 1, "No floor plan DXF found"

    def test_has_elevations(self, dxf_dir):
        """Should have elevation DXF files."""
        elevation_files = list(dxf_dir.glob("*elevation*.dxf"))
        # Also check for cardinal direction names
        elevation_files += list(dxf_dir.glob("*north*.dxf"))
        elevation_files += list(dxf_dir.glob("*south*.dxf"))
        elevation_files += list(dxf_dir.glob("*east*.dxf"))
        elevation_files += list(dxf_dir.glob("*west*.dxf"))
        assert len(elevation_files) >= 1, "No elevation DXF files found"

    def test_has_section(self, dxf_dir):
        """Should have at least one section DXF."""
        section_files = list(dxf_dir.glob("*section*.dxf"))
        assert len(section_files) >= 1, "No section DXF files found"

    def test_floor_plan_opens(self, dxf_dir):
        """Floor plan DXF should open without errors."""
        dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(dxf_files) >= 1, "No DXF files found"

        # Try to open the first DXF file
        dxf_file = dxf_files[0]
        doc = ezdxf.readfile(str(dxf_file))
        assert doc is not None

    def test_floor_plan_has_entities(self, dxf_dir):
        """Floor plan should contain drawing entities (lines, arcs, etc.)."""
        dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(dxf_files) >= 1, "No DXF files found"

        # Check that at least one DXF has entities
        for dxf_file in dxf_files:
            doc = ezdxf.readfile(str(dxf_file))
            msp = doc.modelspace()
            entities = list(msp)
            if len(entities) > 0:
                return  # Found a DXF with entities

        pytest.fail("No DXF files contain drawing entities")


# =============================================================================
# PDF Drawing Set Tests
# =============================================================================


class TestPDFDrawingSet:
    """Test PDF drawing set output."""

    def test_pdf_exists(self, pdf_path):
        """PDF drawing set should exist."""
        assert pdf_path.exists(), f"PDF not found: {pdf_path}"

    def test_pdf_opens(self, pdf_path):
        """PDF should open without errors."""
        doc = fitz.open(str(pdf_path))
        assert doc is not None
        doc.close()

    def test_pdf_has_pages(self, pdf_path):
        """PDF should have at least one page."""
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
        assert page_count >= 1, f"PDF has no pages"

    def test_pdf_has_multiple_sheets(self, pdf_path):
        """PDF should have multiple sheets (plan + elevations + section)."""
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
        # Expect at least: 1 floor plan + 1 elevation + 1 section = 3 pages minimum
        assert page_count >= 3, f"Expected at least 3 pages (plan, elevation, section), got {page_count}"
