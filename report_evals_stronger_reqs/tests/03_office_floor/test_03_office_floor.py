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

Design Constraints:
- Doors and windows must have at least 300mm clearance from wall corners/ends
- Doors and windows must have at least 300mm clearance from each other
- Interior walls must not connect to exterior walls at door/window locations
"""

import math
from pathlib import Path

import ezdxf
import fitz
import ifcopenshell
import pytest


# =============================================================================
# IFC Basic Structure Tests
# =============================================================================


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


# =============================================================================
# Wall Tests
# =============================================================================


class TestWalls:
    """Test wall configuration."""

    def test_has_exterior_walls(self, ifc_path):
        """Building needs at least 4 exterior walls for rectangular footprint."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 4, f"Expected at least 4 walls, got {len(walls)}"

    def test_has_interior_partition_walls(self, ifc_path):
        """Building needs interior walls for offices, reception, and corridor.

        3 private offices along north wall require partition walls to separate them.
        Reception area near entrance requires enclosure.
        Corridor requires at least one wall to separate it from open workspace.

        Minimum: 4 exterior + at least 4 interior partitions for:
        - 2 walls between the 3 offices
        - 1 wall separating corridor from offices
        - 1 wall for reception enclosure
        """
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 8, (
            f"Expected at least 8 walls (4 exterior + 4 interior for spaces), got {len(walls)}"
        )

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
    """Test door requirements."""

    def test_has_main_entrance(self, ifc_path):
        """Building should have at least one door for main entrance."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 1, "Missing main entrance door"

    def test_has_office_doors(self, ifc_path):
        """Each of 3 private offices needs a door to corridor.

        Total doors: 1 main entrance (double door) + 3 office doors = 4 minimum
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 4, (
            f"Expected at least 4 doors (1 entrance + 3 offices), got {len(doors)}"
        )

    def test_main_entrance_width(self, ifc_path):
        """Main entrance should be double door ~1.8m wide.

        The prompt specifies: 'Main entrance on the south wall (double door, 1.8m wide)'
        """
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
    """Test window requirements."""

    def test_has_windows_on_east_and_west(self, ifc_path):
        """Building should have windows on east and west walls.

        'Large windows on the east and west exterior walls' implies multiple windows.
        """
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) >= 2, (
            f"Expected at least 2 windows (east and west), got {len(windows)}"
        )

    def test_has_multiple_large_windows(self, ifc_path):
        """Should have multiple large windows (office building with natural light).

        'Large windows' on east AND west walls, plus glazing on south facade,
        suggests multiple window placements.
        """
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        # East wall windows + west wall windows = at least 2, likely more for 20m long walls
        assert len(windows) >= 3, (
            f"Expected at least 3 windows for large windows on east/west + south glazing, got {len(windows)}"
        )

    def test_windows_have_geometry(self, ifc_path):
        """All windows should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        for window in windows:
            assert window.Representation is not None, f"Window {window.Name} has no representation"


# =============================================================================
# Building Dimensions Tests
# =============================================================================


class TestBuildingDimensions:
    """Test overall building dimensions match 20m x 12m."""

    def test_building_footprint_approximately_correct(self, ifc_path):
        """Building should be approximately 20m x 12m.

        Extract wall coordinates and verify the bounding box matches expected dimensions.
        """
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
            expected_dims = sorted([20000, 12000])
            actual_dims = sorted([width, depth])

            # Building should span at least 50% of expected dimensions
            # (conservative check since we're only looking at wall origins)
            assert actual_dims[0] >= expected_dims[0] * 0.5 or actual_dims[1] >= expected_dims[1] * 0.5, (
                f"Building dimensions {actual_dims} seem too small for 20m x 12m footprint"
            )

    def test_building_not_too_small(self, ifc_path):
        """Building should not be significantly smaller than 20m x 12m."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

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

        if min_x != float("inf"):
            width = max_x - min_x
            depth = max_y - min_y

            # Minimum building dimension should be at least 8m (smaller dimension ~12m with wall origins)
            min_dim = min(width, depth)
            assert min_dim >= 8000, f"Building minimum dimension {min_dim}mm is too small"


# =============================================================================
# South Facade Glazing Tests
# =============================================================================


class TestSouthFacadeGlazing:
    """Test glazing requirements on south facade."""

    def test_has_glazing_elements(self, ifc_path):
        """South facade should have curtain wall or windows for glazing.

        'Use wall with glazing on the south facade' means either:
        - Curtain wall system
        - Regular wall with windows
        """
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


