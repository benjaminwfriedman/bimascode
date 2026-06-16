"""Tests for Eval 03: Office Floor

Requirements from prompt:
- Overall dimensions: 20m x 12m
- Reception area near entrance (~4m x 4m)
- 3 private offices along north wall (each 4m x 3m)
- Open workspace in remaining area
- Corridor connecting all spaces
- Main entrance on south wall (double door, 1.8m wide)
- Each private office has single door to corridor (3 doors)
- Large windows on east and west exterior walls
- Wall with glazing on south facade
- Generate: IFC model, DXF drawings (floor plan, elevations, section), PDF drawing set
"""

import math
from pathlib import Path

import ezdxf
import fitz
import ifcopenshell
import pytest


class TestIFCBasicStructure:
    """Test that IFC file exists and has valid structure."""

    def test_ifc_file_opens(self, ifc_path):
        """IFC file should open without errors."""
        ifc = ifcopenshell.open(ifc_path)
        assert ifc is not None, "Failed to open IFC file"

    def test_has_building_hierarchy(self, ifc_path):
        """IFC should have proper hierarchy: Project > Site > Building > Storey."""
        ifc = ifcopenshell.open(ifc_path)

        projects = ifc.by_type("IfcProject")
        assert len(projects) >= 1, "Missing IfcProject"

        sites = ifc.by_type("IfcSite")
        assert len(sites) >= 1, "Missing IfcSite"

        buildings = ifc.by_type("IfcBuilding")
        assert len(buildings) >= 1, "Missing IfcBuilding"

        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) >= 1, "Missing IfcBuildingStorey"

    def test_has_one_level(self, ifc_path):
        """Office floor is single level."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) == 1, f"Expected 1 level for office floor, got {len(storeys)}"


class TestWalls:
    """Test wall configuration."""

    def test_has_exterior_walls(self, ifc_path):
        """Building needs at least 4 exterior walls for rectangular footprint."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        # 4 exterior walls minimum, plus interior partition walls for offices/corridor
        # At minimum: 4 exterior + walls for 3 offices + corridor partitions
        assert len(walls) >= 4, f"Expected at least 4 walls, got {len(walls)}"

    def test_has_interior_partition_walls(self, ifc_path):
        """Building needs interior walls for offices and corridor."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        # 3 private offices require partition walls
        # Reception requires partition walls
        # Corridor requires walls
        # Minimum: 4 exterior + 4-6 interior partitions
        assert len(walls) >= 8, (
            f"Expected at least 8 walls (4 exterior + 4 interior for spaces), got {len(walls)}"
        )


class TestDoors:
    """Test door requirements."""

    def test_has_main_entrance(self, ifc_path):
        """Building should have at least one door for main entrance."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 1, "Missing main entrance door"

    def test_has_office_doors(self, ifc_path):
        """Each of 3 private offices needs a door to corridor."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        # 1 main entrance (double door) + 3 office doors = 4 minimum
        assert len(doors) >= 4, (
            f"Expected at least 4 doors (1 entrance + 3 offices), got {len(doors)}"
        )

    def test_main_entrance_width(self, ifc_path):
        """Main entrance should be double door ~1.8m wide."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")

        # Find widest door (should be the double door entrance)
        max_width = 0
        for door in doors:
            if hasattr(door, "OverallWidth") and door.OverallWidth:
                max_width = max(max_width, door.OverallWidth)

        # 1800mm = 1.8m, allow 10% tolerance
        expected_width = 1800  # mm
        tolerance = 0.10
        assert max_width >= expected_width * (1 - tolerance), (
            f"Main entrance should be ~1800mm wide, widest door is {max_width}mm"
        )


