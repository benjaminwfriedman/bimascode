"""Tests for SpatialIndex class."""

import pytest
from bimascode.performance.bounding_box import BoundingBox
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture.wall import Wall
from bimascode.architecture.wall_type import WallType, LayerFunction
from bimascode.architecture.floor import Floor
from bimascode.architecture.floor_type import FloorType
from bimascode.utils.materials import Material, MaterialLibrary


def create_wall_type(name: str, width: float = 200) -> WallType:
    """Helper to create a wall type with a single layer."""
    wall_type = WallType(name)
    concrete = MaterialLibrary.concrete()
    wall_type.add_layer(concrete, width, LayerFunction.STRUCTURE, structural=True)
    return wall_type


class TestSpatialIndexBasics:
    """Basic tests for SpatialIndex."""

    def test_create_empty_index(self):
        """Test creating an empty spatial index."""
        idx = SpatialIndex()
        assert idx.count == 0
        assert len(idx) == 0

    def test_insert_element(self):
        """Test inserting an element into the index."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        idx.insert(wall)
        assert idx.count == 1
        assert wall in idx

    def test_insert_duplicate(self):
        """Test that inserting the same element twice updates it."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        idx.insert(wall)
        idx.insert(wall)  # Should update, not add duplicate
        assert idx.count == 1

    def test_remove_element(self):
        """Test removing an element from the index."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        idx.insert(wall)
        result = idx.remove(wall)

        assert result is True
        assert idx.count == 0
        assert wall not in idx

    def test_remove_nonexistent(self):
        """Test removing an element that's not in the index."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        result = idx.remove(wall)
        assert result is False

    def test_clear(self):
        """Test clearing all elements from the index."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        for i in range(10):
            wall = Wall(wall_type, (i * 1000, 0), (i * 1000 + 500, 0), level, height=3000)
            idx.insert(wall)

        assert idx.count == 10
        idx.clear()
        assert idx.count == 0


class TestSpatialIndexQueries:
    """Tests for spatial queries."""

    @pytest.fixture
    def populated_index(self):
        """Create an index with test elements."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        walls = []
        # Create a grid of walls
        for i in range(5):
            for j in range(5):
                wall = Wall(
                    wall_type,
                    (i * 2000, j * 2000),
                    (i * 2000 + 1000, j * 2000),
                    level,
                    height=3000,
                    name=f"Wall_{i}_{j}"
                )
                walls.append(wall)
                idx.insert(wall)

        return idx, walls, level

    def test_query_intersects(self, populated_index):
        """Test querying for intersecting elements."""
        idx, walls, _ = populated_index

        # Query a region that should contain some walls
        query_box = BoundingBox(0, 0, 0, 3000, 3000, 5000)
        results = idx.query_intersects(query_box)

        # Should find walls in the first 2x2 grid area
        assert len(results) > 0
        assert len(results) < len(walls)  # Not all walls

    def test_query_intersects_empty(self, populated_index):
        """Test querying a region with no elements."""
        idx, _, _ = populated_index

        # Query far outside the wall grid
        query_box = BoundingBox(100000, 100000, 0, 110000, 110000, 5000)
        results = idx.query_intersects(query_box)

        assert len(results) == 0

    def test_query_contains(self, populated_index):
        """Test querying for contained elements."""
        idx, walls, _ = populated_index

        # Query box that fully contains some walls
        query_box = BoundingBox(-100, -100, -100, 1200, 1200, 3500)
        results = idx.query_contains(query_box)

        # Should find walls fully inside the query box
        for wall in results:
            wall_bbox = wall.get_bounding_box()
            assert query_box.contains(wall_bbox)

    def test_query_z_range(self, populated_index):
        """Test querying by Z range."""
        idx, walls, _ = populated_index

        # Query middle of wall height
        results = idx.query_z_range(1000, 2000)
        assert len(results) == len(walls)  # All walls extend through this range

        # Query above all walls
        results = idx.query_z_range(4000, 5000)
        assert len(results) == 0

    def test_query_cut_plane(self, populated_index):
        """Test querying for floor plan cut plane."""
        idx, walls, _ = populated_index

        # Cut at 1200mm (standard floor plan cut height)
        results = idx.query_cut_plane(1200)
        assert len(results) == len(walls)

    def test_query_level(self, populated_index):
        """Test querying elements on a level."""
        idx, walls, level = populated_index

        # Query the ground level (0 to 3000)
        results = idx.query_level(level.elevation_mm, 3000)
        assert len(results) == len(walls)

    def test_query_point(self, populated_index):
        """Test querying elements at a point."""
        idx, _, _ = populated_index

        # Query at center of first wall
        results = idx.query_point(500, 100, 1500)
        assert len(results) >= 1


class TestSpatialIndexUpdate:
    """Tests for updating elements in the index."""

    def test_update_element(self):
        """Test updating an element's position in the index."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        idx.insert(wall)

        # Query original position
        old_query = BoundingBox(-100, -200, 0, 1100, 200, 3500)
        results = idx.query_intersects(old_query)
        assert wall in results

        # Move wall
        wall.set_start_point((5000, 0))
        wall.set_end_point((6000, 0))
        idx.update(wall)

        # Query new position
        new_query = BoundingBox(4900, -200, 0, 6100, 200, 3500)
        results = idx.query_intersects(new_query)
        assert wall in results


class TestSpatialIndexWithMultipleElementTypes:
    """Tests for spatial index with different element types."""

    def test_mixed_elements(self):
        """Test index with walls and floors."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)

        # Create wall
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)

        # Create floor
        concrete = Material("Concrete")
        floor_type = FloorType("Slab")
        floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
        floor = Floor(
            floor_type,
            [(0, 0), (5000, 0), (5000, 5000), (0, 5000)],
            level
        )

        idx.insert(wall)
        idx.insert(floor)

        assert idx.count == 2

        # Query that should find both
        query = BoundingBox(-100, -100, -100, 5100, 5100, 3500)
        results = idx.query_intersects(query)
        assert wall in results
        assert floor in results


class TestSpatialIndexBounds:
    """Tests for overall index bounds."""

    def test_bounds_empty(self):
        """Test bounds of empty index."""
        idx = SpatialIndex()
        assert idx.bounds is None

    def test_bounds_with_elements(self):
        """Test bounds calculation with elements."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        wall1 = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)
        wall2 = Wall(wall_type, (5000, 5000), (6000, 5000), level, height=3000)

        idx.insert(wall1)
        idx.insert(wall2)

        bounds = idx.bounds
        assert bounds is not None
        assert bounds.min_x <= 0
        assert bounds.max_x >= 6000
        assert bounds.min_y <= 0
        assert bounds.max_y >= 5000


class TestSpatialIndexIteration:
    """Tests for iterating over indexed elements."""

    def test_iteration(self):
        """Test iterating over all elements."""
        idx = SpatialIndex()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        walls = []
        for i in range(5):
            wall = Wall(wall_type, (i * 1000, 0), (i * 1000 + 500, 0), level, height=3000)
            walls.append(wall)
            idx.insert(wall)

        # Iterate and verify all elements present
        indexed_elements = list(idx)
        assert len(indexed_elements) == len(walls)
        for wall in walls:
            assert wall in indexed_elements
