"""
Unit tests for drawing primitives.
"""

import pytest
import math
from bimascode.drawing.primitives import (
    Point2D,
    Line2D,
    Arc2D,
    Polyline2D,
    Hatch2D,
    ViewResult,
)
from bimascode.drawing.line_styles import LineStyle, LineWeight, LineType


class TestPoint2D:
    """Tests for Point2D class."""

    def test_point_creation(self):
        """Test creating a point."""
        p = Point2D(100, 200)
        assert p.x == 100
        assert p.y == 200

    def test_point_frozen(self):
        """Test that Point2D is immutable."""
        p = Point2D(100, 200)
        with pytest.raises(AttributeError):
            p.x = 300

    def test_distance_to(self):
        """Test distance calculation."""
        p1 = Point2D(0, 0)
        p2 = Point2D(3, 4)
        assert p1.distance_to(p2) == 5.0

    def test_translate(self):
        """Test point translation."""
        p = Point2D(100, 200)
        p2 = p.translate(50, -50)
        assert p2.x == 150
        assert p2.y == 150
        # Original unchanged
        assert p.x == 100

    def test_rotate(self):
        """Test point rotation."""
        p = Point2D(100, 0)
        # Rotate 90 degrees around origin
        p2 = p.rotate(math.pi / 2)
        assert pytest.approx(p2.x, abs=1e-10) == 0
        assert pytest.approx(p2.y, abs=1e-10) == 100

    def test_rotate_around_point(self):
        """Test rotation around a specified origin."""
        p = Point2D(200, 0)
        origin = Point2D(100, 0)
        # Rotate 90 degrees around (100, 0)
        p2 = p.rotate(math.pi / 2, origin)
        assert pytest.approx(p2.x, abs=1e-10) == 100
        assert pytest.approx(p2.y, abs=1e-10) == 100

    def test_as_tuple(self):
        """Test conversion to tuple."""
        p = Point2D(100, 200)
        assert p.as_tuple() == (100, 200)


class TestLine2D:
    """Tests for Line2D class."""

    def test_line_creation(self):
        """Test creating a line."""
        style = LineStyle.cut_heavy()
        line = Line2D(
            start=Point2D(0, 0),
            end=Point2D(100, 0),
            style=style,
            layer="A-WALL",
        )
        assert line.start.x == 0
        assert line.end.x == 100
        assert line.layer == "A-WALL"

    def test_line_length(self):
        """Test line length calculation."""
        line = Line2D(
            start=Point2D(0, 0),
            end=Point2D(3000, 4000),
            style=LineStyle.default(),
        )
        assert line.length == 5000.0

    def test_line_midpoint(self):
        """Test line midpoint."""
        line = Line2D(
            start=Point2D(0, 0),
            end=Point2D(100, 100),
            style=LineStyle.default(),
        )
        mid = line.midpoint
        assert mid.x == 50
        assert mid.y == 50

    def test_line_angle(self):
        """Test line angle calculation."""
        line = Line2D(
            start=Point2D(0, 0),
            end=Point2D(100, 100),
            style=LineStyle.default(),
        )
        assert pytest.approx(line.angle, abs=1e-10) == math.pi / 4

    def test_line_translate(self):
        """Test line translation."""
        line = Line2D(
            start=Point2D(0, 0),
            end=Point2D(100, 0),
            style=LineStyle.default(),
        )
        line2 = line.translate(50, 50)
        assert line2.start.x == 50
        assert line2.start.y == 50
        assert line2.end.x == 150

    def test_line_reverse(self):
        """Test line reversal."""
        line = Line2D(
            start=Point2D(0, 0),
            end=Point2D(100, 0),
            style=LineStyle.default(),
        )
        reversed_line = line.reverse()
        assert reversed_line.start.x == 100
        assert reversed_line.end.x == 0


class TestArc2D:
    """Tests for Arc2D class."""

    def test_arc_creation(self):
        """Test creating an arc."""
        arc = Arc2D(
            center=Point2D(0, 0),
            radius=100,
            start_angle=0,
            end_angle=math.pi / 2,
            style=LineStyle.default(),
            layer="A-DOOR",
        )
        assert arc.center.x == 0
        assert arc.radius == 100
        assert arc.layer == "A-DOOR"

    def test_arc_start_end_points(self):
        """Test arc start and end point calculation."""
        arc = Arc2D(
            center=Point2D(0, 0),
            radius=100,
            start_angle=0,
            end_angle=math.pi / 2,
            style=LineStyle.default(),
        )
        assert pytest.approx(arc.start_point.x, abs=1e-10) == 100
        assert pytest.approx(arc.start_point.y, abs=1e-10) == 0
        assert pytest.approx(arc.end_point.x, abs=1e-10) == 0
        assert pytest.approx(arc.end_point.y, abs=1e-10) == 100

    def test_arc_sweep_angle(self):
        """Test arc sweep angle."""
        arc = Arc2D(
            center=Point2D(0, 0),
            radius=100,
            start_angle=0,
            end_angle=math.pi / 2,
            style=LineStyle.default(),
        )
        assert pytest.approx(arc.sweep_angle, abs=1e-10) == math.pi / 2

    def test_arc_length(self):
        """Test arc length calculation."""
        arc = Arc2D(
            center=Point2D(0, 0),
            radius=100,
            start_angle=0,
            end_angle=math.pi,
            style=LineStyle.default(),
        )
        # Half circle: pi * radius
        expected = math.pi * 100
        assert pytest.approx(arc.length, abs=1e-10) == expected


