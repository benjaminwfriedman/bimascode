"""Tests for Eval 05: Structural Grid Building

Requirements from prompt:

Dimensions: 24m x 18m warehouse-style building
Structural grid: 6m x 6m (4 bays x 3 bays)

Structure:
- Steel columns (400mm square) at each grid intersection
  - Grid is 5 columns x 4 columns = 20 columns total
- Main beams spanning in X direction (300mm x 500mm)
- Secondary beams in Y direction (200mm x 400mm)

Envelope:
- Concrete exterior walls (200mm)
- Large loading door on south wall (4m wide x 4m high)
- Regular doors on east and west walls
- Clerestory windows along north wall (4 windows, each 2m wide)

Output:
- IFC model
- DXF drawings (floor plan showing column grid, elevations, section)
- PDF drawing set
"""

import pytest
import ifcopenshell
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

    def test_has_site(self, ifc_path):
        """IFC should have at least one site."""
        ifc = ifcopenshell.open(ifc_path)
        sites = ifc.by_type("IfcSite")
        assert len(sites) >= 1, f"Expected at least 1 IfcSite, got {len(sites)}"

    def test_has_building(self, ifc_path):
        """IFC should have at least one building."""
        ifc = ifcopenshell.open(ifc_path)
        buildings = ifc.by_type("IfcBuilding")
        assert len(buildings) >= 1, f"Expected at least 1 IfcBuilding, got {len(buildings)}"

    def test_has_storey(self, ifc_path):
        """IFC should have at least one building storey."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) >= 1, f"Expected at least 1 IfcBuildingStorey, got {len(storeys)}"


# =============================================================================
# Column Tests (Structural Grid)
# =============================================================================


class TestColumns:
    """Test column count and placement for structural grid."""

    def test_has_columns(self, ifc_path):
        """Building should have columns."""
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")
        assert len(columns) >= 1, "Building should have columns for structural grid"

    def test_has_correct_column_count(self, ifc_path):
        """Structural grid 4 bays x 3 bays = 5 x 4 = 20 column intersections.

        Grid layout:
        - X direction: 0, 6m, 12m, 18m, 24m = 5 grid lines
        - Y direction: 0, 6m, 12m, 18m = 4 grid lines
        - Total intersections: 5 * 4 = 20 columns
        """
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")

        # Exact count should be 20
        assert len(columns) == 20, (
            f"Expected 20 columns (5x4 grid), got {len(columns)}"
        )

    def test_columns_have_geometry(self, ifc_path):
        """All columns should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")
        for column in columns:
            assert column.Representation is not None, (
                f"Column {column.Name} has no representation"
            )


# =============================================================================
# Beam Tests
# =============================================================================


