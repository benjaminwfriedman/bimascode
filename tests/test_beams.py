"""
Tests for structural beams and beam types.
"""

import pytest

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.structure.beam import Beam
from bimascode.structure.beam_type import (
    BeamType,
    create_rectangular_beam_type,
    create_standard_beam_type,
)
from bimascode.structure.profile import RectangularProfile
from bimascode.utils.materials import MaterialLibrary


class TestBeamType:
    """Tests for BeamType class."""

    def test_beam_type_creation(self):
        """Test creating a beam type."""
        profile = RectangularProfile(300, 600)
        beam_type = BeamType("Standard Beam", profile)

        assert beam_type.name == "Standard Beam"
        assert beam_type.width == 300.0
        assert beam_type.height == 600.0
        assert beam_type.profile == profile

    def test_beam_type_area(self):
        """Test beam type cross-sectional area."""
        profile = RectangularProfile(300, 600)
        beam_type = BeamType("Standard Beam", profile)

        assert beam_type.area == 180000.0  # 300 * 600

    def test_rectangular_beam_type_constructor(self):
        """Test rectangular beam type convenience constructor."""
        beam_type = create_rectangular_beam_type("Rect Beam", 300, 600)

        assert beam_type.width == 300.0
        assert beam_type.height == 600.0

    def test_standard_beam_type_constructor(self):
        """Test standard beam type constructor with size string."""
        beam_type = create_standard_beam_type("Standard", size="300x600")

        assert beam_type.width == 300.0
        assert beam_type.height == 600.0

    def test_beam_type_with_material(self):
        """Test beam type with material."""
        profile = RectangularProfile(300, 600)
        concrete = MaterialLibrary.concrete()
        beam_type = BeamType("Concrete Beam", profile, material=concrete)

        assert beam_type.material == concrete


class TestBeam:
    """Tests for Beam class."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with level for beam testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        return building, level

    @pytest.fixture
    def setup_beam_type(self):
        """Create a beam type for testing."""
        profile = RectangularProfile(300, 600)
        return BeamType("Standard Beam", profile)

    def test_beam_creation(self, setup_building, setup_beam_type):
        """Test creating a beam."""
        building, level = setup_building
        beam_type = setup_beam_type

        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))

        assert beam.type == beam_type
        assert beam.level == level
        assert beam.start_point == (0, 0, 3000)
        assert beam.end_point == (6000, 0, 3000)

    def test_beam_length(self, setup_building, setup_beam_type):
        """Test beam length calculation."""
        building, level = setup_building
        beam_type = setup_beam_type

        # Horizontal beam 6m long
        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))

        assert abs(beam.length - 6000.0) < 1.0

    def test_beam_length_diagonal(self, setup_building, setup_beam_type):
        """Test beam length for diagonal beam."""
        building, level = setup_building
        beam_type = setup_beam_type

        # Diagonal beam: sqrt(3000² + 4000²) = 5000mm
        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(3000, 4000, 3000))

        assert abs(beam.length - 5000.0) < 1.0

    def test_beam_dimensions_from_type(self, setup_building, setup_beam_type):
        """Test that beam dimensions come from type."""
        building, level = setup_building
        beam_type = setup_beam_type

        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))

        assert beam.width == 300.0
        assert beam.height == 600.0

    def test_beam_volume(self, setup_building, setup_beam_type):
        """Test beam volume calculation."""
        building, level = setup_building
        beam_type = setup_beam_type

        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))

        # Volume = area * length = 180000 * 6000 = 1,080,000,000 mm³
        assert abs(beam.volume - 1_080_000_000.0) < 1.0
        # 1.08 m³
        assert abs(beam.volume_m3 - 1.08) < 0.01

    def test_beam_midpoint(self, setup_building, setup_beam_type):
        """Test beam midpoint calculation."""
        building, level = setup_building
        beam_type = setup_beam_type

        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))

        mid = beam.get_midpoint()
        assert mid == (3000, 0, 3000)

    def test_beam_is_horizontal(self, setup_building, setup_beam_type):
        """Test horizontal beam detection."""
        building, level = setup_building
        beam_type = setup_beam_type

        # Horizontal beam
        horizontal_beam = Beam(
            beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000)
        )
        assert horizontal_beam.is_horizontal is True

        # Sloped beam
        sloped_beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 4000))
        assert sloped_beam.is_horizontal is False

    def test_beam_horizontal_angle(self, setup_building, setup_beam_type):
        """Test beam horizontal angle calculation."""
        building, level = setup_building
        beam_type = setup_beam_type

        # Beam along X-axis (angle = 0)
        beam_x = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))
        assert abs(beam_x.horizontal_angle) < 0.01

        # Beam along Y-axis (angle = 90 degrees)
        beam_y = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(0, 6000, 3000))
        assert abs(beam_y.horizontal_angle_degrees - 90.0) < 0.1

    def test_beam_registered_with_level(self, setup_building, setup_beam_type):
        """Test that beam is registered with its level."""
        building, level = setup_building
        beam_type = setup_beam_type

        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))

        assert beam in level.elements

    def test_beam_geometry(self, setup_building, setup_beam_type):
        """Test beam geometry creation."""
        building, level = setup_building
        beam_type = setup_beam_type

        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))

        geom = beam.get_geometry()
        assert geom is not None


class TestBeamIFC:
    """Tests for beam IFC export."""

    @pytest.fixture
    def setup_building_with_beam(self):
        """Create a building with a beam."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        profile = RectangularProfile(300, 600)
        beam_type = BeamType("Standard Beam", profile)
        beam = Beam(beam_type, level, start_point=(0, 0, 3000), end_point=(6000, 0, 3000))

        return building, level, beam

    def test_beam_ifc_export(self, setup_building_with_beam, tmp_path):
        """Test beam IFC export."""
        building, level, beam = setup_building_with_beam

        output_file = tmp_path / "test_beam.ifc"
        building.export_ifc(str(output_file))

        assert output_file.exists()
