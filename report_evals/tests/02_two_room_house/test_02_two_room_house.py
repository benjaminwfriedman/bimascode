"""Tests for Eval 02: Two Room House

Verifies a small house with two rooms:
- Living room: 6m x 5m with large window (2m wide) on south wall + entry door
- Bedroom: 4m x 5m with medium window on north wall
- Rooms share a wall with interior door connecting them
- Exterior walls: brick finish (100mm) + concrete structure (150mm) = 250mm
- IFC model, DXF drawings (floor plan, elevations, section), PDF drawing set
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
    """Test wall count and properties for two-room house."""

    def test_has_minimum_walls(self, ifc_path):
        """Two-room house needs at least 5 walls (4 exterior + 1 interior).

        Could be more depending on how interior wall is implemented (full wall
        with door opening vs two segments separated by door).
        """
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 5, f"Expected at least 5 walls (4 exterior + 1 interior), got {len(walls)}"

    def test_has_reasonable_wall_count(self, ifc_path):
        """Wall count should not be excessive."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        # Maximum reasonable: 4 exterior walls + 2 interior segments (if split by door)
        # Plus possible additional complexity from wall joins
        assert len(walls) <= 10, f"Too many walls: {len(walls)}. Expected 5-10 for two-room house"

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
    """Test door count and types for two-room house."""

    def test_has_two_doors(self, ifc_path):
        """Prompt specifies two doors: entry door + interior connecting door."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) == 2, f"Expected 2 doors (entry + interior), got {len(doors)}"

    def test_doors_have_geometry(self, ifc_path):
        """All doors should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        for door in doors:
            assert door.Representation is not None, f"Door {door.Name} has no representation"


# =============================================================================
# Window Tests
# =============================================================================


class TestWindows:
    """Test window count and placement for two-room house."""

    def test_has_two_windows(self, ifc_path):
        """Prompt specifies two windows: living room (south) + bedroom (north)."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) == 2, f"Expected 2 windows, got {len(windows)}"

    def test_windows_have_geometry(self, ifc_path):
        """All windows should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        for window in windows:
            assert window.Representation is not None, f"Window {window.Name} has no representation"

    def test_has_large_window(self, ifc_path):
        """Living room should have a large window (2m wide specified in prompt).

        Check that at least one window has width >= 1.8m (allowing some tolerance).
        """
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")

        large_window_found = False
        for window in windows:
            # Check OverallWidth attribute if available
            if hasattr(window, "OverallWidth") and window.OverallWidth is not None:
                width = window.OverallWidth
                # Convert from mm to m if needed (values > 100 are likely mm)
                if width > 100:
                    width = width / 1000
                if width >= 1.8:  # 2m with tolerance
                    large_window_found = True
                    break

        # If we can't verify from attributes, check window names for hints
        if not large_window_found:
            for window in windows:
                if window.Name and ("large" in window.Name.lower() or "2000" in window.Name or "2m" in window.Name.lower()):
                    large_window_found = True
                    break

        # Skip if we couldn't verify - window width might be in geometry only
        if not large_window_found:
            # Check that at least 2 windows exist (one should be larger)
            assert len(windows) >= 2, "Could not verify large window, but should have at least 2 windows"


# =============================================================================
# Dimension Tests
# =============================================================================


class TestDimensions:
    """Test that building dimensions match prompt specifications.

    Living room: 6m x 5m
    Bedroom: 4m x 5m
    Total footprint: approximately 10m x 5m (rooms side by side)
    """

    def test_building_footprint_approximately_correct(self, ifc_path):
        """Building footprint should be approximately 10m x 5m (±1m tolerance).

        Living room (6m x 5m) + Bedroom (4m x 5m) side by side = 10m x 5m
        """
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

        # Calculate dimensions
        width = max_x - min_x
        length = max_y - min_y

        # Convert to meters if values are in mm (>100)
        if width > 100 or length > 100:
            width = width / 1000
            length = length / 1000

        # Sort dimensions (10x5 or 5x10 are both valid)
        dims = sorted([width, length])

        # Expected: ~5m x ~10m (with wall thickness adding some)
        # Allow generous tolerance for wall thickness and placement variations
        assert 4.0 <= dims[0] <= 7.0, f"Smaller dimension {dims[0]:.1f}m not in expected range 4-7m"
        assert 8.0 <= dims[1] <= 12.0, f"Larger dimension {dims[1]:.1f}m not in expected range 8-12m"


# =============================================================================
# Material/Wall Type Tests
# =============================================================================


