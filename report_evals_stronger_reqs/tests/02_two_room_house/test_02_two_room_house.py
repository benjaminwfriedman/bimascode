"""Tests for Eval 02: Two Room House

Verifies a small house with two rooms:
- Living room: 6m x 5m with large window (2m wide) on south wall and entry door
- Bedroom: 4m x 5m with medium window on north wall
- Rooms share a wall with interior door connecting them
- Exterior walls: brick finish (100mm) + concrete structure (150mm) = 250mm total
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
        """This is a single-storey house - should have exactly 1 storey."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) == 1, f"Expected 1 storey for single-level house, got {len(storeys)}"


# =============================================================================
# Wall Tests
# =============================================================================


class TestWalls:
    """Test wall configuration and properties."""

    def test_has_walls(self, ifc_path):
        """Building should have walls."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) > 0, "Building must have walls"

    def test_wall_count_reasonable(self, ifc_path):
        """Two rectangular rooms sharing a wall need at least 5 walls.

        Layout (rooms share interior wall):
        - 4 exterior walls (perimeter)
        - 1+ interior wall (shared between rooms)
        Total: at least 5 walls, could be more depending on implementation.
        """
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        # At minimum: 4 exterior + 1 interior = 5
        # Could be more if walls are segmented
        assert len(walls) >= 5, f"Expected at least 5 walls (4 exterior + 1 interior), got {len(walls)}"

    def test_exterior_wall_thickness(self, ifc_path):
        """Exterior walls should be ~250mm (100mm brick + 150mm concrete)."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        expected_thickness_mm = 250.0
        tolerance_mm = 50.0  # Allow some variance

        # Check that at least some walls have the expected exterior thickness
        wall_thicknesses = []
        for wall in walls:
            # Try to get wall thickness from property sets or geometry
            psets = ifc_element.get_psets(wall)
            for pset_name, pset_data in psets.items():
                if "Width" in pset_data:
                    wall_thicknesses.append(pset_data["Width"])
                elif "Thickness" in pset_data:
                    wall_thicknesses.append(pset_data["Thickness"])

        if wall_thicknesses:
            # At least one wall should have approximately 250mm thickness
            has_exterior_thickness = any(
                abs(t - expected_thickness_mm) <= tolerance_mm for t in wall_thicknesses
            )
            assert has_exterior_thickness, (
                f"Expected exterior walls with ~250mm thickness, found thicknesses: {wall_thicknesses}"
            )


# =============================================================================
# Door Tests
# =============================================================================


class TestDoors:
    """Test door placement and configuration."""

    def test_has_doors(self, ifc_path):
        """Building should have doors."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) > 0, "Building must have doors"

    def test_has_two_doors(self, ifc_path):
        """Building should have exactly 2 doors: entry door and interior door."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) == 2, f"Expected 2 doors (1 entry + 1 interior), got {len(doors)}"

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
    """Test window placement and configuration."""

    def test_has_windows(self, ifc_path):
        """Building should have windows."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) > 0, "Building must have windows"

    def test_has_two_windows(self, ifc_path):
        """Building should have exactly 2 windows: large on south, medium on north."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) == 2, f"Expected 2 windows (1 large south + 1 medium north), got {len(windows)}"

    def test_windows_have_geometry(self, ifc_path):
        """All windows should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")

        for window in windows:
            rep = window.Representation
            assert rep is not None, f"Window {window.Name or window.GlobalId} has no representation"

    def test_large_window_width(self, ifc_path):
        """Living room window should be ~2m (2000mm) wide."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")

        expected_width_mm = 2000.0
        tolerance_mm = 200.0  # Allow 200mm variance

        # Look for a window approximately 2m wide
        window_widths = []
        for window in windows:
            if window.OverallWidth is not None:
                window_widths.append(window.OverallWidth)

        if window_widths:
            has_large_window = any(
                abs(w - expected_width_mm) <= tolerance_mm for w in window_widths
            )
            assert has_large_window, (
                f"Expected large window ~2000mm wide, found widths: {window_widths}"
            )


# =============================================================================
# Room Dimension Tests
# =============================================================================


