"""
Tests for door, window, and room tags.
"""

import pytest

from bimascode.architecture.door import Door
from bimascode.architecture.door_type import create_standard_door_type
from bimascode.architecture.wall import Wall
from bimascode.architecture.wall_type import LayerFunction, WallType
from bimascode.architecture.window import Window
from bimascode.architecture.window_type import create_standard_window_type
from bimascode.drawing.primitives import Point2D, ViewResult
from bimascode.drawing.tags import DoorTag, RoomTag, TagShape, TagStyle, WindowTag
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room import Room
from bimascode.utils.materials import MaterialLibrary


class TestTagStyle:
    """Tests for TagStyle class."""

    def test_default_door_style(self):
        """Test default door tag style."""
        style = TagStyle.door_default()

        assert style.shape == TagShape.HEXAGON
        assert style.size == 500.0
        assert style.text_height == 150.0
        assert style.show_border is True

    def test_default_window_style(self):
        """Test default window tag style."""
        style = TagStyle.window_default()

        assert style.shape == TagShape.CIRCLE
        assert style.size == 450.0
        assert style.text_height == 150.0

    def test_default_room_style(self):
        """Test default room tag style."""
        style = TagStyle.room_default()

        assert style.shape == TagShape.RECTANGLE
        assert style.size == 400.0  # Height
        assert style.width is None  # Auto-size based on text length
        assert style.text_height == 120.0
        assert style.show_border is True

    def test_custom_style(self):
        """Test creating a custom tag style."""
        style = TagStyle(
            shape=TagShape.RECTANGLE,
            size=400.0,
            text_height=120.0,
            show_border=False,
        )

        assert style.shape == TagShape.RECTANGLE
        assert style.size == 400.0
        assert style.text_height == 120.0
        assert style.show_border is False


class TestDoorTag:
    """Tests for DoorTag class."""

    @pytest.fixture
    def door_with_mark(self):
        """Create a door with a mark for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        wall = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)

        door_type = create_standard_door_type("Entry Door")
        door = Door(door_type, wall, offset=1000.0, mark="101")

        return door

    def test_door_tag_creation(self, door_with_mark):
        """Test creating a door tag."""
        tag = DoorTag(door=door_with_mark)

        assert tag.door == door_with_mark
        assert tag.text == "101"
        assert tag.style.shape == TagShape.HEXAGON

    def test_door_tag_insertion_point_auto(self, door_with_mark):
        """Test automatic tag position from door center."""
        tag = DoorTag(door=door_with_mark)

        position = tag.insertion_point
        world_pos = door_with_mark.get_world_position()

        assert position.x == world_pos[0]
        assert position.y == world_pos[1]

    def test_door_tag_custom_position(self, door_with_mark):
        """Test tag with custom position override."""
        custom_pos = Point2D(2000, 500)
        tag = DoorTag(door=door_with_mark, position=custom_pos)

        assert tag.insertion_point == custom_pos
        assert tag.insertion_point.x == 2000
        assert tag.insertion_point.y == 500

    def test_door_tag_custom_style(self, door_with_mark):
        """Test tag with custom style."""
        style = TagStyle(shape=TagShape.CIRCLE, size=400.0)
        tag = DoorTag(door=door_with_mark, style=style)

        assert tag.style.shape == TagShape.CIRCLE
        assert tag.style.size == 400.0

    def test_door_tag_translate(self, door_with_mark):
        """Test translating a door tag."""
        tag = DoorTag(door=door_with_mark)
        original_pos = tag.insertion_point

        translated = tag.translate(100, 200)

        assert translated.insertion_point.x == original_pos.x + 100
        assert translated.insertion_point.y == original_pos.y + 200
        assert translated.door == door_with_mark

    def test_door_tag_block_name(self, door_with_mark):
        """Test block name generation includes size."""
        tag = DoorTag(door=door_with_mark)

        # Default style: size=500, text_height=150
        assert tag.block_name == "DOOR_TAG_HEXAGON_500_150"

    def test_door_tag_no_mark(self, door_with_mark):
        """Test tag when door has no mark."""
        door_with_mark.mark = None
        tag = DoorTag(door=door_with_mark)

        assert tag.text == ""


class TestWindowTag:
    """Tests for WindowTag class."""

    @pytest.fixture
    def window_with_mark(self):
        """Create a window with a mark for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        wall = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)

        window_type = create_standard_window_type("Standard Window")
        window = Window(window_type, wall, offset=2500.0, mark="W-1")

        return window

    def test_window_tag_creation(self, window_with_mark):
        """Test creating a window tag."""
        tag = WindowTag(window=window_with_mark)

        assert tag.window == window_with_mark
        assert tag.text == "W-1"
        assert tag.style.shape == TagShape.CIRCLE

    def test_window_tag_insertion_point_auto(self, window_with_mark):
        """Test automatic tag position from window center."""
        tag = WindowTag(window=window_with_mark)

        position = tag.insertion_point
        world_pos = window_with_mark.get_world_position()

        assert position.x == world_pos[0]
        assert position.y == world_pos[1]

    def test_window_tag_custom_position(self, window_with_mark):
        """Test tag with custom position override."""
        custom_pos = Point2D(3000, 600)
        tag = WindowTag(window=window_with_mark, position=custom_pos)

        assert tag.insertion_point == custom_pos

    def test_window_tag_translate(self, window_with_mark):
        """Test translating a window tag."""
        tag = WindowTag(window=window_with_mark)
        original_pos = tag.insertion_point

        translated = tag.translate(50, -100)

        assert translated.insertion_point.x == original_pos.x + 50
        assert translated.insertion_point.y == original_pos.y - 100

    def test_window_tag_block_name(self, window_with_mark):
        """Test block name generation includes size."""
        tag = WindowTag(window=window_with_mark)

        # Default style: size=450, text_height=150
        assert tag.block_name == "WINDOW_TAG_CIRCLE_450_150"


