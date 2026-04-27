"""Tests for PDF export functionality."""

import math

import pytest

from bimascode.drawing import (
    Layer,
    Line2D,
    LineStyle,
    Point2D,
    Sheet,
    SheetMetadata,
    SheetSize,
    TitleBlock,
    TitleBlockField,
    ViewResult,
)
from bimascode.drawing.pdf_exporter import PDFExporter, get_pdf_exporter
from bimascode.drawing.primitives import (
    Arc2D,
    ChainDimension2D,
    Hatch2D,
    LinearDimension2D,
    Polyline2D,
    TextNote2D,
)


class TestPDFExporter:
    """Tests for PDFExporter class."""

    def test_exporter_creation(self):
        """Test basic exporter creation."""
        exporter = PDFExporter()
        assert exporter.is_available is True
        assert exporter.color_mode == "color"
        assert exporter.background == "white"
        assert exporter.dpi == 300

    def test_exporter_custom_settings(self):
        """Test exporter with custom settings."""
        exporter = PDFExporter(
            color_mode="grayscale",
            background="transparent",
            dpi=150,
        )
        assert exporter.color_mode == "grayscale"
        assert exporter.background == "transparent"
        assert exporter.dpi == 150

    def test_global_exporter(self):
        """Test global exporter instance."""
        exporter1 = get_pdf_exporter()
        exporter2 = get_pdf_exporter()
        assert exporter1 is exporter2


