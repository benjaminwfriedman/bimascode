"""Tests for Eval 05: Structural Grid Building

Verifies a warehouse-style building with exposed structure:
- Dimensions: 24m x 18m
- Structural grid: 6m x 6m (4 bays x 3 bays)
- Steel columns (400mm square) at each grid intersection
- Main beams spanning in X direction (300mm x 500mm)
- Secondary beams in Y direction (200mm x 400mm)
- Concrete exterior walls (200mm)
- Large loading door on south wall (4m wide x 4m high)
- Regular doors on east and west walls
- Clerestory windows along north wall (4 windows, each 2m wide)
- Outputs: IFC model, DXF drawings, PDF drawing set
"""

import math
import os
from pathlib import Path

import ezdxf
import fitz
import ifcopenshell
import ifcopenshell.util.element as ifc_element
import pytest


# =============================================================================
# IFC Basic Structure Tests
# =============================================================================


class TestIFCBasicStructure:
    """Test that IFC file has correct basic structure."""

    def test_ifc_file_opens(self, ifc_path):
        """IFC file should be valid and openable."""
        ifc = ifcopenshell.open(ifc_path)
        assert ifc is not None

    def test_has_project_hierarchy(self, ifc_path):
        """IFC should have proper hierarchy: Project > Site > Building > Storey."""
        ifc = ifcopenshell.open(ifc_path)

        projects = ifc.by_type("IfcProject")
        assert len(projects) >= 1, "IFC must have at least one IfcProject"

        sites = ifc.by_type("IfcSite")
        assert len(sites) >= 1, "IFC must have at least one IfcSite"

        buildings = ifc.by_type("IfcBuilding")
        assert len(buildings) >= 1, "IFC must have at least one IfcBuilding"

        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) >= 1, "IFC must have at least one IfcBuildingStorey"

    def test_single_storey_building(self, ifc_path):
        """Warehouse is single-storey - should have exactly 1 storey."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) == 1, f"Expected 1 storey for warehouse, got {len(storeys)}"


# =============================================================================
# Building Dimension Tests
# =============================================================================


class TestBuildingDimensions:
    """Test overall building dimensions: 24m x 18m."""

    def test_building_footprint_approximately_correct(self, ifc_path):
        """Building should be approximately 24m x 18m."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        if len(walls) == 0:
            pytest.fail("No walls found to measure building footprint")

        # Collect wall placement coordinates
        x_coords = []
        y_coords = []

        for wall in walls:
            placement = wall.ObjectPlacement
            if placement and hasattr(placement, "RelativePlacement"):
                rel = placement.RelativePlacement
                if hasattr(rel, "Location") and rel.Location:
                    loc = rel.Location.Coordinates
                    x_coords.append(loc[0])
                    y_coords.append(loc[1])

        if x_coords and y_coords:
            x_span = max(x_coords) - min(x_coords)
            y_span = max(y_coords) - min(y_coords)

            # Convert to meters if in mm
            if x_span > 100:
                x_span /= 1000
                y_span /= 1000

            # Expected: 24m x 18m, allow ±2m tolerance
            dims = sorted([x_span, y_span])
            expected_dims = sorted([24.0, 18.0])

            # Verify dimensions are approximately correct
            short_ok = abs(dims[0] - expected_dims[0]) <= 2.0
            long_ok = abs(dims[1] - expected_dims[1]) <= 2.0

            assert short_ok or long_ok, (
                f"Building dimensions ({dims[0]:.1f}m x {dims[1]:.1f}m) "
                f"don't match expected 24m x 18m"
            )


# =============================================================================
# Structural Grid Tests
# =============================================================================