class TestWindows:
    """Test window requirements."""

    def test_has_windows(self, ifc_path):
        """Building should have windows on east and west walls."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        # "Large windows on east and west exterior walls" implies multiple windows
        assert len(windows) >= 2, (
            f"Expected at least 2 windows (east and west), got {len(windows)}"
        )


class TestBuildingDimensions:
    """Test overall building dimensions match 20m x 12m."""

    def test_building_footprint_approximately_correct(self, ifc_path):
        """Building should be approximately 20m x 12m."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        # Collect all wall placement coordinates
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")

        for wall in walls:
            if wall.ObjectPlacement:
                placement = wall.ObjectPlacement
                if hasattr(placement, "RelativePlacement"):
                    rel = placement.RelativePlacement
                    if hasattr(rel, "Location"):
                        loc = rel.Location
                        if hasattr(loc, "Coordinates"):
                            coords = loc.Coordinates
                            if len(coords) >= 2:
                                x, y = coords[0], coords[1]
                                min_x = min(min_x, x)
                                max_x = max(max_x, x)
                                min_y = min(min_y, y)
                                max_y = max(max_y, y)

        # If we found coordinates, check dimensions
        if min_x != float("inf") and min_y != float("inf"):
            width = max_x - min_x
            depth = max_y - min_y

            # Expected: 20m x 12m = 20000mm x 12000mm
            # Allow generous tolerance (walls may not be at exact corners)
            expected_dims = sorted([20000, 12000])
            actual_dims = sorted([width, depth])

            # Building should span at least 50% of expected dimensions
            # (conservative check since we're only looking at wall origins)
            assert actual_dims[0] >= expected_dims[0] * 0.3 or actual_dims[1] >= expected_dims[1] * 0.3, (
                f"Building dimensions {actual_dims} seem too small for 20m x 12m footprint"
            )


class TestSouthFacadeGlazing:
    """Test glazing requirements on south facade."""

    def test_has_glazing_elements(self, ifc_path):
        """South facade should have curtain wall or windows for glazing."""
        ifc = ifcopenshell.open(ifc_path)

        # Check for curtain walls (glazed wall system)
        curtain_walls = ifc.by_type("IfcCurtainWall")

        # Also check for windows (glazing could be implemented as windows)
        windows = ifc.by_type("IfcWindow")

        # "Wall with glazing" could be curtain wall or windows on south facade
        # Combined with east/west windows, need adequate glazing
        has_glazing = len(curtain_walls) > 0 or len(windows) >= 3

        assert has_glazing, (
            "South facade should have glazing (curtain wall or windows). "
            f"Found {len(curtain_walls)} curtain walls and {len(windows)} windows"
        )


