"""
Tests for section symbol annotations.
"""

import math

import pytest

from bimascode.drawing.primitives import Point2D, ViewResult
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.tags import SectionSymbol, SectionSymbolStyle


class TestSectionSymbolStyle:
    """Tests for SectionSymbolStyle class."""

    def test_default_style(self):
        """Test default section symbol style."""
        style = SectionSymbolStyle.default()

        assert style.bubble_radius == 200.0
        assert style.text_height == 120.0
        assert style.arrow_size == 150.0
        assert style.line_extension == 100.0
        assert style.show_arrows is True
        assert style.show_bubbles is True

    def test_custom_style(self):
        """Test creating a custom style."""
        style = SectionSymbolStyle(
            bubble_radius=250.0,
            text_height=150.0,
            arrow_size=200.0,
            line_extension=150.0,
            show_arrows=False,
            show_bubbles=True,
        )

        assert style.bubble_radius == 250.0
        assert style.text_height == 150.0
        assert style.arrow_size == 200.0
        assert style.line_extension == 150.0
        assert style.show_arrows is False
        assert style.show_bubbles is True

    def test_style_scale(self):
        """Test scaling a style."""
        style = SectionSymbolStyle.default()
        scaled = style.scale(2.0)

        assert scaled.bubble_radius == style.bubble_radius * 2.0
        assert scaled.text_height == style.text_height * 2.0
        assert scaled.arrow_size == style.arrow_size * 2.0
        assert scaled.line_extension == style.line_extension * 2.0
        # Boolean properties unchanged
        assert scaled.show_arrows == style.show_arrows
        assert scaled.show_bubbles == style.show_bubbles


class TestSectionSymbol:
    """Tests for SectionSymbol class."""

    def test_basic_creation(self):
        """Test basic section symbol creation."""
        symbol = SectionSymbol(
            start_point=Point2D(5000, 0),
            end_point=Point2D(5000, 10000),
            section_id="A",
            sheet_number="A2",
        )

        assert symbol.start_point == Point2D(5000, 0)
        assert symbol.end_point == Point2D(5000, 10000)
        assert symbol.section_id == "A"
        assert symbol.sheet_number == "A2"
        assert symbol.look_direction == "right"  # default

    def test_labels(self):
        """Test section symbol labels."""
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 0),
            section_id="B",
            sheet_number="S-101",
        )

        assert symbol.start_label == "B"
        assert symbol.end_label == "B"
        assert symbol.start_sheet == "S-101"
        assert symbol.end_sheet == "S-101"

    def test_line_angle_horizontal(self):
        """Test line angle for horizontal section."""
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 0),
        )

        # Horizontal line pointing right = 0 radians
        assert abs(symbol.line_angle) < 0.001

    def test_line_angle_vertical(self):
        """Test line angle for vertical section."""
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(0, 1000),
        )

        # Vertical line pointing up = pi/2 radians
        assert abs(symbol.line_angle - math.pi / 2) < 0.001

    def test_line_angle_diagonal(self):
        """Test line angle for diagonal section."""
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 1000),
        )

        # 45 degree line = pi/4 radians
        assert abs(symbol.line_angle - math.pi / 4) < 0.001

    def test_line_length(self):
        """Test line length calculation."""
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(3000, 4000),
        )

        # 3-4-5 triangle: length = 5000
        assert abs(symbol.line_length - 5000.0) < 0.001

    def test_arrow_angle_right(self):
        """Test arrow angle for look_direction='right'."""
        # Vertical section line going north
        symbol = SectionSymbol(
            start_point=Point2D(5000, 0),
            end_point=Point2D(5000, 10000),
            look_direction="right",
        )

        # Line angle is pi/2 (pointing up)
        # Right of that is 0 (pointing east)
        expected_arrow_angle = math.pi / 2 - math.pi / 2  # = 0
        assert abs(symbol.arrow_angle - expected_arrow_angle) < 0.001

    def test_arrow_angle_left(self):
        """Test arrow angle for look_direction='left'."""
        # Vertical section line going north
        symbol = SectionSymbol(
            start_point=Point2D(5000, 0),
            end_point=Point2D(5000, 10000),
            look_direction="left",
        )

        # Line angle is pi/2 (pointing up)
        # Left of that is pi (pointing west)
        assert abs(symbol.arrow_angle - math.pi) < 0.001

    def test_midpoint(self):
        """Test midpoint calculation."""
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 2000),
        )

        midpoint = symbol.midpoint
        assert midpoint.x == 500.0
        assert midpoint.y == 1000.0

    def test_bubble_centers(self):
        """Test bubble center calculations."""
        style = SectionSymbolStyle(bubble_radius=200.0, line_extension=100.0)
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 0),  # Horizontal line pointing right
            style=style,
        )

        start_bubble = symbol.get_start_bubble_center()
        end_bubble = symbol.get_end_bubble_center()

        # Start bubble should be to the left of start point
        # offset = bubble_radius + line_extension = 300
        assert abs(start_bubble.x - (-300.0)) < 0.001
        assert abs(start_bubble.y - 0.0) < 0.001

        # End bubble should be to the right of end point
        assert abs(end_bubble.x - 1300.0) < 0.001
        assert abs(end_bubble.y - 0.0) < 0.001

    def test_layer(self):
        """Test layer property."""
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 0),
        )

        from bimascode.drawing.line_styles import Layer

        assert symbol.layer == Layer.SYMBOL

    def test_block_name(self):
        """Test block name generation."""
        style = SectionSymbolStyle(bubble_radius=200.0, text_height=120.0, arrow_size=150.0)
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 0),
            style=style,
        )

        assert symbol.block_name == "SECTION_SYMBOL_200_120_150"

    def test_translate(self):
        """Test translating a section symbol."""
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 0),
            section_id="A",
            sheet_number="A2",
        )

        translated = symbol.translate(500, 300)

        assert translated.start_point.x == 500
        assert translated.start_point.y == 300
        assert translated.end_point.x == 1500
        assert translated.end_point.y == 300
        # Other properties preserved
        assert translated.section_id == "A"
        assert translated.sheet_number == "A2"

    def test_scale_and_translate(self):
        """Test scaling and translating a section symbol."""
        style = SectionSymbolStyle(bubble_radius=200.0, text_height=120.0)
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(1000, 0),
            style=style,
        )

        scaled = symbol.scale_and_translate(0.5, 100, 200)

        # Points scaled and translated
        assert scaled.start_point.x == 100  # 0 * 0.5 + 100
        assert scaled.start_point.y == 200  # 0 * 0.5 + 200
        assert scaled.end_point.x == 600  # 1000 * 0.5 + 100
        assert scaled.end_point.y == 200  # 0 * 0.5 + 200
        # Style scaled
        assert scaled.style.bubble_radius == 100.0  # 200 * 0.5
        assert scaled.style.text_height == 60.0  # 120 * 0.5