class TestViewResultWithTags:
    """Tests for ViewResult with tag support."""

    @pytest.fixture
    def door_and_window_tags(self):
        """Create door and window tags for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        wall = Wall(wall_type, (0, 0), (10000, 0), level, height=3000)

        door_type = create_standard_door_type("Entry Door")
        door = Door(door_type, wall, offset=1000.0, mark="D-1")
        door_tag = DoorTag(door=door)

        window_type = create_standard_window_type("Standard Window")
        window = Window(window_type, wall, offset=5000.0, mark="W-1")
        window_tag = WindowTag(window=window)

        return door_tag, window_tag

    def test_view_result_with_tags(self, door_and_window_tags):
        """Test ViewResult containing tags."""
        door_tag, window_tag = door_and_window_tags

        result = ViewResult(
            door_tags=[door_tag],
            window_tags=[window_tag],
        )

        assert len(result.door_tags) == 1
        assert len(result.window_tags) == 1
        assert result.door_tags[0].text == "D-1"
        assert result.window_tags[0].text == "W-1"

    def test_view_result_total_count_includes_tags(self, door_and_window_tags):
        """Test that total_geometry_count includes tags."""
        door_tag, window_tag = door_and_window_tags

        result = ViewResult(
            door_tags=[door_tag],
            window_tags=[window_tag],
        )

        assert result.total_geometry_count == 2

    def test_view_result_extend_with_tags(self, door_and_window_tags):
        """Test extending ViewResult preserves tags."""
        door_tag, window_tag = door_and_window_tags

        result1 = ViewResult(door_tags=[door_tag])
        result2 = ViewResult(window_tags=[window_tag])

        result1.extend(result2)

        assert len(result1.door_tags) == 1
        assert len(result1.window_tags) == 1

    def test_view_result_translate_with_tags(self, door_and_window_tags):
        """Test translating ViewResult includes tags."""
        door_tag, window_tag = door_and_window_tags

        result = ViewResult(
            door_tags=[door_tag],
            window_tags=[window_tag],
        )

        original_door_pos = door_tag.insertion_point
        original_window_pos = window_tag.insertion_point

        translated = result.translate(500, 300)

        assert translated.door_tags[0].insertion_point.x == original_door_pos.x + 500
        assert translated.door_tags[0].insertion_point.y == original_door_pos.y + 300
        assert translated.window_tags[0].insertion_point.x == original_window_pos.x + 500
        assert translated.window_tags[0].insertion_point.y == original_window_pos.y + 300

    def test_view_result_bounds_includes_tags(self, door_and_window_tags):
        """Test that get_bounds includes tag positions."""
        door_tag, window_tag = door_and_window_tags

        result = ViewResult(
            door_tags=[door_tag],
            window_tags=[window_tag],
        )

        bounds = result.get_bounds()

        assert bounds is not None
        min_x, min_y, max_x, max_y = bounds

        # Bounds should include both tag positions
        assert min_x <= door_tag.insertion_point.x <= max_x
        assert min_y <= door_tag.insertion_point.y <= max_y
        assert min_x <= window_tag.insertion_point.x <= max_x
        assert min_y <= window_tag.insertion_point.y <= max_y


class TestDoorMarkProperty:
    """Tests for Door mark property."""

    @pytest.fixture
    def wall(self):
        """Create a wall for door testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        return Wall(wall_type, (0, 0), (5000, 0), level, height=3000)

    def test_door_mark_in_constructor(self, wall):
        """Test setting mark in door constructor."""
        door_type = create_standard_door_type("Entry Door")
        door = Door(door_type, wall, offset=1000.0, mark="101")

        assert door.mark == "101"

    def test_door_mark_setter(self, wall):
        """Test setting mark after construction."""
        door_type = create_standard_door_type("Entry Door")
        door = Door(door_type, wall, offset=1000.0)

        assert door.mark is None

        door.mark = "102"
        assert door.mark == "102"

    def test_door_no_mark(self, wall):
        """Test door without mark."""
        door_type = create_standard_door_type("Entry Door")
        door = Door(door_type, wall, offset=1000.0)

        assert door.mark is None


