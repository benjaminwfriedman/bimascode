"""Performance benchmark tests for Sprint 5.

These tests verify that the spatial index and caching meet performance targets:
- Intersection test: <1ms per query
- Index build time: <100ms for 1000 elements
- Cache speedup: 90% reduction in section cut computation time
"""

import time

import pytest

from bimascode.architecture.ceiling import Ceiling
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.architecture.floor import Floor
from bimascode.architecture.floor_type import FloorType
from bimascode.architecture.wall import Wall
from bimascode.architecture.wall_type import LayerFunction, WallType
from bimascode.performance.bounding_box import BoundingBox
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room import Room
from bimascode.structure.column import StructuralColumn
from bimascode.structure.column_type import ColumnType
from bimascode.structure.profile import RectangularProfile
from bimascode.utils.materials import MaterialLibrary


def create_wall_type(name: str, width: float = 200) -> WallType:
    """Helper to create a wall type with a single layer."""
    wall_type = WallType(name)
    concrete = MaterialLibrary.concrete()
    wall_type.add_layer(concrete, width, LayerFunction.STRUCTURE, structural=True)
    return wall_type


class TestSpatialIndexPerformance:
    """Performance tests for SpatialIndex."""

    @pytest.fixture
    def large_model(self):
        """Create a model with 1000+ elements."""
        building = Building("Performance Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        elements = []

        # Create grid of walls (40x25 = 1000 walls)
        for i in range(40):
            for j in range(25):
                wall = Wall(
                    wall_type,
                    (i * 1000, j * 1000),
                    (i * 1000 + 500, j * 1000),
                    level,
                    height=3000,
                    name=f"Wall_{i}_{j}",
                )
                elements.append(wall)

        return building, level, elements

    def test_spatial_index_build_time(self, large_model):
        """Index build time should be <100ms for 1000 elements."""
        _, _, elements = large_model
        idx = SpatialIndex()

        start = time.time()
        for element in elements:
            idx.insert(element)
        elapsed = time.time() - start

        assert idx.count == len(elements)
        assert elapsed < 0.1, f"Index build took {elapsed*1000:.1f}ms, expected <100ms"

    def test_spatial_index_query_time(self, large_model):
        """Spatial query should be <1ms per query."""
        _, _, elements = large_model
        idx = SpatialIndex()

        for element in elements:
            idx.insert(element)

        # Typical floor plan query box
        query_box = BoundingBox(5000, 5000, 0, 15000, 15000, 3500)

        # Run many queries and average
        num_queries = 100
        start = time.time()
        for _ in range(num_queries):
            idx.query_intersects(query_box)
        elapsed = (time.time() - start) / num_queries

        assert elapsed < 0.001, f"Query took {elapsed*1000:.3f}ms, expected <1ms"

    def test_spatial_index_filtering_efficiency(self, large_model):
        """Should filter 1000 elements to ~100 for typical floor plan."""
        _, _, elements = large_model
        idx = SpatialIndex()

        for element in elements:
            idx.insert(element)

        # Query covering ~10% of the model area
        bounds = idx.bounds
        query_box = BoundingBox(
            bounds.min_x,
            bounds.min_y,
            0,
            bounds.min_x + (bounds.max_x - bounds.min_x) * 0.32,  # ~10% area
            bounds.min_y + (bounds.max_y - bounds.min_y) * 0.32,
            3500,
        )

        results = idx.query_intersects(query_box)

        # Should return roughly 10% of elements
        assert len(results) < len(elements), "Should filter out most elements"
        assert len(results) < len(elements) * 0.2, "Should return <20% of elements"

    def test_spatial_index_z_filter_efficiency(self, large_model):
        """Z-range filter should quickly find level-specific elements."""
        _, _, elements = large_model
        idx = SpatialIndex()

        for element in elements:
            idx.insert(element)

        # Query for cut plane at 1200mm
        start = time.time()
        for _ in range(100):
            idx.query_cut_plane(1200)
        elapsed = (time.time() - start) / 100

        assert elapsed < 0.001, f"Z-filter query took {elapsed*1000:.3f}ms"


class TestCachePerformance:
    """Performance tests for RepresentationCache."""

    def test_cache_speedup(self):
        """Second floor plan generation should be 90% faster with caching."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        # Create walls
        walls = []
        for i in range(100):
            wall = Wall(wall_type, (i * 100, 0), (i * 100 + 50, 0), level, height=3000)
            walls.append(wall)

        # Simulate expensive section cut computation
        def expensive_compute(element, cut_height):
            # Simulate ~1ms of computation
            start = time.time()
            total = 0
            while time.time() - start < 0.001:
                total += 1
            return {"lines": [(0, 0), (100, 0)]}

        # First pass - all cache misses
        start = time.time()
        for wall in walls:
            cache.get_or_compute(wall, 1200.0, expensive_compute)
        first_pass_time = time.time() - start

        # Second pass - all cache hits
        start = time.time()
        for wall in walls:
            cache.get_or_compute(wall, 1200.0, expensive_compute)
        second_pass_time = time.time() - start

        # Second pass should be at least 90% faster
        speedup = 1 - (second_pass_time / first_pass_time)
        assert speedup > 0.9, f"Cache speedup was only {speedup*100:.1f}%, expected >90%"

    def test_cache_hit_rate(self):
        """Cache should achieve high hit rate for repeated queries."""
        cache = RepresentationCache()
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        walls = []
        for i in range(50):
            wall = Wall(wall_type, (i * 100, 0), (i * 100 + 50, 0), level, height=3000)
            walls.append(wall)

        def compute_func(element, cut_height):
            return {"computed": True}

        # Simulate multiple floor plan generations
        for _ in range(5):
            for wall in walls:
                cache.get_or_compute(wall, 1200.0, compute_func)

        # Should have 50 misses (first pass) and 200 hits (4 more passes)
        expected_hit_rate = (200 / 250) * 100  # 80%
        actual_hit_rate = cache.stats.hit_rate

        assert (
            actual_hit_rate >= expected_hit_rate - 1
        ), f"Hit rate was {actual_hit_rate:.1f}%, expected ~{expected_hit_rate:.1f}%"


class TestBoundingBoxPerformance:
    """Performance tests for BoundingBox calculations."""

    def test_bbox_calculation_speed(self):
        """Bounding box calculation should be fast."""
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        walls = []
        for i in range(1000):
            wall = Wall(wall_type, (i * 100, 0), (i * 100 + 50, 0), level, height=3000)
            walls.append(wall)

        # Calculate all bounding boxes
        start = time.time()
        for wall in walls:
            wall.get_bounding_box()
        elapsed = time.time() - start

        # Should complete in <50ms for 1000 elements
        assert elapsed < 0.05, f"Bbox calculation took {elapsed*1000:.1f}ms, expected <50ms"


class TestMixedElementTypePerformance:
    """Performance tests with multiple element types."""

    def test_mixed_model_performance(self):
        """Test performance with varied element types."""
        building = Building("Mixed Model")
        level = Level(building, "Ground", 0)

        # Create various element types
        wall_type = create_wall_type("Standard", 200)
        concrete = MaterialLibrary.concrete()
        floor_type = FloorType("Slab")
        floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
        ceiling_type = CeilingType("GWB", thickness=12.5, material=concrete)
        column_profile = RectangularProfile(300, 300)
        column_type = ColumnType("C1", column_profile, material=concrete)

        idx = SpatialIndex()
        element_count = 0

        # Add walls (200)
        for i in range(20):
            for j in range(10):
                wall = Wall(
                    wall_type, (i * 1000, j * 1000), (i * 1000 + 500, j * 1000), level, height=3000
                )
                idx.insert(wall)
                element_count += 1

        # Add floors (10)
        for i in range(10):
            floor = Floor(
                floor_type,
                [(i * 2000, 0), (i * 2000 + 1500, 0), (i * 2000 + 1500, 1500), (i * 2000, 1500)],
                level,
            )
            idx.insert(floor)
            element_count += 1

        # Add ceilings (10)
        for i in range(10):
            ceiling = Ceiling(
                ceiling_type,
                [(i * 2000, 0), (i * 2000 + 1500, 0), (i * 2000 + 1500, 1500), (i * 2000, 1500)],
                level,
                height=2700,
            )
            idx.insert(ceiling)
            element_count += 1

        # Add columns (25)
        for i in range(5):
            for j in range(5):
                column = StructuralColumn(column_type, level, (i * 4000, j * 2000), height=3000)
                idx.insert(column)
                element_count += 1

        # Add rooms (10)
        for i in range(10):
            room = Room(
                f"Room {i}",
                f"R{i:03d}",
                [(i * 2000, 0), (i * 2000 + 1500, 0), (i * 2000 + 1500, 1500), (i * 2000, 1500)],
                level,
            )
            idx.insert(room)
            element_count += 1

        assert idx.count == element_count

        # Query performance should still be fast
        query_box = BoundingBox(5000, 0, 0, 15000, 10000, 3500)
        start = time.time()
        for _ in range(100):
            idx.query_intersects(query_box)
        elapsed = (time.time() - start) / 100

        assert elapsed < 0.001, f"Query took {elapsed*1000:.3f}ms, expected <1ms"


class TestMemoryOverhead:
    """Tests for memory efficiency."""

    def test_cache_memory_limit(self):
        """Cache should respect max_entries limit."""
        cache = RepresentationCache(max_entries=100)
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_wall_type("Standard", 200)

        # Try to add more entries than limit
        for i in range(200):
            wall = Wall(wall_type, (i * 100, 0), (i * 100 + 50, 0), level, height=3000)
            cache.put(wall, 1200.0, {"large": "data" * 100})

        # Should not exceed limit
        assert cache.size <= 100
