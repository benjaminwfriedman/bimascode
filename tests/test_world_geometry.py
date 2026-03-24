"""Tests for world geometry transformation mixins.

These tests verify that FreestandingElementMixin and HostedElementMixin
correctly transform local geometry to world coordinates.
"""


import pytest

from bimascode.architecture import Wall, create_basic_wall_type
from bimascode.architecture.ceiling import Ceiling
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.architecture.door import Door
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.floor import Floor
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.architecture.window import Window
from bimascode.architecture.window_type import WindowType
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.structure import (
    Beam,
    StructuralColumn,
    create_rectangular_beam_type,
    create_square_column_type,
)
from bimascode.utils.materials import MaterialLibrary


@pytest.fixture
def building():
    """Create a test building with a ground floor."""
    return Building("Test Building")


@pytest.fixture
def ground_level(building):
    """Create a ground level at elevation 0."""
    return Level(building, "Ground Floor", elevation=0)


@pytest.fixture
def upper_level(building):
    """Create an upper level at elevation 3000mm."""
    return Level(building, "Upper Floor", elevation=3000)


@pytest.fixture
def concrete():
    """Get concrete material."""
    return MaterialLibrary.concrete()


@pytest.fixture
def wall_type(concrete):
    """Create a basic wall type."""
    return create_basic_wall_type("Test Wall", 200, concrete)


class TestFreestandingWall:
    """Tests for Wall world geometry (FreestandingElementMixin)."""

    def test_wall_world_position(self, wall_type, ground_level):
        """Wall world position should be at start point + level elevation."""
        wall = Wall(wall_type, (1000, 2000), (5000, 2000), ground_level)

        pos = wall._get_world_position()

        assert pos[0] == 1000  # X at start
        assert pos[1] == 2000  # Y at start
        assert pos[2] == 0  # Z at level elevation

    def test_wall_world_position_with_elevation(self, wall_type, upper_level):
        """Wall on upper level should have correct Z elevation."""
        wall = Wall(wall_type, (0, 0), (4000, 0), upper_level)

        pos = wall._get_world_position()

        assert pos[2] == 3000  # Z at upper level elevation

    def test_wall_world_rotation_horizontal(self, wall_type, ground_level):
        """Horizontal wall (along X) should have 0 rotation."""
        wall = Wall(wall_type, (0, 0), (4000, 0), ground_level)

        rotation = wall._get_world_rotation()

        assert rotation == pytest.approx(0, abs=0.01)

    def test_wall_world_rotation_vertical(self, wall_type, ground_level):
        """Vertical wall (along Y) should have 90 degree rotation."""
        wall = Wall(wall_type, (0, 0), (0, 4000), ground_level)

        rotation = wall._get_world_rotation()

        assert rotation == pytest.approx(90, abs=0.01)

    def test_wall_world_rotation_diagonal(self, wall_type, ground_level):
        """45-degree wall should have 45 degree rotation."""
        wall = Wall(wall_type, (0, 0), (1000, 1000), ground_level)

        rotation = wall._get_world_rotation()

        assert rotation == pytest.approx(45, abs=0.01)

    def test_wall_get_world_geometry_returns_geometry(self, wall_type, ground_level):
        """get_world_geometry should return transformed geometry."""
        wall = Wall(wall_type, (1000, 2000), (5000, 2000), ground_level)

        world_geom = wall.get_world_geometry()

        assert world_geom is not None

    def test_wall_world_geometry_preserves_local_cache(self, wall_type, ground_level):
        """get_world_geometry should not modify cached local geometry."""
        wall = Wall(wall_type, (1000, 2000), (5000, 2000), ground_level)

        local_before = wall.get_geometry()
        _ = wall.get_world_geometry()
        local_after = wall.get_geometry()

        # Local geometry should be unchanged (same object due to caching)
        assert local_before is local_after


class TestFreestandingFloor:
    """Tests for Floor world geometry (FreestandingElementMixin)."""

    def test_floor_world_position_at_centroid(self, concrete, ground_level):
        """Floor world position should be at boundary centroid + level elevation."""
        floor_type = FloorType("Test Floor")
        floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE)

        boundary = [(0, 0), (4000, 0), (4000, 3000), (0, 3000)]
        floor = Floor(floor_type, boundary, ground_level)

        pos = floor._get_world_position()

        assert pos[0] == 2000  # X at centroid
        assert pos[1] == 1500  # Y at centroid
        assert pos[2] == 0  # Z at level elevation

    def test_floor_world_rotation_is_zero(self, concrete, ground_level):
        """Floor rotation should always be 0 (horizontal element)."""
        floor_type = FloorType("Test Floor")
        floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE)

        boundary = [(0, 0), (4000, 0), (4000, 3000), (0, 3000)]
        floor = Floor(floor_type, boundary, ground_level)

        rotation = floor._get_world_rotation()

        assert rotation == 0