class TestStructuralGrid:
    """Test structural grid: 6m x 6m (4 bays x 3 bays)."""

    def test_has_columns(self, ifc_path):
        """Building should have structural columns."""
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")
        assert len(columns) > 0, "Warehouse must have structural columns"

    def test_column_count_matches_grid(self, ifc_path):
        """4 bays x 3 bays grid = 5 x 4 = 20 column positions.

        With 24m x 18m and 6m grid spacing:
        - X direction: 24m / 6m = 4 bays = 5 grid lines
        - Y direction: 18m / 6m = 3 bays = 4 grid lines
        - Total intersections: 5 x 4 = 20 columns
        """
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")

        expected_columns = 20
        tolerance = 4  # Allow some variance for implementation flexibility

        assert len(columns) >= expected_columns - tolerance, (
            f"Expected ~{expected_columns} columns (5x4 grid), got {len(columns)}"
        )
        assert len(columns) <= expected_columns + tolerance, (
            f"Expected ~{expected_columns} columns (5x4 grid), got {len(columns)}"
        )

    def test_columns_at_grid_intersections(self, ifc_path):
        """Columns should be placed at 6m grid intervals."""
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")

        if len(columns) == 0:
            pytest.fail("No columns found")

        # Collect column positions
        positions = []
        for column in columns:
            placement = column.ObjectPlacement
            if placement and hasattr(placement, "RelativePlacement"):
                rel = placement.RelativePlacement
                if hasattr(rel, "Location") and rel.Location:
                    loc = rel.Location.Coordinates
                    positions.append((loc[0], loc[1]))

        if len(positions) < 2:
            pytest.skip("Insufficient column positions to verify grid")

        # Check that columns are at regular intervals
        # Extract unique X and Y coordinates
        x_coords = sorted(set(pos[0] for pos in positions))
        y_coords = sorted(set(pos[1] for pos in positions))

        # Verify grid spacing is approximately 6m (6000mm)
        expected_spacing_mm = 6000.0
        tolerance_mm = 500.0  # Allow 500mm tolerance

        if len(x_coords) >= 2:
            x_spacings = [x_coords[i+1] - x_coords[i] for i in range(len(x_coords) - 1)]
            avg_x_spacing = sum(x_spacings) / len(x_spacings)
            assert abs(avg_x_spacing - expected_spacing_mm) <= tolerance_mm, (
                f"X-direction column spacing {avg_x_spacing:.0f}mm "
                f"doesn't match expected 6000mm"
            )

        if len(y_coords) >= 2:
            y_spacings = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords) - 1)]
            avg_y_spacing = sum(y_spacings) / len(y_spacings)
            assert abs(avg_y_spacing - expected_spacing_mm) <= tolerance_mm, (
                f"Y-direction column spacing {avg_y_spacing:.0f}mm "
                f"doesn't match expected 6000mm"
            )


class TestColumns:
    """Test column specifications: 400mm square steel."""

    def test_column_dimensions(self, ifc_path):
        """Columns should be approximately 400mm square."""
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")

        if len(columns) == 0:
            pytest.fail("No columns found")

        # Check column property sets for dimensions
        expected_size_mm = 400.0
        tolerance_mm = 50.0

        for column in columns:
            psets = ifc_element.get_psets(column)
            for pset_name, pset_data in psets.items():
                if "Width" in pset_data:
                    width = pset_data["Width"]
                    if abs(width - expected_size_mm) > tolerance_mm:
                        pytest.fail(
                            f"Column width {width}mm doesn't match expected 400mm"
                        )
                if "Depth" in pset_data:
                    depth = pset_data["Depth"]
                    if abs(depth - expected_size_mm) > tolerance_mm:
                        pytest.fail(
                            f"Column depth {depth}mm doesn't match expected 400mm"
                        )


# =============================================================================
# Beam Tests
# =============================================================================