class TestSectionSymbolFromSectionView:
    """Tests for creating SectionSymbol from SectionView."""

    def test_from_section_view_right(self):
        """Test creating symbol from section view looking right."""
        section_view = SectionView.from_section_line(
            name="Section A-A",
            start_point=(5000, 0),
            end_point=(5000, 10000),
            look_direction="right",
        )

        symbol = SectionSymbol.from_section_view(
            section_view,
            start_point=Point2D(5000, 0),
            end_point=Point2D(5000, 10000),
            section_id="A",
            sheet_number="A2",
        )

        assert symbol.section_view == section_view
        assert symbol.section_id == "A"
        assert symbol.sheet_number == "A2"
        assert symbol.look_direction == "right"

    def test_from_section_view_left(self):
        """Test creating symbol from section view looking left."""
        section_view = SectionView.from_section_line(
            name="Section B-B",
            start_point=(5000, 0),
            end_point=(5000, 10000),
            look_direction="left",
        )

        symbol = SectionSymbol.from_section_view(
            section_view,
            start_point=Point2D(5000, 0),
            end_point=Point2D(5000, 10000),
            section_id="B",
            sheet_number="A3",
        )

        assert symbol.look_direction == "left"


class TestViewResultWithSectionSymbols:
    """Tests for ViewResult with section symbol support."""

    @pytest.fixture
    def section_symbol(self):
        """Create a section symbol for testing."""
        return SectionSymbol(
            start_point=Point2D(5000, 0),
            end_point=Point2D(5000, 10000),
            section_id="A",
            sheet_number="A2",
        )

    def test_view_result_with_section_symbols(self, section_symbol):
        """Test ViewResult containing section symbols."""
        result = ViewResult(section_symbols=[section_symbol])

        assert len(result.section_symbols) == 1
        assert result.section_symbols[0].section_id == "A"

    def test_view_result_total_count_includes_section_symbols(self, section_symbol):
        """Test that total_geometry_count includes section symbols."""
        result = ViewResult(section_symbols=[section_symbol])

        assert result.total_geometry_count == 1

    def test_view_result_extend_with_section_symbols(self, section_symbol):
        """Test extending ViewResult preserves section symbols."""
        result1 = ViewResult()
        result2 = ViewResult(section_symbols=[section_symbol])

        result1.extend(result2)

        assert len(result1.section_symbols) == 1
        assert result1.section_symbols[0].section_id == "A"

    def test_view_result_translate_with_section_symbols(self, section_symbol):
        """Test translating ViewResult includes section symbols."""
        result = ViewResult(section_symbols=[section_symbol])

        original_start = section_symbol.start_point

        translated = result.translate(500, 300)

        assert translated.section_symbols[0].start_point.x == original_start.x + 500
        assert translated.section_symbols[0].start_point.y == original_start.y + 300

    def test_view_result_scale_and_translate_with_section_symbols(self, section_symbol):
        """Test scaling and translating ViewResult includes section symbols."""
        result = ViewResult(section_symbols=[section_symbol])

        scaled = result.scale_and_translate(0.5, 100, 200)

        # start_point was (5000, 0), scaled by 0.5 = (2500, 0), then + (100, 200)
        assert scaled.section_symbols[0].start_point.x == 2600
        assert scaled.section_symbols[0].start_point.y == 200

    def test_view_result_bounds_includes_section_symbols(self, section_symbol):
        """Test that get_bounds includes section symbol positions."""
        result = ViewResult(section_symbols=[section_symbol])

        bounds = result.get_bounds()

        assert bounds is not None
        min_x, min_y, max_x, max_y = bounds

        # Bounds should include section symbol endpoints and bubbles
        assert min_x <= section_symbol.start_point.x <= max_x
        assert min_y <= section_symbol.start_point.y <= max_y
        assert min_x <= section_symbol.end_point.x <= max_x
        assert min_y <= section_symbol.end_point.y <= max_y