class TestBeams:
    """Test beam framing for structural grid."""

    def test_has_beams(self, ifc_path):
        """Building should have beams."""
        ifc = ifcopenshell.open(ifc_path)
        beams = ifc.by_type("IfcBeam")
        assert len(beams) >= 1, "Building should have beams"

    def test_has_adequate_beam_count(self, ifc_path):
        """Structural grid should have beams in both directions.

        Main beams (X direction): 4 beams per row * 4 rows = 16 main beams
        Secondary beams (Y direction): 3 beams per column * 5 columns = 15 secondary beams
        Total expected: ~31 beams (may vary based on interpretation)

        Minimum: at least 10 beams for a substantial grid
        """
        ifc = ifcopenshell.open(ifc_path)
        beams = ifc.by_type("IfcBeam")

        # At minimum, expect beams at perimeter and some interior
        assert len(beams) >= 10, (
            f"Expected at least 10 beams for structural grid, got {len(beams)}"
        )

    def test_beams_have_geometry(self, ifc_path):
        """All beams should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        beams = ifc.by_type("IfcBeam")
        for beam in beams:
            assert beam.Representation is not None, (
                f"Beam {beam.Name} has no representation"
            )


# =============================================================================
# Wall Tests
# =============================================================================


class TestWalls:
    """Test exterior wall envelope."""

    def test_has_walls(self, ifc_path):
        """Building should have exterior walls."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 1, "Building should have walls"

    def test_has_four_exterior_walls(self, ifc_path):
        """Rectangular building should have 4 exterior walls."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 4, (
            f"Expected at least 4 walls for rectangular building, got {len(walls)}"
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
    """Test door placement including loading door."""

    def test_has_doors(self, ifc_path):
        """Building should have doors."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 1, "Building should have doors"

    def test_has_three_doors(self, ifc_path):
        """Prompt specifies:
        - Large loading door on south wall
        - Regular doors on east and west walls
        Total: 3 doors
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 3, (
            f"Expected at least 3 doors (loading + east + west), got {len(doors)}"
        )

    def test_doors_have_geometry(self, ifc_path):
        """All doors should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        for door in doors:
            assert door.Representation is not None, f"Door {door.Name} has no representation"

    def test_has_large_loading_door(self, ifc_path):
        """Should have a large loading door (4m x 4m = 4000mm x 4000mm)."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")

        large_door_found = False
        for door in doors:
            # Check if door has dimensions > 3m (3000mm)
            overall_width = door.OverallWidth if hasattr(door, "OverallWidth") else None
            overall_height = door.OverallHeight if hasattr(door, "OverallHeight") else None

            if overall_width is not None and overall_height is not None:
                # Check if dimensions are approximately 4m (could be mm or m)
                if overall_width >= 3000 and overall_height >= 3000:
                    large_door_found = True
                    break
                # If in meters
                elif overall_width >= 3 and overall_height >= 3:
                    large_door_found = True
                    break

            # Also check by name if dimensions not available
            if door.Name and any(kw in door.Name.lower() for kw in ["loading", "large", "industrial"]):
                large_door_found = True
                break

        # This is a soft check - if we can't verify by dimensions/name, check door count
        if not large_door_found:
            # At minimum, verify we have enough doors
            assert len(doors) >= 3, (
                f"Could not verify large loading door exists. Found {len(doors)} doors total."
            )


# =============================================================================
# Window Tests
# =============================================================================


class TestWindows:
    """Test clerestory windows on north wall."""

    def test_has_windows(self, ifc_path):
        """Building should have windows."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) >= 1, "Building should have windows"

    def test_has_four_clerestory_windows(self, ifc_path):
        """Prompt specifies 4 clerestory windows along north wall, each 2m wide."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) >= 4, (
            f"Expected at least 4 windows (clerestory on north wall), got {len(windows)}"
        )

    def test_windows_have_geometry(self, ifc_path):
        """All windows should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        for window in windows:
            assert window.Representation is not None, (
                f"Window {window.Name} has no representation"
            )


# =============================================================================
# Building Dimensions Tests
# =============================================================================


class TestBuildingDimensions:
    """Test that building matches specified dimensions (24m x 18m)."""

    def test_has_grid_elements(self, ifc_path):
        """Building should have grid elements for structural layout."""
        ifc = ifcopenshell.open(ifc_path)

        # Check for grid elements
        grids = ifc.by_type("IfcGrid")
        grid_axes = ifc.by_type("IfcGridAxis")

        # Grid elements are optional but useful for structural buildings
        # Don't fail if not present, just verify overall structure is correct
        if len(grids) == 0 and len(grid_axes) == 0:
            # Verify we at least have the structural elements
            columns = ifc.by_type("IfcColumn")
            assert len(columns) >= 20, (
                "No grid elements found. Expected at least 20 columns for 5x4 grid."
            )


# =============================================================================
# Material Tests
# =============================================================================