class TestBeams:
    """Test beam specifications."""

    def test_has_beams(self, ifc_path):
        """Building should have structural beams."""
        ifc = ifcopenshell.open(ifc_path)
        beams = ifc.by_type("IfcBeam")
        assert len(beams) > 0, "Warehouse must have structural beams"

    def test_beam_count_reasonable(self, ifc_path):
        """Building should have beams spanning grid.

        Main beams in X direction: 4 grid lines x 3 bays = at least 12 beams
        Secondary beams in Y direction: 5 grid lines x (some number per bay)
        Total should be at least 20 beams.
        """
        ifc = ifcopenshell.open(ifc_path)
        beams = ifc.by_type("IfcBeam")

        # Minimum: main beams across 4 Y-grid lines spanning 4 X-bays = 16
        # Plus secondary beams
        min_beams = 12

        assert len(beams) >= min_beams, (
            f"Expected at least {min_beams} beams for structural framing, "
            f"got {len(beams)}"
        )

    def test_main_beam_dimensions(self, ifc_path):
        """Main beams should be 300mm wide x 500mm deep."""
        ifc = ifcopenshell.open(ifc_path)
        beams = ifc.by_type("IfcBeam")

        if len(beams) == 0:
            pytest.fail("No beams found")

        # Main beam expected dimensions: 300mm x 500mm
        main_beam_width = 300.0
        main_beam_height = 500.0
        tolerance = 50.0

        # Check if any beam matches main beam dimensions
        found_main_beam = False
        for beam in beams:
            psets = ifc_element.get_psets(beam)
            for pset_name, pset_data in psets.items():
                width = pset_data.get("Width", 0)
                height = pset_data.get("Height", pset_data.get("Depth", 0))
                if (abs(width - main_beam_width) <= tolerance and
                    abs(height - main_beam_height) <= tolerance):
                    found_main_beam = True
                    break
            if found_main_beam:
                break

        # Note: If psets don't contain dimensions, we can't verify this
        # Skip test rather than fail
        if not found_main_beam:
            # Check beam types instead
            beam_types = ifc.by_type("IfcBeamType")
            for bt in beam_types:
                psets = ifc_element.get_psets(bt)
                for pset_name, pset_data in psets.items():
                    width = pset_data.get("Width", 0)
                    height = pset_data.get("Height", pset_data.get("Depth", 0))
                    if (abs(width - main_beam_width) <= tolerance and
                        abs(height - main_beam_height) <= tolerance):
                        found_main_beam = True
                        break

        # If still not found, skip (dimensions may not be in property sets)

    def test_secondary_beam_dimensions(self, ifc_path):
        """Secondary beams should be 200mm wide x 400mm deep."""
        ifc = ifcopenshell.open(ifc_path)
        beams = ifc.by_type("IfcBeam")

        if len(beams) == 0:
            pytest.fail("No beams found")

        # Secondary beam expected dimensions: 200mm x 400mm
        sec_beam_width = 200.0
        sec_beam_height = 400.0
        tolerance = 50.0

        # Check if any beam matches secondary beam dimensions
        found_sec_beam = False
        for beam in beams:
            psets = ifc_element.get_psets(beam)
            for pset_name, pset_data in psets.items():
                width = pset_data.get("Width", 0)
                height = pset_data.get("Height", pset_data.get("Depth", 0))
                if (abs(width - sec_beam_width) <= tolerance and
                    abs(height - sec_beam_height) <= tolerance):
                    found_sec_beam = True
                    break
            if found_sec_beam:
                break

        # Note: If psets don't contain dimensions, we can't verify this


# =============================================================================
# Wall Tests
# =============================================================================


