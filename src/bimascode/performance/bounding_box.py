"""Axis-Aligned Bounding Box (AABB) for spatial queries.

BoundingBox provides a simple 3D AABB representation with intersection
testing capabilities for use with spatial indexing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in 3D space.

    All coordinates are in millimeters, consistent with the BIMasCode
    coordinate system.

    Attributes:
        min_x: Minimum X coordinate
        min_y: Minimum Y coordinate
        min_z: Minimum Z coordinate
        max_x: Maximum X coordinate
        max_y: Maximum Y coordinate
        max_z: Maximum Z coordinate
    """

    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    def __post_init__(self):
        """Validate that min values are less than or equal to max values."""
        if self.min_x > self.max_x:
            old_min_x, old_max_x = self.min_x, self.max_x
            object.__setattr__(self, "min_x", old_max_x)
            object.__setattr__(self, "max_x", old_min_x)
        if self.min_y > self.max_y:
            old_min_y, old_max_y = self.min_y, self.max_y
            object.__setattr__(self, "min_y", old_max_y)
            object.__setattr__(self, "max_y", old_min_y)
        if self.min_z > self.max_z:
            old_min_z, old_max_z = self.min_z, self.max_z
            object.__setattr__(self, "min_z", old_max_z)
            object.__setattr__(self, "max_z", old_min_z)

    @property
    def as_tuple(self) -> Tuple[float, float, float, float, float, float]:
        """Return bounding box as a 6-tuple for R-tree compatibility.

        Returns:
            Tuple of (min_x, min_y, min_z, max_x, max_y, max_z)
        """
        return (self.min_x, self.min_y, self.min_z, self.max_x, self.max_y, self.max_z)

    @property
    def center(self) -> Tuple[float, float, float]:
        """Return the center point of the bounding box.

        Returns:
            Tuple of (center_x, center_y, center_z)
        """
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2,
        )

    @property
    def size(self) -> Tuple[float, float, float]:
        """Return the dimensions of the bounding box.

        Returns:
            Tuple of (width, depth, height) in mm
        """
        return (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z,
        )

    @property
    def volume(self) -> float:
        """Return the volume of the bounding box in cubic millimeters.

        Returns:
            Volume in mm³
        """
        w, d, h = self.size
        return w * d * h

    def intersects(self, other: BoundingBox) -> bool:
        """Test if this bounding box intersects another.

        Two AABBs intersect if they overlap in all three dimensions.

        Args:
            other: Another BoundingBox to test against

        Returns:
            True if the boxes intersect, False otherwise
        """
        return (
            self.min_x <= other.max_x
            and self.max_x >= other.min_x
            and self.min_y <= other.max_y
            and self.max_y >= other.min_y
            and self.min_z <= other.max_z
            and self.max_z >= other.min_z
        )

    def contains(self, other: BoundingBox) -> bool:
        """Test if this bounding box fully contains another.

        Args:
            other: Another BoundingBox to test

        Returns:
            True if other is fully contained within this box
        """
        return (
            self.min_x <= other.min_x
            and self.max_x >= other.max_x
            and self.min_y <= other.min_y
            and self.max_y >= other.max_y
            and self.min_z <= other.min_z
            and self.max_z >= other.max_z
        )

    def contains_point(self, x: float, y: float, z: float) -> bool:
        """Test if this bounding box contains a point.

        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate

        Returns:
            True if the point is inside or on the boundary
        """
        return (
            self.min_x <= x <= self.max_x
            and self.min_y <= y <= self.max_y
            and self.min_z <= z <= self.max_z
        )

    def expand(self, margin: float) -> BoundingBox:
        """Return a new bounding box expanded by a margin in all directions.

        Args:
            margin: Amount to expand in each direction (mm)

        Returns:
            New expanded BoundingBox
        """
        return BoundingBox(
            self.min_x - margin,
            self.min_y - margin,
            self.min_z - margin,
            self.max_x + margin,
            self.max_y + margin,
            self.max_z + margin,
        )

    def union(self, other: BoundingBox) -> BoundingBox:
        """Return a bounding box that contains both this and another box.

        Args:
            other: Another BoundingBox

        Returns:
            New BoundingBox encompassing both
        """
        return BoundingBox(
            min(self.min_x, other.min_x),
            min(self.min_y, other.min_y),
            min(self.min_z, other.min_z),
            max(self.max_x, other.max_x),
            max(self.max_y, other.max_y),
            max(self.max_z, other.max_z),
        )

    def intersects_z_range(self, z_min: float, z_max: float) -> bool:
        """Test if this bounding box intersects a Z range.

        Useful for floor plan cut plane filtering.

        Args:
            z_min: Minimum Z of the range
            z_max: Maximum Z of the range

        Returns:
            True if the box intersects the Z range
        """
        return self.min_z <= z_max and self.max_z >= z_min

    def intersects_horizontal_plane(self, z: float) -> bool:
        """Test if this bounding box intersects a horizontal plane at Z.

        Useful for determining if an element should appear in a floor plan.

        Args:
            z: Z coordinate of the horizontal plane

        Returns:
            True if the plane intersects this box
        """
        return self.min_z <= z <= self.max_z

    @classmethod
    def from_points(cls, points: list) -> BoundingBox:
        """Create a bounding box from a list of 3D points.

        Args:
            points: List of (x, y, z) tuples

        Returns:
            BoundingBox encompassing all points
        """
        if not points:
            raise ValueError("Cannot create bounding box from empty point list")

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        zs = [p[2] for p in points]

        return cls(min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    @classmethod
    def from_polygon_2d(
        cls, boundary: list, z_min: float, z_max: float
    ) -> BoundingBox:
        """Create a bounding box from a 2D polygon boundary and Z range.

        Args:
            boundary: List of (x, y) tuples defining polygon vertices
            z_min: Minimum Z coordinate
            z_max: Maximum Z coordinate

        Returns:
            BoundingBox for the extruded polygon
        """
        if not boundary:
            raise ValueError("Cannot create bounding box from empty boundary")

        xs = [p[0] for p in boundary]
        ys = [p[1] for p in boundary]

        return cls(min(xs), min(ys), z_min, max(xs), max(ys), z_max)
