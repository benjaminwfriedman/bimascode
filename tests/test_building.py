"""
Unit tests for Building and Level classes.
"""

import tempfile
from pathlib import Path

import pytest

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, UnitSystem


class TestBuilding:
    """Test Building class."""

    def test_creation(self):
        """Test creating a building."""
        building = Building("Test Building")
        assert building.name == "Test Building"
        assert building.unit_system == UnitSystem.METRIC

    def test_creation_with_address(self):
        """Test creating a building with address."""
        building = Building("Test Building", address="123 Main St")
        assert building.address == "123 Main St"

    def test_unit_system_metric(self):
        """Test metric unit system."""
        building = Building("Test", unit_system="metric")
        assert building.unit_system == UnitSystem.METRIC

    def test_unit_system_imperial(self):
        """Test imperial unit system."""
        building = Building("Test", unit_system="imperial")
        assert building.unit_system == UnitSystem.IMPERIAL

    def test_guid_generation(self):
        """Test that building gets a GUID."""
        building = Building("Test")
        assert building.guid is not None
        assert len(building.guid) > 0

    def test_guid_persistence(self):
        """Test that GUID persists."""
        building = Building("Test")
        guid1 = building.guid
        guid2 = building.guid
        assert guid1 == guid2

    def test_guid_uniqueness(self):
        """Test that different buildings get different GUIDs."""
        b1 = Building("Test 1")
        b2 = Building("Test 2")
        assert b1.guid != b2.guid

    def test_levels_empty_initially(self):
        """Test that building starts with no levels."""
        building = Building("Test")
        assert len(building.levels) == 0

    def test_get_level_not_found(self):
        """Test getting non-existent level."""
        building = Building("Test")
        assert building.get_level("Nonexistent") is None


class TestLevel:
    """Test Level class."""

    def test_creation(self):
        """Test creating a level."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", Length(0, "mm"))

        assert level.name == "Ground Floor"
        assert level.elevation_mm == 0
        assert level.building == building

    def test_creation_with_elevation(self):
        """Test creating a level with elevation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", Length(4000, "mm"))

        assert level.elevation_mm == 4000
        assert level.elevation.m == 4

    def test_level_auto_registers(self):
        """Test that level automatically registers with building."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", Length(0, "mm"))

        assert len(building.levels) == 1
        assert building.levels[0] == level

    def test_multiple_levels(self):
        """Test adding multiple levels."""
        building = Building("Test Building")
        Level(building, "Ground", Length(0, "mm"))
        level_1 = Level(building, "First", Length(4000, "mm"))
        Level(building, "Second", Length(8000, "mm"))

        assert len(building.levels) == 3
        assert building.get_level("First") == level_1

    def test_set_elevation(self):
        """Test changing level elevation."""
        building = Building("Test Building")
        level = Level(building, "Ground", Length(0, "mm"))

        level.set_elevation(Length(100, "mm"))
        assert level.elevation_mm == 100

    def test_level_with_description(self):
        """Test creating level with description."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", Length(0, "mm"), description="Main entrance level")

        assert level.description == "Main entrance level"


class TestIFCExport:
    """Test IFC export functionality."""

    def test_export_basic(self):
        """Test basic IFC export."""
        building = Building("Test Building")
        Level(building, "Ground", Length(0, "mm"))

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.ifc"
            building.export_ifc(str(filepath))

            assert filepath.exists()
            assert filepath.stat().st_size > 0

    def test_export_multiple_levels(self):
        """Test exporting building with multiple levels."""
        building = Building("Test Building", address="123 Test St")
        Level(building, "Ground", Length(0, "mm"))
        Level(building, "First", Length(4000, "mm"))
        Level(building, "Second", Length(8000, "mm"))

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.ifc"
            building.export_ifc(str(filepath))

            assert filepath.exists()

            # Verify with ifcopenshell
            try:
                import ifcopenshell

                ifc_file = ifcopenshell.open(str(filepath))

                buildings = ifc_file.by_type("IfcBuilding")
                assert len(buildings) == 1
                assert buildings[0].Name == "Test Building"

                storeys = ifc_file.by_type("IfcBuildingStorey")
                assert len(storeys) == 3

            except ImportError:
                pytest.skip("ifcopenshell not available")


class TestIFCImport:
    """Test IFC import functionality."""

    def test_import_roundtrip(self):
        """Test importing an exported building."""
        # Create and export
        original = Building("Original Building", address="123 Export St")
        Level(original, "Ground", Length(0, "mm"))
        Level(original, "First", Length(4000, "mm"))

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "roundtrip.ifc"
            original.export_ifc(str(filepath))

            # Import
            imported = Building.from_ifc(str(filepath))

            # Verify
            assert imported.name == original.name
            assert imported.address == original.address
            assert imported.guid == original.guid
            assert len(imported.levels) == len(original.levels)

            # Verify levels
            for orig_level, imp_level in zip(original.levels, imported.levels, strict=False):
                assert orig_level.name == imp_level.name
                assert abs(orig_level.elevation_mm - imp_level.elevation_mm) < 0.01

    def test_import_nonexistent_file(self):
        """Test importing non-existent file."""
        with pytest.raises(FileNotFoundError):
            Building.from_ifc("nonexistent.ifc")