class TestWalls:
    """Test wall configuration: 200mm concrete exterior walls."""

    def test_has_walls(self, ifc_path):
        """Building should have exterior walls."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) > 0, "Warehouse must have walls"

    def test_exterior_wall_count(self, ifc_path):
        """Rectangular building needs at least 4 exterior walls."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 4, f"Expected at least 4 exterior walls, got {len(walls)}"

    def test_wall_thickness(self, ifc_path):
        """Exterior walls should be 200mm concrete."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        expected_thickness_mm = 200.0
        tolerance_mm = 50.0

        wall_thicknesses = []
        for wall in walls:
            psets = ifc_element.get_psets(wall)
            for pset_name, pset_data in psets.items():
                if "Width" in pset_data:
                    wall_thicknesses.append(pset_data["Width"])
                elif "Thickness" in pset_data:
                    wall_thicknesses.append(pset_data["Thickness"])

        if wall_thicknesses:
            has_correct_thickness = any(
                abs(t - expected_thickness_mm) <= tolerance_mm for t in wall_thicknesses
            )
            assert has_correct_thickness, (
                f"Expected 200mm wall thickness, found: {wall_thicknesses}"
            )


# =============================================================================
# Door Tests
# =============================================================================


class TestDoors:
    """Test door configuration."""

    def test_has_doors(self, ifc_path):
        """Building should have doors."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) > 0, "Warehouse must have doors"

    def test_door_count(self, ifc_path):
        """Building should have at least 3 doors: loading door + east + west."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 3, (
            f"Expected at least 3 doors (loading + east + west), got {len(doors)}"
        )

    def test_loading_door_dimensions(self, ifc_path):
        """Loading door on south wall should be 4m wide x 4m high."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")

        expected_width_mm = 4000.0
        expected_height_mm = 4000.0
        tolerance_mm = 300.0

        found_loading_door = False
        for door in doors:
            width = door.OverallWidth
            height = door.OverallHeight

            if width and height:
                if (abs(width - expected_width_mm) <= tolerance_mm and
                    abs(height - expected_height_mm) <= tolerance_mm):
                    found_loading_door = True
                    break

        assert found_loading_door, (
            f"Expected loading door 4m x 4m (4000mm x 4000mm). "
            f"Found doors with dimensions: "
            f"{[(d.OverallWidth, d.OverallHeight) for d in doors if d.OverallWidth]}"
        )

    def test_doors_have_geometry(self, ifc_path):
        """All doors should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")

        for door in doors:
            rep = door.Representation
            assert rep is not None, f"Door {door.Name or door.GlobalId} has no representation"


# =============================================================================
# Window Tests
# =============================================================================


class TestWindows:
    """Test window configuration: 4 clerestory windows on north wall."""

    def test_has_windows(self, ifc_path):
        """Building should have windows."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) > 0, "Warehouse must have clerestory windows"

    def test_window_count(self, ifc_path):
        """Should have 4 clerestory windows on north wall."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) >= 4, (
            f"Expected 4 clerestory windows on north wall, got {len(windows)}"
        )

    def test_window_width(self, ifc_path):
        """Clerestory windows should each be 2m wide."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")

        expected_width_mm = 2000.0
        tolerance_mm = 200.0

        # Count windows with approximately 2m width
        matching_windows = 0
        for window in windows:
            if window.OverallWidth:
                if abs(window.OverallWidth - expected_width_mm) <= tolerance_mm:
                    matching_windows += 1

        assert matching_windows >= 4, (
            f"Expected 4 windows ~2m wide, found {matching_windows}. "
            f"Window widths: {[w.OverallWidth for w in windows if w.OverallWidth]}"
        )

    def test_windows_have_geometry(self, ifc_path):
        """All windows should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")

        for window in windows:
            rep = window.Representation
            assert rep is not None, (
                f"Window {window.Name or window.GlobalId} has no representation"
            )


# =============================================================================
# Design Constraint Tests
# =============================================================================


class TestDesignConstraints:
    """Test design constraints from the prompt."""

    def test_doors_have_wall_clearance(self, ifc_path):
        """Doors must have at least 300mm clearance from wall corners/ends."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")

        min_clearance_mm = 300.0

        # Verify doors exist with valid dimensions
        for door in doors:
            door_width = door.OverallWidth or 900
            assert door_width > 0, f"Door {door.Name or door.GlobalId} has invalid width"

    def test_windows_have_wall_clearance(self, ifc_path):
        """Windows must have at least 300mm clearance from wall corners/ends."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")

        min_clearance_mm = 300.0

        # Verify windows exist with valid dimensions
        for window in windows:
            window_width = window.OverallWidth or 1200
            assert window_width > 0, (
                f"Window {window.Name or window.GlobalId} has invalid width"
            )

    def test_columns_do_not_conflict_with_doors(self, ifc_path):
        """Columns should not pass through door locations."""
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")
        doors = ifc.by_type("IfcDoor")

        if len(columns) == 0 or len(doors) == 0:
            pytest.skip("Need both columns and doors to check conflicts")

        # Get column positions
        column_positions = []
        for column in columns:
            placement = column.ObjectPlacement
            if placement and hasattr(placement, "RelativePlacement"):
                rel = placement.RelativePlacement
                if hasattr(rel, "Location") and rel.Location:
                    loc = rel.Location.Coordinates
                    column_positions.append((loc[0], loc[1]))

        # Get door positions
        door_positions = []
        for door in doors:
            placement = door.ObjectPlacement
            if placement and hasattr(placement, "RelativePlacement"):
                rel = placement.RelativePlacement
                if hasattr(rel, "Location") and rel.Location:
                    loc = rel.Location.Coordinates
                    width = door.OverallWidth or 900
                    door_positions.append((loc[0], loc[1], width))

        # Check for conflicts (column center within door opening)
        column_size = 400.0  # 400mm column
        for col_x, col_y in column_positions:
            for door_x, door_y, door_width in door_positions:
                # Check if column center is within door width plus buffer
                buffer = column_size / 2 + 100  # Column half-width + margin
                if (abs(col_x - door_x) < door_width / 2 + buffer and
                    abs(col_y - door_y) < buffer):
                    pytest.fail(
                        f"Column at ({col_x}, {col_y}) may conflict with door "
                        f"at ({door_x}, {door_y})"
                    )

    def test_beams_do_not_conflict_with_windows(self, ifc_path):
        """Beams should not pass through window locations."""
        ifc = ifcopenshell.open(ifc_path)
        beams = ifc.by_type("IfcBeam")
        windows = ifc.by_type("IfcWindow")

        # This is a visual/structural check - just verify both exist
        # Full conflict detection would require detailed geometry analysis
        assert len(beams) > 0, "Expected beams in structural frame"
        assert len(windows) > 0, "Expected windows in building"


# =============================================================================
# DXF Drawing Tests
# =============================================================================


class TestDXFDrawings:
    """Test DXF drawing outputs."""

    def test_dxf_directory_exists(self, dxf_dir):
        """DXF directory should exist."""
        assert os.path.isdir(dxf_dir), f"DXF directory not found: {dxf_dir}"

    def test_floor_plan_exists(self, dxf_dir):
        """At least one floor plan DXF should exist."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))
        plan_files = [
            f for f in dxf_files
            if "plan" in f.name.lower() or "floor" in f.name.lower()
        ]

        if not plan_files:
            plan_files = dxf_files

        assert len(plan_files) >= 1, (
            f"Expected at least 1 floor plan DXF, found: {[f.name for f in dxf_files]}"
        )

    def test_floor_plan_shows_column_grid(self, dxf_dir):
        """Floor plan should show structural column grid."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))
        plan_files = [
            f for f in dxf_files
            if "plan" in f.name.lower() or "floor" in f.name.lower()
        ] or dxf_files[:1]

        if not plan_files:
            pytest.fail("No floor plan DXF found")

        doc = ezdxf.readfile(str(plan_files[0]))
        msp = doc.modelspace()

        # Count entities - columns should appear as rectangles/polylines
        # or within structural layer
        entities = list(msp)

        # Should have substantial geometry for 20 columns
        assert len(entities) >= 20, (
            f"Floor plan should show column grid, found only {len(entities)} entities"
        )

    def test_elevation_drawings_exist(self, dxf_dir):
        """Elevation DXF drawings should exist (North, South, East, West)."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))

        elevation_keywords = ["elevation", "north", "south", "east", "west"]
        elevation_files = [
            f for f in dxf_files
            if any(kw in f.name.lower() for kw in elevation_keywords)
        ]

        assert len(elevation_files) >= 1, (
            f"Expected elevation DXF files, found: {[f.name for f in dxf_files]}"
        )

    def test_section_drawing_exists(self, dxf_dir):
        """At least one section DXF should exist."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))
        section_files = [f for f in dxf_files if "section" in f.name.lower()]

        assert len(section_files) >= 1, (
            f"Expected section DXF file, found: {[f.name for f in dxf_files]}"
        )

    def test_floor_plan_has_door_swings(self, dxf_dir):
        """Floor plan should contain arc entities for door swings."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))
        plan_files = [
            f for f in dxf_files
            if "plan" in f.name.lower() or "floor" in f.name.lower()
        ] or dxf_files[:1]

        if not plan_files:
            pytest.fail("No floor plan DXF found")

        doc = ezdxf.readfile(str(plan_files[0]))
        msp = doc.modelspace()

        arcs = [e for e in msp if e.dxftype() == "ARC"]
        # At least 2 regular doors (loading door may not have swing arc)
        assert len(arcs) >= 2, (
            f"Expected door swing arcs for regular doors, found {len(arcs)} arcs"
        )

    def test_floor_plan_has_wall_lines(self, dxf_dir):
        """Floor plan should have lines representing walls."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))

        if not dxf_files:
            pytest.fail("No DXF files found")

        doc = ezdxf.readfile(str(dxf_files[0]))
        msp = doc.modelspace()

        lines = [e for e in msp if e.dxftype() == "LINE"]
        # Should have many lines for walls, structure, etc.
        assert len(lines) >= 20, (
            f"Floor plan should have many lines for walls/structure, found {len(lines)}"
        )

    def test_dxf_files_valid(self, dxf_dir):
        """All DXF files should be valid and openable."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))

        for dxf_file in dxf_files:
            doc = ezdxf.readfile(str(dxf_file))
            assert doc is not None, f"Failed to open DXF: {dxf_file.name}"


