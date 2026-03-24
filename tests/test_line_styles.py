"""
Unit tests for line styles module.
"""

from bimascode.drawing.line_styles import (
    Layer,
    LineStyle,
    LineType,
    LineWeight,
)


class TestLineWeight:
    """Tests for LineWeight enum."""

    def test_line_weights_exist(self):
        """Test all standard line weights exist."""
        assert LineWeight.HEAVY.value == 0.70
        assert LineWeight.WIDE.value == 0.50
        assert LineWeight.MEDIUM.value == 0.35
        assert LineWeight.NARROW.value == 0.25
        assert LineWeight.FINE.value == 0.18
        assert LineWeight.EXTRA_FINE.value == 0.13

    def test_for_cut_element(self):
        """Test line weight selection for cut elements."""
        assert LineWeight.for_cut_element(is_structural=True) == LineWeight.HEAVY
        assert LineWeight.for_cut_element(is_structural=False) == LineWeight.WIDE

    def test_for_projection(self):
        """Test line weight selection for projections."""
        assert LineWeight.for_projection(is_hidden=False) == LineWeight.NARROW
        assert LineWeight.for_projection(is_hidden=True) == LineWeight.FINE


class TestLineType:
    """Tests for LineType enum."""

    def test_line_types_exist(self):
        """Test all standard line types exist."""
        assert LineType.CONTINUOUS.value == "CONTINUOUS"
        assert LineType.DASHED.value == "DASHED"
        assert LineType.HIDDEN.value == "HIDDEN"
        assert LineType.CENTER.value == "CENTER"

    def test_continuous_pattern(self):
        """Test continuous line has no pattern."""
        assert LineType.CONTINUOUS.pattern == ()

    def test_dashed_pattern(self):
        """Test dashed line pattern."""
        pattern = LineType.DASHED.pattern
        assert len(pattern) == 2
        assert pattern[0] > 0  # Dash
        assert pattern[1] > 0  # Gap


class TestLineStyle:
    """Tests for LineStyle class."""

    def test_line_style_creation(self):
        """Test creating a line style."""
        style = LineStyle(
            weight=LineWeight.HEAVY,
            type=LineType.CONTINUOUS,
            is_cut=True,
        )
        assert style.weight == LineWeight.HEAVY
        assert style.type == LineType.CONTINUOUS
        assert style.is_cut is True
        assert style.color is None

    def test_line_style_with_color(self):
        """Test line style with color."""
        style = LineStyle(
            weight=LineWeight.MEDIUM,
            type=LineType.CONTINUOUS,
            color=(255, 0, 0),
        )
        assert style.color == (255, 0, 0)

    def test_cut_heavy_factory(self):
        """Test cut_heavy factory method."""
        style = LineStyle.cut_heavy()
        assert style.weight == LineWeight.HEAVY
        assert style.type == LineType.CONTINUOUS
        assert style.is_cut is True

    def test_cut_wide_factory(self):
        """Test cut_wide factory method."""
        style = LineStyle.cut_wide()
        assert style.weight == LineWeight.WIDE
        assert style.is_cut is True

    def test_visible_factory(self):
        """Test visible factory method."""
        style = LineStyle.visible()
        assert style.weight == LineWeight.NARROW
        assert style.type == LineType.CONTINUOUS
        assert style.is_cut is False

    def test_hidden_factory(self):
        """Test hidden factory method."""
        style = LineStyle.hidden()
        assert style.weight == LineWeight.FINE
        assert style.type == LineType.HIDDEN
        assert style.is_cut is False

    def test_above_cut_factory(self):
        """Test above_cut factory method."""
        style = LineStyle.above_cut()
        assert style.weight == LineWeight.FINE
        assert style.type == LineType.ABOVE_CUT

    def test_center_factory(self):
        """Test center factory method."""
        style = LineStyle.center()
        assert style.weight == LineWeight.EXTRA_FINE
        assert style.type == LineType.CENTER

    def test_default_factory(self):
        """Test default factory method."""
        style = LineStyle.default()
        assert style.weight == LineWeight.NARROW
        assert style.type == LineType.CONTINUOUS

    def test_with_color(self):
        """Test with_color method."""
        style = LineStyle.cut_heavy()
        colored = style.with_color((0, 255, 0))
        assert colored.color == (0, 255, 0)
        assert colored.weight == style.weight
        assert colored.type == style.type

    def test_with_weight(self):
        """Test with_weight method."""
        style = LineStyle.cut_heavy()
        modified = style.with_weight(LineWeight.FINE)
        assert modified.weight == LineWeight.FINE
        assert modified.type == style.type
        assert modified.is_cut == style.is_cut


class TestLayer:
    """Tests for Layer class constants."""

    def test_architecture_layers(self):
        """Test architecture layer names."""
        assert Layer.WALL == "A-WALL"
        assert Layer.DOOR == "A-DOOR"
        assert Layer.WINDOW == "A-GLAZ"
        assert Layer.FLOOR == "A-FLOR"
        assert Layer.CEILING == "A-CLNG"

    def test_structure_layers(self):
        """Test structure layer names."""
        assert Layer.COLUMN == "S-COLS"
        assert Layer.BEAM == "S-BEAM"
        assert Layer.SLAB == "S-SLAB"

    def test_for_element_type(self):
        """Test layer lookup by element type."""
        assert Layer.for_element_type("Wall") == "A-WALL"
        assert Layer.for_element_type("Door") == "A-DOOR"
        assert Layer.for_element_type("Window") == "A-GLAZ"
        assert Layer.for_element_type("Column") == "S-COLS"
        assert Layer.for_element_type("Unknown") == "0"
