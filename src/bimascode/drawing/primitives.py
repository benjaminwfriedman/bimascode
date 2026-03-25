"""2D drawing primitives for view generation.

This module defines the fundamental 2D geometric primitives used
in floor plans, sections, and elevations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Union

from bimascode.drawing.line_styles import LineStyle


@dataclass(frozen=True)
class Point2D:
    """2D point in view coordinates.

    All coordinates are in millimeters unless scaled by a ViewScale.

    Attributes:
        x: X coordinate
        y: Y coordinate
    """

    x: float
    y: float

    def distance_to(self, other: Point2D) -> float:
        """Calculate distance to another point.

        Args:
            other: Target point

        Returns:
            Distance in mm
        """
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx * dx + dy * dy)

    def translate(self, dx: float, dy: float) -> Point2D:
        """Return a new point translated by (dx, dy).

        Args:
            dx: X translation
            dy: Y translation

        Returns:
            Translated Point2D
        """
        return Point2D(self.x + dx, self.y + dy)

    def rotate(self, angle: float, origin: Point2D | None = None) -> Point2D:
        """Return a new point rotated around an origin.

        Args:
            angle: Rotation angle in radians
            origin: Center of rotation (default: (0, 0))

        Returns:
            Rotated Point2D
        """
        if origin is None:
            origin = Point2D(0, 0)

        # Translate to origin
        dx = self.x - origin.x
        dy = self.y - origin.y

        # Rotate
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        new_x = dx * cos_a - dy * sin_a
        new_y = dx * sin_a + dy * cos_a

        # Translate back
        return Point2D(new_x + origin.x, new_y + origin.y)

    def as_tuple(self) -> tuple[float, float]:
        """Return point as (x, y) tuple."""
        return (self.x, self.y)


@dataclass
class Line2D:
    """2D line segment with styling.

    Represents a single line segment in a 2D view with associated
    line style and layer assignment.

    Attributes:
        start: Start point
        end: End point
        style: Line styling (weight, type, color)
        layer: CAD layer name (e.g., "A-WALL", "A-DOOR")
    """

    start: Point2D
    end: Point2D
    style: LineStyle
    layer: str = "0"

    @property
    def length(self) -> float:
        """Get line length in mm."""
        return self.start.distance_to(self.end)

    @property
    def midpoint(self) -> Point2D:
        """Get line midpoint."""
        return Point2D(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2,
        )

    @property
    def angle(self) -> float:
        """Get line angle in radians."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return math.atan2(dy, dx)

    def translate(self, dx: float, dy: float) -> Line2D:
        """Return a translated copy of this line."""
        return Line2D(
            start=self.start.translate(dx, dy),
            end=self.end.translate(dx, dy),
            style=self.style,
            layer=self.layer,
        )

    def reverse(self) -> Line2D:
        """Return a copy with start and end swapped."""
        return Line2D(
            start=self.end,
            end=self.start,
            style=self.style,
            layer=self.layer,
        )


@dataclass
class Arc2D:
    """2D arc segment with styling.

    Represents a circular arc in a 2D view.

    Attributes:
        center: Arc center point
        radius: Arc radius in mm
        start_angle: Start angle in radians
        end_angle: End angle in radians
        style: Line styling
        layer: CAD layer name
    """

    center: Point2D
    radius: float
    start_angle: float
    end_angle: float
    style: LineStyle
    layer: str = "0"

    @property
    def start_point(self) -> Point2D:
        """Get the arc start point."""
        return Point2D(
            self.center.x + self.radius * math.cos(self.start_angle),
            self.center.y + self.radius * math.sin(self.start_angle),
        )

    @property
    def end_point(self) -> Point2D:
        """Get the arc end point."""
        return Point2D(
            self.center.x + self.radius * math.cos(self.end_angle),
            self.center.y + self.radius * math.sin(self.end_angle),
        )

    @property
    def sweep_angle(self) -> float:
        """Get the sweep angle in radians."""
        sweep = self.end_angle - self.start_angle
        if sweep < 0:
            sweep += 2 * math.pi
        return sweep

    @property
    def length(self) -> float:
        """Get arc length in mm."""
        return abs(self.sweep_angle) * self.radius

    def translate(self, dx: float, dy: float) -> Arc2D:
        """Return a translated copy of this arc."""
        return Arc2D(
            center=self.center.translate(dx, dy),
            radius=self.radius,
            start_angle=self.start_angle,
            end_angle=self.end_angle,
            style=self.style,
            layer=self.layer,
        )