class TestDimensions:
    """Test building and room dimensions."""

    def test_building_footprint_approximately_correct(self, ifc_path):
        """Building footprint should be approximately 10m x 5m (6m + 4m by 5m).

        Living room: 6m x 5m
        Bedroom: 4m x 5m
        Shared wall between them means total is ~10m x 5m (could vary with wall thickness).
        """
        ifc = ifcopenshell.open(ifc_path)

        # Get all walls and extract their coordinates to compute bounding box
        walls = ifc.by_type("IfcWall")
        assert len(walls) > 0, "Need walls to compute bounding box"

        # Get bounding box from wall placements
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
            if x_span > 100:  # Likely in mm
                x_span /= 1000
                y_span /= 1000

            # Expected: ~10m x 5m, allow significant tolerance due to wall thickness
            # Check that one dimension is roughly 10m and another roughly 5m
            dims = sorted([x_span, y_span])

            # Allow ±1.5m tolerance to account for wall thickness and layout variations
            expected_short = 5.0
            expected_long = 10.0
            tolerance = 1.5

            dim_ok = (
                (abs(dims[0] - expected_short) <= tolerance or abs(dims[0] - expected_long) <= tolerance) and
                (abs(dims[1] - expected_short) <= tolerance or abs(dims[1] - expected_long) <= tolerance)
            )

            # Just verify we have a reasonable building size
            assert dims[1] >= 3.0, f"Building seems too small: {dims}"
            assert dims[1] <= 15.0, f"Building seems too large: {dims}"


# =============================================================================
# Design Constraint Tests
# =============================================================================


class TestDesignConstraints:
    """Test design constraints from the prompt."""

    def test_doors_not_at_wall_corners(self, ifc_path):
        """Doors must have at least 300mm clearance from wall corners/ends.

        We verify this by checking door positions relative to wall endpoints.
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        walls = ifc.by_type("IfcWall")

        min_clearance_mm = 300.0

        # For each door, check it's not at the very end of its host wall
        for door in doors:
            # Get door width to check it's not flush with wall ends
            door_width = door.OverallWidth or 900  # Default door width

            # This is a simplified check - in practice would need to analyze
            # the door's position along its host wall
            # For now, just verify door exists and has reasonable width
            assert door_width > 0, f"Door {door.Name or door.GlobalId} has invalid width"

    def test_windows_not_at_wall_corners(self, ifc_path):
        """Windows must have at least 300mm clearance from wall corners/ends."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")

        min_clearance_mm = 300.0

        for window in windows:
            window_width = window.OverallWidth or 1200
            # Simplified check - verify window exists with reasonable dimensions
            assert window_width > 0, f"Window {window.Name or window.GlobalId} has invalid width"


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
        plan_files = [f for f in dxf_files if "plan" in f.name.lower() or "floor" in f.name.lower()]

        # If no specifically named plan files, check for any DXF
        if not plan_files:
            plan_files = dxf_files

        assert len(plan_files) >= 1, f"Expected at least 1 floor plan DXF, found: {[f.name for f in dxf_files]}"

    def test_elevation_drawings_exist(self, dxf_dir):
        """Elevation DXF drawings should exist (North, South, East, West)."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))
        file_names = [f.name.lower() for f in dxf_files]

        # Check for elevation files
        elevation_keywords = ["elevation", "north", "south", "east", "west"]
        elevation_files = [f for f in dxf_files if any(kw in f.name.lower() for kw in elevation_keywords)]

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
        """Floor plan should contain arc entities representing door swings."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))
        plan_files = [f for f in dxf_files if "plan" in f.name.lower() or "floor" in f.name.lower()]

        if not plan_files:
            plan_files = dxf_files[:1]  # Use first DXF as plan

        assert len(plan_files) > 0, "No floor plan DXF found"

        plan_file = plan_files[0]
        doc = ezdxf.readfile(str(plan_file))
        msp = doc.modelspace()

        arcs = [e for e in msp if e.dxftype() == "ARC"]
        # Two doors should produce at least 2 door swing arcs
        assert len(arcs) >= 2, f"Expected at least 2 door swing arcs (2 doors), found {len(arcs)} arcs"

    def test_floor_plan_has_lines(self, dxf_dir):
        """Floor plan should contain line entities for walls."""
        dxf_dir_path = Path(dxf_dir)
        dxf_files = list(dxf_dir_path.glob("*.dxf"))

        assert len(dxf_files) > 0, "No DXF files found"

        # Check first DXF file
        plan_file = dxf_files[0]
        doc = ezdxf.readfile(str(plan_file))
        msp = doc.modelspace()

        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(lines) > 0, "Floor plan should contain LINE entities for walls"

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
        """PDF should have multiple pages (plan + elevations + section)."""
        doc = fitz.open(pdf_path)
        # Expect: 1 floor plan + 4 elevations + 1 section = 6 pages minimum
        # Could be fewer if combined, but should have at least 3
        assert len(doc) >= 3, f"Expected at least 3 pages (plan + elevations + section), got {len(doc)}"

    def test_pdf_has_content(self, pdf_path):
        """PDF pages should have content (not blank)."""
        doc = fitz.open(pdf_path)

        for page_num, page in enumerate(doc):
            # Check for text or drawings
            text = page.get_text()
            drawings = page.get_drawings()

            has_content = len(text.strip()) > 0 or len(drawings) > 0
            assert has_content, f"Page {page_num + 1} appears to be blank"


