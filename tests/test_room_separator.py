"""
Tests for Room Separators.
"""

import math

import pytest

from bimascode.drawing.line_styles import LineType, LineWeight
from bimascode.drawing.view_base import ViewRange
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room_separator import RoomSeparator


class TestRoomSeparator:
    """Tests for RoomSeparator class."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with level for room separator testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        return building, level

    def test_room_separator_creation(self, setup_building):
        """Test creating a room separator with basic parameters."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 0),
            level=level,
            name="Test Separator",
        )

        assert separator.name == "Test Separator"
        assert separator.start == (0, 0)
        assert separator.end == (5000, 0)
        assert separator.level == level

    def test_room_separator_default_name(self, setup_building):
        """Test that room separator has default name if not provided."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 0),
            level=level,
        )

        assert separator.name == "Room Separator"

    def test_room_separator_length(self, setup_building):
        """Test room separator length calculation."""
        building, level = setup_building

        # Horizontal line: 5m
        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 0),
            level=level,
        )
        assert abs(separator.length - 5000.0) < 0.01
        assert abs(separator.length_m - 5.0) < 0.01

    def test_room_separator_diagonal_length(self, setup_building):
        """Test room separator length for diagonal line."""
        building, level = setup_building

        # 3-4-5 triangle: length should be 5000
        separator = RoomSeparator(
            start=(0, 0),
            end=(3000, 4000),
            level=level,
        )
        assert abs(separator.length - 5000.0) < 0.01

    def test_room_separator_midpoint(self, setup_building):
        """Test room separator midpoint calculation."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(4000, 2000),
            level=level,
        )

        midpoint = separator.midpoint
        assert abs(midpoint[0] - 2000.0) < 0.01
        assert abs(midpoint[1] - 1000.0) < 0.01

    def test_room_separator_angle_horizontal(self, setup_building):
        """Test room separator angle for horizontal line."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 0),
            level=level,
        )

        assert abs(separator.angle) < 0.01  # 0 radians
        assert abs(separator.angle_degrees) < 0.01  # 0 degrees

    def test_room_separator_angle_vertical(self, setup_building):
        """Test room separator angle for vertical line."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(0, 5000),
            level=level,
        )

        assert abs(separator.angle - math.pi / 2) < 0.01  # 90 degrees
        assert abs(separator.angle_degrees - 90.0) < 0.01

    def test_room_separator_angle_diagonal(self, setup_building):
        """Test room separator angle for 45-degree line."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(1000, 1000),
            level=level,
        )

        assert abs(separator.angle - math.pi / 4) < 0.01  # 45 degrees
        assert abs(separator.angle_degrees - 45.0) < 0.01

    def test_room_separator_registered_with_level(self, setup_building):
        """Test that room separator is registered with its level."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 0),
            level=level,
        )

        assert separator in level.elements

    def test_room_separator_setters(self, setup_building):
        """Test room separator start/end setters."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 0),
            level=level,
        )

        separator.start = (1000, 1000)
        separator.end = (6000, 1000)

        assert separator.start == (1000, 1000)
        assert separator.end == (6000, 1000)
        assert abs(separator.length - 5000.0) < 0.01

    def test_room_separator_bounding_box(self, setup_building):
        """Test room separator bounding box."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(1000, 2000),
            end=(4000, 5000),
            level=level,
        )

        bbox = separator.get_bounding_box()

        assert bbox.min_x == 1000.0
        assert bbox.min_y == 2000.0
        assert bbox.max_x == 4000.0
        assert bbox.max_y == 5000.0
        # Z is at level elevation (0)
        assert bbox.min_z == 0.0
        assert bbox.max_z == 0.0

    def test_room_separator_repr(self, setup_building):
        """Test room separator string representation."""
        building, level = setup_building

        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 0),
            level=level,
        )

        repr_str = repr(separator)
        assert "RoomSeparator" in repr_str
        assert "5.00m" in repr_str