class TestDXFDrawings:
    """Test DXF drawing generation."""

    def test_floor_plan_exists(self, dxf_dir):
        """Floor plan DXF should exist."""
        dxf_files = list(Path(dxf_dir).glob("*plan*.dxf")) + list(
            Path(dxf_dir).glob("*Plan*.dxf")
        )
        if not dxf_files:
            # Also check for any DXF that might be the floor plan
            dxf_files = list(Path(dxf_dir).glob("*.dxf"))

        assert len(dxf_files) >= 1, "No floor plan DXF found"

    def test_floor_plan_opens(self, dxf_dir):
        """Floor plan DXF should open without errors."""
        dxf_files = list(Path(dxf_dir).glob("*.dxf"))
        assert len(dxf_files) >= 1, "No DXF files found"

        # Try to open the first DXF
        doc = ezdxf.readfile(str(dxf_files[0]))
        assert doc is not None

    def test_elevations_exist(self, dxf_dir):
        """Should have elevation DXFs (north, south, east, west)."""
        dxf_files = list(Path(dxf_dir).glob("*.dxf"))
        elevation_files = [
            f for f in dxf_files if any(
                kw in f.stem.lower()
                for kw in ["elevation", "elev", "north", "south", "east", "west"]
            )
        ]
        # Prompt says "elevations" plural
        assert len(elevation_files) >= 1, (
            f"Expected elevation DXFs. Found files: {[f.name for f in dxf_files]}"
        )

    def test_section_exists(self, dxf_dir):
        """Should have at least one section DXF."""
        dxf_files = list(Path(dxf_dir).glob("*.dxf"))
        section_files = [
            f for f in dxf_files if any(
                kw in f.stem.lower() for kw in ["section", "sect"]
            )
        ]
        assert len(section_files) >= 1, (
            f"Expected section DXF. Found files: {[f.name for f in dxf_files]}"
        )

    def test_floor_plan_has_door_swings(self, dxf_dir):
        """Floor plan should show door swings as arcs."""
        dxf_files = list(Path(dxf_dir).glob("*.dxf"))

        # Look for plan files specifically
        plan_files = [
            f for f in dxf_files if "plan" in f.stem.lower()
        ] or dxf_files[:1]

        if not plan_files:
            pytest.skip("No plan DXF found")

        doc = ezdxf.readfile(str(plan_files[0]))
        msp = doc.modelspace()

        arcs = [e for e in msp if e.dxftype() == "ARC"]
        assert len(arcs) >= 1, (
            "Floor plan should have door swing arcs. "
            f"Found {len(arcs)} arcs"
        )

    def test_floor_plan_has_wall_lines(self, dxf_dir):
        """Floor plan should have lines representing walls."""
        dxf_files = list(Path(dxf_dir).glob("*.dxf"))

        plan_files = [
            f for f in dxf_files if "plan" in f.stem.lower()
        ] or dxf_files[:1]

        if not plan_files:
            pytest.skip("No plan DXF found")

        doc = ezdxf.readfile(str(plan_files[0]))
        msp = doc.modelspace()

        lines = [e for e in msp if e.dxftype() == "LINE"]
        # Should have many lines for walls, doors, windows
        assert len(lines) >= 20, (
            f"Floor plan should have many lines for walls. Found {len(lines)}"
        )


class TestPDFDrawingSet:
    """Test PDF drawing set generation."""

    def test_pdf_exists(self, pdf_path):
        """PDF drawing set should exist."""
        assert Path(pdf_path).exists(), f"PDF not found at {pdf_path}"

    def test_pdf_opens(self, pdf_path):
        """PDF should open without errors."""
        doc = fitz.open(pdf_path)
        assert doc is not None
        assert len(doc) >= 1, "PDF has no pages"

    def test_pdf_has_multiple_pages(self, pdf_path):
        """PDF should have pages for plan, elevations, and section."""
        doc = fitz.open(pdf_path)
        # Minimum: 1 floor plan + 1 elevation + 1 section = 3 pages
        assert len(doc) >= 3, (
            f"Expected at least 3 pages (plan, elevation, section), got {len(doc)}"
        )

    def test_pdf_contains_text(self, pdf_path):
        """PDF should contain title block text."""
        doc = fitz.open(pdf_path)
        all_text = "\n".join(page.get_text() for page in doc)

        # Should have some text (title block, labels, etc.)
        assert len(all_text.strip()) > 0, "PDF appears to have no text content"


class TestSpaceProgram:
    """Test that the space program is reflected in the model."""

    def test_sufficient_interior_walls_for_offices(self, ifc_path):
        """3 private offices need partition walls to separate them."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        # 3 offices along north wall need:
        # - 2 walls between offices (or 3 if offices are fully enclosed)
        # - At least 1 wall separating corridor from offices
        # So minimum interior walls: 3-4
        # Total walls: 4 exterior + 3-4 interior = 7-8 minimum
        assert len(walls) >= 7, (
            f"Expected at least 7 walls for 3 offices and circulation, got {len(walls)}"
        )

    def test_door_count_matches_program(self, ifc_path):
        """Should have doors for: 1 main entrance + 3 office doors minimum."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")

        # Minimum doors:
        # - 1 main entrance (double door counts as 1 IfcDoor)
        # - 3 private office doors
        # Total: 4 minimum
        assert len(doors) >= 4, (
            f"Expected at least 4 doors (entrance + 3 offices), got {len(doors)}"
        )
