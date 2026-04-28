"""2D drawing primitives for view generation.

This module defines the fundamental 2D geometric primitives used
in floor plans, sections, and elevations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Union

from bimascode.drawing.line_styles import LineStyle

if TYPE_CHECKING:
    from bimascode.drawing.tags import DoorTag, RoomTag, SectionSymbol, WindowTag


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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> Point2D:
        """Return a new point scaled and translated.

        Args:
            scale: Scale factor (applied first)
            dx: X translation (applied after scaling)
            dy: Y translation (applied after scaling)

        Returns:
            Scaled and translated Point2D
        """
        return Point2D(self.x * scale + dx, self.y * scale + dy)

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

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {"x": self.x, "y": self.y}


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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> Line2D:
        """Return a scaled and translated copy of this line."""
        return Line2D(
            start=self.start.scale_and_translate(scale, dx, dy),
            end=self.end.scale_and_translate(scale, dx, dy),
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

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "style": self.style.to_dict(),
            "layer": self.layer,
        }


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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> Arc2D:
        """Return a scaled and translated copy of this arc."""
        return Arc2D(
            center=self.center.scale_and_translate(scale, dx, dy),
            radius=self.radius * scale,
            start_angle=self.start_angle,
            end_angle=self.end_angle,
            style=self.style,
            layer=self.layer,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "center": self.center.to_dict(),
            "radius": self.radius,
            "start_angle": self.start_angle,
            "end_angle": self.end_angle,
            "style": self.style.to_dict(),
            "layer": self.layer,
        }


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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> Polyline2D:
        """Return a scaled and translated copy of this polyline."""
        return Polyline2D(
            points=[p.scale_and_translate(scale, dx, dy) for p in self.points],
            closed=self.closed,
            style=self.style,
            layer=self.layer,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "points": [p.to_dict() for p in self.points],
            "closed": self.closed,
            "style": self.style.to_dict(),
            "layer": self.layer,
        }


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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> Hatch2D:
        """Return a scaled and translated copy of this hatch."""
        return Hatch2D(
            boundary=[p.scale_and_translate(scale, dx, dy) for p in self.boundary],
            pattern=self.pattern,
            scale=self.scale * scale,
            rotation=self.rotation,
            color=self.color,
            layer=self.layer,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "boundary": [p.to_dict() for p in self.boundary],
            "pattern": self.pattern,
            "scale": self.scale,
            "rotation": self.rotation,
            "color": list(self.color) if self.color else None,
            "layer": self.layer,
        }


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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> TextNote2D:
        """Return a scaled and translated copy of this text note."""
        return TextNote2D(
            position=self.position.scale_and_translate(scale, dx, dy),
            content=self.content,
            height=self.height * scale,
            alignment=self.alignment,
            rotation=self.rotation,
            width=self.width * scale,
            layer=self.layer,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "position": self.position.to_dict(),
            "content": self.content,
            "height": self.height,
            "alignment": self.alignment,
            "rotation": self.rotation,
            "width": self.width,
            "layer": self.layer,
        }


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
    dimlfac: float = 1.0  # Linear scale factor for dimension text display

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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> LinearDimension2D:
        """Return a scaled and translated copy.

        The dimlfac is set to maintain correct dimension text display.
        When geometry is scaled down (e.g., 0.01 for 1:100), dimlfac is
        set to the inverse (100) so dimension text shows model values.
        """
        # Accumulate dimlfac - if already scaled, multiply
        new_dimlfac = self.dimlfac / scale if scale != 0 else self.dimlfac
        return LinearDimension2D(
            start=self.start.scale_and_translate(scale, dx, dy),
            end=self.end.scale_and_translate(scale, dx, dy),
            offset=self.offset * scale,
            text=self.text,
            precision=self.precision,
            style=self.style,
            layer=self.layer,
            dimlfac=new_dimlfac,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "offset": self.offset,
            "text": self.text,
            "precision": self.precision,
            "style": self.style.to_dict(),
            "layer": self.layer,
            "dimlfac": self.dimlfac,
        }


@dataclass(frozen=True)
class ChainDimension2D:
    """2D chain dimension connecting multiple points along a continuous baseline.

    Represents a series of connected dimension segments that share a common
    baseline. Used for dimensioning wall runs, grid lines, or any series of
    aligned points.

    Attributes:
        points: Sequence of measurement points (minimum 2)
        offset: Perpendicular distance from baseline to dimension line
        text: Dimension text for segments ("<>" = auto-calculate)
        precision: Decimal places for auto-calculated text
        style: Line styling for dimension/extension lines
        layer: CAD layer name

    Example:
        >>> points = [Point2D(0, 0), Point2D(1000, 0), Point2D(2500, 0)]
        >>> chain = ChainDimension2D(points=points, offset=500)
        >>> len(chain.segments)  # 2 segments
        2
    """

    points: tuple[Point2D, ...]
    offset: float
    text: str = "<>"
    precision: int = 0
    style: LineStyle = field(default_factory=LineStyle.default)
    layer: str = "G-ANNO-DIMS"
    dimlfac: float = 1.0  # Linear scale factor for dimension text display

    def __post_init__(self):
        """Validate that at least 2 points are provided."""
        if len(self.points) < 2:
            raise ValueError("ChainDimension2D requires at least 2 points")

    @property
    def num_segments(self) -> int:
        """Get the number of dimension segments."""
        return len(self.points) - 1

    @property
    def segments(self) -> list[LinearDimension2D]:
        """Generate individual LinearDimension2D segments.

        Returns:
            List of LinearDimension2D objects, one for each consecutive
            pair of points.
        """
        result = []
        for i in range(len(self.points) - 1):
            result.append(
                LinearDimension2D(
                    start=self.points[i],
                    end=self.points[i + 1],
                    offset=self.offset,
                    text=self.text,
                    precision=self.precision,
                    style=self.style,
                    layer=self.layer,
                    dimlfac=self.dimlfac,
                )
            )
        return result

    @property
    def total_distance(self) -> float:
        """Get the total distance across all segments."""
        total = 0.0
        for i in range(len(self.points) - 1):
            total += self.points[i].distance_to(self.points[i + 1])
        return total

    def translate(self, dx: float, dy: float) -> ChainDimension2D:
        """Return a translated copy."""
        return ChainDimension2D(
            points=tuple(p.translate(dx, dy) for p in self.points),
            offset=self.offset,
            text=self.text,
            precision=self.precision,
            style=self.style,
            layer=self.layer,
        )

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> ChainDimension2D:
        """Return a scaled and translated copy.

        The dimlfac is set to maintain correct dimension text display.
        When geometry is scaled down (e.g., 0.01 for 1:100), dimlfac is
        set to the inverse (100) so dimension text shows model values.
        """
        new_dimlfac = self.dimlfac / scale if scale != 0 else self.dimlfac
        return ChainDimension2D(
            points=tuple(p.scale_and_translate(scale, dx, dy) for p in self.points),
            offset=self.offset * scale,
            text=self.text,
            precision=self.precision,
            style=self.style,
            layer=self.layer,
            dimlfac=new_dimlfac,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "points": [p.to_dict() for p in self.points],
            "offset": self.offset,
            "text": self.text,
            "precision": self.precision,
            "style": self.style.to_dict(),
            "layer": self.layer,
            "dimlfac": self.dimlfac,
        }


# Import tag types for Geometry2D union
# Note: Tags are defined in tags.py to avoid circular imports
# They are added to Geometry2D at runtime in tags.py

# Type alias for any 2D geometry primitive (excluding tags which are in tags.py)
Geometry2D = Union[
    Line2D, Arc2D, Polyline2D, Hatch2D, LinearDimension2D, ChainDimension2D, TextNote2D
]


@dataclass
class ViewResult:
    """Result of view generation containing all 2D geometry.

    Contains all linework, arcs, polylines, hatches, dimensions, and tags
    generated by a view, along with metadata about the view generation.

    Attributes:
        lines: List of line segments
        arcs: List of arcs
        polylines: List of polylines
        hatches: List of hatches
        dimensions: List of linear dimensions
        chain_dimensions: List of chain dimensions
        text_notes: List of text annotations
        door_tags: List of door tags
        window_tags: List of window tags
        room_tags: List of room tags
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
    chain_dimensions: list[ChainDimension2D] = field(default_factory=list)
    text_notes: list[TextNote2D] = field(default_factory=list)
    door_tags: list[DoorTag] = field(default_factory=list)
    window_tags: list[WindowTag] = field(default_factory=list)
    room_tags: list[RoomTag] = field(default_factory=list)
    section_symbols: list[SectionSymbol] = field(default_factory=list)
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
            + len(self.chain_dimensions)
            + len(self.text_notes)
            + len(self.door_tags)
            + len(self.window_tags)
            + len(self.room_tags)
            + len(self.section_symbols)
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
        result.extend(self.chain_dimensions)
        result.extend(self.text_notes)
        return result

    def extend(self, other: ViewResult) -> None:
        """Extend this result with geometry from another result."""
        self.lines.extend(other.lines)
        self.arcs.extend(other.arcs)
        self.polylines.extend(other.polylines)
        self.hatches.extend(other.hatches)
        self.dimensions.extend(other.dimensions)
        self.chain_dimensions.extend(other.chain_dimensions)
        self.text_notes.extend(other.text_notes)
        self.door_tags.extend(other.door_tags)
        self.window_tags.extend(other.window_tags)
        self.room_tags.extend(other.room_tags)
        self.section_symbols.extend(other.section_symbols)
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
            chain_dimensions=[c.translate(dx, dy) for c in self.chain_dimensions],
            text_notes=[t.translate(dx, dy) for t in self.text_notes],
            door_tags=[t.translate(dx, dy) for t in self.door_tags],
            window_tags=[t.translate(dx, dy) for t in self.window_tags],
            room_tags=[t.translate(dx, dy) for t in self.room_tags],
            section_symbols=[s.translate(dx, dy) for s in self.section_symbols],
            view_name=self.view_name,
            generation_time=self.generation_time,
            element_count=self.element_count,
            cache_hits=self.cache_hits,
        )

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> ViewResult:
        """Return a scaled and translated copy of all geometry.

        Applies scaling first (from origin), then translation.

        Args:
            scale: Scale factor
            dx: X translation (applied after scaling)
            dy: Y translation (applied after scaling)

        Returns:
            New ViewResult with transformed geometry
        """
        return ViewResult(
            lines=[line.scale_and_translate(scale, dx, dy) for line in self.lines],
            arcs=[arc.scale_and_translate(scale, dx, dy) for arc in self.arcs],
            polylines=[pl.scale_and_translate(scale, dx, dy) for pl in self.polylines],
            hatches=[h.scale_and_translate(scale, dx, dy) for h in self.hatches],
            dimensions=[d.scale_and_translate(scale, dx, dy) for d in self.dimensions],
            chain_dimensions=[c.scale_and_translate(scale, dx, dy) for c in self.chain_dimensions],
            text_notes=[t.scale_and_translate(scale, dx, dy) for t in self.text_notes],
            door_tags=[t.scale_and_translate(scale, dx, dy) for t in self.door_tags],
            window_tags=[t.scale_and_translate(scale, dx, dy) for t in self.window_tags],
            room_tags=[t.scale_and_translate(scale, dx, dy) for t in self.room_tags],
            section_symbols=[s.scale_and_translate(scale, dx, dy) for s in self.section_symbols],
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

        for chain in self.chain_dimensions:
            # Include all chain points and offset positions
            for seg in chain.segments:
                all_points.append(seg.start)
                all_points.append(seg.end)
                perp_angle = seg.angle + math.pi / 2
                offset_x = seg.offset * math.cos(perp_angle)
                offset_y = seg.offset * math.sin(perp_angle)
                all_points.append(Point2D(seg.start.x + offset_x, seg.start.y + offset_y))
                all_points.append(Point2D(seg.end.x + offset_x, seg.end.y + offset_y))

        for text in self.text_notes:
            # Include text position (approximate - actual bounds depend on content)
            all_points.append(text.position)

        for tag in self.door_tags:
            # Include tag position
            all_points.append(tag.insertion_point)

        for tag in self.window_tags:
            # Include tag position
            all_points.append(tag.insertion_point)

        for tag in self.room_tags:
            # Include tag position
            all_points.append(tag.insertion_point)

        for symbol in self.section_symbols:
            # Include section symbol endpoints and bubble centers
            all_points.append(symbol.start_point)
            all_points.append(symbol.end_point)
            all_points.append(symbol.get_start_bubble_center())
            all_points.append(symbol.get_end_bubble_center())

        if not all_points:
            return None

        min_x = min(p.x for p in all_points)
        max_x = max(p.x for p in all_points)
        min_y = min(p.y for p in all_points)
        max_y = max(p.y for p in all_points)

        return (min_x, min_y, max_x, max_y)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary.

        Returns a complete representation of the view result that can be
        serialized to JSON for web viewers or other consumers.
        """
        return {
            "lines": [line.to_dict() for line in self.lines],
            "arcs": [arc.to_dict() for arc in self.arcs],
            "polylines": [pl.to_dict() for pl in self.polylines],
            "hatches": [h.to_dict() for h in self.hatches],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "chain_dimensions": [c.to_dict() for c in self.chain_dimensions],
            "text_notes": [t.to_dict() for t in self.text_notes],
            "door_tags": [t.to_dict() for t in self.door_tags],
            "window_tags": [t.to_dict() for t in self.window_tags],
            "room_tags": [t.to_dict() for t in self.room_tags],
            "section_symbols": [s.to_dict() for s in self.section_symbols],
            "view_name": self.view_name,
            "generation_time": self.generation_time,
            "element_count": self.element_count,
            "cache_hits": self.cache_hits,
            "total_geometry_count": self.total_geometry_count,
        }