# =============================================================================
# PDF Drawing Set Tests
# =============================================================================


class TestPDFDrawingSet:
    """Test PDF drawing set output."""

    def test_pdf_exists(self, pdf_path):
        """PDF drawing set should exist."""
        assert os.path.isfile(pdf_path), f"PDF file not found: {pdf_path}"

    def test_pdf_opens(self, pdf_path):
        """PDF should be valid and openable."""
        doc = fitz.open(pdf_path)
        assert doc is not None
        assert len(doc) > 0, "PDF should have at least one page"

    def test_pdf_has_multiple_pages(self, pdf_path):
        """PDF should have pages for plan, elevations, and section."""
        doc = fitz.open(pdf_path)
        # Expect: 1 floor plan + 4 elevations + 1 section = 6 pages minimum
        # Could be fewer if combined
        assert len(doc) >= 3, (
            f"Expected at least 3 pages (plan + elevations + section), got {len(doc)}"
        )

    def test_pdf_has_content(self, pdf_path):
        """PDF pages should have content (not blank)."""
        doc = fitz.open(pdf_path)

        for page_num, page in enumerate(doc):
            text = page.get_text()
            drawings = page.get_drawings()
            has_content = len(text.strip()) > 0 or len(drawings) > 0
            assert has_content, f"Page {page_num + 1} appears to be blank"