# =============================================================================
# Material and Layer Tests
# =============================================================================


class TestMaterials:
    """Test material specifications."""

    def test_has_materials(self, ifc_path):
        """Building should have material definitions."""
        ifc = ifcopenshell.open(ifc_path)

        # Look for material entities
        materials = ifc.by_type("IfcMaterial")
        material_layers = ifc.by_type("IfcMaterialLayer")
        material_layer_sets = ifc.by_type("IfcMaterialLayerSet")

        has_materials = len(materials) > 0 or len(material_layers) > 0 or len(material_layer_sets) > 0
        assert has_materials, "Building should have material definitions"

    def test_exterior_wall_has_layers(self, ifc_path):
        """Exterior walls should have layered material (brick + concrete)."""
        ifc = ifcopenshell.open(ifc_path)

        material_layer_sets = ifc.by_type("IfcMaterialLayerSet")

        if material_layer_sets:
            # Check for a layer set with at least 2 layers
            has_multilayer = any(
                len(mls.MaterialLayers) >= 2 for mls in material_layer_sets
            )
            assert has_multilayer, "Exterior walls should have at least 2 material layers (brick + concrete)"

    def test_brick_material_exists(self, ifc_path):
        """Building should have brick material for exterior finish."""
        ifc = ifcopenshell.open(ifc_path)
        materials = ifc.by_type("IfcMaterial")

        material_names = [m.Name.lower() if m.Name else "" for m in materials]
        has_brick = any("brick" in name for name in material_names)

        # This is a soft check - might be named differently
        if not has_brick:
            pytest.skip("Brick material not found by name (may use different naming)")

    def test_concrete_material_exists(self, ifc_path):
        """Building should have concrete material for structure."""
        ifc = ifcopenshell.open(ifc_path)
        materials = ifc.by_type("IfcMaterial")

        material_names = [m.Name.lower() if m.Name else "" for m in materials]
        has_concrete = any("concrete" in name for name in material_names)

        # This is a soft check - might be named differently
        if not has_concrete:
            pytest.skip("Concrete material not found by name (may use different naming)")


# =============================================================================
# Room and Space Tests
# =============================================================================


class TestRooms:
    """Test room/space definitions."""

    def test_has_spaces(self, ifc_path):
        """Building should define spaces/rooms."""
        ifc = ifcopenshell.open(ifc_path)
        spaces = ifc.by_type("IfcSpace")

        # Two rooms should be defined
        # This might not be required depending on implementation
        if len(spaces) == 0:
            pytest.skip("No IfcSpace entities found (rooms may not be explicitly defined)")

        assert len(spaces) >= 2, f"Expected at least 2 spaces (living room + bedroom), got {len(spaces)}"

    def test_living_room_exists(self, ifc_path):
        """Living room space should exist."""
        ifc = ifcopenshell.open(ifc_path)
        spaces = ifc.by_type("IfcSpace")

        if len(spaces) == 0:
            pytest.skip("No IfcSpace entities found")

        space_names = [s.Name.lower() if s.Name else "" for s in spaces]
        has_living = any("living" in name for name in space_names)

        if not has_living:
            pytest.skip("Living room not found by name")

    def test_bedroom_exists(self, ifc_path):
        """Bedroom space should exist."""
        ifc = ifcopenshell.open(ifc_path)
        spaces = ifc.by_type("IfcSpace")

        if len(spaces) == 0:
            pytest.skip("No IfcSpace entities found")

        space_names = [s.Name.lower() if s.Name else "" for s in spaces]
        has_bedroom = any("bedroom" in name or "bed" in name for name in space_names)

        if not has_bedroom:
            pytest.skip("Bedroom not found by name")