@dataclass
class Polyline2D:
    """2D polyline (connected line segments) with styling.

    Represents a series of connected line segments, optionally closed.

    Attributes:
        points: List of vertices
        closed: Whether the polyline forms a closed loop
        style: Line styling
        layer: CAD layer name
    """

    points: list[Point2D]
    closed: bool = False
    style: LineStyle = field(default_factory=LineStyle.default)
    layer: str = "0"

    @property
    def num_points(self) -> int:
        """Get number of vertices."""
        return len(self.points)

    @property
    def num_segments(self) -> int:
        """Get number of line segments."""
        if len(self.points) < 2:
            return 0
        n = len(self.points) - 1
        if self.closed:
            n += 1
        return n

    @property
    def length(self) -> float:
        """Get total polyline length in mm."""
        if len(self.points) < 2:
            return 0.0

        total = 0.0
        for i in range(len(self.points) - 1):
            total += self.points[i].distance_to(self.points[i + 1])

        if self.closed and len(self.points) > 2:
            total += self.points[-1].distance_to(self.points[0])

        return total

    def to_lines(self) -> list[Line2D]:
        """Convert to individual Line2D segments."""
        lines = []
        if len(self.points) < 2:
            return lines

        for i in range(len(self.points) - 1):
            lines.append(
                Line2D(
                    start=self.points[i],
                    end=self.points[i + 1],
                    style=self.style,
                    layer=self.layer,
                )
            )

        if self.closed and len(self.points) > 2:
            lines.append(
                Line2D(
                    start=self.points[-1],
                    end=self.points[0],
                    style=self.style,
                    layer=self.layer,
                )
            )

        return lines

    def translate(self, dx: float, dy: float) -> Polyline2D:
        """Return a translated copy of this polyline."""
        return Polyline2D(
            points=[p.translate(dx, dy) for p in self.points],
            closed=self.closed,
            style=self.style,
            layer=self.layer,
        )


@dataclass
class Hatch2D:
    """2D hatch pattern for filled regions.

    Represents a filled area with a pattern (solid, diagonal, etc.).

    Attributes:
        boundary: List of boundary points (closed polygon)
        pattern: Hatch pattern name (e.g., "SOLID", "ANSI31", "AR-CONC")
        scale: Pattern scale factor
        rotation: Pattern rotation in degrees
        color: Fill color as RGB tuple (0-255)
        layer: CAD layer name
    """

    boundary: list[Point2D]
    pattern: str = "SOLID"
    scale: float = 1.0
    rotation: float = 0.0
    color: tuple[int, int, int] | None = None
    layer: str = "0"

    @property
    def num_points(self) -> int:
        """Get number of boundary vertices."""
        return len(self.boundary)

    def translate(self, dx: float, dy: float) -> Hatch2D:
        """Return a translated copy of this hatch."""
        return Hatch2D(
            boundary=[p.translate(dx, dy) for p in self.boundary],
            pattern=self.pattern,
            scale=self.scale,
            rotation=self.rotation,
            color=self.color,
            layer=self.layer,
        )


class TextAlignment:
    """Text alignment options for TextNote2D.

    These values map directly to ezdxf MTEXT attachment points.
    """

    TOP_LEFT = "TOP_LEFT"
    TOP_CENTER = "TOP_CENTER"
    TOP_RIGHT = "TOP_RIGHT"
    MIDDLE_LEFT = "MIDDLE_LEFT"
    MIDDLE_CENTER = "MIDDLE_CENTER"
    MIDDLE_RIGHT = "MIDDLE_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_CENTER = "BOTTOM_CENTER"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"