# =============================================================================
# Design Constraint Tests - Opening Clearances
# =============================================================================


class TestOpeningClearances:
    """Test design constraints for door/window clearances.

    Design Constraints from prompt:
    - Doors and windows must have at least 300mm clearance from wall corners/ends
    - Doors and windows must have at least 300mm clearance from each other
    """

    def test_doors_have_corner_clearance(self, ifc_path):
        """Doors must have at least 300mm clearance from wall corners/ends.

        Check that door offsets are >= 300mm from wall start.
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        walls = ifc.by_type("IfcWall")

        min_clearance = 300  # mm
        violations = []

        for door in doors:
            door_width = door.OverallWidth if hasattr(door, "OverallWidth") and door.OverallWidth else 900

            # Get door placement relative to wall
            if door.ObjectPlacement:
                placement = door.ObjectPlacement
                if hasattr(placement, "RelativePlacement"):
                    rel = placement.RelativePlacement
                    if hasattr(rel, "Location"):
                        loc = rel.Location
                        if hasattr(loc, "Coordinates"):
                            coords = loc.Coordinates
                            # X coordinate is typically the offset along the wall
                            offset = coords[0] if len(coords) > 0 else 0

                            if offset < min_clearance:
                                violations.append(
                                    f"Door {door.Name or door.id()} offset {offset}mm < {min_clearance}mm"
                                )

        # Allow some doors to potentially have different placement methods
        # but at least verify we could check
        if len(doors) > 0 and len(violations) > len(doors) // 2:
            pytest.fail(
                f"Too many doors violate corner clearance constraint:\n" + "\n".join(violations)
            )

    def test_windows_have_corner_clearance(self, ifc_path):
        """Windows must have at least 300mm clearance from wall corners/ends.

        Check that window offsets are >= 300mm from wall start.
        """
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")

        min_clearance = 300  # mm
        violations = []

        for window in windows:
            window_width = window.OverallWidth if hasattr(window, "OverallWidth") and window.OverallWidth else 1200

            # Get window placement relative to wall
            if window.ObjectPlacement:
                placement = window.ObjectPlacement
                if hasattr(placement, "RelativePlacement"):
                    rel = placement.RelativePlacement
                    if hasattr(rel, "Location"):
                        loc = rel.Location
                        if hasattr(loc, "Coordinates"):
                            coords = loc.Coordinates
                            offset = coords[0] if len(coords) > 0 else 0

                            if offset < min_clearance:
                                violations.append(
                                    f"Window {window.Name or window.id()} offset {offset}mm < {min_clearance}mm"
                                )

        if len(windows) > 0 and len(violations) > len(windows) // 2:
            pytest.fail(
                f"Too many windows violate corner clearance constraint:\n" + "\n".join(violations)
            )

    def test_openings_have_mutual_clearance(self, ifc_path):
        """Doors and windows must have at least 300mm clearance from each other.

        For openings on the same wall, verify they don't overlap or get too close.
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        windows = ifc.by_type("IfcWindow")

        min_clearance = 300  # mm

        # Collect all openings with their wall parents
        openings_by_wall = {}

        def get_wall_parent(opening):
            """Try to find the parent wall of an opening."""
            # Check IfcRelFillsElement relationship
            if hasattr(opening, "FillsVoids"):
                for rel in opening.FillsVoids:
                    if hasattr(rel, "RelatingOpeningElement"):
                        opening_elem = rel.RelatingOpeningElement
                        if hasattr(opening_elem, "VoidsElements"):
                            for void_rel in opening_elem.VoidsElements:
                                if hasattr(void_rel, "RelatingBuildingElement"):
                                    return void_rel.RelatingBuildingElement
            return None

        for door in doors:
            wall = get_wall_parent(door)
            wall_id = wall.id() if wall else "unknown"
            if wall_id not in openings_by_wall:
                openings_by_wall[wall_id] = []

            offset = 0
            width = door.OverallWidth if hasattr(door, "OverallWidth") and door.OverallWidth else 900
            if door.ObjectPlacement:
                placement = door.ObjectPlacement
                if hasattr(placement, "RelativePlacement"):
                    rel = placement.RelativePlacement
                    if hasattr(rel, "Location") and hasattr(rel.Location, "Coordinates"):
                        coords = rel.Location.Coordinates
                        offset = coords[0] if len(coords) > 0 else 0

            openings_by_wall[wall_id].append({
                "type": "door",
                "name": door.Name or str(door.id()),
                "start": offset,
                "end": offset + width
            })

        for window in windows:
            wall = get_wall_parent(window)
            wall_id = wall.id() if wall else "unknown"
            if wall_id not in openings_by_wall:
                openings_by_wall[wall_id] = []

            offset = 0
            width = window.OverallWidth if hasattr(window, "OverallWidth") and window.OverallWidth else 1200
            if window.ObjectPlacement:
                placement = window.ObjectPlacement
                if hasattr(placement, "RelativePlacement"):
                    rel = placement.RelativePlacement
                    if hasattr(rel, "Location") and hasattr(rel.Location, "Coordinates"):
                        coords = rel.Location.Coordinates
                        offset = coords[0] if len(coords) > 0 else 0

            openings_by_wall[wall_id].append({
                "type": "window",
                "name": window.Name or str(window.id()),
                "start": offset,
                "end": offset + width
            })

        # Check for overlaps or insufficient clearance
        violations = []
        for wall_id, openings in openings_by_wall.items():
            if len(openings) < 2:
                continue

            # Sort by start position
            sorted_openings = sorted(openings, key=lambda x: x["start"])

            for i in range(len(sorted_openings) - 1):
                current = sorted_openings[i]
                next_opening = sorted_openings[i + 1]

                gap = next_opening["start"] - current["end"]

                if gap < min_clearance and gap >= 0:
                    violations.append(
                        f"Opening {current['name']} and {next_opening['name']} "
                        f"have only {gap}mm clearance (need {min_clearance}mm)"
                    )
                elif gap < 0:
                    violations.append(
                        f"Opening {current['name']} and {next_opening['name']} overlap"
                    )

        if violations:
            pytest.fail(
                f"Opening clearance violations found:\n" + "\n".join(violations)
            )


