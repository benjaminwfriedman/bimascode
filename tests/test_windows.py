"""
Tests for windows and window types.
"""

import pytest
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture.wall_type import WallType, LayerFunction
from bimascode.architecture.wall import Wall
from bimascode.architecture.window_type import (
    WindowType,
    WindowOperationType,
    create_standard_window_type,
    create_double_window_type,
    create_fixed_window_type,
)
from bimascode.architecture.window import Window
from bimascode.utils.materials import MaterialLibrary


class TestWindowType:
    """Tests for WindowType class."""

    def test_window_type_creation(self):
        """Test creating a window type with default parameters."""
        window_type = WindowType("Standard Window")

        assert window_type.name == "Standard Window"
        assert window_type.width == 1200.0
        assert window_type.height == 1500.0
        assert window_type.frame_width == 50.0
        assert window_type.frame_depth == 70.0
        assert window_type.glazing_thickness == 24.0
        assert window_type.default_sill_height == 900.0

    def test_window_type_custom_dimensions(self):
        """Test creating a window type with custom dimensions."""
        window_type = WindowType(
            "Large Window",
            width=2000.0,
            height=1800.0,
            frame_width=60.0,
            default_sill_height=600.0,
        )

        assert window_type.width == 2000.0
        assert window_type.height == 1800.0
        assert window_type.frame_width == 60.0
        assert window_type.default_sill_height == 600.0

    def test_window_type_overall_dimensions(self):
        """Test overall dimensions including frame."""
        window_type = WindowType(
            "Test Window",
            width=1200.0,
            height=1500.0,
            frame_width=50.0
        )

        assert window_type.overall_width == 1300.0  # 1200 + 2*50
        assert window_type.overall_height == 1600.0  # 1500 + 2*50

    def test_window_type_with_mullions(self):
        """Test window type with mullions."""
        window_type = WindowType(
            "Triple Window",
            width=3000.0,
            height=1500.0,
            mullion_count=2,
            mullion_width=50.0,
        )

        assert window_type.mullion_count == 2
        assert window_type.mullion_width == 50.0

    def test_standard_window_type_constructor(self):
        """Test the standard window type convenience constructor."""
        window_type = create_standard_window_type("Bedroom Window")

        assert window_type.name == "Bedroom Window"
        assert window_type.mullion_count == 0
        assert window_type.operation_type == WindowOperationType.SINGLE_PANEL

    def test_double_window_type_constructor(self):
        """Test the double window type convenience constructor."""
        window_type = create_double_window_type("Living Room Window")

        assert window_type.name == "Living Room Window"
        assert window_type.width == 2400.0
        assert window_type.mullion_count == 1

    def test_fixed_window_type_constructor(self):
        """Test the fixed window type convenience constructor."""
        window_type = create_fixed_window_type("Picture Window")

        assert window_type.name == "Picture Window"
        assert window_type.operation_type == WindowOperationType.FIXED


class TestWindow:
    """Tests for Window class."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with wall for window testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        wall = Wall(wall_type, (0, 0), (6000, 0), level, height=3000)

        return building, level, wall

    def test_window_creation(self, setup_building):
        """Test creating a window in a wall."""
        building, level, wall = setup_building
        window_type = create_standard_window_type("Test Window")

        window = Window(window_type, wall, offset=1000.0)

        assert window.host_wall == wall
        assert window.offset == 1000.0
        assert window.sill_height == 900.0  # default from type
        assert window.level == level

    def test_window_custom_sill_height(self, setup_building):
        """Test creating a window with custom sill height."""
        building, level, wall = setup_building
        window_type = create_standard_window_type("Test Window")

        window = Window(window_type, wall, offset=1000.0, sill_height=600.0)

        assert window.sill_height == 600.0

    def test_window_in_hosted_elements(self, setup_building):
        """Test that window is registered with host wall."""
        building, level, wall = setup_building
        window_type = create_standard_window_type("Test Window")

        window = Window(window_type, wall, offset=1000.0)

        assert window in wall.hosted_elements

    def test_window_dimensions(self, setup_building):
        """Test window dimensions from type."""
        building, level, wall = setup_building
        window_type = WindowType(
            "Test Window",
            width=1200.0,
            height=1500.0,
            frame_width=50.0
        )

        window = Window(window_type, wall, offset=1000.0)

        assert window.width == 1300.0  # overall_width
        assert window.height == 1600.0  # overall_height

    def test_window_opening_geometry(self, setup_building):
        """Test that window creates opening geometry."""
        building, level, wall = setup_building
        window_type = create_standard_window_type("Test Window")

        window = Window(window_type, wall, offset=1000.0)
        opening = window.get_opening_geometry()

        assert opening is not None

    def test_window_world_position(self, setup_building):
        """Test window world position calculation."""
        building, level, wall = setup_building
        window_type = WindowType(
            "Test Window",
            width=1200.0,
            height=1500.0,
            frame_width=50.0
        )

        window = Window(window_type, wall, offset=1000.0, sill_height=900.0)
        pos = window.get_world_position()

        # Wall goes from (0,0) to (6000,0)
        # Window offset=1000, width=1300 (overall)
        # Window center should be at x = 1000 + 650 = 1650
        assert abs(pos[0] - 1650.0) < 1.0
        assert abs(pos[1] - 0.0) < 1.0

    def test_window_validate_position_valid(self, setup_building):
        """Test position validation for valid window placement."""
        building, level, wall = setup_building
        window_type = create_standard_window_type("Test Window")

        # Place window with enough clearance
        window = Window(window_type, wall, offset=1000.0)

        assert window.validate_position() is True

    def test_window_validate_position_invalid_height(self, setup_building):
        """Test position validation for window too high."""
        building, level, wall = setup_building
        window_type = WindowType("Test Window", width=1200.0, height=1500.0)

        # Place window with sill too high
        window = Window(window_type, wall, offset=1000.0, sill_height=2000.0)

        assert window.validate_position() is False

    def test_multiple_windows_on_wall(self, setup_building):
        """Test placing multiple windows on same wall."""
        building, level, wall = setup_building
        window_type = create_standard_window_type("Test Window")

        window1 = Window(window_type, wall, offset=500.0)
        window2 = Window(window_type, wall, offset=3000.0)

        assert len(wall.hosted_elements) == 2
        assert window1 in wall.hosted_elements
        assert window2 in wall.hosted_elements

    def test_mixed_doors_and_windows(self, setup_building):
        """Test placing both doors and windows on same wall."""
        from bimascode.architecture.door_type import create_standard_door_type
        from bimascode.architecture.door import Door

        building, level, wall = setup_building
        door_type = create_standard_door_type("Entry Door")
        window_type = create_standard_window_type("Test Window")

        door = Door(door_type, wall, offset=500.0)
        window = Window(window_type, wall, offset=2500.0)

        assert len(wall.hosted_elements) == 2
        assert door in wall.hosted_elements
        assert window in wall.hosted_elements


class TestWindowIFC:
    """Tests for window IFC export."""

    @pytest.fixture
    def setup_building_with_window(self):
        """Create a building with wall and window."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        wall = Wall(wall_type, (0, 0), (6000, 0), level, height=3000)
        window_type = create_standard_window_type("Test Window")
        window = Window(window_type, wall, offset=1000.0)

        return building, level, wall, window

    def test_window_to_ifc_creates_file(self, setup_building_with_window, tmp_path):
        """Test that window export creates IFC file."""
        building, level, wall, window = setup_building_with_window

        # Export building
        output_file = tmp_path / "test_window.ifc"
        building.export_ifc(str(output_file))

        # Check file exists
        assert output_file.exists()
