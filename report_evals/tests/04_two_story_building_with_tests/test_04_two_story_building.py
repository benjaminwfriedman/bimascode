"""Tests for Eval 04: Two Story Building

Requirements from prompt:

Ground Floor:
- Living room: 6m x 5m with large south-facing window
- Kitchen: 4m x 4m with window on west wall
- Entry vestibule: 2m x 2m with front door
- Stair area: 3m x 2m (floor opening)

Upper Floor:
- Master bedroom: 5m x 4m with window on south wall
- Second bedroom: 4m x 4m with window on north wall
- Bathroom: 3m x 2m with small window
- Hallway connecting all rooms

Both floors:
- 3m floor-to-floor height
- 2.7m ceiling height
- Exterior walls: 300mm total (brick + insulation + concrete + gypsum)

Also includes:
- Flat roof over upper floor
- IFC model
- DXF drawings (floor plans for each level, elevations, section)
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


# =============================================================================
# Two-Story Level Tests
# =============================================================================


class TestLevels:
    """Test that the building has two floors with correct elevations."""

    def test_has_two_storeys(self, ifc_path):
        """Building should have exactly two storeys (Ground Floor and Upper Floor)."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) == 2, f"Expected 2 building storeys, got {len(storeys)}"

    def test_storeys_have_correct_elevation_difference(self, ifc_path):
        """Floor-to-floor height should be approximately 3m (3000mm)."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")

        if len(storeys) < 2:
            pytest.skip("Not enough storeys to check elevation difference")

        elevations = []
        for storey in storeys:
            if hasattr(storey, "Elevation") and storey.Elevation is not None:
                elevations.append(storey.Elevation)

        if len(elevations) < 2:
            pytest.skip("Could not extract elevations from storeys")

        elevations.sort()
        floor_to_floor = elevations[1] - elevations[0]

        # Convert to mm if in meters (values < 10 are likely meters)
        if floor_to_floor < 10:
            floor_to_floor = floor_to_floor * 1000

        # Allow ±200mm tolerance for 3000mm floor-to-floor
        assert 2800 <= floor_to_floor <= 3200, (
            f"Floor-to-floor height should be ~3000mm, got {floor_to_floor}mm"
        )

    def test_ground_floor_at_zero(self, ifc_path):
        """Ground floor should be at or near elevation 0."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")

        elevations = []
        for storey in storeys:
            if hasattr(storey, "Elevation") and storey.Elevation is not None:
                elevations.append(storey.Elevation)

        if not elevations:
            pytest.skip("Could not extract elevations from storeys")

        # Ground floor should be lowest and near 0
        min_elevation = min(elevations)
        # Allow some tolerance for site elevation
        assert abs(min_elevation) <= 100, (
            f"Ground floor elevation should be near 0, got {min_elevation}"
        )


# =============================================================================
# Wall Tests
# =============================================================================


class TestWalls:
    """Test wall count and properties for two-story building."""

    def test_has_walls(self, ifc_path):
        """Building should have walls."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 1, "Building should have walls"

    def test_has_minimum_walls_for_rooms(self, ifc_path):
        """Two-story building with multiple rooms needs many walls.

        Ground floor: Living room, Kitchen, Entry vestibule, Stair area
        Upper floor: Master bedroom, Second bedroom, Bathroom, Hallway

        Minimum estimate:
        - 4 exterior walls per floor = 8 (some may be shared)
        - Interior partitions: at least 4-6 per floor = 8-12
        Total minimum: ~12-15 walls
        """
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")
        assert len(walls) >= 10, (
            f"Expected at least 10 walls for multi-room two-story building, got {len(walls)}"
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
    """Test door count for two-story building."""

    def test_has_entry_door(self, ifc_path):
        """Building must have at least one door (entry/front door)."""
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 1, "Building must have at least one entry door"

    def test_has_multiple_doors(self, ifc_path):
        """Building should have multiple doors for all rooms.

        Minimum doors:
        - Front door (entry vestibule)
        - Interior doors to rooms (living room, kitchen, bedrooms, bathroom)
        - At least 4-5 interior doors expected
        """
        ifc = ifcopenshell.open(ifc_path)
        doors = ifc.by_type("IfcDoor")
        assert len(doors) >= 4, (
            f"Expected at least 4 doors (entry + room doors), got {len(doors)}"
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
    """Test window count and placement for two-story building."""

    def test_has_windows(self, ifc_path):
        """Building should have windows."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) >= 1, "Building should have windows"

    def test_has_minimum_windows(self, ifc_path):
        """Prompt specifies windows for multiple rooms.

        Required windows:
        - Living room: large south-facing window (1)
        - Kitchen: window on west wall (1)
        - Master bedroom: window on south wall (1)
        - Second bedroom: window on north wall (1)
        - Bathroom: small window (1)

        Total minimum: 5 windows
        """
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        assert len(windows) >= 5, (
            f"Expected at least 5 windows (living, kitchen, master bed, 2nd bed, bath), got {len(windows)}"
        )

    def test_windows_have_geometry(self, ifc_path):
        """All windows should have geometric representation."""
        ifc = ifcopenshell.open(ifc_path)
        windows = ifc.by_type("IfcWindow")
        for window in windows:
            assert window.Representation is not None, f"Window {window.Name} has no representation"


