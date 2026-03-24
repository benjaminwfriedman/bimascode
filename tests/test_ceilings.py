"""
Tests for ceilings and ceiling types.
"""

import pytest

from bimascode.architecture.ceiling import Ceiling
from bimascode.architecture.ceiling_type import (
    CeilingType,
    create_gypsum_ceiling_type,
    create_suspended_ceiling_type,
)
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level


class TestCeilingType:
    """Tests for CeilingType class."""

    def test_ceiling_type_creation(self):
        """Test creating a ceiling type with default parameters."""
        ceiling_type = CeilingType("Standard Ceiling")

        assert ceiling_type.name == "Standard Ceiling"
        assert ceiling_type.thickness == 15.0

    def test_ceiling_type_custom_thickness(self):
        """Test creating a ceiling type with custom thickness."""
        ceiling_type = CeilingType("Thick Ceiling", thickness=25.0)

        assert ceiling_type.thickness == 25.0

    def test_gypsum_ceiling_type_constructor(self):
        """Test the gypsum ceiling type convenience constructor."""
        ceiling_type = create_gypsum_ceiling_type("Gypsum Ceiling")

        assert ceiling_type.name == "Gypsum Ceiling"
        assert ceiling_type.thickness == 15.0

    def test_suspended_ceiling_type_constructor(self):
        """Test the suspended ceiling type convenience constructor."""
        ceiling_type = create_suspended_ceiling_type("Drop Ceiling", thickness=20.0)

        assert ceiling_type.name == "Drop Ceiling"
        assert ceiling_type.thickness == 20.0


class TestCeiling:
    """Tests for Ceiling class."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with level for ceiling testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        return building, level

    @pytest.fixture
    def setup_ceiling_type(self):
        """Create a ceiling type for testing."""
        return CeilingType("Standard Ceiling", thickness=15.0)

    def test_ceiling_creation(self, setup_building, setup_ceiling_type):
        """Test creating a ceiling."""
        building, level = setup_building
        ceiling_type = setup_ceiling_type

        ceiling = Ceiling(
            ceiling_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            height=2700.0,
        )

        assert ceiling.type == ceiling_type
        assert ceiling.level == level
        assert ceiling.height == 2700.0

    def test_ceiling_thickness_from_type(self, setup_building, setup_ceiling_type):
        """Test that ceiling thickness comes from type."""
        building, level = setup_building
        ceiling_type = setup_ceiling_type

        ceiling = Ceiling(
            ceiling_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            height=2700.0,
        )

        assert ceiling.thickness == 15.0

    def test_ceiling_area(self, setup_building, setup_ceiling_type):
        """Test ceiling area calculation."""
        building, level = setup_building
        ceiling_type = setup_ceiling_type

        # 5m x 4m ceiling = 20 m²
        ceiling = Ceiling(
            ceiling_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            height=2700.0,
        )

        assert abs(ceiling.area_m2 - 20.0) < 0.01

    def test_ceiling_elevation(self, setup_building, setup_ceiling_type):
        """Test ceiling elevation calculation."""
        building, level = setup_building
        ceiling_type = setup_ceiling_type

        ceiling = Ceiling(
            ceiling_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            height=2700.0,
        )

        # Bottom of ceiling should be at 2700 - 15 = 2685mm
        assert ceiling.elevation == 2685.0
        # Top of ceiling should be at 2700mm
        assert ceiling.top_elevation == 2700.0

    def test_ceiling_centroid(self, setup_building, setup_ceiling_type):
        """Test ceiling centroid calculation."""
        building, level = setup_building
        ceiling_type = setup_ceiling_type

        ceiling = Ceiling(
            ceiling_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            height=2700.0,
        )

        cx, cy = ceiling.get_centroid()
        assert abs(cx - 2500.0) < 1.0
        assert abs(cy - 2000.0) < 1.0

    def test_ceiling_registered_with_level(self, setup_building, setup_ceiling_type):
        """Test that ceiling is registered with its level."""
        building, level = setup_building
        ceiling_type = setup_ceiling_type

        ceiling = Ceiling(
            ceiling_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            height=2700.0,
        )

        assert ceiling in level.elements

    def test_ceiling_geometry(self, setup_building, setup_ceiling_type):
        """Test ceiling geometry creation."""
        building, level = setup_building
        ceiling_type = setup_ceiling_type

        ceiling = Ceiling(
            ceiling_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            height=2700.0,
        )

        geom = ceiling.get_geometry()
        assert geom is not None


class TestCeilingIFC:
    """Tests for ceiling IFC export."""

    @pytest.fixture
    def setup_building_with_ceiling(self):
        """Create a building with a ceiling."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        ceiling_type = CeilingType("Standard Ceiling", thickness=15.0)
        ceiling = Ceiling(
            ceiling_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            height=2700.0,
        )

        return building, level, ceiling

    def test_ceiling_ifc_export(self, setup_building_with_ceiling, tmp_path):
        """Test ceiling IFC export."""
        building, level, ceiling = setup_building_with_ceiling

        output_file = tmp_path / "test_ceiling.ifc"
        building.export_ifc(str(output_file))

        assert output_file.exists()
