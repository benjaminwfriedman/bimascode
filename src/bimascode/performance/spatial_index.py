"""Spatial indexing for efficient element queries.

SpatialIndex provides R-tree based spatial indexing for fast
bounding box intersection queries on large element collections.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from rtree import index

from bimascode.performance.bounding_box import BoundingBox

if TYPE_CHECKING:
    from bimascode.core.element import Element


class SpatialIndex:
    """R-tree based spatial index for BIM elements.

    Provides O(log n) intersection queries for element filtering,
    enabling efficient floor plan generation for large models.

    Example:
        >>> spatial_index = SpatialIndex()
        >>> spatial_index.insert(wall)
        >>> elements = spatial_index.query_intersects(cut_plane_bbox)
    """

    def __init__(self):
        """Initialize the spatial index."""
        # Configure R-tree with 3D support
        props = index.Property()
        props.dimension = 3
        props.interleaved = True  # (min_x, min_y, min_z, max_x, max_y, max_z)

        self._idx = index.Index(properties=props)
        self._elements: dict[int, Element] = {}  # id -> element mapping
        self._element_ids: dict[int, int] = {}  # element id() -> index id
        self._next_id = 0

    def insert(self, element: Element) -> None:
        """Insert an element into the spatial index.

        If the element doesn't have a get_bounding_box() method, it
        will be silently skipped.

        Args:
            element: Element to insert
        """
        if not hasattr(element, "get_bounding_box"):
            return

        bbox = element.get_bounding_box()
        if bbox is None:
            return

        # Check if element already exists
        element_id = id(element)
        if element_id in self._element_ids:
            # Update existing entry
            self.update(element)
            return

        # Assign new index ID
        idx_id = self._next_id
        self._next_id += 1

        # Store mappings
        self._elements[idx_id] = element
        self._element_ids[element_id] = idx_id

        # Insert into R-tree
        self._idx.insert(idx_id, bbox.as_tuple)

    def remove(self, element: Element) -> bool:
        """Remove an element from the spatial index.

        Args:
            element: Element to remove

        Returns:
            True if element was found and removed, False otherwise
        """
        element_id = id(element)
        if element_id not in self._element_ids:
            return False

        idx_id = self._element_ids[element_id]

        # Get current bbox for removal
        if hasattr(element, "get_bounding_box"):
            bbox = element.get_bounding_box()
            if bbox is not None:
                self._idx.delete(idx_id, bbox.as_tuple)

        # Remove from mappings
        del self._elements[idx_id]
        del self._element_ids[element_id]

        return True

    def update(self, element: Element) -> None:
        """Update an element's position in the spatial index.

        Call this after modifying an element's geometry.

        Args:
            element: Element that was modified
        """
        element_id = id(element)
        if element_id not in self._element_ids:
            # Element not in index, insert it
            self.insert(element)
            return

        if not hasattr(element, "get_bounding_box"):
            return

        new_bbox = element.get_bounding_box()
        if new_bbox is None:
            return

        idx_id = self._element_ids[element_id]

        # R-tree doesn't support in-place updates, so we delete and re-insert
        # We need the old bbox for deletion, but we don't store it
        # Instead, use the element's current bbox (which may have changed)
        # This works because delete() uses the ID as primary key

        # Delete all entries with this ID (handles bbox mismatch)
        try:
            # Get bounds of the entire index to ensure we capture the old entry
            bounds = self._idx.bounds
            if bounds:
                self._idx.delete(idx_id, bounds)
        except Exception:
            pass  # Entry may not exist

        # Re-insert with new bbox
        self._idx.insert(idx_id, new_bbox.as_tuple)

    def query_intersects(self, bbox: BoundingBox) -> list[Element]:
        """Find all elements whose bounding boxes intersect the query box.

        Args:
            bbox: Query bounding box

        Returns:
            List of elements with intersecting bounding boxes
        """
        idx_ids = list(self._idx.intersection(bbox.as_tuple))
        return [self._elements[idx_id] for idx_id in idx_ids if idx_id in self._elements]

    def query_contains(self, bbox: BoundingBox) -> list[Element]:
        """Find all elements fully contained within the query box.

        Args:
            bbox: Query bounding box

        Returns:
            List of elements fully contained within bbox
        """
        # R-tree intersection gives us candidates, then filter
        candidates = self.query_intersects(bbox)
        result = []

        for element in candidates:
            element_bbox = element.get_bounding_box()
            if element_bbox is not None and bbox.contains(element_bbox):
                result.append(element)

        return result

    def query_z_range(self, z_min: float, z_max: float) -> list[Element]:
        """Find all elements that intersect a Z range.

        Useful for floor plan generation - finds all elements that
        would be cut by a horizontal plane between z_min and z_max.

        Args:
            z_min: Minimum Z coordinate
            z_max: Maximum Z coordinate

        Returns:
            List of elements intersecting the Z range
        """
        # Query with infinite X/Y bounds
        bounds = self._idx.bounds
        if not bounds:
            return []

        query_bbox = BoundingBox(
            bounds[0],  # min_x from index bounds
            bounds[1],  # min_y
            z_min,
            bounds[3],  # max_x
            bounds[4],  # max_y
            z_max,
        )

        return self.query_intersects(query_bbox)

    def query_cut_plane(self, z: float, tolerance: float = 1.0) -> list[Element]:
        """Find all elements that intersect a horizontal cut plane.

        Args:
            z: Z coordinate of the cut plane
            tolerance: Tolerance around the plane (mm)

        Returns:
            List of elements the plane passes through
        """
        return self.query_z_range(z - tolerance, z + tolerance)

    def query_level(self, level_elevation: float, level_height: float) -> list[Element]:
        """Find all elements on a specific level.

        Args:
            level_elevation: Base elevation of the level (mm)
            level_height: Height of the level (mm)

        Returns:
            List of elements on this level
        """
        return self.query_z_range(level_elevation, level_elevation + level_height)

    def query_point(self, x: float, y: float, z: float) -> list[Element]:
        """Find all elements whose bounding boxes contain a point.

        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate

        Returns:
            List of elements containing the point
        """
        # Point query using a tiny bbox
        point_bbox = BoundingBox(x, y, z, x, y, z)
        return self.query_intersects(point_bbox)

    def clear(self) -> None:
        """Remove all elements from the index."""
        # Recreate the R-tree (faster than individual deletes)
        props = index.Property()
        props.dimension = 3
        props.interleaved = True

        self._idx = index.Index(properties=props)
        self._elements.clear()
        self._element_ids.clear()
        self._next_id = 0

    @property
    def count(self) -> int:
        """Return the number of elements in the index."""
        return len(self._elements)

    @property
    def bounds(self) -> BoundingBox | None:
        """Return the bounding box of all indexed elements.

        Returns:
            BoundingBox encompassing all elements, or None if empty
        """
        if not self._elements:
            return None

        b = self._idx.bounds
        if not b:
            return None

        return BoundingBox(b[0], b[1], b[2], b[3], b[4], b[5])

    def __iter__(self) -> Iterator[Element]:
        """Iterate over all indexed elements."""
        return iter(self._elements.values())

    def __len__(self) -> int:
        """Return the number of elements in the index."""
        return len(self._elements)

    def __contains__(self, element: Element) -> bool:
        """Check if an element is in the index."""
        return id(element) in self._element_ids
