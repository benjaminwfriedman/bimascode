"""Tests for RepresentationCache class."""

import pytest
import time
from bimascode.performance.representation_cache import RepresentationCache, CachedRepresentation
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture.wall import Wall
from bimascode.architecture.wall_type import WallType, LayerFunction
from bimascode.utils.materials import MaterialLibrary


def create_wall_type(name: str, width: float = 200) -> WallType:
    """Helper to create a wall type with a single layer."""
    wall_type = WallType(name)
    concrete = MaterialLibrary.concrete()
    wall_type.add_layer(concrete, width, LayerFunction.STRUCTURE, structural=True)
    return wall_type


class MockLinework:
    """Mock 2D linework for testing."""

    def __init__(self, lines):
        self.lines = lines

    def __eq__(self, other):
        if not isinstance(other, MockLinework):
            return False
        return self.lines == other.lines


class TestRepresentationCacheBasics:
    """Basic tests for RepresentationCache."""

    def test_create_empty_cache(self):
        """Test creating an empty cache."""
        cache = RepresentationCache()
        assert cache.size == 0
        assert len(cache) == 0

    def test_put_and_get(self):
        """Test storing and retrieving cached data."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        linework = MockLinework([(0, 0), (100, 0)])
        cache.put(wall, 1200.0, linework)

        result = cache.get(wall, 1200.0)
        assert result == linework
        assert cache.size == 1

    def test_get_miss(self):
        """Test cache miss returns None."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        result = cache.get(wall, 1200.0)
        assert result is None

    def test_different_cut_heights(self):
        """Test different cut heights have separate cache entries."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        linework1 = MockLinework([(0, 0), (100, 0)])
        linework2 = MockLinework([(0, 0), (200, 0)])

        cache.put(wall, 1000.0, linework1)
        cache.put(wall, 2000.0, linework2)

        assert cache.get(wall, 1000.0) == linework1
        assert cache.get(wall, 2000.0) == linework2
        assert cache.size == 2


class TestRepresentationCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_element(self):
        """Test invalidating all entries for an element."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        # Cache at multiple cut heights
        cache.put(wall, 1000.0, MockLinework([]))
        cache.put(wall, 1200.0, MockLinework([]))
        cache.put(wall, 2000.0, MockLinework([]))

        assert cache.size == 3

        count = cache.invalidate(wall)

        assert count == 3
        assert cache.size == 0

    def test_invalidate_cut_height(self):
        """Test invalidating all entries at a cut height."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        wall1 = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)
        wall2 = Wall(wall_type, (2000, 0), (3000, 0), level, height=3000)

        cache.put(wall1, 1200.0, MockLinework([]))
        cache.put(wall1, 2000.0, MockLinework([]))
        cache.put(wall2, 1200.0, MockLinework([]))

        count = cache.invalidate_cut_height(1200.0)

        assert count == 2
        assert cache.size == 1
        assert cache.get(wall1, 2000.0) is not None

    def test_clear(self):
        """Test clearing entire cache."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        for i in range(10):
            wall = Wall(wall_type, (i * 1000, 0), (i * 1000 + 500, 0), level, height=3000)
            cache.put(wall, 1200.0, MockLinework([]))

        assert cache.size == 10
        cache.clear()
        assert cache.size == 0

    def test_stale_cache_invalidation(self):
        """Test that modified elements have stale cache invalidated."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        # Cache some linework
        cache.put(wall, 1200.0, MockLinework([(0, 0), (100, 0)]))

        # Modify wall (this calls _invalidate_cache() via invalidate_geometry())
        time.sleep(0.01)  # Ensure timestamp difference
        wall.set_start_point((100, 0))

        # Cache should be invalidated on next get
        result = cache.get(wall, 1200.0)
        assert result is None


class TestGetOrCompute:
    """Tests for get_or_compute method."""

    def test_get_or_compute_miss(self):
        """Test get_or_compute on cache miss."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        compute_called = [False]

        def compute_func(element, cut_height):
            compute_called[0] = True
            return MockLinework([(0, 0), (100, 0)])

        result = cache.get_or_compute(wall, 1200.0, compute_func)

        assert compute_called[0] is True
        assert result is not None
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

    def test_get_or_compute_hit(self):
        """Test get_or_compute on cache hit."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        expected = MockLinework([(0, 0), (100, 0)])
        cache.put(wall, 1200.0, expected)

        compute_called = [False]

        def compute_func(element, cut_height):
            compute_called[0] = True
            return MockLinework([(0, 0), (999, 0)])

        result = cache.get_or_compute(wall, 1200.0, compute_func)

        assert compute_called[0] is False  # Should not compute
        assert result == expected
        assert cache.stats.hits == 1


class TestCacheStats:
    """Tests for cache statistics."""

    def test_hit_rate_calculation(self):
        """Test hit rate percentage calculation."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        def compute_func(element, cut_height):
            return MockLinework([])

        # Generate some hits and misses
        cache.get_or_compute(wall, 1200.0, compute_func)  # Miss
        cache.get_or_compute(wall, 1200.0, compute_func)  # Hit
        cache.get_or_compute(wall, 1200.0, compute_func)  # Hit
        cache.get_or_compute(wall, 1200.0, compute_func)  # Hit

        assert cache.stats.hits == 3
        assert cache.stats.misses == 1
        assert cache.stats.hit_rate == 75.0

    def test_hit_rate_zero_queries(self):
        """Test hit rate with no queries."""
        cache = RepresentationCache()
        assert cache.stats.hit_rate == 0.0


class TestCacheEviction:
    """Tests for cache eviction (LRU)."""

    def test_max_entries_eviction(self):
        """Test that oldest entries are evicted when cache is full."""
        cache = RepresentationCache(max_entries=5)
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        walls = []
        for i in range(10):
            wall = Wall(wall_type, (i * 1000, 0), (i * 1000 + 500, 0), level, height=3000)
            walls.append(wall)
            cache.put(wall, 1200.0, MockLinework([i]))

        # Should have evicted early entries
        assert cache.size == 5

        # First walls should be evicted
        assert cache.get(walls[0], 1200.0) is None
        assert cache.get(walls[1], 1200.0) is None

        # Later walls should still be cached
        assert cache.get(walls[9], 1200.0) is not None


class TestCachedRepresentation:
    """Tests for CachedRepresentation dataclass."""

    def test_is_valid_fresh(self):
        """Test validity check for fresh cache."""
        cached = CachedRepresentation(
            element_id=12345,
            cut_height=1200.0,
            linework=MockLinework([]),
            timestamp=time.time(),
            element_modified=time.time()
        )

        # Cache is valid if element hasn't been modified since
        assert cached.is_valid(cached.element_modified)

    def test_is_valid_stale(self):
        """Test validity check for stale cache."""
        old_time = time.time() - 1.0

        cached = CachedRepresentation(
            element_id=12345,
            cut_height=1200.0,
            linework=MockLinework([]),
            timestamp=old_time,
            element_modified=old_time
        )

        # Cache is stale if element was modified after
        new_modification_time = time.time()
        assert not cached.is_valid(new_modification_time)


class TestCacheContains:
    """Tests for __contains__ method."""

    def test_contains_true(self):
        """Test element in cache."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        cache.put(wall, 1200.0, MockLinework([]))
        assert wall in cache

    def test_contains_false(self):
        """Test element not in cache."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)
        wall = Wall(wall_type, (0, 0), (1000, 0), level, height=3000)

        assert wall not in cache