@dataclass(frozen=True)
class TextNote2D:
    """2D text annotation for drawings.

    Represents freestanding text in a 2D view, supporting multi-line
    content, word wrapping, and various alignment options. Exports to
    DXF MTEXT entities.

    Attributes:
        position: Insertion point for the text
        content: Text content (supports newlines with \\n)
        height: Text height in mm
        alignment: Text alignment (see TextAlignment constants)
        rotation: Text rotation in degrees
        width: Maximum text width for word wrapping (0 = no wrapping)
        layer: CAD layer name
    """

    position: Point2D
    content: str
    height: float = 150.0
    alignment: str = "MIDDLE_LEFT"
    rotation: float = 0.0
    width: float = 0.0
    layer: str = "G-ANNO"

    @property
    def is_multiline(self) -> bool:
        """Check if text contains multiple lines."""
        return "\n" in self.content

    @property
    def line_count(self) -> int:
        """Get number of lines in text content."""
        return self.content.count("\n") + 1

    def translate(self, dx: float, dy: float) -> TextNote2D:
        """Return a translated copy of this text note."""
        return TextNote2D(
            position=self.position.translate(dx, dy),
            content=self.content,
            height=self.height,
            alignment=self.alignment,
            rotation=self.rotation,
            width=self.width,
            layer=self.layer,
        )