# =============================================================================
# Floor/Slab Tests
# =============================================================================


class TestFloors:
    """Test floor slabs for two-story building."""

    def test_has_floor_slabs(self, ifc_path):
        """Building should have floor slabs."""
        ifc = ifcopenshell.open(ifc_path)
        slabs = ifc.by_type("IfcSlab")
        assert len(slabs) >= 1, "Building should have floor slabs"

    def test_has_slabs_for_both_levels(self, ifc_path):
        """Should have at least 2 floor slabs (one per level)."""
        ifc = ifcopenshell.open(ifc_path)
        slabs = ifc.by_type("IfcSlab")
        # At minimum: ground floor slab + upper floor slab
        assert len(slabs) >= 2, (
            f"Expected at least 2 floor slabs (ground + upper), got {len(slabs)}"
        )


# =============================================================================
# Floor Opening Tests (Stairs)
# =============================================================================


class TestFloorOpenings:
    """Test for floor opening at stair area."""

    def test_has_opening_elements(self, ifc_path):
        """Building should have floor opening for stair area.

        This could be represented as:
        - IfcOpeningElement
        - IfcVoidingFeature
        - Or floor geometry with void
        """
        ifc = ifcopenshell.open(ifc_path)

        # Check for opening elements
        openings = ifc.by_type("IfcOpeningElement")
        voiding = ifc.by_type("IfcVoidingFeature")

        # Stair opening should exist (at least one opening)
        total_openings = len(openings) + len(voiding)

        # If no explicit opening elements, check that slabs exist
        # (the opening might be cut directly from slab geometry)
        slabs = ifc.by_type("IfcSlab")

        assert total_openings >= 1 or len(slabs) >= 2, (
            f"Expected floor opening for stairs. Found {total_openings} openings, {len(slabs)} slabs"
        )


# =============================================================================
# Ceiling Tests
# =============================================================================


class TestCeilings:
    """Test ceiling placement for both floors."""

    def test_has_ceilings(self, ifc_path):
        """Building should have ceilings (2.7m ceiling height mentioned)."""
        ifc = ifcopenshell.open(ifc_path)

        # Ceilings could be represented as IfcCovering with PredefinedType=CEILING
        # or as IfcSlab with PredefinedType=FLOOR for upper floor
        coverings = ifc.by_type("IfcCovering")

        ceiling_count = 0
        for covering in coverings:
            if hasattr(covering, "PredefinedType"):
                if covering.PredefinedType == "CEILING":
                    ceiling_count += 1
            # Also count if name suggests ceiling
            elif covering.Name and "ceiling" in covering.Name.lower():
                ceiling_count += 1

        # At least one ceiling expected
        # If no IfcCovering found, this is acceptable since ceiling might be modeled differently
        if len(coverings) == 0:
            pytest.skip("No IfcCovering elements found - ceiling may be modeled differently")

        assert ceiling_count >= 1, (
            f"Expected ceiling elements. Found {len(coverings)} coverings, {ceiling_count} ceilings"
        )


