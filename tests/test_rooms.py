"""
Tests for rooms/spaces.
"""

import pytest

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room import Room


class TestRoom:
    """Tests for Room class."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with level for room testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        return building, level

    def test_room_creation(self, setup_building):
        """Test creating a room with basic parameters."""
        building, level = setup_building

        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
        )

        assert room.name == "Office"
        assert room.number == "101"
        assert room.level == level

    def test_room_area_calculation(self, setup_building):
        """Test room area calculation using Shoelace formula."""
        building, level = setup_building

        # 5m x 4m room = 20 m²
        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
        )

        # Area should be 20,000,000 mm² = 20 m²
        assert abs(room.area - 20_000_000.0) < 1.0
        assert abs(room.area_m2 - 20.0) < 0.01

    def test_room_volume_calculation(self, setup_building):
        """Test room volume calculation."""
        building, level = setup_building

        # 5m x 4m x 2.7m = 54 m³
        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            floor_to_ceiling_height=2700.0,
        )

        assert abs(room.volume_m3 - 54.0) < 0.01

    def test_room_custom_height(self, setup_building):
        """Test room with custom floor-to-ceiling height."""
        building, level = setup_building

        room = Room(
            name="Lobby",
            number="100",
            boundary=[(0, 0), (10000, 0), (10000, 8000), (0, 8000)],
            level=level,
            floor_to_ceiling_height=4000.0,
        )

        assert room.floor_to_ceiling_height == 4000.0
        assert abs(room.floor_to_ceiling_height_m - 4.0) < 0.01

    def test_room_perimeter(self, setup_building):
        """Test room perimeter calculation."""
        building, level = setup_building

        # 5m x 4m room: perimeter = 2*(5+4) = 18m
        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
        )

        assert abs(room.perimeter - 18000.0) < 1.0
        assert abs(room.perimeter_m - 18.0) < 0.01

    def test_room_centroid(self, setup_building):
        """Test room centroid calculation."""
        building, level = setup_building

        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
        )

        cx, cy = room.get_centroid()
        assert abs(cx - 2500.0) < 1.0
        assert abs(cy - 2000.0) < 1.0

    def test_room_finishes(self, setup_building):
        """Test room finish parameters."""
        building, level = setup_building

        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            floor_finish="Carpet",
            wall_finish="Paint - Eggshell",
            ceiling_finish="Acoustic Tile",
        )

        assert room.floor_finish == "Carpet"
        assert room.wall_finish == "Paint - Eggshell"
        assert room.ceiling_finish == "Acoustic Tile"

    def test_room_to_dict(self, setup_building):
        """Test room dictionary conversion for schedules."""
        building, level = setup_building

        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            floor_finish="Carpet",
        )

        data = room.to_dict()

        assert data["number"] == "101"
        assert data["name"] == "Office"
        assert data["level"] == "Ground Floor"
        assert abs(data["area_m2"] - 20.0) < 0.1
        assert data["floor_finish"] == "Carpet"

    def test_room_registered_with_level(self, setup_building):
        """Test that room is registered with its level."""
        building, level = setup_building

        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
        )

        assert room in level.elements

    def test_room_l_shaped_area(self, setup_building):
        """Test area calculation for L-shaped room."""
        building, level = setup_building

        # L-shaped room: 5x4 + 3x2 = 20 + 6 = 26 m²
        boundary = [(0, 0), (5000, 0), (5000, 2000), (8000, 2000), (8000, 4000), (0, 4000)]

        room = Room(name="L-Room", number="102", boundary=boundary, level=level)

        # Note: This is approximately 26 m² for an L-shape
        assert room.area_m2 > 20.0  # Should be more than a simple rectangle


class TestRoomSchedule:
    """Tests for room schedule generation."""

    @pytest.fixture
    def setup_building_with_rooms(self):
        """Create a building with multiple rooms."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        room1 = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            floor_finish="Carpet",
        )

        room2 = Room(
            name="Conference",
            number="102",
            boundary=[(5500, 0), (10000, 0), (10000, 5000), (5500, 5000)],
            level=level,
            floor_finish="Hardwood",
        )

        return building, level, [room1, room2]

    def test_get_rooms(self, setup_building_with_rooms):
        """Test getting all rooms in building."""
        building, level, rooms = setup_building_with_rooms

        all_rooms = building.get_rooms()
        assert len(all_rooms) == 2

    def test_room_schedule(self, setup_building_with_rooms):
        """Test room schedule generation."""
        building, level, rooms = setup_building_with_rooms

        schedule = building.room_schedule()

        assert len(schedule) == 2
        assert "number" in schedule.columns
        assert "name" in schedule.columns
        assert "area_m2" in schedule.columns
        assert "volume_m3" in schedule.columns

    def test_room_schedule_empty_building(self):
        """Test room schedule for building without rooms."""
        building = Building("Empty Building")
        Level(building, "Ground Floor", elevation=0)

        schedule = building.room_schedule()

        assert len(schedule) == 0
        assert "number" in schedule.columns


class TestRoomIFC:
    """Tests for room IFC export."""

    @pytest.fixture
    def setup_building_with_room(self):
        """Create a building with a room."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        room = Room(
            name="Office",
            number="101",
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            floor_finish="Carpet",
            wall_finish="Paint",
            ceiling_finish="Acoustic",
        )

        return building, level, room

    def test_room_ifc_export(self, setup_building_with_room, tmp_path):
        """Test room IFC export."""
        building, level, room = setup_building_with_room

        output_file = tmp_path / "test_room.ifc"
        building.export_ifc(str(output_file))

        assert output_file.exists()
