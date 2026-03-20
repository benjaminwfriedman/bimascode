"""
Tests for wall joins detection and processing.
"""

import pytest
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture.wall_type import WallType, LayerFunction
from bimascode.architecture.wall import Wall
from bimascode.architecture.wall_joins import (
    JoinType,
    EndCapType,
    WallJoin,
    WallJoinDetector,
    WallJoinProcessor,
    line_intersection,
    point_distance,
    detect_and_process_wall_joins,
)
from bimascode.utils.materials import MaterialLibrary


class TestLineIntersection:
    """Tests for line intersection utility."""

    def test_perpendicular_lines(self):
        """Test intersection of perpendicular lines."""
        # Horizontal line from (0,0) to (100,0)
        # Vertical line from (50,-50) to (50,50)
        result = line_intersection((0, 0), (100, 0), (50, -50), (50, 50))

        assert result is not None
        assert abs(result[0] - 50.0) < 0.01
        assert abs(result[1] - 0.0) < 0.01

    def test_parallel_lines(self):
        """Test that parallel lines return None."""
        # Two horizontal lines
        result = line_intersection((0, 0), (100, 0), (0, 50), (100, 50))

        assert result is None

    def test_diagonal_lines(self):
        """Test intersection of diagonal lines."""
        # Line from (0,0) to (100,100)
        # Line from (0,100) to (100,0)
        result = line_intersection((0, 0), (100, 100), (0, 100), (100, 0))

        assert result is not None
        assert abs(result[0] - 50.0) < 0.01
        assert abs(result[1] - 50.0) < 0.01


class TestWallJoinDetector:
    """Tests for WallJoinDetector class."""

    @pytest.fixture
    def setup_building(self):
        """Create a building for wall join testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        return building, level, wall_type

    def test_l_junction_detection(self, setup_building):
        """Test detection of L-junction (corner)."""
        building, level, wall_type = setup_building

        # Two walls meeting at a corner
        wall1 = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        wall2 = Wall(wall_type, (5000, 0), (5000, 5000), level, height=3000)

        detector = WallJoinDetector([wall1, wall2])
        joins = detector.detect_joins()

        assert len(joins) == 1
        assert joins[0].join_type == JoinType.L_JUNCTION

    def test_t_junction_detection(self, setup_building):
        """Test detection of T-junction."""
        building, level, wall_type = setup_building

        # Main wall
        wall1 = Wall(wall_type, (0, 0), (10000, 0), level, height=3000)
        # Perpendicular wall ending at main wall
        wall2 = Wall(wall_type, (5000, 5000), (5000, 0), level, height=3000)

        detector = WallJoinDetector([wall1, wall2])
        joins = detector.detect_joins()

        assert len(joins) == 1
        assert joins[0].join_type == JoinType.T_JUNCTION

    def test_cross_junction_detection(self, setup_building):
        """Test detection of cross junction."""
        building, level, wall_type = setup_building

        # Two walls crossing in the middle
        wall1 = Wall(wall_type, (0, 2500), (10000, 2500), level, height=3000)
        wall2 = Wall(wall_type, (5000, 0), (5000, 5000), level, height=3000)

        detector = WallJoinDetector([wall1, wall2])
        joins = detector.detect_joins()

        assert len(joins) == 1
        assert joins[0].join_type == JoinType.CROSS

    def test_no_junction_parallel_walls(self, setup_building):
        """Test that parallel walls don't create junction."""
        building, level, wall_type = setup_building

        # Two parallel walls
        wall1 = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        wall2 = Wall(wall_type, (0, 2000), (5000, 2000), level, height=3000)

        detector = WallJoinDetector([wall1, wall2])
        joins = detector.detect_joins()

        assert len(joins) == 0

    def test_no_junction_non_intersecting(self, setup_building):
        """Test that non-intersecting walls don't create junction."""
        building, level, wall_type = setup_building

        # Two walls that don't intersect
        wall1 = Wall(wall_type, (0, 0), (2000, 0), level, height=3000)
        wall2 = Wall(wall_type, (5000, 0), (5000, 2000), level, height=3000)

        detector = WallJoinDetector([wall1, wall2])
        joins = detector.detect_joins()

        assert len(joins) == 0

    def test_multiple_junctions(self, setup_building):
        """Test detection of multiple junctions."""
        building, level, wall_type = setup_building

        # Three walls forming a corner room
        wall1 = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        wall2 = Wall(wall_type, (5000, 0), (5000, 5000), level, height=3000)
        wall3 = Wall(wall_type, (5000, 5000), (0, 5000), level, height=3000)

        detector = WallJoinDetector([wall1, wall2, wall3])
        joins = detector.detect_joins()

        assert len(joins) == 2  # Two L-junctions