class TestWindowMarkProperty:
    """Tests for Window mark property."""

    @pytest.fixture
    def wall(self):
        """Create a wall for window testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        return Wall(wall_type, (0, 0), (5000, 0), level, height=3000)

    def test_window_mark_in_constructor(self, wall):
        """Test setting mark in window constructor."""
        window_type = create_standard_window_type("Standard Window")
        window = Window(window_type, wall, offset=2000.0, mark="W-1")

        assert window.mark == "W-1"

    def test_window_mark_setter(self, wall):
        """Test setting mark after construction."""
        window_type = create_standard_window_type("Standard Window")
        window = Window(window_type, wall, offset=2000.0)

        assert window.mark is None

        window.mark = "A"
        assert window.mark == "A"


class TestRoomTag:
    """Tests for RoomTag class."""

    @pytest.fixture
    def room(self):
        """Create a room for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        # Simple rectangular boundary
        boundary = [
            (0, 0),
            (4000, 0),
            (4000, 3000),
            (0, 3000),
        ]

        return Room("Living Room", "101", boundary, level)

    def test_room_tag_creation(self, room):
        """Test creating a room tag."""
        tag = RoomTag(room=room)

        assert tag.room == room
        assert tag.name_text == "Living Room"
        assert tag.number_text == "101"
        assert tag.style.shape == TagShape.RECTANGLE

    def test_room_tag_text_combined(self, room):
        """Test combined text property."""
        tag = RoomTag(room=room)

        assert tag.text == "Living Room\n101"

    def test_room_tag_insertion_point_auto(self, room):
        """Test automatic tag position from room centroid."""
        tag = RoomTag(room=room)

        position = tag.insertion_point
        centroid = room.get_centroid()

        assert position.x == centroid[0]
        assert position.y == centroid[1]
        # For a 4000x3000 rectangle, centroid should be at (2000, 1500)
        assert position.x == 2000.0
        assert position.y == 1500.0

    def test_room_tag_custom_position(self, room):
        """Test tag with custom position override."""
        custom_pos = Point2D(1000, 1000)
        tag = RoomTag(room=room, position=custom_pos)

        assert tag.insertion_point == custom_pos
        assert tag.insertion_point.x == 1000
        assert tag.insertion_point.y == 1000

    def test_room_tag_custom_style(self, room):
        """Test tag with custom style."""
        style = TagStyle(shape=TagShape.CIRCLE, size=500.0, text_height=100.0)
        tag = RoomTag(room=room, style=style)

        assert tag.style.shape == TagShape.CIRCLE
        assert tag.style.size == 500.0
        assert tag.style.text_height == 100.0

    def test_room_tag_translate(self, room):
        """Test translating a room tag."""
        tag = RoomTag(room=room)
        original_pos = tag.insertion_point

        translated = tag.translate(100, 200)

        assert translated.insertion_point.x == original_pos.x + 100
        assert translated.insertion_point.y == original_pos.y + 200
        assert translated.room == room

    def test_room_tag_block_name(self, room):
        """Test block name generation includes style parameters."""
        tag = RoomTag(room=room)

        # Default style: size=400 (height), auto-calculated width, text_height=120
        # "Living Room" = 11 chars, width = 11 * (120 * 0.8) + (120 * 2.5) = 1356
        assert tag.block_name == "ROOM_TAG_RECTANGLE_400_1356_120"

    def test_room_tag_calculated_width_auto(self, room):
        """Test auto-calculated width based on text length."""
        tag = RoomTag(room=room)

        # "Living Room" = 11 chars
        # char_width = 120 * 0.8 = 96
        # padding = 120 * 2.5 = 300
        # calculated = 11 * 96 + 300 = 1356
        assert tag.calculated_width == 1356.0

    def test_room_tag_calculated_width_explicit(self, room):
        """Test explicit width overrides auto-calculation."""
        style = TagStyle(
            shape=TagShape.RECTANGLE,
            size=400.0,
            text_height=120.0,
            width=2000.0,  # Explicit width
        )
        tag = RoomTag(room=room, style=style)

        assert tag.calculated_width == 2000.0

    def test_room_tag_layer(self, room):
        """Test tag layer property."""
        tag = RoomTag(room=room)

        from bimascode.drawing.line_styles import Layer

        assert tag.layer == Layer.SYMBOL

    def test_room_tag_rotation(self, room):
        """Test tag rotation property."""
        tag = RoomTag(room=room, rotation=45.0)

        assert tag.rotation == 45.0

    def test_room_tag_empty_name(self):
        """Test tag when room has empty name."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        boundary = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]

        room = Room("", "102", boundary, level)
        tag = RoomTag(room=room)

        assert tag.name_text == ""
        assert tag.number_text == "102"
        assert tag.text == "102"

    def test_room_tag_empty_number(self):
        """Test tag when room has empty number."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        boundary = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]

        room = Room("Kitchen", "", boundary, level)
        tag = RoomTag(room=room)

        assert tag.name_text == "Kitchen"
        assert tag.number_text == ""
        assert tag.text == "Kitchen"