@dataclass(frozen=True)
class LinearDimension2D:
    """2D linear dimension between two points.

    Represents a dimension annotation showing the distance between
    two points with extension lines and dimension text.

    Attributes:
        start: First measurement point
        end: Second measurement point
        offset: Perpendicular distance from baseline to dimension line
        text: Dimension text ("<>" = auto-calculate, or custom string)
        precision: Decimal places for auto-calculated text
        style: Line styling for dimension/extension lines
        layer: CAD layer name
    """

    start: Point2D
    end: Point2D
    offset: float
    text: str = "<>"
    precision: int = 0
    style: LineStyle = field(default_factory=LineStyle.default)
    layer: str = "G-ANNO-DIMS"

    @property
    def distance(self) -> float:
        """Get the measured distance in mm."""
        return self.start.distance_to(self.end)

    @property
    def midpoint(self) -> Point2D:
        """Get the midpoint of the baseline."""
        return Point2D(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2,
        )

    @property
    def angle(self) -> float:
        """Get the baseline angle in radians."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return math.atan2(dy, dx)

    def translate(self, dx: float, dy: float) -> LinearDimension2D:
        """Return a translated copy."""
        return LinearDimension2D(
            start=self.start.translate(dx, dy),
            end=self.end.translate(dx, dy),
            offset=self.offset,
            text=self.text,
            precision=self.precision,
            style=self.style,
            layer=self.layer,
        )


# Type alias for any 2D geometry primitive
Geometry2D = Union[Line2D, Arc2D, Polyline2D, Hatch2D, LinearDimension2D, TextNote2D]


@dataclass
class ViewResult:
    """Result of view generation containing all 2D geometry.

    Contains all linework, arcs, polylines, hatches, and dimensions
    generated by a view, along with metadata about the view generation.

    Attributes:
        lines: List of line segments
        arcs: List of arcs
        polylines: List of polylines
        hatches: List of hatches
        dimensions: List of dimensions
        view_name: Name of the view that generated this result
        generation_time: Time taken to generate in seconds
        element_count: Number of elements processed
        cache_hits: Number of cache hits during generation
    """

    lines: list[Line2D] = field(default_factory=list)
    arcs: list[Arc2D] = field(default_factory=list)
    polylines: list[Polyline2D] = field(default_factory=list)
    hatches: list[Hatch2D] = field(default_factory=list)
    dimensions: list[LinearDimension2D] = field(default_factory=list)
    text_notes: list[TextNote2D] = field(default_factory=list)
    view_name: str = ""
    generation_time: float = 0.0
    element_count: int = 0
    cache_hits: int = 0

    @property
    def total_geometry_count(self) -> int:
        """Get total number of geometry primitives."""
        return (
            len(self.lines)
            + len(self.arcs)
            + len(self.polylines)
            + len(self.hatches)
            + len(self.dimensions)
            + len(self.text_notes)
        )

    @property
    def all_geometry(self) -> list[Geometry2D]:
        """Get all geometry as a flat list."""
        result: list[Geometry2D] = []
        result.extend(self.lines)
        result.extend(self.arcs)
        result.extend(self.polylines)
        result.extend(self.hatches)
        result.extend(self.dimensions)
        result.extend(self.text_notes)
        return result

    def extend(self, other: ViewResult) -> None:
        """Extend this result with geometry from another result."""
        self.lines.extend(other.lines)
        self.arcs.extend(other.arcs)
        self.polylines.extend(other.polylines)
        self.hatches.extend(other.hatches)
        self.dimensions.extend(other.dimensions)
        self.text_notes.extend(other.text_notes)
        self.element_count += other.element_count
        self.cache_hits += other.cache_hits

    def translate(self, dx: float, dy: float) -> ViewResult:
        """Return a translated copy of all geometry."""
        return ViewResult(
            lines=[line.translate(dx, dy) for line in self.lines],
            arcs=[arc.translate(dx, dy) for arc in self.arcs],
            polylines=[pl.translate(dx, dy) for pl in self.polylines],
            hatches=[h.translate(dx, dy) for h in self.hatches],
            dimensions=[d.translate(dx, dy) for d in self.dimensions],
            text_notes=[t.translate(dx, dy) for t in self.text_notes],
            view_name=self.view_name,
            generation_time=self.generation_time,
            element_count=self.element_count,
            cache_hits=self.cache_hits,
        )

    def get_bounds(self) -> tuple[float, float, float, float] | None:
        """Get bounding box of all geometry.

        Returns:
            Tuple of (min_x, min_y, max_x, max_y) or None if empty
        """
        all_points: list[Point2D] = []

        for line in self.lines:
            all_points.append(line.start)
            all_points.append(line.end)

        for arc in self.arcs:
            # Include arc endpoints and center +/- radius
            all_points.append(arc.start_point)
            all_points.append(arc.end_point)
            all_points.append(Point2D(arc.center.x - arc.radius, arc.center.y))
            all_points.append(Point2D(arc.center.x + arc.radius, arc.center.y))
            all_points.append(Point2D(arc.center.x, arc.center.y - arc.radius))
            all_points.append(Point2D(arc.center.x, arc.center.y + arc.radius))

        for polyline in self.polylines:
            all_points.extend(polyline.points)

        for hatch in self.hatches:
            all_points.extend(hatch.boundary)

        for dim in self.dimensions:
            # Include dimension endpoints and offset for dimension line
            all_points.append(dim.start)
            all_points.append(dim.end)
            # Also include offset position (approximate bounding)
            perp_angle = dim.angle + math.pi / 2
            offset_x = dim.offset * math.cos(perp_angle)
            offset_y = dim.offset * math.sin(perp_angle)
            all_points.append(Point2D(dim.start.x + offset_x, dim.start.y + offset_y))
            all_points.append(Point2D(dim.end.x + offset_x, dim.end.y + offset_y))

        for text in self.text_notes:
            # Include text position (approximate - actual bounds depend on content)
            all_points.append(text.position)

        if not all_points:
            return None

        min_x = min(p.x for p in all_points)
        max_x = max(p.x for p in all_points)
        min_y = min(p.y for p in all_points)
        max_y = max(p.y for p in all_points)

        return (min_x, min_y, max_x, max_y)