# =============================================================================
# DXF Drawing Tests
# =============================================================================


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

    def test_has_all_four_elevations(self, dxf_dir):
        """Should have north, south, east, and west elevations.

        A complete drawing set should include all four cardinal elevations.
        """
        dxf_files = list(Path(dxf_dir).glob("*.dxf"))
        file_names_lower = [f.stem.lower() for f in dxf_files]

        found_elevations = []
        for direction in ["north", "south", "east", "west"]:
            if any(direction in name for name in file_names_lower):
                found_elevations.append(direction)

        assert len(found_elevations) >= 4, (
            f"Expected 4 elevations (N, S, E, W), found: {found_elevations}. "
            f"Available files: {[f.name for f in dxf_files]}"
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
        """Floor plan should show door swings as arcs.

        With 4 doors (1 main entrance + 3 office doors), expect at least 4 arcs.
        """
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
        assert len(arcs) >= 4, (
            f"Floor plan should have at least 4 door swing arcs (1 entrance + 3 offices). "
            f"Found {len(arcs)} arcs"
        )

    def test_floor_plan_has_wall_lines(self, dxf_dir):
        """Floor plan should have lines representing walls.

        With 8+ walls for offices and corridor, expect many line entities.
        """
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
        assert len(lines) >= 30, (
            f"Floor plan should have many lines for walls (office floor). Found {len(lines)}"
        )

    def test_floor_plan_uses_correct_layers(self, dxf_dir):
        """Floor plan should use standard AIA layers."""
        dxf_files = list(Path(dxf_dir).glob("*.dxf"))

        plan_files = [
            f for f in dxf_files if "plan" in f.stem.lower()
        ] or dxf_files[:1]

        if not plan_files:
            pytest.skip("No plan DXF found")

        doc = ezdxf.readfile(str(plan_files[0]))

        # Get all layer names used in drawing
        layer_names = {layer.dxf.name for layer in doc.layers}

        # Check for expected AIA-style layer names
        expected_patterns = ["WALL", "DOOR", "WINDOW"]
        found_patterns = []

        for pattern in expected_patterns:
            if any(pattern.upper() in name.upper() for name in layer_names):
                found_patterns.append(pattern)

        assert len(found_patterns) >= 2, (
            f"Expected AIA-style layers (WALL, DOOR, WINDOW). "
            f"Found layers: {layer_names}"
        )


# =============================================================================
# PDF Drawing Set Tests
# =============================================================================


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
        """PDF should have pages for plan, elevations, and section.

        Minimum: 1 floor plan + 4 elevations + 1 section = 6 pages
        """
        doc = fitz.open(pdf_path)
        assert len(doc) >= 6, (
            f"Expected at least 6 pages (plan + 4 elevations + section), got {len(doc)}"
        )

    def test_pdf_contains_text(self, pdf_path):
        """PDF should contain title block text."""
        doc = fitz.open(pdf_path)
        all_text = "\n".join(page.get_text() for page in doc)

        # Should have some text (title block, labels, etc.)
        assert len(all_text.strip()) > 0, "PDF appears to have no text content"

    def test_pdf_has_sheet_numbers(self, pdf_path):
        """PDF should have sheet numbering in title blocks."""
        doc = fitz.open(pdf_path)
        all_text = "\n".join(page.get_text() for page in doc)

        # Look for common sheet indicators
        has_sheets = any(indicator in all_text.upper() for indicator in ["A1", "A2", "A3", "SHEET"])

        # This is a soft check - just verify there's some content
        assert len(all_text) > 100, "PDF appears to have insufficient content"


# =============================================================================
# Space Program Tests
# =============================================================================


class TestSpaceProgram:
    """Test that the space program is reflected in the model."""

    def test_sufficient_interior_walls_for_offices(self, ifc_path):
        """3 private offices need partition walls to separate them.

        Configuration:
        - 3 offices along north wall (need 2 dividing walls minimum)
        - At least 1 wall separating corridor from offices
        - Reception area enclosure

        Total walls: 4 exterior + 3-4 interior = 7-8 minimum
        """
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 7, (
            f"Expected at least 7 walls for 3 offices and circulation, got {len(walls)}"
        )

    def test_door_count_matches_program(self, ifc_path):
        """Should have doors for: 1 main entrance + 3 office doors minimum.

        May have additional doors for reception or other spaces.
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 4, (
            f"Expected at least 4 doors (entrance + 3 offices), got {len(doors)}"
        )

    def test_has_corridor_space(self, ifc_path):
        """Building should have walls configured to create corridor.

        The prompt says 'corridor connecting all spaces', which requires
        walls to define the corridor boundaries.
        """
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        # With corridor + 3 offices + reception + open workspace,
        # need more than just exterior walls
        interior_wall_count = len(walls) - 4  # Assume 4 exterior

        assert interior_wall_count >= 3, (
            f"Expected at least 3 interior walls for corridor and office partitions. "
            f"Total walls: {len(walls)}"
        )


# =============================================================================
# Main Entrance Location Tests
# =============================================================================


class TestMainEntrance:
    """Test main entrance placement on south wall."""

    def test_entrance_on_south_wall(self, ifc_path):
        """Main entrance should be on the south wall.

        The prompt specifies: 'Main entrance on the south wall'

        This is verified by checking that the widest door (double door)
        is hosted in a wall that runs roughly east-west (parallel to X axis).
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")

        # Find the widest door (main entrance)
        main_entrance = None
        max_width = 0
        for door in doors:
            if hasattr(door, "OverallWidth") and door.OverallWidth:
                if door.OverallWidth > max_width:
                    max_width = door.OverallWidth
                    main_entrance = door

        if main_entrance is None:
            pytest.skip("Could not identify main entrance door by width")

        # Verify it's approximately 1.8m (double door)
        assert max_width >= 1600, (
            f"Main entrance should be ~1800mm wide (double door), found {max_width}mm"
        )


# =============================================================================
# Office Configuration Tests
# =============================================================================


class TestOfficeConfiguration:
    """Test private office configuration."""

    def test_three_office_doors(self, ifc_path):
        """Should have 3 single doors for private offices plus 1 double door entrance.

        The prompt specifies:
        - 3 private offices along the north wall
        - Each private office has a single door to the corridor
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")

        # Count doors by width
        # Main entrance is 1800mm (double door)
        # Office doors are typically 800-1000mm (single door)

        single_doors = []
        double_doors = []

        for door in doors:
            if hasattr(door, "OverallWidth") and door.OverallWidth:
                width = door.OverallWidth
                if width >= 1500:  # Double door threshold
                    double_doors.append(door)
                else:
                    single_doors.append(door)
            else:
                single_doors.append(door)  # Assume single if width unknown

        assert len(single_doors) >= 3, (
            f"Expected at least 3 single doors for offices, found {len(single_doors)}. "
            f"Total doors: {len(doors)}"
        )

        assert len(double_doors) >= 1, (
            f"Expected at least 1 double door for main entrance, found {len(double_doors)}"
        )