class TestRoomSeparatorPlanRepresentation:
    """Tests for room separator floor plan representation."""

    @pytest.fixture
    def setup_separator(self):
        """Create a room separator for plan representation testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 3000),
            level=level,
        )
        return separator

    def test_plan_representation_returns_line(self, setup_separator):
        """Test that get_plan_representation returns a line."""
        separator = setup_separator
        view_range = ViewRange()

        linework = separator.get_plan_representation(1200, view_range)

        assert len(linework) == 1
        line = linework[0]
        assert line.start.x == 0.0
        assert line.start.y == 0.0
        assert line.end.x == 5000.0
        assert line.end.y == 3000.0

    def test_plan_representation_dashed_style(self, setup_separator):
        """Test that plan representation uses dashed line style."""
        separator = setup_separator
        view_range = ViewRange()

        linework = separator.get_plan_representation(1200, view_range)

        line = linework[0]
        assert line.style.type == LineType.DASHED
        assert line.style.weight == LineWeight.FINE
        assert line.style.is_cut is False

    def test_plan_representation_layer(self, setup_separator):
        """Test that plan representation uses correct layer."""
        separator = setup_separator
        view_range = ViewRange()

        linework = separator.get_plan_representation(1200, view_range)

        line = linework[0]
        assert line.layer == "A-AREA-BNDY"


class TestRoomSeparatorIFC:
    """Tests for room separator IFC export."""

    @pytest.fixture
    def setup_separator(self):
        """Create a room separator for IFC testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        separator = RoomSeparator(
            start=(0, 0),
            end=(5000, 0),
            level=level,
            name="Test Separator",
        )
        return building, level, separator

    def test_room_separator_ifc_export(self, setup_separator, tmp_path):
        """Test room separator IFC export creates valid file."""
        building, level, separator = setup_separator

        output_file = tmp_path / "test_room_separator.ifc"
        building.export_ifc(str(output_file))

        assert output_file.exists()

    def test_room_separator_ifc_contains_virtual_element(self, setup_separator, tmp_path):
        """Test that IFC export contains IfcVirtualElement."""
        building, level, separator = setup_separator

        output_file = tmp_path / "test_room_separator.ifc"
        building.export_ifc(str(output_file))

        # Read the file and check for IfcVirtualElement
        content = output_file.read_text()
        assert "IFCVIRTUALELEMENT" in content


class TestRoomSeparatorUseCases:
    """Tests for common room separator use cases."""

    @pytest.fixture
    def setup_building(self):
        """Create a building for use case testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        return building, level

    def test_open_office_division(self, setup_building):
        """Test using room separators to divide open office."""
        building, level = setup_building

        # Create separators to divide a 20m x 10m open office into 4 areas
        # Vertical separator at x=10000
        sep1 = RoomSeparator(
            start=(10000, 0),
            end=(10000, 10000),
            level=level,
            name="North-South Division",
        )

        # Horizontal separator at y=5000
        sep2 = RoomSeparator(
            start=(0, 5000),
            end=(20000, 5000),
            level=level,
            name="East-West Division",
        )

        assert sep1.length == 10000.0
        assert sep2.length == 20000.0
        assert len(level.elements) == 2

    def test_l_shaped_room_split(self, setup_building):
        """Test using room separator to split L-shaped room."""
        building, level = setup_building

        # Separator to split L-shaped room at the corner
        separator = RoomSeparator(
            start=(5000, 5000),
            end=(8000, 5000),
            level=level,
            name="L-Room Split",
        )

        assert separator.length == 3000.0
        assert separator.angle_degrees == 0.0  # Horizontal

    def test_multiple_separators_on_level(self, setup_building):
        """Test multiple room separators on one level."""
        building, level = setup_building

        separators = []
        for i in range(5):
            sep = RoomSeparator(
                start=(i * 2000, 0),
                end=(i * 2000, 5000),
                level=level,
                name=f"Separator {i + 1}",
            )
            separators.append(sep)

        assert len(level.elements) == 5
        for sep in separators:
            assert sep.length == 5000.0
