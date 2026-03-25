"""
Unit tests for drawing primitives.
"""

import math

import pytest

from bimascode.drawing.line_styles import LineStyle
from bimascode.drawing.primitives import (
    Arc2D,
    Hatch2D,
    Line2D,
    LinearDimension2D,
    Point2D,
    Polyline2D,
    TextAlignment,
    TextNote2D,
    ViewResult,
)


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

    def test_hatch_with_rotation(self):
        """Test creating a hatch with rotation."""
        boundary = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100), Point2D(0, 100)]
        hatch = Hatch2D(
            boundary=boundary,
            pattern="ANSI31",
            scale=0.5,
            rotation=45.0,
            layer="A-WALL",
        )
        assert hatch.rotation == 45.0
        assert hatch.scale == 0.5
        assert hatch.pattern == "ANSI31"

    def test_hatch_with_color(self):
        """Test creating a hatch with RGB color."""
        boundary = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100), Point2D(0, 100)]
        hatch = Hatch2D(
            boundary=boundary,
            pattern="SOLID",
            color=(200, 230, 255),
        )
        assert hatch.color == (200, 230, 255)

    def test_hatch_translate(self):
        """Test hatch translation."""
        boundary = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100), Point2D(0, 100)]
        hatch = Hatch2D(boundary=boundary, pattern="ANSI31")
        hatch2 = hatch.translate(50, 50)
        assert hatch2.boundary[0].x == 50
        assert hatch2.boundary[0].y == 50

    def test_hatch_translate_preserves_rotation(self):
        """Test that translation preserves rotation."""
        boundary = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100), Point2D(0, 100)]
        hatch = Hatch2D(boundary=boundary, pattern="ANSI31", rotation=30.0)
        hatch2 = hatch.translate(50, 50)
        assert hatch2.rotation == 30.0

    def test_hatch_default_rotation(self):
        """Test that hatch defaults to 0 rotation."""
        boundary = [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)]
        hatch = Hatch2D(boundary=boundary)
        assert hatch.rotation == 0.0


class TestLinearDimension2D:
    """Tests for LinearDimension2D class."""

    def test_dimension_creation(self):
        """Test creating a dimension."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(1000, 0),
            offset=500,
            style=LineStyle.dimension(),
        )
        assert dim.start.x == 0
        assert dim.end.x == 1000
        assert dim.offset == 500
        assert dim.layer == "G-ANNO-DIMS"

    def test_dimension_frozen(self):
        """Test that LinearDimension2D is immutable."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(1000, 0),
            offset=500,
            style=LineStyle.dimension(),
        )
        with pytest.raises(AttributeError):
            dim.offset = 600

    def test_dimension_distance(self):
        """Test dimension distance calculation."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(3000, 4000),
            offset=500,
            style=LineStyle.dimension(),
        )
        assert dim.distance == 5000.0

    def test_dimension_midpoint(self):
        """Test dimension midpoint."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(100, 100),
            offset=50,
            style=LineStyle.dimension(),
        )
        mid = dim.midpoint
        assert mid.x == 50
        assert mid.y == 50

    def test_dimension_angle(self):
        """Test dimension angle calculation."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(100, 100),
            offset=50,
            style=LineStyle.dimension(),
        )
        assert pytest.approx(dim.angle, abs=1e-10) == math.pi / 4

    def test_dimension_angle_vertical(self):
        """Test dimension angle for vertical dimension."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(0, 100),
            offset=50,
            style=LineStyle.dimension(),
        )
        assert pytest.approx(dim.angle, abs=1e-10) == math.pi / 2

    def test_dimension_translate(self):
        """Test dimension translation."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(100, 0),
            offset=50,
            style=LineStyle.dimension(),
        )
        dim2 = dim.translate(50, 50)
        assert dim2.start.x == 50
        assert dim2.start.y == 50
        assert dim2.end.x == 150
        assert dim2.end.y == 50
        # Original unchanged
        assert dim.start.x == 0

    def test_dimension_default_text(self):
        """Test default dimension text is auto-calculate marker."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(1000, 0),
            offset=500,
            style=LineStyle.dimension(),
        )
        assert dim.text == "<>"

    def test_dimension_custom_text(self):
        """Test dimension with custom text."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(1000, 0),
            offset=500,
            text="1.0m",
            style=LineStyle.dimension(),
        )
        assert dim.text == "1.0m"

    def test_dimension_precision(self):
        """Test dimension precision setting."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(1000, 0),
            offset=500,
            precision=2,
            style=LineStyle.dimension(),
        )
        assert dim.precision == 2