class TestWallJoinProcessor:
    """Tests for WallJoinProcessor class."""

    @pytest.fixture
    def setup_l_junction(self):
        """Create two walls with L-junction."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        wall1 = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        wall2 = Wall(wall_type, (5000, 0), (5000, 5000), level, height=3000)

        detector = WallJoinDetector([wall1, wall2])
        joins = detector.detect_joins()

        return wall1, wall2, joins

    def test_flush_end_cap(self, setup_l_junction):
        """Test flush end cap processing."""
        wall1, wall2, joins = setup_l_junction

        processor = WallJoinProcessor(joins, EndCapType.FLUSH)
        adjustments = processor.process_joins()

        # Flush should not extend walls
        assert wall1 in adjustments
        assert wall2 in adjustments

    def test_exterior_end_cap(self, setup_l_junction):
        """Test exterior end cap processing."""
        wall1, wall2, joins = setup_l_junction

        processor = WallJoinProcessor(joins, EndCapType.EXTERIOR)
        adjustments = processor.process_joins()

        # One wall should be extended
        assert wall1 in adjustments or wall2 in adjustments


class TestLevelWallJoins:
    """Tests for Level.process_wall_joins()."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with walls."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        return building, level, wall_type

    def test_process_wall_joins(self, setup_building):
        """Test processing wall joins through Level."""
        building, level, wall_type = setup_building

        # Create L-shaped room
        wall1 = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        wall2 = Wall(wall_type, (5000, 0), (5000, 5000), level, height=3000)

        # Process joins
        level.process_wall_joins()

        # Check that adjustments were applied
        assert hasattr(wall1, '_trim_adjustments')
        assert hasattr(wall2, '_trim_adjustments')

    def test_process_wall_joins_with_end_cap_type(self, setup_building):
        """Test processing wall joins with specific end cap type."""
        building, level, wall_type = setup_building

        wall1 = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        wall2 = Wall(wall_type, (5000, 0), (5000, 5000), level, height=3000)

        # Process with exterior end cap
        level.process_wall_joins(end_cap_type=EndCapType.EXTERIOR)

        assert hasattr(wall1, '_trim_adjustments')
        assert hasattr(wall2, '_trim_adjustments')

    def test_get_walls(self, setup_building):
        """Test getting walls from level."""
        building, level, wall_type = setup_building

        wall1 = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        wall2 = Wall(wall_type, (5000, 0), (5000, 5000), level, height=3000)

        walls = level.get_walls()

        assert len(walls) == 2
        assert wall1 in walls
        assert wall2 in walls


class TestWallPriority:
    """Tests for wall priority in join processing."""

    @pytest.fixture
    def setup_mixed_walls(self):
        """Create walls with different properties."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)

        # Structural wall (thicker)
        structural_type = WallType("Structural Wall")
        concrete = MaterialLibrary.concrete()
        structural_type.add_layer(concrete, 300, LayerFunction.STRUCTURE, structural=True)

        # Non-structural wall (thinner)
        partition_type = WallType("Partition Wall")
        gypsum = MaterialLibrary.gypsum_board()
        partition_type.add_layer(gypsum, 100, LayerFunction.FINISH_INTERIOR)

        return building, level, structural_type, partition_type

    def test_structural_wall_priority(self, setup_mixed_walls):
        """Test that structural walls have higher priority."""
        building, level, structural_type, partition_type = setup_mixed_walls

        # Structural wall
        wall1 = Wall(structural_type, (0, 0), (5000, 0), level, height=3000)
        # Partition wall
        wall2 = Wall(partition_type, (5000, 0), (5000, 5000), level, height=3000)

        assert wall1.is_structural is True
        assert wall2.is_structural is False

        detector = WallJoinDetector([wall1, wall2])
        joins = detector.detect_joins()

        processor = WallJoinProcessor(joins, EndCapType.EXTERIOR)
        adjustments = processor.process_joins()

        # Both walls should have adjustments
        assert wall1 in adjustments
        assert wall2 in adjustments
