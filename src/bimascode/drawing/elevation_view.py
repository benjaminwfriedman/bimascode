"""Elevation view generation.

Implements ElevationView for generating orthographic projections
of building facades.
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, List, Optional, Tuple

from bimascode.drawing.hlr_processor import get_hlr_processor
from bimascode.drawing.line_styles import Layer, LineStyle
from bimascode.drawing.primitives import Arc2D, Hatch2D, Line2D, Polyline2D, ViewResult
from bimascode.drawing.protocols import HasBoundingBox
from bimascode.drawing.view_base import ViewBase, ViewCropRegion, ViewScale
from bimascode.performance.bounding_box import BoundingBox

if TYPE_CHECKING:
    from bimascode.performance.representation_cache import RepresentationCache
    from bimascode.performance.spatial_index import SpatialIndex


class ElevationDirection:
    """Standard elevation view directions.

    Named by the face being viewed, following architectural convention:
    - "North Elevation" shows the North face of the building
    - To see the North face, the viewer looks South (toward the building)
    """

    NORTH = (0, -1, 0)  # View of North face (viewer looks South)
    SOUTH = (0, 1, 0)   # View of South face (viewer looks North)
    EAST = (-1, 0, 0)   # View of East face (viewer looks West)
    WEST = (1, 0, 0)    # View of West face (viewer looks East)


class ElevationView(ViewBase):
    """Elevation view generator.

    Generates 2D linework from 3D model by projecting all visible
    elements using Hidden Line Removal (HLR). Unlike section views,
    elevations do not have a cut plane - they show the exterior
    appearance of the building.

    Example:
        >>> # North elevation showing the north face of the building
        >>> view = ElevationView(
        ...     "North Elevation",
        ...     direction=ElevationDirection.NORTH,
        ... )
        >>> result = view.generate(spatial_index, cache)
    """

    def __init__(
        self,
        name: str,
        direction: Tuple[float, float, float],
        origin: Optional[Tuple[float, float, float]] = None,
        depth: float = 100000.0,
        front_clip_depth: float = 1000.0,
        height_range: Optional[Tuple[float, float]] = None,
        scale: ViewScale = ViewScale.SCALE_1_100,
        crop_region: Optional[ViewCropRegion] = None,
        template=None,
        show_hidden_lines: bool = False,
    ):
        """Create an elevation view.

        Args:
            name: View name
            direction: View direction vector (direction viewer is looking)
            origin: Origin point for the view (default: model center)
            depth: How far to look in the view direction (mm)
            front_clip_depth: How deep from the front face to include elements (mm).
                For exterior elevations, use a small value (e.g., 1000mm) to only
                show the facade. For full building projection, use a large value.
            height_range: Optional (min_z, max_z) to limit vertical extent
            scale: View scale
            crop_region: Optional crop region
            template: Optional view template for visibility control
            show_hidden_lines: Whether to show hidden lines (typically False)
        """
        super().__init__(name, scale, crop_region)

        self.direction = self._normalize(direction)
        self.origin = origin
        self.depth = depth
        self.front_clip_depth = front_clip_depth
        self.height_range = height_range
        self._template = template
        self.show_hidden_lines = show_hidden_lines

    def _normalize(self, v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Normalize a vector."""
        length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
        if length < 1e-10:
            return (0, 1, 0)
        return (v[0] / length, v[1] / length, v[2] / length)

    def _get_view_bbox(self, spatial_index) -> Optional[BoundingBox]:
        """Get bounding box for elements in the elevation view.

        The bounding box is limited by front_clip_depth to only include
        elements near the facade facing the viewer.
        """
        # Get overall model bounds
        model_bounds = spatial_index.bounds
        if model_bounds is None:
            return None

        min_x, min_y, min_z = model_bounds.min_x, model_bounds.min_y, model_bounds.min_z
        max_x, max_y, max_z = model_bounds.max_x, model_bounds.max_y, model_bounds.max_z

        # Apply height range if specified
        if self.height_range is not None:
            min_z = max(min_z, self.height_range[0])
            max_z = min(max_z, self.height_range[1])

        # Limit depth based on view direction and front_clip_depth
        # The viewer looks in direction `self.direction` at the building face.
        # The "front" face is the one the viewer sees first (closest to viewer).
        # If looking +X, the front face is at min_x (West face of building).
        # If looking -X, the front face is at max_x (East face of building).
        dx, dy, dz = self.direction

        if abs(dx) > 0.9:
            # Looking along X axis
            if dx > 0:
                # Looking +X (East): seeing West face, front is at min_x
                max_x = min_x + self.front_clip_depth
            else:
                # Looking -X (West): seeing East face, front is at max_x
                min_x = max_x - self.front_clip_depth
        elif abs(dy) > 0.9:
            # Looking along Y axis
            if dy > 0:
                # Looking +Y (North): seeing South face, front is at min_y
                max_y = min_y + self.front_clip_depth
            else:
                # Looking -Y (South): seeing North face, front is at max_y
                min_y = max_y - self.front_clip_depth

        return BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)

    def _get_up_vector(self) -> Tuple[float, float, float]:
        """Get the up vector for the view based on direction."""
        dx, dy, dz = self.direction

        # For most elevations, up is Z (vertical)
        # Unless we're looking straight up or down
        if abs(dz) > 0.99:
            # Looking up or down - use Y as up
            return (0, 1, 0)
        else:
            return (0, 0, 1)

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

        # Get elements in view frustum
        view_bbox = self._get_view_bbox(spatial_index)
        if view_bbox is None:
            result.generation_time = time.time() - start_time
            return result

        elements = spatial_index.query_intersects(view_bbox)

        # Filter by template visibility if set
        if self._template is not None:
            elements = self._template.filter_visible(elements)

        result.element_count = len(elements)

        if not elements:
            result.generation_time = time.time() - start_time
            return result

        # Process all elements with HLR
        hlr = get_hlr_processor()
        up_vector = self._get_up_vector()

        visible_lines, hidden_lines = hlr.process_elements(
            elements,
            self.direction,
            view_up=up_vector,
            show_hidden=self.show_hidden_lines,
        )

        result.lines.extend(visible_lines)
        if self.show_hidden_lines:
            result.lines.extend(hidden_lines)

        result.generation_time = time.time() - start_time

        # Apply crop region
        result = self._apply_crop_region(result)

        return result


