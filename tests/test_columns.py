"""
Tests for structural columns and column types.
"""

import pytest

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.structure.column import StructuralColumn
from bimascode.structure.column_type import (
    ColumnType,
    create_rectangular_column_type,
    create_square_column_type,
)
from bimascode.structure.profile import (
    RectangularProfile,
    create_square_profile,
)
from bimascode.utils.materials import MaterialLibrary


class TestRectangularProfile:
    """Tests for RectangularProfile class."""

    def test_profile_creation(self):
        """Test creating a rectangular profile."""
        profile = RectangularProfile(300, 400)

        assert profile.width == 300.0
        assert profile.height == 400.0
        assert profile.name == "Rectangular_300x400"

    def test_profile_area(self):
        """Test profile area calculation."""
        profile = RectangularProfile(300, 400)

        assert profile.area == 120000.0  # 300 * 400

    def test_profile_moment_of_inertia(self):
        """Test profile moment of inertia calculation."""
        profile = RectangularProfile(300, 400)

        # I_x = (width * height^3) / 12 = (300 * 400^3) / 12
        expected_ix = (300 * 400**3) / 12
        assert abs(profile.moment_of_inertia_x - expected_ix) < 1.0

    def test_square_profile_constructor(self):
        """Test square profile convenience constructor."""
        profile = create_square_profile(300)

        assert profile.width == 300.0
        assert profile.height == 300.0

    def test_profile_to_build123d(self):
        """Test profile conversion to build123d."""
        profile = RectangularProfile(300, 400)
        face = profile.to_build123d()

        assert face is not None


class TestColumnType:
    """Tests for ColumnType class."""

    def test_column_type_creation(self):
        """Test creating a column type."""
        profile = RectangularProfile(400, 400)
        column_type = ColumnType("Square Column", profile)

        assert column_type.name == "Square Column"
        assert column_type.width == 400.0
        assert column_type.depth == 400.0
        assert column_type.profile == profile

    def test_column_type_area(self):
        """Test column type cross-sectional area."""
        profile = RectangularProfile(400, 400)
        column_type = ColumnType("Square Column", profile)

        assert column_type.area == 160000.0  # 400 * 400

    def test_rectangular_column_type_constructor(self):
        """Test rectangular column type convenience constructor."""
        column_type = create_rectangular_column_type("Rect Column", 300, 400)

        assert column_type.width == 300.0
        assert column_type.depth == 400.0

    def test_square_column_type_constructor(self):
        """Test square column type convenience constructor."""
        column_type = create_square_column_type("Square Column", 400)

        assert column_type.width == 400.0
        assert column_type.depth == 400.0

    def test_column_type_with_material(self):
        """Test column type with material."""
        profile = RectangularProfile(400, 400)
        concrete = MaterialLibrary.concrete()
        column_type = ColumnType("Concrete Column", profile, material=concrete)

        assert column_type.material == concrete


class TestStructuralColumn:
    """Tests for StructuralColumn class."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with level for column testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        return building, level

    @pytest.fixture
    def setup_column_type(self):
        """Create a column type for testing."""
        profile = RectangularProfile(400, 400)
        return ColumnType("Square Column", profile)

    def test_column_creation(self, setup_building, setup_column_type):
        """Test creating a column."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(column_type, level, position=(1000, 1000), height=3000.0)

        assert column.type == column_type
        assert column.level == level
        assert column.position == (1000, 1000)
        assert column.height == 3000.0

    def test_column_default_height(self, setup_building, setup_column_type):
        """Test column with default height."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(column_type, level, position=(1000, 1000))

        assert column.height == 3000.0  # Default height

    def test_column_dimensions_from_type(self, setup_building, setup_column_type):
        """Test that column dimensions come from type."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(column_type, level, position=(1000, 1000), height=3000.0)

        assert column.width == 400.0
        assert column.depth == 400.0

    def test_column_volume(self, setup_building, setup_column_type):
        """Test column volume calculation."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(column_type, level, position=(1000, 1000), height=3000.0)

        # Volume = area * height = 160000 * 3000 = 480,000,000 mm³
        assert abs(column.volume - 480_000_000.0) < 1.0
        # 0.48 m³
        assert abs(column.volume_m3 - 0.48) < 0.01

    def test_column_base_center(self, setup_building, setup_column_type):
        """Test column base center calculation."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(column_type, level, position=(1000, 2000), height=3000.0)

        base = column.get_base_center()
        assert base == (1000, 2000, 0)  # At level elevation

    def test_column_top_center(self, setup_building, setup_column_type):
        """Test column top center calculation."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(column_type, level, position=(1000, 2000), height=3000.0)

        top = column.get_top_center()
        assert top == (1000, 2000, 3000)

    def test_column_rotation(self, setup_building, setup_column_type):
        """Test column rotation."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(
            column_type, level, position=(1000, 1000), height=3000.0, rotation=45.0
        )

        assert column.rotation == 45.0

    def test_column_registered_with_level(self, setup_building, setup_column_type):
        """Test that column is registered with its level."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(column_type, level, position=(1000, 1000), height=3000.0)

        assert column in level.elements

    def test_column_geometry(self, setup_building, setup_column_type):
        """Test column geometry creation."""
        building, level = setup_building
        column_type = setup_column_type

        column = StructuralColumn(column_type, level, position=(1000, 1000), height=3000.0)

        geom = column.get_geometry()
        assert geom is not None


class TestColumnIFC:
    """Tests for column IFC export."""

    @pytest.fixture
    def setup_building_with_column(self):
        """Create a building with a column."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        profile = RectangularProfile(400, 400)
        column_type = ColumnType("Square Column", profile)
        column = StructuralColumn(column_type, level, position=(1000, 1000), height=3000.0)

        return building, level, column

    def test_column_ifc_export(self, setup_building_with_column, tmp_path):
        """Test column IFC export."""
        building, level, column = setup_building_with_column

        output_file = tmp_path / "test_column.ifc"
        building.export_ifc(str(output_file))

        assert output_file.exists()
