"""Tests for BoundingBox class."""

import pytest
from bimascode.performance.bounding_box import BoundingBox


class TestBoundingBox:
    """Tests for BoundingBox creation and properties."""

    def test_create_bounding_box(self):
        """Test basic bounding box creation."""
        bbox = BoundingBox(0, 0, 0, 100, 100, 100)
        assert bbox.min_x == 0
        assert bbox.min_y == 0
        assert bbox.min_z == 0
        assert bbox.max_x == 100
        assert bbox.max_y == 100
        assert bbox.max_z == 100

    def test_swapped_coordinates_corrected(self):
        """Test that swapped min/max coordinates are auto-corrected."""
        bbox = BoundingBox(100, 100, 100, 0, 0, 0)
        assert bbox.min_x == 0
        assert bbox.max_x == 100

    def test_as_tuple(self):
        """Test as_tuple property for R-tree compatibility."""
        bbox = BoundingBox(0, 0, 0, 100, 100, 100)
        assert bbox.as_tuple == (0, 0, 0, 100, 100, 100)

    def test_center(self):
        """Test center calculation."""
        bbox = BoundingBox(0, 0, 0, 100, 100, 100)
        assert bbox.center == (50, 50, 50)

    def test_size(self):
        """Test size calculation."""
        bbox = BoundingBox(0, 0, 0, 100, 200, 300)
        assert bbox.size == (100, 200, 300)

    def test_volume(self):
        """Test volume calculation."""
        bbox = BoundingBox(0, 0, 0, 100, 200, 300)
        assert bbox.volume == 100 * 200 * 300


class TestBoundingBoxIntersection:
    """Tests for bounding box intersection methods."""

    def test_intersects_true(self):
        """Test intersection between overlapping boxes."""
        bbox1 = BoundingBox(0, 0, 0, 100, 100, 100)
        bbox2 = BoundingBox(50, 50, 50, 150, 150, 150)
        assert bbox1.intersects(bbox2)
        assert bbox2.intersects(bbox1)

    def test_intersects_false(self):
        """Test non-intersection between separate boxes."""
        bbox1 = BoundingBox(0, 0, 0, 100, 100, 100)
        bbox2 = BoundingBox(200, 200, 200, 300, 300, 300)
        assert not bbox1.intersects(bbox2)
        assert not bbox2.intersects(bbox1)

    def test_intersects_touching(self):
        """Test boxes that share a face."""
        bbox1 = BoundingBox(0, 0, 0, 100, 100, 100)
        bbox2 = BoundingBox(100, 0, 0, 200, 100, 100)
        assert bbox1.intersects(bbox2)

    def test_contains_true(self):
        """Test containment when one box is fully inside another."""
        outer = BoundingBox(0, 0, 0, 100, 100, 100)
        inner = BoundingBox(25, 25, 25, 75, 75, 75)
        assert outer.contains(inner)
        assert not inner.contains(outer)

    def test_contains_false(self):
        """Test containment when boxes only partially overlap."""
        bbox1 = BoundingBox(0, 0, 0, 100, 100, 100)
        bbox2 = BoundingBox(50, 50, 50, 150, 150, 150)
        assert not bbox1.contains(bbox2)
        assert not bbox2.contains(bbox1)

    def test_contains_point(self):
        """Test point containment."""
        bbox = BoundingBox(0, 0, 0, 100, 100, 100)
        assert bbox.contains_point(50, 50, 50)
        assert bbox.contains_point(0, 0, 0)  # On boundary
        assert bbox.contains_point(100, 100, 100)  # On boundary
        assert not bbox.contains_point(150, 50, 50)


class TestBoundingBoxOperations:
    """Tests for bounding box operations."""

    def test_expand(self):
        """Test expanding a bounding box."""
        bbox = BoundingBox(10, 10, 10, 90, 90, 90)
        expanded = bbox.expand(10)
        assert expanded.min_x == 0
        assert expanded.min_y == 0
        assert expanded.min_z == 0
        assert expanded.max_x == 100
        assert expanded.max_y == 100
        assert expanded.max_z == 100

    def test_union(self):
        """Test union of two bounding boxes."""
        bbox1 = BoundingBox(0, 0, 0, 50, 50, 50)
        bbox2 = BoundingBox(25, 25, 25, 100, 100, 100)
        union = bbox1.union(bbox2)
        assert union.min_x == 0
        assert union.min_y == 0
        assert union.min_z == 0
        assert union.max_x == 100
        assert union.max_y == 100
        assert union.max_z == 100

    def test_intersects_z_range(self):
        """Test Z-range intersection for floor plan filtering."""
        bbox = BoundingBox(0, 0, 1000, 100, 100, 4000)  # 1m to 4m height
        assert bbox.intersects_z_range(0, 2000)  # Below and into
        assert bbox.intersects_z_range(2000, 3000)  # Fully inside
        assert bbox.intersects_z_range(3500, 5000)  # Inside and above
        assert bbox.intersects_z_range(0, 5000)  # Fully encompassing
        assert not bbox.intersects_z_range(5000, 6000)  # Above

    def test_intersects_horizontal_plane(self):
        """Test horizontal plane intersection for floor plans."""
        bbox = BoundingBox(0, 0, 1000, 100, 100, 4000)
        assert bbox.intersects_horizontal_plane(2500)  # Inside
        assert bbox.intersects_horizontal_plane(1000)  # At bottom
        assert bbox.intersects_horizontal_plane(4000)  # At top
        assert not bbox.intersects_horizontal_plane(500)  # Below
        assert not bbox.intersects_horizontal_plane(5000)  # Above


class TestBoundingBoxFactoryMethods:
    """Tests for bounding box factory methods."""

    def test_from_points(self):
        """Test creating bbox from a list of 3D points."""
        points = [
            (0, 0, 0),
            (100, 50, 25),
            (50, 100, 75),
            (25, 25, 100),
        ]
        bbox = BoundingBox.from_points(points)
        assert bbox.min_x == 0
        assert bbox.min_y == 0
        assert bbox.min_z == 0
        assert bbox.max_x == 100
        assert bbox.max_y == 100
        assert bbox.max_z == 100

    def test_from_points_empty_raises(self):
        """Test that empty point list raises error."""
        with pytest.raises(ValueError):
            BoundingBox.from_points([])

    def test_from_polygon_2d(self):
        """Test creating bbox from 2D polygon boundary and Z range."""
        boundary = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
        bbox = BoundingBox.from_polygon_2d(boundary, 0, 3000)
        assert bbox.min_x == 0
        assert bbox.min_y == 0
        assert bbox.min_z == 0
        assert bbox.max_x == 1000
        assert bbox.max_y == 1000
        assert bbox.max_z == 3000

    def test_from_polygon_2d_empty_raises(self):
        """Test that empty boundary raises error."""
        with pytest.raises(ValueError):
            BoundingBox.from_polygon_2d([], 0, 100)