class ReflectedCeilingPlanView(ViewBase):
    """Reflected Ceiling Plan (RCP) view generator.

    An RCP is a special type of plan view that shows the ceiling
    as if reflected in a mirror on the floor. This is the standard
    way to document ceiling layouts in architectural drawings.

    The view direction is downward (looking at the floor), but
    we show what would be seen if looking up at a mirrored floor.
    """

    def __init__(
        self,
        name: str,
        level,
        ceiling_height: float = 2700.0,
        scale: ViewScale = ViewScale.SCALE_1_100,
        crop_region: Optional[ViewCropRegion] = None,
        template=None,
    ):
        """Create a reflected ceiling plan view.

        Args:
            name: View name
            level: Level to generate RCP for
            ceiling_height: Height of ceiling above level (mm)
            scale: View scale
            crop_region: Optional crop region
            template: Optional view template
        """
        super().__init__(name, scale, crop_region)

        self.level = level
        self.ceiling_height = ceiling_height
        self._template = template

    def generate(
        self,
        spatial_index: SpatialIndex,
        representation_cache: RepresentationCache,
    ) -> ViewResult:
        """Generate reflected ceiling plan linework.

        Args:
            spatial_index: Spatial index for element queries
            representation_cache: Cache for 2D representations

        Returns:
            ViewResult containing ceiling geometry
        """
        start_time = time.time()

        result = ViewResult(view_name=self.name)

        # Query elements at ceiling level
        level_elev = self.level.elevation_mm
        ceiling_z = level_elev + self.ceiling_height

        # Get elements near the ceiling level
        elements = spatial_index.query_z_range(
            ceiling_z - 100,  # Small tolerance below
            ceiling_z + 500,  # Include things above ceiling
        )

        # Filter by template visibility if set
        if self._template is not None:
            elements = self._template.filter_visible(elements)

        # Filter to ceiling-related elements only
        ceiling_elements = [
            e for e in elements
            if type(e).__name__ in ("Ceiling", "Beam", "Light", "Sprinkler")
        ]

        result.element_count = len(ceiling_elements)

        # For RCP, we use plan representation but at ceiling height
        for element in ceiling_elements:
            if hasattr(element, "get_plan_representation"):
                # Import ViewRange here to avoid circular import
                from bimascode.drawing.view_base import ViewRange

                view_range = ViewRange(
                    cut_height=self.ceiling_height,
                    top_clip=self.ceiling_height + 500,
                    bottom_clip=self.ceiling_height - 100,
                )

                linework = element.get_plan_representation(ceiling_z, view_range)

                for item in linework:
                    if isinstance(item, Line2D):
                        result.lines.append(item)
                    elif isinstance(item, Arc2D):
                        result.arcs.append(item)
                    elif isinstance(item, Polyline2D):
                        result.polylines.append(item)
                    elif isinstance(item, Hatch2D):
                        result.hatches.append(item)

        result.generation_time = time.time() - start_time

        # Apply crop region
        result = self._apply_crop_region(result)

        return result
