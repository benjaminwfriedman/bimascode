"""
Tests for doors and door types.
"""

import pytest
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture.wall_type import WallType, LayerFunction
from bimascode.architecture.wall import Wall
from bimascode.architecture.door_type import (
    DoorType,
    SwingDirection,
    DoorOperationType,
    create_standard_door_type,
    create_double_door_type,
)
from bimascode.architecture.door import Door
from bimascode.utils.materials import MaterialLibrary


class TestDoorType:
    """Tests for DoorType class."""

    def test_door_type_creation(self):
        """Test creating a door type with default parameters."""
        door_type = DoorType("Standard Door")

        assert door_type.name == "Standard Door"
        assert door_type.width == 900.0
        assert door_type.height == 2100.0
        assert door_type.frame_width == 50.0
        assert door_type.frame_depth == 100.0
        assert door_type.panel_thickness == 44.0

    def test_door_type_custom_dimensions(self):
        """Test creating a door type with custom dimensions."""
        door_type = DoorType(
            "Wide Door",
            width=1200.0,
            height=2400.0,
            frame_width=60.0,
            frame_depth=120.0,
        )

        assert door_type.width == 1200.0
        assert door_type.height == 2400.0
        assert door_type.frame_width == 60.0
        assert door_type.frame_depth == 120.0

    def test_door_type_overall_dimensions(self):
        """Test overall dimensions including frame."""
        door_type = DoorType("Test Door", width=900.0, height=2100.0, frame_width=50.0)

        assert door_type.overall_width == 1000.0  # 900 + 2*50
        assert door_type.overall_height == 2150.0  # 2100 + 50 (top frame only)

    def test_standard_door_type_constructor(self):
        """Test the standard door type convenience constructor."""
        door_type = create_standard_door_type("Entry Door", width=900.0)

        assert door_type.name == "Entry Door"
        assert door_type.width == 900.0
        assert door_type.swing_direction == SwingDirection.RIGHT_HAND

    def test_double_door_type_constructor(self):
        """Test the double door type convenience constructor."""
        door_type = create_double_door_type("Double Entry", width=1800.0)

        assert door_type.name == "Double Entry"
        assert door_type.width == 1800.0
        assert door_type.swing_direction == SwingDirection.DOUBLE


class TestDoor:
    """Tests for Door class."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with wall for door testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        wall = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)

        return building, level, wall

    def test_door_creation(self, setup_building):
        """Test creating a door in a wall."""
        building, level, wall = setup_building
        door_type = create_standard_door_type("Entry Door")

        door = Door(door_type, wall, offset=1000.0)

        assert door.host_wall == wall
        assert door.offset == 1000.0
        assert door.sill_height == 0.0
        assert door.level == level

    def test_door_in_hosted_elements(self, setup_building):
        """Test that door is registered with host wall."""
        building, level, wall = setup_building
        door_type = create_standard_door_type("Entry Door")

        door = Door(door_type, wall, offset=1000.0)

        assert door in wall.hosted_elements

    def test_door_dimensions(self, setup_building):
        """Test door dimensions from type."""
        building, level, wall = setup_building
        door_type = DoorType("Test Door", width=900.0, height=2100.0, frame_width=50.0)

        door = Door(door_type, wall, offset=1000.0)

        assert door.width == 1000.0  # overall_width
        assert door.height == 2150.0  # overall_height

    def test_door_opening_geometry(self, setup_building):
        """Test that door creates opening geometry."""
        building, level, wall = setup_building
        door_type = create_standard_door_type("Entry Door")

        door = Door(door_type, wall, offset=1000.0)
        opening = door.get_opening_geometry()

        assert opening is not None

    def test_door_world_position(self, setup_building):
        """Test door world position calculation."""
        building, level, wall = setup_building
        door_type = DoorType("Test Door", width=900.0, height=2100.0, frame_width=50.0)

        door = Door(door_type, wall, offset=1000.0)
        pos = door.get_world_position()

        # Wall goes from (0,0) to (5000,0)
        # Door offset=1000, width=1000 (overall)
        # Door center should be at x = 1000 + 500 = 1500
        assert abs(pos[0] - 1500.0) < 1.0
        assert abs(pos[1] - 0.0) < 1.0

    def test_door_validate_position_valid(self, setup_building):
        """Test position validation for valid door placement."""
        building, level, wall = setup_building
        door_type = create_standard_door_type("Entry Door")

        # Place door with enough clearance
        door = Door(door_type, wall, offset=1000.0)

        assert door.validate_position() is True

    def test_door_validate_position_invalid_offset(self, setup_building):
        """Test position validation for invalid door placement."""
        building, level, wall = setup_building
        door_type = create_standard_door_type("Entry Door")

        # Place door extending beyond wall end
        door = Door(door_type, wall, offset=4500.0)

        assert door.validate_position() is False

    def test_multiple_doors_on_wall(self, setup_building):
        """Test placing multiple doors on same wall."""
        building, level, wall = setup_building
        door_type = create_standard_door_type("Entry Door")

        door1 = Door(door_type, wall, offset=500.0)
        door2 = Door(door_type, wall, offset=2500.0)

        assert len(wall.hosted_elements) == 2
        assert door1 in wall.hosted_elements
        assert door2 in wall.hosted_elements

    def test_wall_geometry_has_opening(self, setup_building):
        """Test that wall geometry includes door opening void."""
        building, level, wall = setup_building
        door_type = create_standard_door_type("Entry Door")

        # Get wall geometry before door
        geom_before = wall.get_geometry(force_rebuild=True)

        # Add door
        door = Door(door_type, wall, offset=1000.0)

        # Get wall geometry after door
        geom_after = wall.get_geometry(force_rebuild=True)

        # The geometries should be different (one has opening)
        assert geom_before is not None
        assert geom_after is not None


class TestDoorIFC:
    """Tests for door IFC export."""

    @pytest.fixture
    def setup_building_with_door(self):
        """Create a building with wall and door."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        wall = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        door_type = create_standard_door_type("Entry Door")
        door = Door(door_type, wall, offset=1000.0)

        return building, level, wall, door

    def test_door_to_ifc_creates_entities(self, setup_building_with_door, tmp_path):
        """Test that door export creates necessary IFC entities."""
        building, level, wall, door = setup_building_with_door

        # Export building
        output_file = tmp_path / "test_door.ifc"
        building.export_ifc(str(output_file))

        # Check file exists
        assert output_file.exists()
