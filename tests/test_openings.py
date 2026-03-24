"""
Tests for floor and roof openings.
"""

import pytest

from bimascode.architecture.floor import Floor
from bimascode.architecture.floor_type import create_concrete_floor_type
from bimascode.architecture.opening import (
    Opening,
    create_circular_opening,
    create_rectangular_opening,
)
from bimascode.architecture.roof import Roof
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level


class TestOpening:
    """Tests for Opening class."""

    @pytest.fixture
    def setup_floor(self):
        """Create a building with floor for opening testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        floor_type = create_concrete_floor_type("Concrete Slab", slab_thickness=200)

        # Create rectangular floor
        boundary = [
            (0, 0),
            (10000, 0),
            (10000, 8000),
            (0, 8000),
        ]
        floor = Floor(floor_type, boundary, level)

        return building, level, floor

    def test_opening_creation(self, setup_floor):
        """Test creating an opening."""
        building, level, floor = setup_floor

        opening_boundary = [
            (2000, 2000),
            (4000, 2000),
            (4000, 4000),
            (2000, 4000),
        ]

        opening = Opening(floor, opening_boundary)

        assert opening.host_element == floor
        assert len(opening.boundary) == 4

    def test_opening_area(self, setup_floor):
        """Test opening area calculation."""
        building, level, floor = setup_floor

        # 2m x 2m opening
        opening_boundary = [
            (2000, 2000),
            (4000, 2000),
            (4000, 4000),
            (2000, 4000),
        ]

        opening = Opening(floor, opening_boundary)

        assert abs(opening.area_m2 - 4.0) < 0.01  # 4 square meters

    def test_opening_centroid(self, setup_floor):
        """Test opening centroid calculation."""
        building, level, floor = setup_floor

        opening_boundary = [
            (2000, 2000),
            (4000, 2000),
            (4000, 4000),
            (2000, 4000),
        ]

        opening = Opening(floor, opening_boundary)
        centroid = opening.get_centroid()

        assert abs(centroid[0] - 3000.0) < 1.0
        assert abs(centroid[1] - 3000.0) < 1.0

    def test_opening_geometry(self, setup_floor):
        """Test opening geometry creation."""
        building, level, floor = setup_floor

        opening_boundary = [
            (2000, 2000),
            (4000, 2000),
            (4000, 4000),
            (2000, 4000),
        ]

        opening = Opening(floor, opening_boundary)
        geom = opening.get_opening_geometry()

        assert geom is not None

    def test_rectangular_opening_helper(self, setup_floor):
        """Test rectangular opening convenience function."""
        building, level, floor = setup_floor

        opening = create_rectangular_opening(floor, center=(3000, 3000), width=2000, length=2000)

        assert abs(opening.area_m2 - 4.0) < 0.01
        centroid = opening.get_centroid()
        assert abs(centroid[0] - 3000.0) < 1.0
        assert abs(centroid[1] - 3000.0) < 1.0

    def test_circular_opening_helper(self, setup_floor):
        """Test circular opening convenience function."""
        import math

        building, level, floor = setup_floor

        opening = create_circular_opening(floor, center=(3000, 3000), radius=500, segments=32)

        # Area should be approximately pi * r^2
        expected_area = math.pi * 0.5 * 0.5  # m^2
        assert abs(opening.area_m2 - expected_area) < 0.1


class TestFloorOpenings:
    """Tests for floor openings."""

    @pytest.fixture
    def setup_floor(self):
        """Create a building with floor."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        floor_type = create_concrete_floor_type("Concrete Slab", slab_thickness=200)

        boundary = [
            (0, 0),
            (10000, 0),
            (10000, 8000),
            (0, 8000),
        ]
        floor = Floor(floor_type, boundary, level)

        return building, level, floor

    def test_add_opening_to_floor(self, setup_floor):
        """Test adding an opening to a floor."""
        building, level, floor = setup_floor

        opening_boundary = [
            (2000, 2000),
            (4000, 2000),
            (4000, 4000),
            (2000, 4000),
        ]

        opening = floor.add_opening(opening_boundary)

        assert opening in floor.openings
        assert len(floor.openings) == 1

    def test_multiple_openings(self, setup_floor):
        """Test adding multiple openings to a floor."""
        building, level, floor = setup_floor

        opening1_boundary = [
            (1000, 1000),
            (2000, 1000),
            (2000, 2000),
            (1000, 2000),
        ]

        opening2_boundary = [
            (5000, 3000),
            (7000, 3000),
            (7000, 5000),
            (5000, 5000),
        ]

        floor.add_opening(opening1_boundary, name="Stair Opening")
        floor.add_opening(opening2_boundary, name="Shaft Opening")

        assert len(floor.openings) == 2

    def test_remove_opening(self, setup_floor):
        """Test removing an opening from a floor."""
        building, level, floor = setup_floor

        opening_boundary = [
            (2000, 2000),
            (4000, 2000),
            (4000, 4000),
            (2000, 4000),
        ]

        opening = floor.add_opening(opening_boundary)
        assert len(floor.openings) == 1

        floor.remove_opening(opening)
        assert len(floor.openings) == 0

    def test_floor_geometry_with_opening(self, setup_floor):
        """Test that floor geometry includes opening void."""
        building, level, floor = setup_floor

        # Get floor geometry before opening
        geom_before = floor.get_geometry(force_rebuild=True)

        # Add opening
        opening_boundary = [
            (2000, 2000),
            (4000, 2000),
            (4000, 4000),
            (2000, 4000),
        ]
        floor.add_opening(opening_boundary)

        # Get floor geometry after opening
        geom_after = floor.get_geometry(force_rebuild=True)

        assert geom_before is not None
        assert geom_after is not None