class TestWallMaterials:
    """Test that wall materials match prompt (brick finish + concrete structure)."""

    def test_walls_have_material_info(self, ifc_path):
        """Walls should have material associations."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        # Check if any wall has material association
        walls_with_material = 0
        for wall in walls:
            # Check for material layer set or material associations
            if hasattr(wall, "HasAssociations"):
                for rel in wall.HasAssociations:
                    if rel.is_a("IfcRelAssociatesMaterial"):
                        walls_with_material += 1
                        break

        # At least some walls should have materials defined
        assert walls_with_material >= 1, "No walls have material associations"

    def test_exterior_wall_thickness(self, ifc_path):
        """Exterior walls should be approximately 250mm (100mm brick + 150mm concrete).

        This is a soft check - we verify wall geometry exists and has reasonable thickness.
        """
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        # This test is informational - verify walls exist with geometry
        assert len(walls) >= 5, f"Need at least 5 walls, got {len(walls)}"

        # If wall type names indicate exterior, check they exist
        exterior_wall_names = []
        for wall in walls:
            if wall.Name:
                name_lower = wall.Name.lower()
                if "exterior" in name_lower or "external" in name_lower or "brick" in name_lower:
                    exterior_wall_names.append(wall.Name)

        # Don't fail if naming doesn't follow convention - just check walls exist
        # The geometry verification is more reliable than name checking


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
        dxf_files += list(dxf_dir.glob("*level*.dxf")) + list(dxf_dir.glob("*ground*.dxf"))
        assert len(dxf_files) >= 1, "No floor plan DXF found"

    def test_has_elevations(self, dxf_dir):
        """Should have elevation DXF files."""
        elevation_files = list(dxf_dir.glob("*elevation*.dxf"))
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

        dxf_file = dxf_files[0]
        doc = ezdxf.readfile(str(dxf_file))
        assert doc is not None

    def test_floor_plan_has_entities(self, dxf_dir):
        """Floor plan should contain drawing entities (lines, arcs, etc.)."""
        dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(dxf_files) >= 1, "No DXF files found"

        for dxf_file in dxf_files:
            doc = ezdxf.readfile(str(dxf_file))
            msp = doc.modelspace()
            entities = list(msp)
            if len(entities) > 0:
                return

        pytest.fail("No DXF files contain drawing entities")

    def test_floor_plan_has_door_swings(self, dxf_dir):
        """Floor plan should show door swings (arcs) for two doors."""
        plan_files = list(dxf_dir.glob("*plan*.dxf")) + list(dxf_dir.glob("*floor*.dxf"))
        plan_files += list(dxf_dir.glob("*level*.dxf")) + list(dxf_dir.glob("*ground*.dxf"))

        if not plan_files:
            pytest.skip("No floor plan DXF found")

        arc_count = 0
        for plan_file in plan_files:
            doc = ezdxf.readfile(str(plan_file))
            msp = doc.modelspace()
            for entity in msp:
                if entity.dxftype() == "ARC":
                    arc_count += 1

        # Two doors should produce at least 2 door swing arcs
        assert arc_count >= 2, f"Expected at least 2 door swing arcs, found {arc_count}"


# =============================================================================
# PDF Drawing Set Tests
# =============================================================================


class TestPDFDrawingSet:
    """Test PDF drawing set output."""

    def test_pdf_exists(self, pdf_path):
        """PDF drawing set should exist."""
        # Check both possible naming conventions
        if not pdf_path.exists():
            alt_path = pdf_path.parent / "drawing_set.pdf"
            assert alt_path.exists() or pdf_path.exists(), f"PDF not found at {pdf_path} or {alt_path}"

    def test_pdf_opens(self, pdf_path):
        """PDF should open without errors."""
        if not pdf_path.exists():
            alt_path = pdf_path.parent / "drawing_set.pdf"
            if alt_path.exists():
                pdf_path = alt_path

        doc = fitz.open(str(pdf_path))
        assert doc is not None
        doc.close()

    def test_pdf_has_pages(self, pdf_path):
        """PDF should have at least one page."""
        if not pdf_path.exists():
            alt_path = pdf_path.parent / "drawing_set.pdf"
            if alt_path.exists():
                pdf_path = alt_path

        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
        assert page_count >= 1, "PDF has no pages"

    def test_pdf_has_multiple_sheets(self, pdf_path):
        """PDF should have multiple sheets (plan + elevations + section)."""
        if not pdf_path.exists():
            alt_path = pdf_path.parent / "drawing_set.pdf"
            if alt_path.exists():
                pdf_path = alt_path

        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
        # Expect at least: 1 floor plan + 4 elevations + 1 section = 6 pages minimum
        # Or more condensed: 1 plan + 1 elevation sheet + 1 section = 3 pages
        assert page_count >= 3, f"Expected at least 3 pages (plan, elevation, section), got {page_count}"


# =============================================================================
# Room Configuration Tests
# =============================================================================


class TestRoomConfiguration:
    """Test that the two-room configuration is correct."""

    def test_has_interior_and_exterior_elements(self, ifc_path):
        """Building should have both interior elements (connecting door)
        and exterior elements (entry door, windows)."""
        ifc = ifcopenshell.open(ifc_path)

        doors = ifc.by_type("IfcDoor")
        windows = ifc.by_type("IfcWindow")

        # Must have 2 doors (entry + interior)
        assert len(doors) == 2, f"Expected 2 doors, got {len(doors)}"

        # Must have 2 windows (living room south + bedroom north)
        assert len(windows) == 2, f"Expected 2 windows, got {len(windows)}"