class TestSectionSymbolDXFExport:
    """Tests for section symbol DXF export."""

    def test_dxf_export_section_symbols(self, tmp_path):
        """Test exporting section symbols to DXF."""
        from bimascode.drawing.dxf_exporter import DXFExporter

        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(0, 10000),
            section_id="A",
            sheet_number="A2",
        )

        result = ViewResult(section_symbols=[symbol])

        exporter = DXFExporter()
        if not exporter.is_available:
            pytest.skip("ezdxf not available")

        output_path = tmp_path / "test_section_symbol.dxf"
        success = exporter.export(result, str(output_path))

        assert success is True
        assert output_path.exists()

    def test_dxf_export_multiple_section_symbols(self, tmp_path):
        """Test exporting multiple section symbols to DXF."""
        from bimascode.drawing.dxf_exporter import DXFExporter

        symbols = [
            SectionSymbol(
                start_point=Point2D(0, 0),
                end_point=Point2D(0, 10000),
                section_id="A",
                sheet_number="A2",
            ),
            SectionSymbol(
                start_point=Point2D(5000, 0),
                end_point=Point2D(5000, 10000),
                section_id="B",
                sheet_number="A3",
                look_direction="left",
            ),
        ]

        result = ViewResult(section_symbols=symbols)

        exporter = DXFExporter()
        if not exporter.is_available:
            pytest.skip("ezdxf not available")

        output_path = tmp_path / "test_multiple_section_symbols.dxf"
        success = exporter.export(result, str(output_path))

        assert success is True
        assert output_path.exists()

    def test_dxf_export_section_symbol_no_arrows(self, tmp_path):
        """Test exporting section symbol without arrows."""
        from bimascode.drawing.dxf_exporter import DXFExporter

        style = SectionSymbolStyle(show_arrows=False, show_bubbles=True)
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(0, 10000),
            section_id="C",
            style=style,
        )

        result = ViewResult(section_symbols=[symbol])

        exporter = DXFExporter()
        if not exporter.is_available:
            pytest.skip("ezdxf not available")

        output_path = tmp_path / "test_section_no_arrows.dxf"
        success = exporter.export(result, str(output_path))

        assert success is True
        assert output_path.exists()

    def test_dxf_export_section_symbol_no_bubbles(self, tmp_path):
        """Test exporting section symbol without bubbles."""
        from bimascode.drawing.dxf_exporter import DXFExporter

        style = SectionSymbolStyle(show_arrows=True, show_bubbles=False)
        symbol = SectionSymbol(
            start_point=Point2D(0, 0),
            end_point=Point2D(0, 10000),
            section_id="D",
            style=style,
        )

        result = ViewResult(section_symbols=[symbol])

        exporter = DXFExporter()
        if not exporter.is_available:
            pytest.skip("ezdxf not available")

        output_path = tmp_path / "test_section_no_bubbles.dxf"
        success = exporter.export(result, str(output_path))

        assert success is True
        assert output_path.exists()
