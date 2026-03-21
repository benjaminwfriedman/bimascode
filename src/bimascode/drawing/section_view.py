"""Section view generation.

Implements SectionView for generating vertical section cuts
through building models.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, List, Optional, Tuple

from bimascode.drawing.hlr_processor import get_hlr_processor
from bimascode.drawing.line_styles import Layer, LineStyle
from bimascode.drawing.primitives import Arc2D, Hatch2D, Line2D, Point2D, Polyline2D, ViewResult
from bimascode.drawing.protocols import HasBoundingBox, HasGeometry
from bimascode.drawing.section_cutter import get_section_cutter
from bimascode.drawing.view_base import ViewBase, ViewCropRegion, ViewScale
from bimascode.performance.bounding_box import BoundingBox

if TYPE_CHECKING:
    from bimascode.performance.representation_cache import RepresentationCache
    from bimascode.performance.spatial_index import SpatialIndex


class SectionView(ViewBase):
    """Section view generator.

    Generates 2D linework from 3D model by performing a vertical
    section cut along a defined plane, then projecting elements
    behind the cut using HLR.

    Elements are classified as:
    - Cut: Intersected by the section plane (heavy lines)
    - Visible: Behind the cut plane, visible (medium lines)
    - Hidden: Behind visible elements (dashed lines)

    Example:
        >>> # Section along X axis at Y=5000
        >>> view = SectionView(
        ...     "Section A-A",
        ...     plane_point=(0, 5000, 0),
        ...     plane_normal=(0, 1, 0),
        ...     depth=10000,
        ... )
        >>> result = view.generate(spatial_index, cache)
    """

    def __init__(
        self,
        name: str,
        plane_point: Tuple[float, float, float],
        plane_normal: Tuple[float, float, float],
        depth: float = 50000.0,
        height_range: Optional[Tuple[float, float]] = None,
        scale: ViewScale = ViewScale.SCALE_1_50,
        crop_region: Optional[ViewCropRegion] = None,
        template=None,
        show_hidden_lines: bool = True,
    ):
        """Create a section view.

        Args:
            name: View name
            plane_point: A point on the section plane
            plane_normal: Normal vector of the section plane (view direction)
            depth: How far behind the cut to show elements (mm)
            height_range: Optional (min_z, max_z) to limit vertical extent
            scale: View scale
            crop_region: Optional crop region
            template: Optional view template for visibility control
            show_hidden_lines: Whether to show hidden lines
        """
        super().__init__(name, scale, crop_region)

        self.plane_point = plane_point
        self.plane_normal = self._normalize(plane_normal)
        self.depth = depth
        self.height_range = height_range
        self._template = template
        self.show_hidden_lines = show_hidden_lines

    def _normalize(self, v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Normalize a vector."""
        import math

        length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
        if length < 1e-10:
            return (0, 1, 0)  # Default to Y direction
        return (v[0] / length, v[1] / length, v[2] / length)

    def _get_section_bbox(self) -> BoundingBox:
        """Get bounding box for elements to consider in section."""
        # Create a thin slice bbox at the section plane
        # Extended by depth in the direction of normal
        nx, ny, nz = self.plane_normal
        px, py, pz = self.plane_point

        # Section plane is perpendicular to normal
        # We need to create a bbox that captures elements:
        # 1. At the section plane (will be cut)
        # 2. Behind the section plane up to depth (will be projected)

        # For a large model, use generous bounds
        large_extent = 1e9  # Very large number

        if abs(nx) > 0.9:
            # Section plane perpendicular to X
            min_x = px
            max_x = px + self.depth * nx
            if max_x < min_x:
                min_x, max_x = max_x, min_x
            min_y, max_y = -large_extent, large_extent
            min_z, max_z = -large_extent, large_extent
        elif abs(ny) > 0.9:
            # Section plane perpendicular to Y
            min_x, max_x = -large_extent, large_extent
            min_y = py
            max_y = py + self.depth * ny
            if max_y < min_y:
                min_y, max_y = max_y, min_y
            min_z, max_z = -large_extent, large_extent
        else:
            # Section plane perpendicular to Z (unusual for building section)
            min_x, max_x = -large_extent, large_extent
            min_y, max_y = -large_extent, large_extent
            min_z = pz
            max_z = pz + self.depth * nz
            if max_z < min_z:
                min_z, max_z = max_z, min_z

        # Apply height range if specified
        if self.height_range is not None:
            min_z = max(min_z, self.height_range[0])
            max_z = min(max_z, self.height_range[1])

        return BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)

    def _is_cut_by_plane(self, element) -> bool:
        """Check if an element is cut by the section plane."""
        if not isinstance(element, HasBoundingBox):
            return False

        bbox = element.get_bounding_box()
        if bbox is None:
            return False

        # Check if plane intersects the bounding box
        px, py, pz = self.plane_point
        nx, ny, nz = self.plane_normal

        # Get bbox corners
        corners = [
            (bbox.min_x, bbox.min_y, bbox.min_z),
            (bbox.max_x, bbox.min_y, bbox.min_z),
            (bbox.min_x, bbox.max_y, bbox.min_z),
            (bbox.max_x, bbox.max_y, bbox.min_z),
            (bbox.min_x, bbox.min_y, bbox.max_z),
            (bbox.max_x, bbox.min_y, bbox.max_z),
            (bbox.min_x, bbox.max_y, bbox.max_z),
            (bbox.max_x, bbox.max_y, bbox.max_z),
        ]

        # Calculate signed distance from plane for each corner
        signs = set()
        for cx, cy, cz in corners:
            dist = (cx - px) * nx + (cy - py) * ny + (cz - pz) * nz
            if dist > 1e-6:
                signs.add(1)
            elif dist < -1e-6:
                signs.add(-1)
            else:
                signs.add(0)

        # If corners are on both sides, plane intersects bbox
        return 1 in signs and -1 in signs

    def generate(
        self,
        spatial_index: SpatialIndex,
        representation_cache: RepresentationCache,
    ) -> ViewResult:
        """Generate 2D linework from 3D model.

        Args:
            spatial_index: Spatial index for element queries
            representation_cache: Cache for 2D representations

        Returns:
            ViewResult containing all 2D geometry
        """
        start_time = time.time()

        result = ViewResult(view_name=self.name)
        cache_hits = 0

        # Query elements in the section region
        section_bbox = self._get_section_bbox()
        elements = spatial_index.query_intersects(section_bbox)

        # Filter by template visibility if set
        if self._template is not None:
            elements = self._template.filter_visible(elements)

        result.element_count = len(elements)

        # Separate cut elements from projection elements
        cut_elements = []
        projection_elements = []

        for element in elements:
            if self._is_cut_by_plane(element):
                cut_elements.append(element)
            else:
                projection_elements.append(element)

        # Process cut elements with section cutter
        cutter = get_section_cutter()
        for element in cut_elements:
            linework = self._process_cut_element(element, cutter)
            self._add_linework(result, linework)

        # Process projection elements with HLR
        hlr = get_hlr_processor()
        visible_lines, hidden_lines = hlr.process_elements(
            projection_elements,
            self.plane_normal,
            show_hidden=self.show_hidden_lines,
        )

        result.lines.extend(visible_lines)
        if self.show_hidden_lines:
            result.lines.extend(hidden_lines)

        result.cache_hits = cache_hits
        result.generation_time = time.time() - start_time

        # Apply crop region
        result = self._apply_crop_region(result)

        return result

    def _process_cut_element(self, element, cutter) -> List:
        """Process an element that is cut by the section plane."""
        if not isinstance(element, HasGeometry):
            return []

        # Use world geometry if available (includes transform to world coordinates)
        if hasattr(element, 'get_world_geometry'):
            geometry = element.get_world_geometry()
        else:
            geometry = element.get_geometry()

        if geometry is None:
            return []

        layer = self._get_layer_for_element(element)
        linework = cutter.vertical_cut(
            geometry,
            self.plane_point,
            self.plane_normal,
            style=LineStyle.cut_heavy(),
            layer=layer,
        )

        return linework

    def _add_linework(self, result: ViewResult, linework: List) -> None:
        """Add linework to view result."""
        for item in linework:
            if isinstance(item, Line2D):
                result.lines.append(item)
            elif isinstance(item, Arc2D):
                result.arcs.append(item)
            elif isinstance(item, Polyline2D):
                result.polylines.append(item)
            elif isinstance(item, Hatch2D):
                result.hatches.append(item)

    def _get_layer_for_element(self, element) -> str:
        """Get the appropriate AIA layer for an element."""
        element_type = type(element).__name__
        return Layer.for_element_type(element_type)