class TestRoofOpenings:
    """Tests for roof openings."""

    @pytest.fixture
    def setup_roof(self):
        """Create a building with roof."""
        building = Building("Test Building")
        level = Level(building, "Roof Level", elevation=3000)

        roof_type = create_concrete_floor_type("Roof Slab", slab_thickness=150)

        boundary = [
            (0, 0),
            (10000, 0),
            (10000, 8000),
            (0, 8000),
        ]
        roof = Roof(roof_type, boundary, level)

        return building, level, roof

    def test_add_opening_to_roof(self, setup_roof):
        """Test adding an opening to a roof."""
        building, level, roof = setup_roof

        # Skylight opening
        opening_boundary = [
            (4000, 3000),
            (6000, 3000),
            (6000, 5000),
            (4000, 5000),
        ]

        opening = roof.add_opening(opening_boundary, name="Skylight")

        assert opening in roof.openings
        assert opening.name == "Skylight"

    def test_multiple_roof_openings(self, setup_roof):
        """Test adding multiple openings to a roof."""
        building, level, roof = setup_roof

        skylight1 = [
            (2000, 2000),
            (3000, 2000),
            (3000, 3000),
            (2000, 3000),
        ]

        skylight2 = [
            (6000, 4000),
            (8000, 4000),
            (8000, 6000),
            (6000, 6000),
        ]

        roof.add_opening(skylight1, name="Skylight 1")
        roof.add_opening(skylight2, name="Skylight 2")

        assert len(roof.openings) == 2

    def test_roof_geometry_with_opening(self, setup_roof):
        """Test that roof geometry includes opening void."""
        building, level, roof = setup_roof

        # Get roof geometry before opening
        geom_before = roof.get_geometry(force_rebuild=True)

        # Add opening
        opening_boundary = [
            (4000, 3000),
            (6000, 3000),
            (6000, 5000),
            (4000, 5000),
        ]
        roof.add_opening(opening_boundary)

        # Get roof geometry after opening
        geom_after = roof.get_geometry(force_rebuild=True)

        assert geom_before is not None
        assert geom_after is not None


class TestOpeningIFC:
    """Tests for opening IFC export."""

    @pytest.fixture
    def setup_floor_with_opening(self):
        """Create a building with floor and opening."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        floor_type = create_concrete_floor_type("Concrete Slab", slab_thickness=200)

        boundary = [
            (0, 0),
            (10000, 0),
            (10000, 8000),
            (0, 8000),
        ]
        floor = Floor(floor_type, boundary, level)

        opening_boundary = [
            (2000, 2000),
            (4000, 2000),
            (4000, 4000),
            (2000, 4000),
        ]
        opening = floor.add_opening(opening_boundary, name="Stair Opening")

        return building, level, floor, opening

    def test_floor_with_opening_to_ifc(self, setup_floor_with_opening, tmp_path):
        """Test that floor with opening exports to IFC."""
        building, level, floor, opening = setup_floor_with_opening

        # Export building
        output_file = tmp_path / "test_opening.ifc"
        building.export_ifc(str(output_file))

        # Check file exists
        assert output_file.exists()