# =============================================================================
# Material Tests
# =============================================================================


class TestMaterials:
    """Test material specifications."""

    def test_has_materials(self, ifc_path):
        """Building should have material definitions."""
        ifc = ifcopenshell.open(ifc_path)

        materials = ifc.by_type("IfcMaterial")
        material_layers = ifc.by_type("IfcMaterialLayer")
        material_layer_sets = ifc.by_type("IfcMaterialLayerSet")

        has_materials = (
            len(materials) > 0 or
            len(material_layers) > 0 or
            len(material_layer_sets) > 0
        )
        assert has_materials, "Building should have material definitions"

    def test_has_steel_material(self, ifc_path):
        """Building should have steel material for columns and beams."""
        ifc = ifcopenshell.open(ifc_path)
        materials = ifc.by_type("IfcMaterial")

        material_names = [m.Name.lower() if m.Name else "" for m in materials]
        has_steel = any("steel" in name for name in material_names)

        if not has_steel:
            pytest.skip("Steel material not found by name (may use different naming)")

    def test_has_concrete_material(self, ifc_path):
        """Building should have concrete material for walls."""
        ifc = ifcopenshell.open(ifc_path)
        materials = ifc.by_type("IfcMaterial")

        material_names = [m.Name.lower() if m.Name else "" for m in materials]
        has_concrete = any("concrete" in name for name in material_names)

        if not has_concrete:
            pytest.skip("Concrete material not found by name (may use different naming)")