class TestPolyline2D:
    """Tests for Polyline2D class."""

    def test_polyline_creation(self):
        """Test creating a polyline."""
        points = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)]
        polyline = Polyline2D(points=points, closed=False, style=LineStyle.default())
        assert polyline.num_points == 3
        assert polyline.closed is False

    def test_polyline_closed(self):
        """Test closed polyline."""
        points = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)]
        polyline = Polyline2D(points=points, closed=True, style=LineStyle.default())
        assert polyline.num_segments == 3  # Including closing segment

    def test_polyline_open(self):
        """Test open polyline segment count."""
        points = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)]
        polyline = Polyline2D(points=points, closed=False, style=LineStyle.default())
        assert polyline.num_segments == 2

    def test_polyline_length(self):
        """Test polyline length calculation."""
        points = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)]
        polyline = Polyline2D(points=points, closed=False, style=LineStyle.default())
        assert polyline.length == 200.0

    def test_polyline_to_lines(self):
        """Test converting polyline to lines."""
        points = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)]
        polyline = Polyline2D(points=points, closed=True, style=LineStyle.default())
        lines = polyline.to_lines()
        assert len(lines) == 3


class TestHatch2D:
    """Tests for Hatch2D class."""

    def test_hatch_creation(self):
        """Test creating a hatch."""
        boundary = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100), Point2D(0, 100)]
        hatch = Hatch2D(
            boundary=boundary,
            pattern="SOLID",
            scale=1.0,
            layer="A-WALL",
        )
        assert hatch.num_points == 4
        assert hatch.pattern == "SOLID"
        assert hatch.layer == "A-WALL"

    def test_hatch_translate(self):
        """Test hatch translation."""
        boundary = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100), Point2D(0, 100)]
        hatch = Hatch2D(boundary=boundary, pattern="ANSI31")
        hatch2 = hatch.translate(50, 50)
        assert hatch2.boundary[0].x == 50
        assert hatch2.boundary[0].y == 50


class TestViewResult:
    """Tests for ViewResult class."""

    def test_view_result_creation(self):
        """Test creating a view result."""
        result = ViewResult(view_name="Test Plan")
        assert result.view_name == "Test Plan"
        assert result.total_geometry_count == 0

    def test_view_result_add_geometry(self):
        """Test adding geometry to view result."""
        result = ViewResult()
        result.lines.append(
            Line2D(
                start=Point2D(0, 0),
                end=Point2D(100, 0),
                style=LineStyle.default(),
            )
        )
        result.arcs.append(
            Arc2D(
                center=Point2D(0, 0),
                radius=50,
                start_angle=0,
                end_angle=math.pi,
                style=LineStyle.default(),
            )
        )
        assert result.total_geometry_count == 2

    def test_view_result_extend(self):
        """Test extending view result."""
        result1 = ViewResult()
        result1.lines.append(
            Line2D(
                start=Point2D(0, 0),
                end=Point2D(100, 0),
                style=LineStyle.default(),
            )
        )

        result2 = ViewResult()
        result2.lines.append(
            Line2D(
                start=Point2D(100, 0),
                end=Point2D(200, 0),
                style=LineStyle.default(),
            )
        )

        result1.extend(result2)
        assert len(result1.lines) == 2

    def test_view_result_bounds(self):
        """Test view result bounds calculation."""
        result = ViewResult()
        result.lines.append(
            Line2D(
                start=Point2D(0, 0),
                end=Point2D(100, 100),
                style=LineStyle.default(),
            )
        )
        bounds = result.get_bounds()
        assert bounds is not None
        assert bounds == (0, 0, 100, 100)

    def test_view_result_empty_bounds(self):
        """Test bounds for empty view result."""
        result = ViewResult()
        bounds = result.get_bounds()
        assert bounds is None

    def test_view_result_translate(self):
        """Test translating view result."""
        result = ViewResult()
        result.lines.append(
            Line2D(
                start=Point2D(0, 0),
                end=Point2D(100, 0),
                style=LineStyle.default(),
            )
        )
        translated = result.translate(50, 50)
        assert translated.lines[0].start.x == 50
        assert translated.lines[0].start.y == 50
