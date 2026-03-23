"""Floor plan view generation.

Implements FloorPlanView for generating horizontal section cuts
of building models at specified levels.
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, List, Optional

from bimascode.drawing.line_styles import Layer, LineStyle
from bimascode.drawing.primitives import Arc2D, Hatch2D, Line2D, Polyline2D, ViewResult
from bimascode.drawing.protocols import Drawable2D, HasBoundingBox, HasGeometry
from bimascode.drawing.section_cutter import get_section_cutter
from bimascode.drawing.view_base import ViewBase, ViewCropRegion, ViewRange, ViewScale

if TYPE_CHECKING:
    from bimascode.performance.representation_cache import RepresentationCache
    from bimascode.performance.spatial_index import SpatialIndex
    from bimascode.spatial.level import Level


class FloorPlanView(ViewBase):
    """Floor plan view generator.

    Generates 2D linework from 3D model by performing a horizontal
    section cut at a specified height above the level.

    Elements are classified as:
    - Cut: Intersected by the section plane (heavy lines)
    - Below: Below the cut plane but visible (medium lines)
    - Above: Above the cut plane (dashed lines, if visible)

    Example:
        >>> view = FloorPlanView("Ground Floor Plan", level)
        >>> result = view.generate(spatial_index, cache)
        >>> print(f"Generated {len(result.lines)} lines")
    """

    def __init__(
        self,
        name: str,
        level: Level,
        view_range: Optional[ViewRange] = None,
        scale: ViewScale = ViewScale.SCALE_1_100,
        crop_region: Optional[ViewCropRegion] = None,
        template=None,
    ):
        """Create a floor plan view.

        Args:
            name: View name
            level: Level to generate floor plan for
            view_range: View range parameters (defaults to standard range)
            scale: View scale
            crop_region: Optional crop region
            template: Optional view template for visibility control
        """
        super().__init__(name, scale, crop_region)

        self.level = level
        self.view_range = view_range or ViewRange()
        self._template = template

    @property
    def cut_height(self) -> float:
        """Get absolute Z coordinate of the cut plane."""
        return self.level.elevation_mm + self.view_range.cut_height

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

        # Activate scale behavior in template
        if self._template is not None:
            self._template.set_active_scale(self.scale)

        # Get the absolute Z range for this view
        # Query from view_depth (lowest visible) to top (highest visible)
        level_elev = self.level.elevation_mm
        z_min = self.view_range.get_absolute_view_depth(level_elev)
        z_max = self.view_range.get_absolute_top(level_elev)
        cut_z = self.view_range.get_absolute_cut_height(level_elev)

        # Query elements in the visible Z range
        elements = spatial_index.query_z_range(z_min, z_max)

        # Filter by template visibility if a template is set
        if self._template is not None:
            elements = self._template.filter_visible(elements)
            # Apply scale-based filtering
            elements = self._filter_by_scale(elements)

        result.element_count = len(elements)

        # Process each element
        for element in elements:
            linework = self._process_element(
                element, cut_z, representation_cache
            )

            if linework is not None:
                # Track cache hits
                if representation_cache.get(element, cut_z) is not None:
                    cache_hits += 1

                # Filter linework by scale
                linework = self._filter_linework_by_scale(linework)

                # Add linework to result
                for item in linework:
                    # Apply scale styling
                    item = self._apply_scale_styling(element, item)

                    if isinstance(item, Line2D):
                        result.lines.append(item)
                    elif isinstance(item, Arc2D):
                        result.arcs.append(item)
                    elif isinstance(item, Polyline2D):
                        result.polylines.append(item)
                    elif isinstance(item, Hatch2D):
                        result.hatches.append(item)

        result.cache_hits = cache_hits
        result.generation_time = time.time() - start_time

        # Apply crop region
        result = self._apply_crop_region(result)

        return result

    def _process_element(
        self,
        element,
        cut_z: float,
        cache: RepresentationCache,
    ) -> Optional[List]:
        """Process a single element for floor plan generation.

        Args:
            element: Element to process
            cut_z: Absolute Z coordinate of cut plane
            cache: Representation cache

        Returns:
            List of 2D geometry primitives, or None
        """
        # Try to use cached representation first
        def compute_representation(elem, cut_height):
            return self._compute_element_linework(elem, cut_height)

        linework = cache.get_or_compute(element, cut_z, compute_representation)
        return linework

    def _compute_element_linework(
        self,
        element,
        cut_z: float,
    ) -> List:
        """Compute 2D linework for an element.

        First tries to use the element's get_plan_representation() method
        (Drawable2D protocol). Falls back to OCCT section cutting if
        the element doesn't implement Drawable2D.

        Args:
            element: Element to compute linework for
            cut_z: Absolute Z coordinate of cut plane

        Returns:
            List of 2D geometry primitives
        """
        # Check if element has get_plan_representation method
        # (may not implement full Drawable2D protocol)
        if hasattr(element, 'get_plan_representation'):
            return element.get_plan_representation(cut_z, self.view_range)

        # Fall back to OCCT section cutting
        if isinstance(element, HasGeometry):
            geometry = element.get_geometry()
            if geometry is not None:
                cutter = get_section_cutter()
                layer = self._get_layer_for_element(element)
                return cutter.horizontal_cut(
                    geometry,
                    cut_z,
                    style=LineStyle.cut_heavy(),
                    layer=layer,
                )

        # Element has no way to generate 2D representation
        return []

    def _get_layer_for_element(self, element) -> str:
        """Get the appropriate AIA layer for an element.

        Args:
            element: Element to get layer for

        Returns:
            AIA layer name
        """
        element_type = type(element).__name__
        return Layer.for_element_type(element_type)

    def _classify_element(self, element, cut_z: float) -> str:
        """Classify an element for display based on view range.

        Uses ViewRange.get_display_region() to classify elements according
        to Revit's view range model:
        - "cut": Heavy lines (element intersects cut plane)
        - "above_cut": Medium lines (between cut and top)
        - "below_cut": Medium lines (between bottom and cut)
        - "beyond_bottom": Light lines (between view_depth and bottom)
        - "hidden": Not visible

        Args:
            element: Element to classify
            cut_z: Absolute Z coordinate of cut plane (deprecated, uses view_range)

        Returns:
            Display region name
        """
        if not isinstance(element, HasBoundingBox):
            return "cut"  # Default for elements without bounding box

        bbox = element.get_bounding_box()
        if bbox is None:
            return "cut"

        # Use ViewRange's display region classification
        level_elev = self.level.elevation_mm
        return self.view_range.get_display_region(
            bbox.min_z, bbox.max_z, level_elev
        )

    def _filter_by_scale(self, elements: List) -> List:
        """Filter elements based on scale behavior.

        Args:
            elements: Elements to filter

        Returns:
            Filtered list of elements
        """
        if self._template is None:
            return elements

        filtered = []
        for element in elements:
            size_hint = self._get_element_size_hint(element)
            if self._template.should_show_element(element, size_hint):
                filtered.append(element)

        return filtered

    def _get_element_size_hint(self, element) -> Optional[float]:
        """Get size hint for element (width, diameter, etc.).

        Args:
            element: Element to analyze

        Returns:
            Size hint in mm, or None if unavailable
        """
        # Try common size attributes
        if hasattr(element, 'width'):
            return getattr(element, 'width')
        elif hasattr(element, 'diameter'):
            return getattr(element, 'diameter')
        elif hasattr(element, 'thickness'):
            return getattr(element, 'thickness')

        # Fall back to bounding box diagonal
        if isinstance(element, HasBoundingBox):
            bbox = element.get_bounding_box()
            if bbox is not None:
                dx = bbox.max_x - bbox.min_x
                dy = bbox.max_y - bbox.min_y
                return math.sqrt(dx * dx + dy * dy)

        return None

    def _filter_linework_by_scale(self, linework: List) -> List:
        """Filter line segments based on minimum length.

        Args:
            linework: List of 2D geometry items

        Returns:
            Filtered list
        """
        if self._template is None:
            return linework

        config = self._template.get_scale_behavior(self.scale)

        if config.min_line_length <= 0:
            return linework

        filtered = []
        for item in linework:
            if isinstance(item, Line2D):
                if item.length >= config.min_line_length:
                    filtered.append(item)
            elif isinstance(item, Arc2D):
                if item.length >= config.min_line_length:
                    filtered.append(item)
            else:
                # Keep polylines and hatches
                filtered.append(item)

        return filtered

    def _apply_scale_styling(self, element, geometry_item):
        """Apply scale-adjusted styling to geometry.

        Args:
            element: Source element
            geometry_item: 2D geometry item

        Returns:
            Geometry item with adjusted style
        """
        if self._template is None or not hasattr(geometry_item, 'style'):
            return geometry_item

        adjusted_style = self._template.apply_scale_adjusted_style(
            element, geometry_item.style
        )

        # Create new geometry with adjusted style
        if isinstance(geometry_item, Line2D):
            return Line2D(
                start=geometry_item.start,
                end=geometry_item.end,
                style=adjusted_style,
                layer=geometry_item.layer,
            )
        elif isinstance(geometry_item, Arc2D):
            return Arc2D(
                center=geometry_item.center,
                radius=geometry_item.radius,
                start_angle=geometry_item.start_angle,
                end_angle=geometry_item.end_angle,
                style=adjusted_style,
                layer=geometry_item.layer,
            )
        elif isinstance(geometry_item, Polyline2D):
            return Polyline2D(
                points=geometry_item.points,
                closed=geometry_item.closed,
                style=adjusted_style,
                layer=geometry_item.layer,
            )

        return geometry_item