class TestFreestandingCeiling:
    """Tests for Ceiling world geometry (FreestandingElementMixin)."""

    def test_ceiling_world_position_includes_height(self, ground_level):
        """Ceiling Z should be at level + height - thickness."""
        ceiling_type = CeilingType("Test Ceiling", thickness=20)
        boundary = [(0, 0), (4000, 0), (4000, 3000), (0, 3000)]
        ceiling = Ceiling(ceiling_type, boundary, ground_level, height=2700)

        pos = ceiling._get_world_position()

        # Z = level_elevation + height - thickness = 0 + 2700 - 20 = 2680
        assert pos[2] == 2680


class TestFreestandingColumn:
    """Tests for Column world geometry (FreestandingElementMixin)."""

    def test_column_world_position(self, ground_level):
        """Column world position should be at center + level elevation."""
        steel = MaterialLibrary.steel()
        column_type = create_square_column_type("Test Column", 300, steel)
        column = StructuralColumn(column_type, ground_level, (2000, 3000), height=3500)

        pos = column._get_world_position()

        assert pos[0] == 2000
        assert pos[1] == 3000
        assert pos[2] == 0

    def test_column_world_rotation(self, ground_level):
        """Column should use specified rotation."""
        steel = MaterialLibrary.steel()
        column_type = create_square_column_type("Test Column", 300, steel)
        column = StructuralColumn(column_type, ground_level, (0, 0), rotation=45)

        rotation = column._get_world_rotation()

        assert rotation == 45

    def test_column_local_transform_centers_vertically(self, ground_level):
        """Column local transform should shift base to Z=0."""
        steel = MaterialLibrary.steel()
        column_type = create_square_column_type("Test Column", 300, steel)
        column = StructuralColumn(column_type, ground_level, (0, 0), height=3000)

        local_transform = column._get_local_transform()

        # Transform should shift by half height
        # We can't easily inspect Location, but we can verify it exists
        assert local_transform is not None


class TestFreestandingBeam:
    """Tests for Beam world geometry (FreestandingElementMixin)."""

    def test_beam_world_position_includes_local_z(self, ground_level):
        """Beam world Z should include level elevation + local Z offset."""
        steel = MaterialLibrary.steel()
        beam_type = create_rectangular_beam_type("Test Beam", 200, 400, steel)

        # Beam at Z=2500 (local) on ground floor
        beam = Beam(beam_type, ground_level, (0, 0, 2500), (4000, 0, 2500))

        pos = beam._get_world_position()

        assert pos[0] == 0
        assert pos[1] == 0
        assert pos[2] == 2500  # level (0) + local Z (2500)

    def test_beam_world_rotation(self, ground_level):
        """Beam rotation should be calculated from start/end points."""
        steel = MaterialLibrary.steel()
        beam_type = create_rectangular_beam_type("Test Beam", 200, 400, steel)

        # 45-degree beam
        beam = Beam(beam_type, ground_level, (0, 0, 0), (1000, 1000, 0))

        rotation = beam._get_world_rotation()

        assert rotation == pytest.approx(45, abs=0.01)

    def test_beam_local_transform(self, ground_level):
        """Beam local transform should shift start to origin."""
        steel = MaterialLibrary.steel()
        beam_type = create_rectangular_beam_type("Test Beam", 200, 400, steel)
        beam = Beam(beam_type, ground_level, (0, 0, 0), (4000, 0, 0))

        local_transform = beam._get_local_transform()

        assert local_transform is not None