class TestTextNote2D:
    """Tests for TextNote2D class."""

    def test_text_note_creation(self):
        """Test creating a text note."""
        note = TextNote2D(
            position=Point2D(1000, 2000),
            content="General Note",
        )
        assert note.position.x == 1000
        assert note.position.y == 2000
        assert note.content == "General Note"
        assert note.layer == "G-ANNO"

    def test_text_note_frozen(self):
        """Test that TextNote2D is immutable."""
        note = TextNote2D(
            position=Point2D(1000, 2000),
            content="Test",
        )
        with pytest.raises(AttributeError):
            note.content = "Modified"

    def test_text_note_defaults(self):
        """Test default values."""
        note = TextNote2D(
            position=Point2D(0, 0),
            content="Test",
        )
        assert note.height == 150.0
        assert note.alignment == "MIDDLE_LEFT"
        assert note.rotation == 0.0
        assert note.width == 0.0
        assert note.layer == "G-ANNO"

    def test_text_note_custom_values(self):
        """Test text note with custom values."""
        note = TextNote2D(
            position=Point2D(500, 500),
            content="Custom Note",
            height=200.0,
            alignment=TextAlignment.TOP_CENTER,
            rotation=45.0,
            width=1000.0,
            layer="A-ANNO",
        )
        assert note.height == 200.0
        assert note.alignment == "TOP_CENTER"
        assert note.rotation == 45.0
        assert note.width == 1000.0
        assert note.layer == "A-ANNO"

    def test_text_note_multiline(self):
        """Test multiline text detection."""
        single_line = TextNote2D(
            position=Point2D(0, 0),
            content="Single line",
        )
        assert single_line.is_multiline is False
        assert single_line.line_count == 1

        multi_line = TextNote2D(
            position=Point2D(0, 0),
            content="Line 1\nLine 2\nLine 3",
        )
        assert multi_line.is_multiline is True
        assert multi_line.line_count == 3

    def test_text_note_translate(self):
        """Test text note translation."""
        note = TextNote2D(
            position=Point2D(100, 200),
            content="Test",
            height=150.0,
            alignment=TextAlignment.MIDDLE_CENTER,
            rotation=30.0,
        )
        note2 = note.translate(50, -50)
        assert note2.position.x == 150
        assert note2.position.y == 150
        # Original unchanged
        assert note.position.x == 100
        assert note.position.y == 200
        # Other properties preserved
        assert note2.content == "Test"
        assert note2.height == 150.0
        assert note2.alignment == "MIDDLE_CENTER"
        assert note2.rotation == 30.0

    def test_text_alignment_constants(self):
        """Test TextAlignment constants."""
        assert TextAlignment.TOP_LEFT == "TOP_LEFT"
        assert TextAlignment.TOP_CENTER == "TOP_CENTER"
        assert TextAlignment.TOP_RIGHT == "TOP_RIGHT"
        assert TextAlignment.MIDDLE_LEFT == "MIDDLE_LEFT"
        assert TextAlignment.MIDDLE_CENTER == "MIDDLE_CENTER"
        assert TextAlignment.MIDDLE_RIGHT == "MIDDLE_RIGHT"
        assert TextAlignment.BOTTOM_LEFT == "BOTTOM_LEFT"
        assert TextAlignment.BOTTOM_CENTER == "BOTTOM_CENTER"
        assert TextAlignment.BOTTOM_RIGHT == "BOTTOM_RIGHT"


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

    def test_view_result_with_dimensions(self):
        """Test ViewResult can hold dimensions."""
        result = ViewResult()
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(1000, 0),
            offset=500,
            style=LineStyle.dimension(),
        )
        result.dimensions.append(dim)
        assert len(result.dimensions) == 1
        assert result.total_geometry_count == 1

    def test_view_result_extend_with_dimensions(self):
        """Test extending ViewResult with dimensions."""
        result1 = ViewResult()
        result1.dimensions.append(
            LinearDimension2D(
                start=Point2D(0, 0),
                end=Point2D(100, 0),
                offset=50,
                style=LineStyle.dimension(),
            )
        )

        result2 = ViewResult()
        result2.dimensions.append(
            LinearDimension2D(
                start=Point2D(100, 0),
                end=Point2D(200, 0),
                offset=50,
                style=LineStyle.dimension(),
            )
        )

        result1.extend(result2)
        assert len(result1.dimensions) == 2

    def test_view_result_translate_with_dimensions(self):
        """Test translating ViewResult with dimensions."""
        result = ViewResult()
        result.dimensions.append(
            LinearDimension2D(
                start=Point2D(0, 0),
                end=Point2D(100, 0),
                offset=50,
                style=LineStyle.dimension(),
            )
        )
        translated = result.translate(50, 50)
        assert translated.dimensions[0].start.x == 50
        assert translated.dimensions[0].start.y == 50

    def test_view_result_bounds_with_dimensions(self):
        """Test ViewResult bounds include dimensions."""
        result = ViewResult()
        result.dimensions.append(
            LinearDimension2D(
                start=Point2D(0, 0),
                end=Point2D(100, 0),
                offset=50,  # Positive offset means dimension line is above
                style=LineStyle.dimension(),
            )
        )
        bounds = result.get_bounds()
        assert bounds is not None
        # Bounds should include dimension line position (offset above)
        assert bounds[0] == 0  # min_x
        assert bounds[2] == 100  # max_x
        # Y should extend to include offset
        assert bounds[3] == 50  # max_y (offset)

    def test_view_result_with_text_notes(self):
        """Test ViewResult can hold text notes."""
        result = ViewResult()
        note = TextNote2D(
            position=Point2D(500, 500),
            content="Test Note",
        )
        result.text_notes.append(note)
        assert len(result.text_notes) == 1
        assert result.total_geometry_count == 1

    def test_view_result_extend_with_text_notes(self):
        """Test extending ViewResult with text notes."""
        result1 = ViewResult()
        result1.text_notes.append(
            TextNote2D(
                position=Point2D(0, 0),
                content="Note 1",
            )
        )

        result2 = ViewResult()
        result2.text_notes.append(
            TextNote2D(
                position=Point2D(1000, 1000),
                content="Note 2",
            )
        )

        result1.extend(result2)
        assert len(result1.text_notes) == 2

    def test_view_result_translate_with_text_notes(self):
        """Test translating ViewResult with text notes."""
        result = ViewResult()
        result.text_notes.append(
            TextNote2D(
                position=Point2D(100, 200),
                content="Test",
            )
        )
        translated = result.translate(50, 50)
        assert translated.text_notes[0].position.x == 150
        assert translated.text_notes[0].position.y == 250

    def test_view_result_bounds_with_text_notes(self):
        """Test ViewResult bounds include text notes."""
        result = ViewResult()
        result.text_notes.append(
            TextNote2D(
                position=Point2D(500, 300),
                content="Test",
            )
        )
        bounds = result.get_bounds()
        assert bounds is not None
        assert bounds[0] == 500  # min_x
        assert bounds[1] == 300  # min_y
        assert bounds[2] == 500  # max_x
        assert bounds[3] == 300  # max_y

    def test_view_result_all_geometry_includes_text_notes(self):
        """Test all_geometry property includes text notes."""
        result = ViewResult()
        result.lines.append(
            Line2D(
                start=Point2D(0, 0),
                end=Point2D(100, 0),
                style=LineStyle.default(),
            )
        )
        result.text_notes.append(
            TextNote2D(
                position=Point2D(50, 50),
                content="Note",
            )
        )
        all_geom = result.all_geometry
        assert len(all_geom) == 2