class TestViewResultWithRoomTags:
    """Tests for ViewResult with room tag support."""

    @pytest.fixture
    def room_tag(self):
        """Create a room tag for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        boundary = [(0, 0), (5000, 0), (5000, 4000), (0, 4000)]

        room = Room("Office", "201", boundary, level)
        return RoomTag(room=room)

    def test_view_result_with_room_tags(self, room_tag):
        """Test ViewResult containing room tags."""
        result = ViewResult(room_tags=[room_tag])

        assert len(result.room_tags) == 1
        assert result.room_tags[0].name_text == "Office"
        assert result.room_tags[0].number_text == "201"

    def test_view_result_total_count_includes_room_tags(self, room_tag):
        """Test that total_geometry_count includes room tags."""
        result = ViewResult(room_tags=[room_tag])

        assert result.total_geometry_count == 1

    def test_view_result_extend_with_room_tags(self, room_tag):
        """Test extending ViewResult preserves room tags."""
        result1 = ViewResult()
        result2 = ViewResult(room_tags=[room_tag])

        result1.extend(result2)

        assert len(result1.room_tags) == 1
        assert result1.room_tags[0].number_text == "201"

    def test_view_result_translate_with_room_tags(self, room_tag):
        """Test translating ViewResult includes room tags."""
        result = ViewResult(room_tags=[room_tag])

        original_pos = room_tag.insertion_point

        translated = result.translate(500, 300)

        assert translated.room_tags[0].insertion_point.x == original_pos.x + 500
        assert translated.room_tags[0].insertion_point.y == original_pos.y + 300

    def test_view_result_bounds_includes_room_tags(self, room_tag):
        """Test that get_bounds includes room tag positions."""
        result = ViewResult(room_tags=[room_tag])

        bounds = result.get_bounds()

        assert bounds is not None
        min_x, min_y, max_x, max_y = bounds

        # Bounds should include room tag position
        assert min_x <= room_tag.insertion_point.x <= max_x
        assert min_y <= room_tag.insertion_point.y <= max_y