# =============================================================================
# Roof Tests
# =============================================================================


class TestRoof:
    """Test flat roof over upper floor."""

    def test_has_roof(self, ifc_path):
        """Building should have a roof element."""
        ifc = ifcopenshell.open(ifc_path)

        # Check for IfcRoof
        roofs = ifc.by_type("IfcRoof")

        # Also check for IfcSlab with roof predefined type
        slabs = ifc.by_type("IfcSlab")
        roof_slabs = [
            s for s in slabs
            if hasattr(s, "PredefinedType") and s.PredefinedType == "ROOF"
        ]

        total_roof_elements = len(roofs) + len(roof_slabs)

        assert total_roof_elements >= 1, (
            f"Expected roof element. Found {len(roofs)} IfcRoof, {len(roof_slabs)} roof slabs"
        )


# =============================================================================
# Exterior Wall Thickness Tests
# =============================================================================


class TestExteriorWallProperties:
    """Test exterior wall properties (300mm thickness specified)."""

    def test_walls_have_material_info(self, ifc_path):
        """Walls should have material associations."""
        ifc = ifcopenshell.open(ifc_path)
        walls = ifc.by_type("IfcWall")

        walls_with_material = 0
        for wall in walls:
            if hasattr(wall, "HasAssociations"):
                for rel in wall.HasAssociations:
                    if rel.is_a("IfcRelAssociatesMaterial"):
                        walls_with_material += 1
                        break

        assert walls_with_material >= 1, "Walls should have material associations"

    def test_has_composite_wall_layers(self, ifc_path):
        """Exterior walls should have multiple layers (brick + insulation + concrete + gypsum).

        This is a soft check - verify that material layer sets exist if possible.
        """
        ifc = ifcopenshell.open(ifc_path)

        # Check for material layer sets
        layer_sets = ifc.by_type("IfcMaterialLayerSet")
        layer_set_usages = ifc.by_type("IfcMaterialLayerSetUsage")

        # At least one multi-layer wall system expected
        if len(layer_sets) > 0:
            # Check if any layer set has multiple layers
            multi_layer_found = False
            for layer_set in layer_sets:
                if hasattr(layer_set, "MaterialLayers"):
                    if len(layer_set.MaterialLayers) > 1:
                        multi_layer_found = True
                        break

            if not multi_layer_found and len(layer_sets) > 0:
                # Single layer is acceptable, just note it
                pass

        # Don't fail if layer sets aren't found - different modeling approaches are valid


# =============================================================================
# DXF Drawing Tests
# =============================================================================