class TestPDFExportViewResult:
    """Tests for exporting ViewResult to PDF."""

    @pytest.fixture
    def simple_view_result(self):
        """Create a simple ViewResult for testing."""
        return ViewResult(
            lines=[
                Line2D(
                    Point2D(0, 0),
                    Point2D(10000, 0),
                    LineStyle.cut_heavy(),
                    Layer.WALL,
                ),
                Line2D(
                    Point2D(10000, 0),
                    Point2D(10000, 5000),
                    LineStyle.cut_heavy(),
                    Layer.WALL,
                ),
                Line2D(
                    Point2D(10000, 5000),
                    Point2D(0, 5000),
                    LineStyle.cut_heavy(),
                    Layer.WALL,
                ),
                Line2D(
                    Point2D(0, 5000),
                    Point2D(0, 0),
                    LineStyle.cut_heavy(),
                    Layer.WALL,
                ),
            ],
        )

    def test_export_creates_file(self, simple_view_result, tmp_path):
        """Test that export creates a PDF file."""
        filepath = tmp_path / "test_view.pdf"
        exporter = PDFExporter()

        result = exporter.export(simple_view_result, str(filepath))

        assert result is True
        assert filepath.exists()
        assert filepath.stat().st_size > 0

    def test_export_with_scale(self, simple_view_result, tmp_path):
        """Test export with scaling."""
        filepath = tmp_path / "test_scaled.pdf"
        exporter = PDFExporter()

        result = exporter.export(simple_view_result, str(filepath), scale=0.01)

        assert result is True
        assert filepath.exists()

    def test_export_with_paper_size(self, simple_view_result, tmp_path):
        """Test export with specific paper size."""
        filepath = tmp_path / "test_paper.pdf"
        exporter = PDFExporter()

        result = exporter.export(
            simple_view_result,
            str(filepath),
            paper_size=(297, 210),  # A4 landscape
        )

        assert result is True
        assert filepath.exists()

    def test_export_empty_view_result(self, tmp_path):
        """Test export of empty ViewResult."""
        filepath = tmp_path / "test_empty.pdf"
        exporter = PDFExporter()
        empty_view = ViewResult()

        result = exporter.export(empty_view, str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_grayscale(self, simple_view_result, tmp_path):
        """Test export in grayscale mode."""
        filepath = tmp_path / "test_grayscale.pdf"
        exporter = PDFExporter(color_mode="grayscale")

        result = exporter.export(simple_view_result, str(filepath))

        assert result is True
        assert filepath.exists()


class TestPDFExportGeometryTypes:
    """Tests for exporting different geometry types."""

    def test_export_arcs(self, tmp_path):
        """Test export of arc geometry."""
        view_result = ViewResult(
            arcs=[
                Arc2D(
                    center=Point2D(5000, 5000),
                    radius=2000,
                    start_angle=0,
                    end_angle=math.pi,
                    style=LineStyle.cut_heavy(),
                    layer=Layer.WALL,
                ),
            ],
        )
        filepath = tmp_path / "test_arcs.pdf"
        exporter = PDFExporter()

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_polylines(self, tmp_path):
        """Test export of polyline geometry."""
        view_result = ViewResult(
            polylines=[
                Polyline2D(
                    points=[
                        Point2D(0, 0),
                        Point2D(1000, 0),
                        Point2D(1000, 1000),
                        Point2D(0, 1000),
                    ],
                    closed=True,
                    style=LineStyle.cut_heavy(),
                    layer=Layer.WALL,
                ),
            ],
        )
        filepath = tmp_path / "test_polylines.pdf"
        exporter = PDFExporter()

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_hatches(self, tmp_path):
        """Test export of hatch geometry."""
        view_result = ViewResult(
            hatches=[
                Hatch2D(
                    boundary=[
                        Point2D(0, 0),
                        Point2D(5000, 0),
                        Point2D(5000, 3000),
                        Point2D(0, 3000),
                    ],
                    pattern="SOLID",
                    color=(200, 200, 200),
                    layer=Layer.WALL,
                ),
            ],
        )
        filepath = tmp_path / "test_hatches.pdf"
        exporter = PDFExporter()

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_dimensions(self, tmp_path):
        """Test export of dimension geometry."""
        view_result = ViewResult(
            dimensions=[
                LinearDimension2D(
                    start=Point2D(0, 0),
                    end=Point2D(5000, 0),
                    offset=500,
                    precision=0,
                    layer=Layer.DIMENSION,
                ),
            ],
        )
        filepath = tmp_path / "test_dimensions.pdf"
        exporter = PDFExporter()

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_chain_dimensions(self, tmp_path):
        """Test export of chain dimension geometry."""
        view_result = ViewResult(
            chain_dimensions=[
                ChainDimension2D(
                    points=(Point2D(0, 0), Point2D(2000, 0), Point2D(5000, 0)),
                    offset=500,
                    precision=0,
                    layer=Layer.DIMENSION,
                ),
            ],
        )
        filepath = tmp_path / "test_chain_dims.pdf"
        exporter = PDFExporter()

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_text_notes(self, tmp_path):
        """Test export of text notes."""
        view_result = ViewResult(
            text_notes=[
                TextNote2D(
                    position=Point2D(2500, 2500),
                    content="Test Note",
                    height=200,
                    alignment="MIDDLE_CENTER",
                    layer=Layer.ANNOTATION,
                ),
            ],
        )
        filepath = tmp_path / "test_text.pdf"
        exporter = PDFExporter()

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()


class TestPDFExportSheet:
    """Tests for exporting Sheet to PDF."""

    @pytest.fixture
    def sheet_with_viewport(self):
        """Create a sheet with a viewport for testing."""
        sheet = Sheet(size=SheetSize.A1, number="A-101", name="Test Sheet")
        view_result = ViewResult(
            lines=[
                Line2D(Point2D(0, 0), Point2D(10000, 0), LineStyle.cut_heavy(), Layer.WALL),
                Line2D(Point2D(10000, 0), Point2D(10000, 5000), LineStyle.cut_heavy(), Layer.WALL),
                Line2D(Point2D(10000, 5000), Point2D(0, 5000), LineStyle.cut_heavy(), Layer.WALL),
                Line2D(Point2D(0, 5000), Point2D(0, 0), LineStyle.cut_heavy(), Layer.WALL),
            ],
            view_name="Floor Plan",
        )
        sheet.add_viewport(view_result, position=(300, 400), scale="1:100", name="Floor Plan")
        return sheet

    def test_sheet_export_pdf(self, sheet_with_viewport, tmp_path):
        """Test basic sheet PDF export."""
        filepath = tmp_path / "test_sheet.pdf"

        result = sheet_with_viewport.export_pdf(str(filepath))

        assert result is True
        assert filepath.exists()
        assert filepath.stat().st_size > 0

    def test_sheet_export_pdf_grayscale(self, sheet_with_viewport, tmp_path):
        """Test sheet PDF export in grayscale."""
        filepath = tmp_path / "test_sheet_bw.pdf"

        result = sheet_with_viewport.export_pdf(str(filepath), color_mode="grayscale")

        assert result is True
        assert filepath.exists()

    def test_sheet_export_pdf_transparent(self, sheet_with_viewport, tmp_path):
        """Test sheet PDF export with transparent background."""
        filepath = tmp_path / "test_sheet_transparent.pdf"

        result = sheet_with_viewport.export_pdf(str(filepath), background="transparent")

        assert result is True
        assert filepath.exists()

    def test_sheet_export_pdf_custom_dpi(self, sheet_with_viewport, tmp_path):
        """Test sheet PDF export with custom DPI."""
        filepath = tmp_path / "test_sheet_150dpi.pdf"

        result = sheet_with_viewport.export_pdf(str(filepath), dpi=150)

        assert result is True
        assert filepath.exists()

    def test_sheet_export_empty_sheet(self, tmp_path):
        """Test exporting sheet with no viewports."""
        sheet = Sheet(size=SheetSize.A1, number="A-102", name="Empty")
        filepath = tmp_path / "empty_sheet.pdf"

        result = sheet.export_pdf(str(filepath))

        assert result is True
        assert filepath.exists()

    def test_sheet_export_multiple_viewports(self, tmp_path):
        """Test exporting sheet with multiple viewports."""
        sheet = Sheet(size=SheetSize.ARCH_D, number="A-103")

        view1 = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(3000, 0), LineStyle.cut_heavy())],
            view_name="Plan",
        )
        view2 = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(2000, 2000), LineStyle.cut_heavy())],
            view_name="Section",
        )

        sheet.add_viewport(view1, position=(200, 500), scale="1:100", name="Plan")
        sheet.add_viewport(view2, position=(500, 300), scale="1:50", name="Section")

        filepath = tmp_path / "multi_viewport.pdf"
        result = sheet.export_pdf(str(filepath))

        assert result is True
        assert filepath.exists()

    def test_sheet_export_with_title_block(self, tmp_path):
        """Test exporting sheet with title block."""
        sheet = Sheet(
            size=SheetSize.ANSI_D,
            number="A-101",
            name="Ground Floor",
            metadata=SheetMetadata(project="Test Project", drawn_by="BF"),
        )
        view_result = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(5000, 0), LineStyle.cut_heavy())]
        )
        sheet.add_viewport(view_result, position=(300, 400), scale="1:100")

        # Add title block
        tb = TitleBlock.from_sheet(sheet, template_name="standard_ansi_d")
        sheet.set_title_block(tb)

        filepath = tmp_path / "sheet_with_tb.pdf"
        result = sheet.export_pdf(str(filepath))

        assert result is True
        assert filepath.exists()

    def test_sheet_export_with_all_fields(self, tmp_path):
        """Test sheet export with all title block fields."""
        sheet = Sheet(
            size=SheetSize.ANSI_D,
            number="A-105",
            name="Full Fields Test",
        )
        view_result = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(5000, 0), LineStyle.cut_heavy())]
        )
        sheet.add_viewport(view_result, position=(300, 400), scale="1:100")

        # Create title block with all fields
        tb = TitleBlock.from_template(
            "standard_ansi_d",
            fields={
                TitleBlockField.PROJECT_NAME.value: "Complete Project",
                TitleBlockField.PROJECT_ADDRESS.value: "123 Main St",
                TitleBlockField.CLIENT_NAME.value: "ACME Corp",
                TitleBlockField.SHEET_NAME.value: "Ground Floor Plan",
                TitleBlockField.SHEET_NUMBER.value: "A-105",
                TitleBlockField.DRAWN_BY.value: "JD",
                TitleBlockField.CHECKED_BY.value: "SM",
                TitleBlockField.DATE.value: "2026-04-26",
                TitleBlockField.SCALE.value: "1:100",
                TitleBlockField.REVISION.value: "A",
            },
        )
        sheet.set_title_block(tb)

        filepath = tmp_path / "full_fields.pdf"
        result = sheet.export_pdf(str(filepath))

        assert result is True
        assert filepath.exists()


