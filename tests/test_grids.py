"""
Unit tests for Grid Lines.
"""

import pytest

from bimascode.spatial.building import Building
from bimascode.spatial.grid import GridLine, create_orthogonal_grid
from bimascode.spatial.level import Level
from bimascode.utils.units import Length


class TestGridLine:
    """Test GridLine class."""

    def test_creation(self):
        """Test creating a grid line."""
        building = Building("Test")
        grid = GridLine(building, "A", (0, 0), (0, 12000))

        assert grid.label == "A"
        assert grid.start_point_mm == (0.0, 0.0)
        assert grid.end_point_mm == (0.0, 12000.0)

    def test_auto_registers_with_building(self):
        """Test that grid automatically registers with building."""
        building = Building("Test")
        grid = GridLine(building, "A", (0, 0), (0, 12000))

        assert len(building.grids) == 1
        assert building.grids[0] == grid

    def test_length_calculation(self):
        """Test grid line length calculation."""
        building = Building("Test")
        grid = GridLine(building, "A", (0, 0), (0, 12000))

        assert grid.length.mm == 12000

    def test_vertical_detection(self):
        """Test vertical grid line detection."""
        building = Building("Test")
        vertical = GridLine(building, "A", (0, 0), (0, 12000))
        horizontal = GridLine(building, "1", (0, 0), (12000, 0))

        assert vertical.is_vertical() is True
        assert vertical.is_horizontal() is False
        assert horizontal.is_vertical() is False
        assert horizontal.is_horizontal() is True

    def test_horizontal_detection(self):
        """Test horizontal grid line detection."""
        building = Building("Test")
        grid = GridLine(building, "1", (0, 0), (12000, 0))

        assert grid.is_horizontal() is True
        assert grid.is_vertical() is False

    def test_multiple_grids(self):
        """Test adding multiple grid lines."""
        building = Building("Test")
        GridLine(building, "A", (0, 0), (0, 12000))
        GridLine(building, "B", (6000, 0), (6000, 12000))
        GridLine(building, "1", (0, 0), (12000, 0))

        assert len(building.grids) == 3


class TestOrthogonalGrid:
    """Test orthogonal grid helper function."""

    def test_create_simple_grid(self):
        """Test creating a simple 3x3 grid."""
        building = Building("Test")

        grids = create_orthogonal_grid(
            building,
            x_grid_labels=["A", "B", "C"],
            x_grid_positions=[0, 6000, 12000],
            y_grid_labels=["1", "2", "3"],
            y_grid_positions=[0, 6000, 12000],
            x_extent=(0, 12000),
            y_extent=(0, 12000),
        )

        # 3 vertical + 3 horizontal = 6 total
        assert len(grids) == 6
        assert len(building.grids) == 6

    def test_grid_labels(self):
        """Test that grid labels are correct."""
        building = Building("Test")

        create_orthogonal_grid(
            building,
            x_grid_labels=["A", "B"],
            x_grid_positions=[0, 6000],
            y_grid_labels=["1", "2"],
            y_grid_positions=[0, 6000],
            x_extent=(0, 6000),
            y_extent=(0, 6000),
        )

        labels = [g.label for g in building.grids]
        assert "A" in labels
        assert "B" in labels
        assert "1" in labels
        assert "2" in labels

    def test_grid_orientation(self):
        """Test that grids have correct orientation."""
        building = Building("Test")

        create_orthogonal_grid(
            building,
            x_grid_labels=["A", "B"],
            x_grid_positions=[0, 6000],
            y_grid_labels=["1", "2"],
            y_grid_positions=[0, 6000],
            x_extent=(0, 6000),
            y_extent=(0, 6000),
        )

        # Find vertical grids (should have same X coordinate for start and end)
        vertical_grids = [g for g in building.grids if g.is_vertical()]
        horizontal_grids = [g for g in building.grids if g.is_horizontal()]

        assert len(vertical_grids) == 2  # A, B
        assert len(horizontal_grids) == 2  # 1, 2


class TestGridIFCExport:
    """Test grid IFC export."""

    def test_grids_export_to_ifc(self):
        """Test that grids are exported to IFC."""
        import tempfile
        from pathlib import Path

        building = Building("Test")
        Level(building, "Ground", Length(0, "mm"))

        GridLine(building, "A", (0, 0), (0, 12000))
        GridLine(building, "B", (6000, 0), (6000, 12000))
        GridLine(building, "1", (0, 0), (12000, 0))

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_grids.ifc"
            building.export_ifc(str(filepath))

            # Verify with ifcopenshell
            try:
                import ifcopenshell

                ifc_file = ifcopenshell.open(str(filepath))

                grids = ifc_file.by_type("IfcGrid")
                assert len(grids) >= 1

                # Check for grid axes
                grid = grids[0]
                if grid.UAxes:
                    assert len(grid.UAxes) == 2  # A, B (vertical)
                if grid.VAxes:
                    assert len(grid.VAxes) == 1  # 1 (horizontal)

            except ImportError:
                pytest.skip("ifcopenshell not available")

    def test_grids_roundtrip(self):
        """Test grid import/export round-trip."""
        import tempfile
        from pathlib import Path

        # Create building with grids
        original = Building("Test")
        Level(original, "Ground", Length(0, "mm"))

        create_orthogonal_grid(
            original,
            x_grid_labels=["A", "B", "C"],
            x_grid_positions=[0, 6000, 12000],
            y_grid_labels=["1", "2"],
            y_grid_positions=[0, 6000],
            x_extent=(0, 12000),
            y_extent=(0, 6000),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "roundtrip.ifc"
            original.export_ifc(str(filepath))

            # Import back
            imported = Building.from_ifc(str(filepath))

            # Verify grids preserved
            assert len(imported.grids) == len(original.grids)

            # Verify grid labels preserved
            orig_labels = sorted([g.label for g in original.grids])
            imp_labels = sorted([g.label for g in imported.grids])
            assert orig_labels == imp_labels