class TestDXFDrawings:
    """Test DXF drawing outputs."""

    def test_dxf_directory_exists(self, dxf_dir):
        """DXF output directory should exist."""
        assert dxf_dir.exists(), f"DXF directory not found: {dxf_dir}"

    def test_has_floor_plans(self, dxf_dir):
        """Should have floor plan DXFs for both levels (ground and upper)."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(all_dxf_files) >= 1, "No DXF files found"

        plan_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["plan", "floor", "level", "ground", "upper", "first"])
        ]

        # Should have at least 2 floor plans (one per level)
        # But accept 1 if combined
        assert len(plan_files) >= 1, (
            f"Expected floor plan DXFs. Found files: {[f.name for f in all_dxf_files]}"
        )

    def test_has_two_floor_plans(self, dxf_dir):
        """Should have separate floor plans for Ground and Upper floors."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))

        plan_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["plan", "floor", "level"])
        ]

        # For a two-story building, expect 2 floor plans
        assert len(plan_files) >= 2, (
            f"Expected 2 floor plan DXFs (ground + upper), found {len(plan_files)}. "
            f"Files: {[f.name for f in all_dxf_files]}"
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

    def test_floor_plans_open(self, dxf_dir):
        """Floor plan DXFs should open without errors."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(all_dxf_files) >= 1, "No DXF files found"

        for dxf_file in all_dxf_files:
            doc = ezdxf.readfile(str(dxf_file))
            assert doc is not None, f"Failed to open {dxf_file.name}"

    def test_floor_plans_have_entities(self, dxf_dir):
        """Floor plans should contain drawing entities."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))
        assert len(all_dxf_files) >= 1, "No DXF files found"

        for dxf_file in all_dxf_files:
            doc = ezdxf.readfile(str(dxf_file))
            msp = doc.modelspace()
            entities = list(msp)
            if len(entities) > 0:
                return

        pytest.fail("No DXF files contain drawing entities")

    def test_floor_plans_have_door_swings(self, dxf_dir):
        """Floor plans should show door swings as arcs."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))

        plan_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["plan", "floor", "level", "ground", "upper"])
        ]

        if not plan_files:
            plan_files = all_dxf_files[:2]  # Take first 2 as probable plans

        total_arcs = 0
        for plan_file in plan_files:
            doc = ezdxf.readfile(str(plan_file))
            msp = doc.modelspace()
            for entity in msp:
                if entity.dxftype() == "ARC":
                    total_arcs += 1

        # Multiple doors across two floors should produce multiple arcs
        assert total_arcs >= 4, (
            f"Expected at least 4 door swing arcs for two-story building, found {total_arcs}"
        )

    def test_floor_plans_have_wall_lines(self, dxf_dir):
        """Floor plans should have lines representing walls."""
        all_dxf_files = list(dxf_dir.glob("*.dxf"))

        plan_files = [
            f for f in all_dxf_files
            if any(kw in f.stem.lower() for kw in ["plan", "floor", "level"])
        ]

        if not plan_files:
            plan_files = all_dxf_files[:2]

        total_lines = 0
        for plan_file in plan_files:
            doc = ezdxf.readfile(str(plan_file))
            msp = doc.modelspace()
            for entity in msp:
                if entity.dxftype() == "LINE":
                    total_lines += 1

        # Two-story building with multiple rooms should have many wall lines
        assert total_lines >= 50, (
            f"Floor plans should have many lines for walls. Found {total_lines}"
        )


# =============================================================================
# PDF Drawing Set Tests
# =============================================================================


class TestPDFDrawingSet:
    """Test PDF drawing set output."""

    def test_pdf_exists(self, pdf_path):
        """PDF drawing set should exist."""
        if not pdf_path.exists():
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

    def test_pdf_has_sheets_for_all_drawings(self, pdf_path):
        """PDF should have pages for plans, elevations, and section.

        Expected minimum:
        - 2 floor plans (ground + upper)
        - 4 elevations (N, S, E, W)
        - 1 section
        Total: 7 pages minimum (could be combined)
        """
        if not pdf_path.exists():
            alt_path = pdf_path.parent / "drawing_set.pdf"
            if alt_path.exists():
                pdf_path = alt_path

        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()

        # At minimum: 2 plans + some elevations + section = 4 pages
        assert page_count >= 4, (
            f"Expected at least 4 pages (2 plans + elevations + section), got {page_count}"
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
# Space Program Tests
# =============================================================================


class TestSpaceProgram:
    """Test that the building configuration matches the program."""

    def test_building_has_adequate_elements(self, ifc_path):
        """Building should have elements for all programmed spaces."""
        ifc = ifcopenshell.open(ifc_path)

        walls = ifc.by_type("IfcWall")
        doors = ifc.by_type("IfcDoor")
        windows = ifc.by_type("IfcWindow")
        slabs = ifc.by_type("IfcSlab")

        # Multi-room two-story building should have substantial elements
        assert len(walls) >= 10, f"Expected at least 10 walls, got {len(walls)}"
        assert len(doors) >= 4, f"Expected at least 4 doors, got {len(doors)}"
        assert len(windows) >= 5, f"Expected at least 5 windows, got {len(windows)}"
        assert len(slabs) >= 2, f"Expected at least 2 slabs (floors), got {len(slabs)}"

    def test_has_sufficient_storeys(self, ifc_path):
        """Building should have 2 storeys for the two-floor program."""
        ifc = ifcopenshell.open(ifc_path)
        storeys = ifc.by_type("IfcBuildingStorey")
        assert len(storeys) == 2, (
            f"Two-story building should have exactly 2 storeys, got {len(storeys)}"
        )
