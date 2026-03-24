"""Base classes for view generation.

Defines ViewRange, ViewScale, ViewCropRegion, and the abstract ViewBase class
that all view types (floor plan, section, elevation) inherit from.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from bimascode.drawing.primitives import (
    Arc2D,
    Geometry2D,
    Hatch2D,
    Line2D,
    Point2D,
    Polyline2D,
    ViewResult,
)

if TYPE_CHECKING:
    from bimascode.performance.representation_cache import RepresentationCache
    from bimascode.performance.spatial_index import SpatialIndex


@dataclass(frozen=True)
class ViewRange:
    """Controls what's visible in a floor plan view.

    Follows Revit's view range model with five horizontal planes:
    - Top: Upper limit of visibility (elements above are hidden)
    - Cut Plane: Where the horizontal section cuts (heavy lines)
    - Bottom: Lower limit for medium-weight visualization
    - View Depth: Extended visibility below bottom (light lines)
    - Level: The base reference (implied by FloorPlanView.level)

    All offsets are measured from the associated level elevation.

    Display behavior (matching Revit):
    - Elements cut by cut plane → Heavy lines (1.4mm)
    - Elements between cut and bottom → Medium lines (0.7mm)
    - Elements between bottom and view depth → Light lines (0.35mm)
    - Elements above top or below view depth → Hidden

    Attributes:
        cut_height: Cut plane offset from level (mm). Default 1200mm (4 feet).
        top: Top plane offset from level (mm). Default 2400mm.
        bottom: Bottom plane offset from level (mm). Default 0mm (at level).
        view_depth: View depth plane offset from level (mm). Default 0mm.
            When view_depth < bottom, it extends visibility below bottom.
            Typically set same as bottom, or lower to show foundation elements.

    Example:
        >>> # Standard floor plan: cut at 1200mm, show up to 2400mm
        >>> view_range = ViewRange(cut_height=1200, top=2400, bottom=0, view_depth=0)
        >>>
        >>> # Show basement: extend view depth below floor
        >>> view_range = ViewRange(cut_height=1200, top=2400, bottom=0, view_depth=-1000)
    """

    cut_height: float = 1200.0  # Cut plane at 1.2m above floor (Revit default: 4')
    top: float = 2400.0  # Top at 2.4m above floor
    bottom: float = 0.0  # Bottom at floor level
    view_depth: float = 0.0  # View depth at floor level (same as bottom)

    # Backward compatibility properties
    @property
    def top_clip(self) -> float:
        """Backward compatibility: top_clip is now 'top'."""
        return self.top

    @property
    def bottom_clip(self) -> float:
        """Backward compatibility: bottom_clip is now 'bottom'."""
        return self.bottom

    def get_absolute_top(self, level_elevation: float) -> float:
        """Get absolute Z coordinate of top plane.

        Args:
            level_elevation: Level elevation in mm

        Returns:
            Absolute Z coordinate of top plane
        """
        return level_elevation + self.top

    def get_absolute_bottom(self, level_elevation: float) -> float:
        """Get absolute Z coordinate of bottom plane.

        Args:
            level_elevation: Level elevation in mm

        Returns:
            Absolute Z coordinate of bottom plane
        """
        return level_elevation + self.bottom

    def get_absolute_view_depth(self, level_elevation: float) -> float:
        """Get absolute Z coordinate of view depth plane.

        Args:
            level_elevation: Level elevation in mm

        Returns:
            Absolute Z coordinate of view depth plane
        """
        return level_elevation + self.view_depth

    def get_absolute_cut_height(self, level_elevation: float) -> float:
        """Get absolute Z coordinate of cut plane.

        Args:
            level_elevation: Level elevation in mm

        Returns:
            Absolute Z coordinate of cut plane
        """
        return level_elevation + self.cut_height

    def is_at_cut(self, z: float, level_elevation: float) -> bool:
        """Check if a Z coordinate is at the cut plane.

        Args:
            z: Absolute Z coordinate
            level_elevation: Level elevation in mm

        Returns:
            True if z is at the cut height
        """
        cut_z = level_elevation + self.cut_height
        return abs(z - cut_z) < 1.0  # 1mm tolerance

    def is_above_cut(self, z_min: float, level_elevation: float) -> bool:
        """Check if an element is entirely above the cut plane.

        Args:
            z_min: Element's minimum Z coordinate
            level_elevation: Level elevation in mm

        Returns:
            True if element is above the cut
        """
        cut_z = level_elevation + self.cut_height
        return z_min > cut_z

    def is_below_cut(self, z_max: float, level_elevation: float) -> bool:
        """Check if an element is entirely below the cut plane.

        Args:
            z_max: Element's maximum Z coordinate
            level_elevation: Level elevation in mm

        Returns:
            True if element is below the cut
        """
        cut_z = level_elevation + self.cut_height
        return z_max < cut_z

    def is_cut_by_plane(self, z_min: float, z_max: float, level_elevation: float) -> bool:
        """Check if an element is cut by the section plane.

        Args:
            z_min: Element's minimum Z coordinate
            z_max: Element's maximum Z coordinate
            level_elevation: Level elevation in mm

        Returns:
            True if the cut plane intersects the element
        """
        cut_z = level_elevation + self.cut_height
        return z_min <= cut_z <= z_max

    def is_visible(self, z_min: float, z_max: float, level_elevation: float) -> bool:
        """Check if an element is within the visible range.

        Elements are visible if they overlap with [view_depth, top].
        This includes elements that are cut, above cut, or below cut.

        Args:
            z_min: Element's minimum Z coordinate
            z_max: Element's maximum Z coordinate
            level_elevation: Level elevation in mm

        Returns:
            True if element is visible in this view range
        """
        abs_view_depth = level_elevation + self.view_depth
        abs_top = level_elevation + self.top

        # Element must overlap with [view_depth, top]
        return z_min <= abs_top and z_max >= abs_view_depth

    def is_above_top(self, z_min: float, level_elevation: float) -> bool:
        """Check if an element is entirely above the top plane (hidden).

        Args:
            z_min: Element's minimum Z coordinate
            level_elevation: Level elevation in mm

        Returns:
            True if element is above top plane and not visible
        """
        abs_top = level_elevation + self.top
        return z_min > abs_top

    def is_below_view_depth(self, z_max: float, level_elevation: float) -> bool:
        """Check if an element is entirely below view depth plane (hidden).

        Args:
            z_max: Element's maximum Z coordinate
            level_elevation: Level elevation in mm

        Returns:
            True if element is below view depth and not visible
        """
        abs_view_depth = level_elevation + self.view_depth
        return z_max < abs_view_depth

    def get_display_region(self, z_min: float, z_max: float, level_elevation: float) -> str:
        """Determine which display region an element belongs to.

        This determines line weight according to Revit conventions:
        - "cut": Element intersects cut plane → Heavy lines (1.4mm)
        - "above_cut": Element between cut and top → Medium lines (0.7mm)
        - "below_cut": Element between bottom and cut → Medium lines (0.7mm)
        - "beyond_bottom": Element between view_depth and bottom → Light lines (0.35mm)
        - "hidden": Element outside visible range

        Args:
            z_min: Element's minimum Z coordinate
            z_max: Element's maximum Z coordinate
            level_elevation: Level elevation in mm

        Returns:
            Display region name
        """
        if not self.is_visible(z_min, z_max, level_elevation):
            return "hidden"

        cut_z = level_elevation + self.cut_height
        bottom_z = level_elevation + self.bottom

        # Check if cut by plane
        if z_min <= cut_z <= z_max:
            return "cut"

        # Above cut plane
        if z_min > cut_z:
            return "above_cut"

        # Below cut plane - distinguish between bottom and view depth regions
        if z_max < cut_z:
            if z_max <= bottom_z:
                return "beyond_bottom"  # Between view_depth and bottom
            else:
                return "below_cut"  # Between bottom and cut

        return "hidden"


class DetailLevel(Enum):
    """Level of detail for view rendering.

    Controls visibility of small elements and line weight adjustments
    based on the view scale. Maps to standard architectural drawing scales.
    """

    VERY_HIGH = "very_high"  # 1:1 to 1:20 - Show all details
    HIGH = "high"  # 1:20 to 1:50 - Show most details
    MEDIUM = "medium"  # 1:50 to 1:100 - Standard details
    LOW = "low"  # 1:100 to 1:200 - Reduced details
    VERY_LOW = "very_low"  # 1:200+ - Minimal details

    @classmethod
    def from_scale(cls, scale: ViewScale) -> DetailLevel:
        """Automatically determine detail level from scale ratio.

        Args:
            scale: ViewScale to analyze

        Returns:
            Appropriate DetailLevel for the scale
        """
        ratio = scale.ratio

        if ratio >= 0.05:  # 1:20 or larger
            return cls.VERY_HIGH
        elif ratio >= 0.02:  # 1:50
            return cls.HIGH
        elif ratio >= 0.01:  # 1:100
            return cls.MEDIUM
        elif ratio >= 0.005:  # 1:200
            return cls.LOW
        else:  # 1:500 or smaller
            return cls.VERY_LOW


@dataclass
class ScaleBehaviorConfig:
    """Configuration for scale-dependent rendering behavior.

    Controls how views render elements at different scales to maintain
    visual clarity and appropriate level of detail.

    Attributes:
        detail_level: Level of detail to render
        min_element_size: Minimum element size to show (mm)
        min_line_length: Minimum line length to show (mm)
        line_weight_factor: Multiplier for line weights (0.7 = 30% reduction)
        show_small_details: Whether to show small details like hardware
        simplify_geometry: Whether to simplify geometry (future enhancement)
    """

    detail_level: DetailLevel
    min_element_size: float = 0.0
    min_line_length: float = 0.0
    line_weight_factor: float = 1.0
    show_small_details: bool = True
    simplify_geometry: bool = False

    @classmethod
    def for_detail_level(cls, level: DetailLevel) -> ScaleBehaviorConfig:
        """Create standard configuration for a detail level.

        Provides industry-standard thresholds for each detail level
        based on architectural drawing conventions.

        Args:
            level: DetailLevel to configure

        Returns:
            ScaleBehaviorConfig with appropriate settings
        """
        configs = {
            DetailLevel.VERY_HIGH: cls(
                detail_level=DetailLevel.VERY_HIGH,
                min_element_size=0.0,
                min_line_length=0.0,
                line_weight_factor=1.0,
                show_small_details=True,
            ),
            DetailLevel.HIGH: cls(
                detail_level=DetailLevel.HIGH,
                min_element_size=10.0,
                min_line_length=5.0,
                line_weight_factor=1.0,
                show_small_details=True,
            ),
            DetailLevel.MEDIUM: cls(
                detail_level=DetailLevel.MEDIUM,
                min_element_size=50.0,
                min_line_length=20.0,
                line_weight_factor=0.9,
                show_small_details=True,
            ),
            DetailLevel.LOW: cls(
                detail_level=DetailLevel.LOW,
                min_element_size=100.0,
                min_line_length=50.0,
                line_weight_factor=0.8,
                show_small_details=False,
            ),
            DetailLevel.VERY_LOW: cls(
                detail_level=DetailLevel.VERY_LOW,
                min_element_size=200.0,
                min_line_length=100.0,
                line_weight_factor=0.7,
                show_small_details=False,
                simplify_geometry=True,
            ),
        }
        return configs[level]


@dataclass(frozen=True)
class ViewScale:
    """Scale factor for views.

    Handles conversion between model space (mm) and paper space.

    Attributes:
        ratio: Scale ratio (e.g., 0.01 for 1:100)
        name: Human-readable scale name (e.g., "1:100")
    """

    ratio: float
    name: str = ""

    # Standard architectural scales
    SCALE_1_1 = None  # Will be set below
    SCALE_1_10 = None
    SCALE_1_20 = None
    SCALE_1_50 = None
    SCALE_1_100 = None
    SCALE_1_200 = None
    SCALE_1_500 = None

    @classmethod
    def from_string(cls, scale_str: str) -> ViewScale:
        """Create a ViewScale from a string like '1:100'.

        Args:
            scale_str: Scale string (e.g., "1:100", "1/100")

        Returns:
            ViewScale instance
        """
        # Handle both "1:100" and "1/100" formats
        if ":" in scale_str:
            parts = scale_str.split(":")
        elif "/" in scale_str:
            parts = scale_str.split("/")
        else:
            raise ValueError(f"Invalid scale format: {scale_str}")

        if len(parts) != 2:
            raise ValueError(f"Invalid scale format: {scale_str}")

        numerator = float(parts[0].strip())
        denominator = float(parts[1].strip())

        return cls(ratio=numerator / denominator, name=scale_str)

    def to_paper(self, model_dimension: float) -> float:
        """Convert model dimension to paper dimension.

        Args:
            model_dimension: Dimension in mm (model space)

        Returns:
            Dimension in mm (paper space)
        """
        return model_dimension * self.ratio

    def to_model(self, paper_dimension: float) -> float:
        """Convert paper dimension to model dimension.

        Args:
            paper_dimension: Dimension in mm (paper space)

        Returns:
            Dimension in mm (model space)
        """
        return paper_dimension / self.ratio

    def get_default_detail_level(self) -> DetailLevel:
        """Get the recommended detail level for this scale.

        Returns:
            DetailLevel appropriate for this scale
        """
        return DetailLevel.from_scale(self)

    def get_behavior_config(
        self, override_level: DetailLevel | None = None
    ) -> ScaleBehaviorConfig:
        """Get scale behavior configuration.

        Args:
            override_level: Optional detail level override

        Returns:
            ScaleBehaviorConfig with appropriate settings
        """
        level = override_level or self.get_default_detail_level()
        return ScaleBehaviorConfig.for_detail_level(level)

    @classmethod
    def recommend_for_view_type(cls, view_type: str) -> ViewScale:
        """Recommend appropriate scale for a view type.

        Provides standard scale recommendations based on architectural
        drawing conventions for different view types.

        Args:
            view_type: Type of view (floor_plan, section, elevation, detail, site)

        Returns:
            Recommended ViewScale for the view type
        """
        recommendations = {
            "floor_plan": cls.SCALE_1_100,
            "section": cls.SCALE_1_50,
            "elevation": cls.SCALE_1_100,
            "detail": cls.SCALE_1_20,
            "site": cls.SCALE_1_500,
        }
        return recommendations.get(view_type, cls.SCALE_1_100)


# Initialize standard scales
ViewScale.SCALE_1_1 = ViewScale(1.0, "1:1")
ViewScale.SCALE_1_10 = ViewScale(0.1, "1:10")
ViewScale.SCALE_1_20 = ViewScale(0.05, "1:20")
ViewScale.SCALE_1_50 = ViewScale(0.02, "1:50")
ViewScale.SCALE_1_100 = ViewScale(0.01, "1:100")
ViewScale.SCALE_1_200 = ViewScale(0.005, "1:200")
ViewScale.SCALE_1_500 = ViewScale(0.002, "1:500")


@dataclass
class ViewCropRegion:
    """Rectangular boundary that clips view extent.

    Defines a rectangular area in model coordinates that clips
    all geometry to its boundary.

    Attributes:
        min_x: Minimum X coordinate
        min_y: Minimum Y coordinate
        max_x: Maximum X coordinate
        max_y: Maximum Y coordinate
        enabled: Whether crop region is active
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float
    enabled: bool = True

    @property
    def width(self) -> float:
        """Get crop region width."""
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        """Get crop region height."""
        return self.max_y - self.min_y

    @property
    def center(self) -> Point2D:
        """Get crop region center."""
        return Point2D(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
        )

    def contains_point(self, point: Point2D) -> bool:
        """Check if a point is inside the crop region.

        Args:
            point: Point to test

        Returns:
            True if point is inside
        """
        return self.min_x <= point.x <= self.max_x and self.min_y <= point.y <= self.max_y

    def _compute_outcode(self, point: Point2D) -> int:
        """Compute Cohen-Sutherland outcode for a point."""
        code = 0
        if point.x < self.min_x:
            code |= 1  # LEFT
        elif point.x > self.max_x:
            code |= 2  # RIGHT
        if point.y < self.min_y:
            code |= 4  # BOTTOM
        elif point.y > self.max_y:
            code |= 8  # TOP
        return code

    def clip_line(self, line: Line2D) -> Line2D | None:
        """Clip a line segment to the crop region using Cohen-Sutherland.

        Args:
            line: Line to clip

        Returns:
            Clipped line, or None if line is entirely outside
        """
        if not self.enabled:
            return line

        x0, y0 = line.start.x, line.start.y
        x1, y1 = line.end.x, line.end.y

        outcode0 = self._compute_outcode(Point2D(x0, y0))
        outcode1 = self._compute_outcode(Point2D(x1, y1))

        while True:
            if not (outcode0 | outcode1):
                # Both points inside
                return Line2D(
                    start=Point2D(x0, y0),
                    end=Point2D(x1, y1),
                    style=line.style,
                    layer=line.layer,
                )
            elif outcode0 & outcode1:
                # Both points outside same region
                return None
            else:
                # Some clipping needed
                outcode_out = outcode0 if outcode0 else outcode1

                if outcode_out & 8:  # TOP
                    x = x0 + (x1 - x0) * (self.max_y - y0) / (y1 - y0)
                    y = self.max_y
                elif outcode_out & 4:  # BOTTOM
                    x = x0 + (x1 - x0) * (self.min_y - y0) / (y1 - y0)
                    y = self.min_y
                elif outcode_out & 2:  # RIGHT
                    y = y0 + (y1 - y0) * (self.max_x - x0) / (x1 - x0)
                    x = self.max_x
                else:  # LEFT
                    y = y0 + (y1 - y0) * (self.min_x - x0) / (x1 - x0)
                    x = self.min_x

                if outcode_out == outcode0:
                    x0, y0 = x, y
                    outcode0 = self._compute_outcode(Point2D(x0, y0))
                else:
                    x1, y1 = x, y
                    outcode1 = self._compute_outcode(Point2D(x1, y1))

    def clip_geometry(self, geometry: list[Geometry2D]) -> list[Geometry2D]:
        """Clip a list of geometry to the crop region.

        Args:
            geometry: List of 2D geometry primitives

        Returns:
            Clipped geometry list
        """
        if not self.enabled:
            return geometry

        result: list[Geometry2D] = []

        for geom in geometry:
            if isinstance(geom, Line2D):
                clipped = self.clip_line(geom)
                if clipped is not None:
                    result.append(clipped)
            elif isinstance(geom, Polyline2D):
                # Clip each segment individually
                lines = geom.to_lines()
                clipped_lines = []
                for line in lines:
                    clipped = self.clip_line(line)
                    if clipped is not None:
                        clipped_lines.append(clipped)
                result.extend(clipped_lines)
            elif isinstance(geom, Arc2D):
                # Simple check: if center is inside or arc endpoints are inside
                if (
                    self.contains_point(geom.center)
                    or self.contains_point(geom.start_point)
                    or self.contains_point(geom.end_point)
                ):
                    result.append(geom)
            elif isinstance(geom, Hatch2D):
                # Simple check: if any boundary point is inside
                if any(self.contains_point(p) for p in geom.boundary):
                    result.append(geom)

        return result

    def clip_view_result(self, view_result: ViewResult) -> ViewResult:
        """Clip all geometry in a ViewResult.

        Args:
            view_result: ViewResult to clip

        Returns:
            New ViewResult with clipped geometry
        """
        if not self.enabled:
            return view_result

        clipped_lines = []
        for line in view_result.lines:
            clipped = self.clip_line(line)
            if clipped is not None:
                clipped_lines.append(clipped)

        # For simplicity, keep arcs/polylines/hatches if they intersect
        clipped_arcs = [
            arc
            for arc in view_result.arcs
            if (
                self.contains_point(arc.center)
                or self.contains_point(arc.start_point)
                or self.contains_point(arc.end_point)
            )
        ]

        for pl in view_result.polylines:
            # Convert to lines and clip each
            lines = pl.to_lines()
            for line in lines:
                clipped = self.clip_line(line)
                if clipped is not None:
                    clipped_lines.append(clipped)

        clipped_hatches = [
            h for h in view_result.hatches if any(self.contains_point(p) for p in h.boundary)
        ]

        return ViewResult(
            lines=clipped_lines,
            arcs=clipped_arcs,
            polylines=[],  # Converted to lines above
            hatches=clipped_hatches,
            view_name=view_result.view_name,
            generation_time=view_result.generation_time,
            element_count=view_result.element_count,
            cache_hits=view_result.cache_hits,
        )

    @classmethod
    def from_bounds(
        cls,
        bounds: tuple[float, float, float, float],
        margin: float = 0.0,
    ) -> ViewCropRegion:
        """Create crop region from (min_x, min_y, max_x, max_y) bounds.

        Args:
            bounds: Tuple of (min_x, min_y, max_x, max_y)
            margin: Optional margin to add around bounds

        Returns:
            ViewCropRegion instance
        """
        return cls(
            min_x=bounds[0] - margin,
            min_y=bounds[1] - margin,
            max_x=bounds[2] + margin,
            max_y=bounds[3] + margin,
        )


class ViewBase(ABC):
    """Abstract base class for all view types.

    Provides common interface for floor plans, sections, and elevations.
    """

    def __init__(
        self,
        name: str,
        scale: ViewScale = ViewScale.SCALE_1_100,
        crop_region: ViewCropRegion | None = None,
    ):
        """Initialize a view.

        Args:
            name: View name
            scale: View scale
            crop_region: Optional crop region
        """
        self.name = name
        self.scale = scale
        self.crop_region = crop_region
        self._template = None

    @property
    def template(self):
        """Get the view template."""
        return self._template

    @template.setter
    def template(self, value):
        """Set the view template."""
        self._template = value

    @abstractmethod
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
        pass

    def _apply_crop_region(self, result: ViewResult) -> ViewResult:
        """Apply crop region to view result.

        Args:
            result: ViewResult to clip

        Returns:
            Clipped ViewResult
        """
        if self.crop_region is not None and self.crop_region.enabled:
            return self.crop_region.clip_view_result(result)
        return result