class TestPDFExportDirectMethod:
    """Tests for PDFExporter.export_sheet direct method."""

    def test_export_sheet_via_exporter(self, tmp_path):
        """Test exporting sheet via PDFExporter directly."""
        sheet = Sheet(size=SheetSize.A1, number="A-101")
        view_result = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(5000, 0), LineStyle.cut_heavy())]
        )
        sheet.add_viewport(view_result, position=(300, 400), scale="1:100")

        exporter = PDFExporter()
        filepath = tmp_path / "direct_export.pdf"

        result = exporter.export_sheet(sheet, str(filepath))

        assert result is True
        assert filepath.exists()


class TestPDFExportLineStyles:
    """Tests for correct line style rendering."""

    def test_all_line_types(self, tmp_path):
        """Test export of all line types."""
        from bimascode.drawing.line_styles import LineType, LineWeight

        y_pos = 0
        lines = []
        for line_type in LineType:
            style = LineStyle(weight=LineWeight.MEDIUM, type=line_type)
            lines.append(
                Line2D(
                    Point2D(0, y_pos),
                    Point2D(10000, y_pos),
                    style=style,
                    layer=Layer.WALL,
                )
            )
            y_pos += 500

        view_result = ViewResult(lines=lines)
        filepath = tmp_path / "line_types.pdf"
        exporter = PDFExporter()

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()

    def test_all_line_weights(self, tmp_path):
        """Test export of all line weights."""
        from bimascode.drawing.line_styles import LineType, LineWeight

        y_pos = 0
        lines = []
        for weight in LineWeight:
            style = LineStyle(weight=weight, type=LineType.CONTINUOUS)
            lines.append(
                Line2D(
                    Point2D(0, y_pos),
                    Point2D(10000, y_pos),
                    style=style,
                    layer=Layer.WALL,
                )
            )
            y_pos += 500

        view_result = ViewResult(lines=lines)
        filepath = tmp_path / "line_weights.pdf"
        exporter = PDFExporter()

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()

    def test_colored_lines(self, tmp_path):
        """Test export of colored lines."""
        lines = [
            Line2D(
                Point2D(0, 0),
                Point2D(5000, 0),
                style=LineStyle.cut_heavy().with_color((255, 0, 0)),  # Red
                layer=Layer.WALL,
            ),
            Line2D(
                Point2D(0, 500),
                Point2D(5000, 500),
                style=LineStyle.cut_heavy().with_color((0, 255, 0)),  # Green
                layer=Layer.WALL,
            ),
            Line2D(
                Point2D(0, 1000),
                Point2D(5000, 1000),
                style=LineStyle.cut_heavy().with_color((0, 0, 255)),  # Blue
                layer=Layer.WALL,
            ),
        ]

        view_result = ViewResult(lines=lines)
        filepath = tmp_path / "colored_lines.pdf"
        exporter = PDFExporter(color_mode="color")

        result = exporter.export(view_result, str(filepath))

        assert result is True
        assert filepath.exists()