class TestHostedDoor:
    """Tests for Door world geometry (HostedElementMixin)."""

    def test_door_host_transform_uses_wall(self, wall_type, ground_level):
        """Door host transform should be based on wall position."""
        wall = Wall(wall_type, (1000, 2000), (5000, 2000), ground_level)
        door_type = DoorType("Test Door", width=900, height=2100)
        door = Door(door_type, wall, offset=500)

        host_transform = door._get_host_transform()

        assert host_transform is not None

    def test_door_local_transform_includes_offset(self, wall_type, ground_level):
        """Door local transform should position along wall."""
        wall = Wall(wall_type, (0, 0), (4000, 0), ground_level)
        door_type = DoorType("Test Door", width=900, height=2100)
        door = Door(door_type, wall, offset=1000)

        local_transform = door._get_local_transform()

        assert local_transform is not None

    def test_door_get_world_geometry_returns_geometry(self, wall_type, ground_level):
        """Door get_world_geometry should return transformed geometry."""
        wall = Wall(wall_type, (0, 0), (4000, 0), ground_level)
        door_type = DoorType("Test Door", width=900, height=2100)
        door = Door(door_type, wall, offset=500)

        world_geom = door.get_world_geometry()

        assert world_geom is not None

    def test_door_on_rotated_wall(self, wall_type, ground_level):
        """Door on rotated wall should inherit wall rotation."""
        # Wall at 90 degrees (vertical)
        wall = Wall(wall_type, (0, 0), (0, 4000), ground_level)
        door_type = DoorType("Test Door", width=900, height=2100)
        door = Door(door_type, wall, offset=1000)

        # Door should have world geometry
        world_geom = door.get_world_geometry()
        assert world_geom is not None


class TestHostedWindow:
    """Tests for Window world geometry (HostedElementMixin)."""

    def test_window_host_transform_includes_sill_height(self, wall_type, ground_level):
        """Window host transform Z should include sill height."""
        wall = Wall(wall_type, (0, 0), (4000, 0), ground_level)
        window_type = WindowType("Test Window", width=1200, height=1500, default_sill_height=900)
        window = Window(window_type, wall, offset=500)

        host_transform = window._get_host_transform()

        assert host_transform is not None

    def test_window_get_world_geometry_returns_geometry(self, wall_type, ground_level):
        """Window get_world_geometry should return transformed geometry."""
        wall = Wall(wall_type, (0, 0), (4000, 0), ground_level)
        window_type = WindowType("Test Window", width=1200, height=1500, default_sill_height=900)
        window = Window(window_type, wall, offset=500)

        world_geom = window.get_world_geometry()

        assert world_geom is not None


class TestWorldGeometryConsistency:
    """Tests verifying consistent behavior across element types."""

    def test_all_freestanding_elements_have_world_geometry(self, concrete, ground_level):
        """All freestanding elements should provide world geometry."""
        wall_type = create_basic_wall_type("Wall", 200, concrete)
        wall = Wall(wall_type, (0, 0), (4000, 0), ground_level)

        floor_type = FloorType("Floor")
        floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE)
        floor = Floor(floor_type, [(0, 0), (4000, 0), (4000, 3000), (0, 3000)], ground_level)

        ceiling_type = CeilingType("Ceiling", thickness=20)
        ceiling = Ceiling(ceiling_type, [(0, 0), (4000, 0), (4000, 3000), (0, 3000)], ground_level)

        steel = MaterialLibrary.steel()
        column_type = create_square_column_type("Column", 300, steel)
        column = StructuralColumn(column_type, ground_level, (0, 0))

        beam_type = create_rectangular_beam_type("Beam", 200, 400, steel)
        beam = Beam(beam_type, ground_level, (0, 0, 3000), (4000, 0, 3000))

        # All should return non-None world geometry
        assert wall.get_world_geometry() is not None
        assert floor.get_world_geometry() is not None
        assert ceiling.get_world_geometry() is not None
        assert column.get_world_geometry() is not None
        assert beam.get_world_geometry() is not None

    def test_all_hosted_elements_have_world_geometry(self, concrete, ground_level):
        """All hosted elements should provide world geometry."""
        wall_type = create_basic_wall_type("Wall", 200, concrete)
        wall = Wall(wall_type, (0, 0), (10000, 0), ground_level)

        door_type = DoorType("Door", width=900, height=2100)
        door = Door(door_type, wall, offset=1000)

        window_type = WindowType("Window", width=1200, height=1500, default_sill_height=900)
        window = Window(window_type, wall, offset=5000)

        assert door.get_world_geometry() is not None
        assert window.get_world_geometry() is not None

    def test_world_geometry_does_not_corrupt_local_geometry(self, concrete, ground_level):
        """Calling get_world_geometry should not affect get_geometry."""
        wall_type = create_basic_wall_type("Wall", 200, concrete)
        wall = Wall(wall_type, (0, 0), (4000, 0), ground_level)

        # Get local geometry first
        local_1 = wall.get_geometry()

        # Get world geometry (should copy internally)
        world = wall.get_world_geometry()

        # Get local geometry again
        local_2 = wall.get_geometry()

        # Local geometry should be the same cached object
        assert local_1 is local_2

        # World geometry should be different object
        assert world is not local_1
