"""Tests for JSON serialization of 2D primitives and ViewResult."""

import json
import math

from bimascode.drawing.line_styles import LineStyle, LineType, LineWeight
from bimascode.drawing.primitives import (
    Arc2D,
    ChainDimension2D,
    Hatch2D,
    Line2D,
    LinearDimension2D,
    Point2D,
    Polyline2D,
    TextNote2D,
    ViewResult,
)


class TestPoint2DSerialization:
    """Tests for Point2D.to_dict()."""

    def test_basic_point(self):
        """Point2D serializes to x/y dict."""
        point = Point2D(100.0, 200.0)
        result = point.to_dict()

        assert result == {"x": 100.0, "y": 200.0}

    def test_negative_coordinates(self):
        """Negative coordinates serialize correctly."""
        point = Point2D(-50.5, -100.25)
        result = point.to_dict()

        assert result["x"] == -50.5
        assert result["y"] == -100.25

    def test_json_serializable(self):
        """Point2D.to_dict() is JSON serializable."""
        point = Point2D(1000.0, 2000.0)
        # Should not raise
        json_str = json.dumps(point.to_dict())
        parsed = json.loads(json_str)
        assert parsed == {"x": 1000.0, "y": 2000.0}


class TestLineStyleSerialization:
    """Tests for LineStyle and related enum serialization."""

    def test_line_weight_to_dict(self):
        """LineWeight serializes with name and width."""
        weight = LineWeight.HEAVY
        result = weight.to_dict()

        assert result["name"] == "HEAVY"
        assert result["width_mm"] == 0.70

    def test_line_type_to_dict(self):
        """LineType serializes with name and pattern."""
        line_type = LineType.DASHED
        result = line_type.to_dict()

        assert result["name"] == "DASHED"
        assert result["pattern"] == [6.0, 3.0]

    def test_continuous_line_type(self):
        """Continuous line type has empty pattern."""
        line_type = LineType.CONTINUOUS
        result = line_type.to_dict()

        assert result["name"] == "CONTINUOUS"
        assert result["pattern"] == []

    def test_line_style_to_dict(self):
        """LineStyle serializes all properties."""
        style = LineStyle(
            weight=LineWeight.MEDIUM,
            type=LineType.CENTER,
            color=(255, 0, 0),
            is_cut=True,
        )
        result = style.to_dict()

        assert result["weight"]["name"] == "MEDIUM"
        assert result["type"]["name"] == "CENTER"
        assert result["color"] == [255, 0, 0]
        assert result["is_cut"] is True

    def test_line_style_no_color(self):
        """LineStyle with no color serializes as None."""
        style = LineStyle.default()
        result = style.to_dict()

        assert result["color"] is None

    def test_line_style_json_serializable(self):
        """LineStyle.to_dict() is JSON serializable."""
        style = LineStyle.cut_heavy()
        json_str = json.dumps(style.to_dict())
        parsed = json.loads(json_str)
        assert parsed["weight"]["name"] == "HEAVY"


class TestLine2DSerialization:
    """Tests for Line2D.to_dict()."""

    def test_basic_line(self):
        """Line2D serializes start, end, style, layer."""
        line = Line2D(
            start=Point2D(0, 0),
            end=Point2D(1000, 500),
            style=LineStyle.default(),
            layer="A-WALL",
        )
        result = line.to_dict()

        assert result["start"] == {"x": 0, "y": 0}
        assert result["end"] == {"x": 1000, "y": 500}
        assert result["layer"] == "A-WALL"
        assert "style" in result

    def test_json_serializable(self):
        """Line2D.to_dict() is JSON serializable."""
        line = Line2D(
            start=Point2D(0, 0),
            end=Point2D(100, 100),
            style=LineStyle.cut_heavy(),
        )
        json_str = json.dumps(line.to_dict())
        parsed = json.loads(json_str)
        assert parsed["start"]["x"] == 0
        assert parsed["end"]["y"] == 100