class TestMaterials:
    """Test material assignments (steel columns, concrete walls)."""

    def test_columns_have_material(self, ifc_path):
        """Columns should have material associations (steel specified)."""
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")

        if not columns:
            pytest.skip("No columns found")

        columns_with_material = 0
        for column in columns:
            if hasattr(column, "HasAssociations"):
                for rel in column.HasAssociations:
                    if rel.is_a("IfcRelAssociatesMaterial"):
                        columns_with_material += 1
                        break

        assert columns_with_material >= 1, "At least some columns should have material associations"

    def test_walls_have_material(self, ifc_path):
        """Walls should have material associations (concrete specified)."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        if not walls:
            pytest.skip("No walls found")

        walls_with_material = 0
        for wall in walls:
            if hasattr(wall, "HasAssociations"):
                for rel in wall.HasAssociations:
                    if rel.is_a("IfcRelAssociatesMaterial"):
                        walls_with_material += 1
                        break

        assert walls_with_material >= 1, "At least some walls should have material associations"


# =============================================================================
# Structural Consistency Tests
# =============================================================================


class TestStructuralConsistency:
    """Test consistency between structural elements."""

    def test_columns_and_beams_connected(self, ifc_path):
        """Both columns and beams should exist for a framed structure."""
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")
        beams = ifc.by_type("IfcBeam")

        assert len(columns) >= 1, "Structural building needs columns"
        assert len(beams) >= 1, "Structural building needs beams"

    def test_structural_element_ratio(self, ifc_path):
        """Beams should roughly match column grid pattern.

        For 5x4 grid (20 columns):
        - Main beams: 4 per row * 4 rows = 16
        - Secondary beams: 3 per column * 5 columns = 15
        Ratio: ~1.5 beams per column (rough estimate)
        """
        ifc = ifcopenshell.open(ifc_path)
        columns = ifc.by_type("IfcColumn")
        beams = ifc.by_type("IfcBeam")

        if len(columns) == 0:
            pytest.skip("No columns to compare ratio")

        # Beams should be at least half the column count
        # (very loose check - just ensuring beams exist in proportion)
        ratio = len(beams) / len(columns)
        assert ratio >= 0.5, (
            f"Expected reasonable beam-to-column ratio, got {ratio:.2f} "
            f"({len(beams)} beams / {len(columns)} columns)"
        )


# =============================================================================
# DXF Drawing Tests
# =============================================================================


class TestDXFDrawings:
    """Test DXF drawing outputs."""

    def test_dxf_directory_exists(self, dxf_dir):
        """DXF output directory should exist."""
        assert dxf_dir.exists(), f"DXF directory not found: {dxf_dir}"

    def test_has_dxf_files(self, dxf_dir):
        """Should have DXF files."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(all_dxf_files) >= 1, "No DXF files found"

    def test_has_floor_plan(self, dxf_dir):
        """Should have floor plan DXF showing column grid."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(all_dxf_files) >= 1, "No DXF files found"

        plan_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["plan", "floor", "level", "ground"])
        ]

        assert len(plan_files) >= 1, (
            f"Expected floor plan DXF. Found files: {[f.name for f in all_dxf_files]}"
        )

    def test_has_elevations(self, dxf_dir):
        """Should have elevation DXF files."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))

        elevation_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["elevation", "elev", "north", "south", "east", "west"])
        ]

        assert len(elevation_files) >= 1, (
            f"Expected elevation DXFs. Found files: {[f.name for f in all_dxf_files]}"
        )

    def test_has_section(self, dxf_dir):
        """Should have at least one section DXF."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))

        section_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["section", "sect"])
        ]

        assert len(section_files) >= 1, (
            f"Expected section DXF. Found files: {[f.name for f in all_dxf_files]}"
        )

    def test_dxf_files_open(self, dxf_dir):
        """DXF files should open without errors."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(all_dxf_files) >= 1, "No DXF files found"

        for dxf_file in all_dxf_files:
            doc = ezdxf.readfile(str(dxf_file))
            assert doc is not None, f"Failed to open {dxf_file.name}"

    def test_dxf_files_have_entities(self, dxf_dir):
        """DXF files should contain drawing entities."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(all_dxf_files) >= 1, "No DXF files found"

        for dxf_file in all_dxf_files:
            doc = ezdxf.readfile(str(dxf_file))
            msp = doc.modelspace()
            entities = list(msp)
            if len(entities) > 0:
                return

        pytest.fail("No DXF files contain drawing entities")

    def test_floor_plan_shows_columns(self, dxf_dir):
        """Floor plan should show column grid (circles or rectangles for columns)."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))

        plan_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["plan", "floor", "level", "ground"])
        ]

        if not plan_files:
            plan_files = all_dxf_files[:1]  # Take first file as probable plan

        if not plan_files:
            pytest.skip("No floor plan files found")

        # Check for column representations
        # Columns typically shown as circles, rectangles, or small squares
        column_indicators = 0
        for plan_file in plan_files:
            doc = ezdxf.readfile(str(plan_file))
            msp = doc.modelspace()
            for entity in msp:
                # Circles often represent columns in plan
                if entity.dxftype() == "CIRCLE":
                    column_indicators += 1
                # Closed polylines (squares/rectangles) may also be columns
                elif entity.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
                    if hasattr(entity, "is_closed") and entity.is_closed:
                        column_indicators += 1

        # Expect at least some column indicators (20 columns = should see ~20 circles/squares)
        # Use 10 as minimum since some may be combined or represented differently
        assert column_indicators >= 10, (
            f"Expected column representations in floor plan, found {column_indicators} "
            "circles/closed polylines"
        )

    def test_floor_plan_has_wall_lines(self, dxf_dir):
        """Floor plan should have lines representing walls."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))

        plan_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["plan", "floor", "level"])
        ]

        if not plan_files:
            plan_files = all_dxf_files[:1]

        if not plan_files:
            pytest.skip("No floor plan files found")

        total_lines = 0
        for plan_file in plan_files:
            doc = ezdxf.readfile(str(plan_file))
            msp = doc.modelspace()
            for entity in msp:
                if entity.dxftype() == "LINE":
                    total_lines += 1

        # Warehouse with 4 walls should have substantial line count
        assert total_lines >= 20, (
            f"Floor plan should have lines for walls. Found {total_lines}"
        )


# =============================================================================
# PDF Drawing Set Tests
# =============================================================================


class TestPDFDrawingSet:
    """Test PDF drawing set output."""

    def test_pdf_exists(self, pdf_path):
        """PDF drawing set should exist."""
        if not pdf_path.exists():
            # Check alternative naming
            alt_path = pdf_path.parent / "drawing_set.pdf"
            assert alt_path.exists() or pdf_path.exists(), (
                f"PDF not found at {pdf_path} or {alt_path}"
            )

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

    def test_pdf_has_drawing_sheets(self, pdf_path):
        """PDF should have pages for plan, elevations, and section.

        Expected minimum:
        - 1 floor plan (showing column grid)
        - 4 elevations (N, S, E, W) - may be combined
        - 1 section
        Total: ~3-6 pages
        """
        if not pdf_path.exists():
            alt_path = pdf_path.parent / "drawing_set.pdf"
            if alt_path.exists():
                pdf_path = alt_path

        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()

        # At minimum: plan + some elevations + section = 3 pages
        assert page_count >= 3, (
            f"Expected at least 3 pages (plan + elevations + section), got {page_count}"
        )

    def test_pdf_contains_text(self, pdf_path):
        """PDF should contain title block or label text."""
        if not pdf_path.exists():
            alt_path = pdf_path.parent / "drawing_set.pdf"
            if alt_path.exists():
                pdf_path = alt_path

        doc = fitz.open(str(pdf_path))
        all_text = "\n".join(page.get_text() for page in doc)
        doc.close()

        assert len(all_text.strip()) > 0, "PDF appears to have no text content"


# =============================================================================
# Summary Tests
# =============================================================================


class TestOverallBuilding:
    """Summary tests for the complete building."""

    def test_building_has_all_structural_elements(self, ifc_path):
        """Building should have all required structural elements."""
        ifc = ifcopenshell.open(ifc_path)

        columns = ifc.by_type("IfcColumn")
        beams = ifc.by_type("IfcBeam")
        walls = ifc.by_type("IfcWall")
        doors = ifc.by_type("IfcDoor")
        windows = ifc.by_type("IfcWindow")

        assert len(columns) == 20, f"Expected 20 columns (5x4 grid), got {len(columns)}"
        assert len(beams) >= 10, f"Expected at least 10 beams, got {len(beams)}"
        assert len(walls) >= 4, f"Expected at least 4 walls, got {len(walls)}"
        assert len(doors) >= 3, f"Expected at least 3 doors, got {len(doors)}"
        assert len(windows) >= 4, f"Expected at least 4 windows, got {len(windows)}"

    def test_building_is_warehouse_scale(self, ifc_path):
        """Building should be approximately 24m x 18m scale.

        This is a soft check based on element counts and proportions.
        """
        ifc = ifcopenshell.open(ifc_path)

        # 24m x 18m warehouse at 6m grid = 4 x 3 bays
        # Should have substantial structural system
        columns = ifc.by_type("IfcColumn")
        beams = ifc.by_type("IfcBeam")

        # 20 columns indicates proper grid sizing
        assert len(columns) >= 16, (
            f"Column count ({len(columns)}) suggests grid doesn't match 24m x 18m / 6m spacing"
        )

        # Should have beams connecting the grid
        assert len(beams) >= 8, (
            f"Beam count ({len(beams)}) is too low for a proper framed structure"
        )
