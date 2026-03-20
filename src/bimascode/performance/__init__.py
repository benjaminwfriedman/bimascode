"""Performance infrastructure for BIMasCode.

This module provides spatial indexing and caching capabilities for
scalable floor plan generation and element querying.
"""

from bimascode.performance.bounding_box import BoundingBox
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.performance.representation_cache import RepresentationCache

__all__ = ["BoundingBox", "SpatialIndex", "RepresentationCache"]