class TestArc2DSerialization:
    """Tests for Arc2D.to_dict()."""

    def test_basic_arc(self):
        """Arc2D serializes all properties."""
        arc = Arc2D(
            center=Point2D(500, 500),
            radius=100.0,
            start_angle=0.0,
            end_angle=math.pi,
            style=LineStyle.default(),
            layer="A-DOOR",
        )
        result = arc.to_dict()

        assert result["center"] == {"x": 500, "y": 500}
        assert result["radius"] == 100.0
        assert result["start_angle"] == 0.0
        assert result["end_angle"] == math.pi
        assert result["layer"] == "A-DOOR"

    def test_json_serializable(self):
        """Arc2D.to_dict() is JSON serializable."""
        arc = Arc2D(
            center=Point2D(0, 0),
            radius=50.0,
            start_angle=0.0,
            end_angle=math.pi / 2,
            style=LineStyle.default(),
        )
        json_str = json.dumps(arc.to_dict())
        assert "center" in json_str


class TestPolyline2DSerialization:
    """Tests for Polyline2D.to_dict()."""

    def test_basic_polyline(self):
        """Polyline2D serializes points and properties."""
        polyline = Polyline2D(
            points=[Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)],
            closed=True,
            style=LineStyle.default(),
            layer="A-WALL",
        )
        result = polyline.to_dict()

        assert len(result["points"]) == 3
        assert result["points"][0] == {"x": 0, "y": 0}
        assert result["closed"] is True
        assert result["layer"] == "A-WALL"

    def test_json_serializable(self):
        """Polyline2D.to_dict() is JSON serializable."""
        polyline = Polyline2D(
            points=[Point2D(0, 0), Point2D(100, 100)],
            closed=False,
        )
        json_str = json.dumps(polyline.to_dict())
        parsed = json.loads(json_str)
        assert len(parsed["points"]) == 2


class TestHatch2DSerialization:
    """Tests for Hatch2D.to_dict()."""

    def test_basic_hatch(self):
        """Hatch2D serializes boundary and properties."""
        hatch = Hatch2D(
            boundary=[Point2D(0, 0), Point2D(100, 0), Point2D(100, 100), Point2D(0, 100)],
            pattern="SOLID",
            scale=1.0,
            rotation=45.0,
            color=(128, 128, 128),
            layer="A-WALL",
        )
        result = hatch.to_dict()

        assert len(result["boundary"]) == 4
        assert result["pattern"] == "SOLID"
        assert result["scale"] == 1.0
        assert result["rotation"] == 45.0
        assert result["color"] == [128, 128, 128]
        assert result["layer"] == "A-WALL"

    def test_no_color(self):
        """Hatch2D with no color serializes as None."""
        hatch = Hatch2D(
            boundary=[Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)],
        )
        result = hatch.to_dict()
        assert result["color"] is None


class TestTextNote2DSerialization:
    """Tests for TextNote2D.to_dict()."""

    def test_basic_text_note(self):
        """TextNote2D serializes all properties."""
        text = TextNote2D(
            position=Point2D(500, 500),
            content="Hello World",
            height=150.0,
            alignment="MIDDLE_CENTER",
            rotation=0.0,
            width=500.0,
            layer="G-ANNO",
        )
        result = text.to_dict()

        assert result["position"] == {"x": 500, "y": 500}
        assert result["content"] == "Hello World"
        assert result["height"] == 150.0
        assert result["alignment"] == "MIDDLE_CENTER"
        assert result["rotation"] == 0.0
        assert result["width"] == 500.0
        assert result["layer"] == "G-ANNO"


class TestDimensionSerialization:
    """Tests for LinearDimension2D and ChainDimension2D serialization."""

    def test_linear_dimension(self):
        """LinearDimension2D serializes all properties."""
        dim = LinearDimension2D(
            start=Point2D(0, 0),
            end=Point2D(1000, 0),
            offset=200.0,
            text="<>",
            precision=0,
            style=LineStyle.dimension(),
            layer="G-ANNO-DIMS",
            dimlfac=1.0,
        )
        result = dim.to_dict()

        assert result["start"] == {"x": 0, "y": 0}
        assert result["end"] == {"x": 1000, "y": 0}
        assert result["offset"] == 200.0
        assert result["text"] == "<>"
        assert result["precision"] == 0
        assert result["dimlfac"] == 1.0

    def test_chain_dimension(self):
        """ChainDimension2D serializes all points."""
        chain = ChainDimension2D(
            points=(Point2D(0, 0), Point2D(1000, 0), Point2D(2500, 0)),
            offset=300.0,
        )
        result = chain.to_dict()

        assert len(result["points"]) == 3
        assert result["offset"] == 300.0


class TestViewResultSerialization:
    """Tests for ViewResult.to_dict()."""

    def test_empty_view_result(self):
        """Empty ViewResult serializes with empty lists."""
        view = ViewResult(view_name="Test View")
        result = view.to_dict()

        assert result["lines"] == []
        assert result["arcs"] == []
        assert result["polylines"] == []
        assert result["hatches"] == []
        assert result["dimensions"] == []
        assert result["chain_dimensions"] == []
        assert result["text_notes"] == []
        assert result["door_tags"] == []
        assert result["window_tags"] == []
        assert result["room_tags"] == []
        assert result["section_symbols"] == []
        assert result["view_name"] == "Test View"
        assert result["total_geometry_count"] == 0

    def test_view_result_with_geometry(self):
        """ViewResult with geometry serializes correctly."""
        view = ViewResult(
            lines=[
                Line2D(Point2D(0, 0), Point2D(100, 0), LineStyle.default()),
                Line2D(Point2D(100, 0), Point2D(100, 100), LineStyle.default()),
            ],
            arcs=[
                Arc2D(Point2D(50, 50), 25.0, 0.0, math.pi, LineStyle.default()),
            ],
            view_name="Ground Floor Plan",
            generation_time=0.5,
            element_count=10,
            cache_hits=5,
        )
        result = view.to_dict()

        assert len(result["lines"]) == 2
        assert len(result["arcs"]) == 1
        assert result["view_name"] == "Ground Floor Plan"
        assert result["generation_time"] == 0.5
        assert result["element_count"] == 10
        assert result["cache_hits"] == 5
        assert result["total_geometry_count"] == 3

    def test_view_result_json_serializable(self):
        """ViewResult.to_dict() is fully JSON serializable."""
        view = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(100, 100), LineStyle.cut_heavy())],
            polylines=[
                Polyline2D(
                    [Point2D(0, 0), Point2D(50, 50), Point2D(100, 0)],
                    closed=True,
                )
            ],
            hatches=[
                Hatch2D(
                    [Point2D(0, 0), Point2D(100, 0), Point2D(100, 100)],
                    color=(200, 200, 200),
                )
            ],
            view_name="Test",
        )
        # Should not raise
        json_str = json.dumps(view.to_dict())
        parsed = json.loads(json_str)

        assert len(parsed["lines"]) == 1
        assert len(parsed["polylines"]) == 1
        assert len(parsed["hatches"]) == 1
        assert parsed["view_name"] == "Test"


class TestRoundTrip:
    """Tests that serialized data can be used to reconstruct objects."""

    def test_point_round_trip(self):
        """Point data can be extracted from serialized form."""
        original = Point2D(123.456, 789.012)
        data = original.to_dict()

        # Reconstruct
        reconstructed = Point2D(data["x"], data["y"])
        assert reconstructed.x == original.x
        assert reconstructed.y == original.y

    def test_line_style_data_accessible(self):
        """LineStyle data is accessible from serialized form."""
        style = LineStyle(
            weight=LineWeight.HEAVY,
            type=LineType.DASHED,
            color=(255, 128, 0),
            is_cut=True,
        )
        data = style.to_dict()

        # Access nested data
        assert data["weight"]["width_mm"] == 0.70
        assert data["type"]["pattern"] == [6.0, 3.0]
        assert data["color"] == [255, 128, 0]
