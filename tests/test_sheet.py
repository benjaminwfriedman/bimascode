"""Tests for Sheet, SheetSize, SheetViewport, and TitleBlock classes."""

import pytest

from bimascode.drawing import (
    Line2D,
    LineStyle,
    Point2D,
    Sheet,
    SheetMetadata,
    SheetSize,
    SheetViewport,
    TitleBlock,
    TitleBlockField,
    TitleBlockFieldDefinition,
    TitleBlockTemplate,
    ViewResult,
    ViewScale,
    get_title_block_template,
    list_title_block_templates,
    register_title_block_template,
)


class TestSheetSize:
    """Tests for SheetSize class."""

    def test_standard_iso_sizes_defined(self):
        """Test that ISO sizes are defined correctly."""
        assert SheetSize.A0.width == 841.0
        assert SheetSize.A0.height == 1189.0

        assert SheetSize.A1.width == 594.0
        assert SheetSize.A1.height == 841.0

        assert SheetSize.A4.width == 210.0
        assert SheetSize.A4.height == 297.0

    def test_standard_ansi_sizes_defined(self):
        """Test that ANSI sizes are defined correctly."""
        # ANSI D: 22" x 34" = 558.8mm x 863.6mm
        assert SheetSize.ANSI_D.width == pytest.approx(558.8, rel=0.01)
        assert SheetSize.ANSI_D.height == pytest.approx(863.6, rel=0.01)

        # ANSI A: 8.5" x 11" = 215.9mm x 279.4mm
        assert SheetSize.ANSI_A.width == pytest.approx(215.9, rel=0.01)
        assert SheetSize.ANSI_A.height == pytest.approx(279.4, rel=0.01)

    def test_standard_arch_sizes_defined(self):
        """Test that ARCH sizes are defined correctly."""
        # ARCH D: 24" x 36" = 609.6mm x 914.4mm
        assert SheetSize.ARCH_D.width == pytest.approx(609.6, rel=0.01)
        assert SheetSize.ARCH_D.height == pytest.approx(914.4, rel=0.01)

    def test_from_string_iso(self):
        """Test creating ISO size from string."""
        size = SheetSize.from_string("A1")
        assert size == SheetSize.A1

        size = SheetSize.from_string("a1")  # lowercase
        assert size == SheetSize.A1

    def test_from_string_ansi(self):
        """Test creating ANSI size from string."""
        size = SheetSize.from_string("ANSI D")
        assert size == SheetSize.ANSI_D

        size = SheetSize.from_string("ANSI_D")
        assert size == SheetSize.ANSI_D

        size = SheetSize.from_string("ansi-d")
        assert size == SheetSize.ANSI_D

    def test_from_string_arch(self):
        """Test creating ARCH size from string."""
        size = SheetSize.from_string("ARCH D")
        assert size == SheetSize.ARCH_D

        size = SheetSize.from_string("ARCH_D")
        assert size == SheetSize.ARCH_D

    def test_from_string_invalid(self):
        """Test that invalid size name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown sheet size"):
            SheetSize.from_string("INVALID")

    def test_custom_size(self):
        """Test creating custom sheet size."""
        size = SheetSize.custom(1000, 700, "Custom")
        assert size.width == 1000
        assert size.height == 700
        assert size.name == "Custom"

    def test_landscape_property(self):
        """Test landscape property."""
        # ANSI D is portrait (width=558.8 < height=863.6)
        assert SheetSize.ANSI_D.landscape is False
        assert SheetSize.ANSI_D.portrait is True

        # ARCH D is landscape (width=609.6 < height=914.4) - also portrait
        # Let's use a custom landscape sheet
        landscape = SheetSize.custom(1000, 500, "Landscape")
        assert landscape.landscape is True
        assert landscape.portrait is False

        # A4 is portrait (height > width)
        assert SheetSize.A4.landscape is False
        assert SheetSize.A4.portrait is True

    def test_size_tuple(self):
        """Test size_tuple property."""
        assert SheetSize.A1.size_tuple == (594.0, 841.0)

    def test_area(self):
        """Test area property."""
        assert SheetSize.A4.area == 210.0 * 297.0


class TestSheetMetadata:
    """Tests for SheetMetadata class."""

    def test_default_values(self):
        """Test default metadata values."""
        metadata = SheetMetadata()
        assert metadata.project == ""
        assert metadata.drawn_by == ""
        assert metadata.date == ""

    def test_custom_values(self):
        """Test custom metadata values."""
        metadata = SheetMetadata(
            project="Test Project",
            drawn_by="BF",
            checked_by="JS",
            date="2026-03-25",
            revision="A",
        )
        assert metadata.project == "Test Project"
        assert metadata.drawn_by == "BF"
        assert metadata.checked_by == "JS"
        assert metadata.date == "2026-03-25"
        assert metadata.revision == "A"


class TestSheet:
    """Tests for Sheet class."""

    def test_sheet_creation(self):
        """Test basic sheet creation."""
        sheet = Sheet(size=SheetSize.ANSI_D, number="A-101", name="Ground Floor")

        assert sheet.number == "A-101"
        assert sheet.name == "Ground Floor"
        assert sheet.size == SheetSize.ANSI_D

    def test_sheet_from_string_size(self):
        """Test sheet creation with string size."""
        sheet = Sheet(size="ANSI D", number="A-101")

        assert sheet.size == SheetSize.ANSI_D

    def test_default_margins(self):
        """Test default margins."""
        sheet = Sheet(size=SheetSize.A1)

        assert sheet.margins == (10.0, 10.0, 10.0, 10.0)

    def test_custom_margins(self):
        """Test custom margins."""
        sheet = Sheet(size=SheetSize.A1, margins=(20, 15, 20, 15))

        assert sheet.margins == (20, 15, 20, 15)

    def test_printable_area(self):
        """Test printable area calculation."""
        sheet = Sheet(size=SheetSize.A1)
        sheet.margins = (10, 10, 10, 10)

        area = sheet.printable_area
        assert area[0] == 10  # min_x
        assert area[1] == 10  # min_y
        assert area[2] == SheetSize.A1.width - 10  # max_x
        assert area[3] == SheetSize.A1.height - 10  # max_y

    def test_printable_dimensions(self):
        """Test printable width and height."""
        sheet = Sheet(size=SheetSize.A1, margins=(10, 10, 10, 10))

        assert sheet.printable_width == SheetSize.A1.width - 20
        assert sheet.printable_height == SheetSize.A1.height - 20

    def test_metadata(self):
        """Test metadata property."""
        metadata = SheetMetadata(project="Test")
        sheet = Sheet(size=SheetSize.A1, metadata=metadata)

        assert sheet.metadata.project == "Test"

    def test_repr(self):
        """Test string representation."""
        sheet = Sheet(size=SheetSize.ANSI_D, number="A-101", name="Ground Floor")

        repr_str = repr(sheet)
        assert "A-101" in repr_str
        assert "Ground Floor" in repr_str
        assert "ANSI D" in repr_str


class TestSheetViewport:
    """Tests for adding viewports to sheets."""

    @pytest.fixture
    def simple_view_result(self):
        """Create a simple ViewResult for testing."""
        return ViewResult(
            lines=[
                Line2D(
                    Point2D(0, 0),
                    Point2D(10000, 0),
                    LineStyle.default(),
                ),
                Line2D(
                    Point2D(10000, 0),
                    Point2D(10000, 5000),
                    LineStyle.default(),
                ),
            ],
        )

    def test_add_viewport(self, simple_view_result):
        """Test adding a viewport to a sheet."""
        sheet = Sheet(size=SheetSize.A1, number="A-101")

        vp = sheet.add_viewport(
            simple_view_result,
            position=(300, 200),
            scale="1:100",
        )

        assert len(sheet.viewports) == 1
        assert vp.position == Point2D(300, 200)
        assert vp.scale.ratio == 0.01

    def test_add_viewport_with_viewscale(self, simple_view_result):
        """Test adding viewport with ViewScale object."""
        sheet = Sheet(size=SheetSize.A1)

        vp = sheet.add_viewport(
            simple_view_result,
            position=Point2D(300, 200),
            scale=ViewScale.SCALE_1_50,
        )

        assert vp.scale == ViewScale.SCALE_1_50

    def test_add_multiple_viewports(self, simple_view_result):
        """Test adding multiple viewports."""
        sheet = Sheet(size=SheetSize.A1)

        sheet.add_viewport(simple_view_result, position=(200, 300), scale="1:100")
        sheet.add_viewport(simple_view_result, position=(500, 300), scale="1:50")

        assert len(sheet.viewports) == 2

    def test_remove_viewport(self, simple_view_result):
        """Test removing a viewport."""
        sheet = Sheet(size=SheetSize.A1)
        vp = sheet.add_viewport(simple_view_result, position=(0, 0), scale="1:100")

        result = sheet.remove_viewport(vp)

        assert result is True
        assert len(sheet.viewports) == 0

    def test_remove_nonexistent_viewport(self, simple_view_result):
        """Test removing a viewport that doesn't exist."""
        sheet = Sheet(size=SheetSize.A1)
        vp = SheetViewport(
            view_result=simple_view_result,
            position=Point2D(0, 0),
            scale=ViewScale.SCALE_1_100,
        )

        result = sheet.remove_viewport(vp)

        assert result is False

    def test_clear_viewports(self, simple_view_result):
        """Test clearing all viewports."""
        sheet = Sheet(size=SheetSize.A1)
        sheet.add_viewport(simple_view_result, position=(200, 300), scale="1:100")
        sheet.add_viewport(simple_view_result, position=(500, 300), scale="1:50")

        sheet.clear_viewports()

        assert len(sheet.viewports) == 0

    def test_get_viewport_by_name(self, simple_view_result):
        """Test finding viewport by name."""
        sheet = Sheet(size=SheetSize.A1)
        sheet.add_viewport(
            simple_view_result, position=(200, 300), scale="1:100", name="Floor Plan"
        )
        sheet.add_viewport(simple_view_result, position=(500, 300), scale="1:50", name="Section")

        vp = sheet.get_viewport_by_name("Floor Plan")

        assert vp is not None
        assert vp.name == "Floor Plan"

    def test_get_viewport_by_name_not_found(self, simple_view_result):
        """Test finding viewport by name when not found."""
        sheet = Sheet(size=SheetSize.A1)

        vp = sheet.get_viewport_by_name("Nonexistent")

        assert vp is None

    def test_viewport_bounds_on_sheet(self, simple_view_result):
        """Test viewport bounds calculation."""
        vp = SheetViewport(
            view_result=simple_view_result,
            position=Point2D(300, 200),
            scale=ViewScale.SCALE_1_100,
            width=200,
            height=100,
        )

        bounds = vp.bounds_on_sheet

        assert bounds == (200, 150, 400, 250)  # center - half, center + half


class TestTitleBlockTemplate:
    """Tests for TitleBlockTemplate class."""

    def test_list_templates(self):
        """Test listing available templates."""
        templates = list_title_block_templates()
        assert "standard_ansi_d" in templates
        assert "standard_arch_d" in templates
        assert "standard_iso_a1" in templates
        assert "minimal" in templates

    def test_get_template(self):
        """Test getting a template by name."""
        template = get_title_block_template("standard_ansi_d")
        assert template is not None
        assert template.name == "standard_ansi_d"
        assert template.width == 180.0
        assert template.height == 50.0

    def test_get_nonexistent_template(self):
        """Test getting a template that doesn't exist."""
        template = get_title_block_template("nonexistent")
        assert template is None

    def test_template_has_fields(self):
        """Test that templates define fields."""
        template = get_title_block_template("standard_ansi_d")
        assert len(template.fields) > 0

        # Check for expected fields
        tags = [f.tag for f in template.fields]
        assert TitleBlockField.PROJECT_NAME.value in tags
        assert TitleBlockField.SHEET_NUMBER.value in tags
        assert TitleBlockField.SHEET_NAME.value in tags
        assert TitleBlockField.DATE.value in tags

    def test_template_generate_geometry(self):
        """Test template geometry generation."""
        template = get_title_block_template("standard_ansi_d")
        geometry = template.generate_geometry()

        assert geometry is not None
        assert len(geometry.lines) == 4  # Border rectangle

    def test_register_custom_template(self):
        """Test registering a custom template."""
        custom = TitleBlockTemplate(
            name="custom_test",
            width=100.0,
            height=30.0,
            fields=[
                TitleBlockFieldDefinition(
                    tag="CUSTOM_FIELD",
                    prompt="Custom Field",
                    position=Point2D(10, 20),
                    height=3.0,
                )
            ],
        )
        register_title_block_template(custom)

        retrieved = get_title_block_template("custom_test")
        assert retrieved is not None
        assert retrieved.name == "custom_test"
        assert len(retrieved.fields) == 1


class TestTitleBlock:
    """Tests for TitleBlock class."""

    def test_title_block_creation(self):
        """Test basic title block creation."""
        tb = TitleBlock(
            name="standard",
            fields={
                TitleBlockField.PROJECT_NAME.value: "Test Project",
                TitleBlockField.SHEET_NUMBER.value: "A-101",
            },
        )

        assert tb.name == "standard"
        assert tb.project_name == "Test Project"
        assert tb.sheet_number == "A-101"

    def test_title_block_from_template(self):
        """Test creating title block from template."""
        tb = TitleBlock.from_template(
            "standard_ansi_d",
            fields={
                TitleBlockField.PROJECT_NAME.value: "One Harbor Place",
                TitleBlockField.SHEET_NUMBER.value: "A-101",
                TitleBlockField.SHEET_NAME.value: "Ground Floor Plan",
            },
        )

        assert tb.name == "standard_ansi_d"
        assert tb.project_name == "One Harbor Place"
        assert tb.sheet_number == "A-101"
        assert tb.sheet_name == "Ground Floor Plan"
        assert tb.template is not None
        assert tb.has_geometry() is True

    def test_title_block_from_template_with_position(self):
        """Test creating title block with position."""
        tb = TitleBlock.from_template(
            "standard_ansi_d",
            position=(100.0, 50.0),
        )

        assert tb.position == Point2D(100.0, 50.0)

    def test_title_block_from_invalid_template(self):
        """Test that invalid template raises error."""
        with pytest.raises(ValueError, match="Unknown title block template"):
            TitleBlock.from_template("nonexistent")

    def test_title_block_from_sheet(self):
        """Test creating title block from sheet metadata."""
        metadata = SheetMetadata(
            project="Test Project",
            drawn_by="BF",
            checked_by="JS",
            date="2026-04-26",
            scale="1:100",
        )
        sheet = Sheet(
            size=SheetSize.ANSI_D,
            number="A-101",
            name="Ground Floor",
            metadata=metadata,
        )

        tb = TitleBlock.from_sheet(sheet, template_name="standard_ansi_d")

        assert tb.project_name == "Test Project"
        assert tb.sheet_number == "A-101"
        assert tb.sheet_name == "Ground Floor"
        assert tb.drawn_by == "BF"
        assert tb.checked_by == "JS"
        assert tb.date == "2026-04-26"
        # Position should be at lower-right
        assert tb.position.x > 0
        assert tb.position.y > 0

    def test_title_block_field_setters(self):
        """Test title block field setters."""
        tb = TitleBlock(name="standard")

        tb.project_name = "My Project"
        tb.sheet_number = "A-102"
        tb.drawn_by = "BF"

        assert tb.project_name == "My Project"
        assert tb.sheet_number == "A-102"
        assert tb.drawn_by == "BF"

    def test_title_block_get_set_field(self):
        """Test generic get/set field methods."""
        tb = TitleBlock(name="standard")

        tb.set_field("custom_field", "custom_value")

        assert tb.get_field("custom_field") == "custom_value"
        assert tb.get_field("nonexistent", "default") == "default"

    def test_has_geometry(self):
        """Test has_geometry method."""
        tb = TitleBlock(name="standard")
        assert tb.has_geometry() is False

        tb.geometry = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(100, 0), LineStyle.default())]
        )
        assert tb.has_geometry() is True

    def test_get_text_notes(self):
        """Test generating text notes from fields."""
        tb = TitleBlock.from_template(
            "standard_ansi_d",
            fields={
                TitleBlockField.PROJECT_NAME.value: "Test Project",
                TitleBlockField.SHEET_NUMBER.value: "A-101",
            },
            position=(100.0, 50.0),
        )

        notes = tb.get_text_notes()

        assert len(notes) == 2
        # Check that positions are offset by title block position
        for note in notes:
            assert note.position.x >= 100.0
            assert note.position.y >= 50.0

    def test_get_full_geometry(self):
        """Test getting complete geometry with text."""
        tb = TitleBlock.from_template(
            "standard_ansi_d",
            fields={
                TitleBlockField.PROJECT_NAME.value: "Test Project",
            },
            position=(100.0, 50.0),
        )

        geometry = tb.get_full_geometry()

        assert len(geometry.lines) == 4  # Border
        assert len(geometry.text_notes) == 1  # Project name

    def test_width_height_from_template(self):
        """Test width/height properties from template."""
        tb = TitleBlock.from_template("standard_ansi_d")

        assert tb.width == 180.0
        assert tb.height == 50.0

    def test_width_height_defaults(self):
        """Test width/height defaults without template."""
        tb = TitleBlock(name="custom")

        assert tb.width == 180.0  # Default
        assert tb.height == 50.0  # Default

    def test_block_name(self):
        """Test DXF block name generation."""
        tb = TitleBlock.from_template("standard_ansi_d")

        block_name = tb.block_name
        assert "TITLE_BLOCK" in block_name
        assert "standard_ansi_d" in block_name


class TestSheetTitleBlock:
    """Tests for title block management on sheets."""

    def test_set_title_block(self):
        """Test setting title block on sheet."""
        sheet = Sheet(size=SheetSize.A1, number="A-101")
        tb = TitleBlock(name="standard")

        sheet.set_title_block(tb)

        assert sheet.title_block is not None
        assert sheet.title_block.name == "standard"

    def test_set_title_block_with_position(self):
        """Test setting title block with position override."""
        sheet = Sheet(size=SheetSize.A1)
        tb = TitleBlock(name="standard", position=Point2D(0, 0))

        sheet.set_title_block(tb, position=(100, 50))

        assert sheet.title_block.position == Point2D(100, 50)

    def test_remove_title_block(self):
        """Test removing title block from sheet."""
        sheet = Sheet(size=SheetSize.A1)
        tb = TitleBlock(name="standard")
        sheet.set_title_block(tb)

        sheet.remove_title_block()

        assert sheet.title_block is None


class TestSheetExport:
    """Tests for sheet DXF export."""

    @pytest.fixture
    def sheet_with_viewport(self):
        """Create a sheet with a viewport for testing."""
        sheet = Sheet(size=SheetSize.A1, number="A-101", name="Test")
        view_result = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(5000, 0), LineStyle.default())],
        )
        sheet.add_viewport(view_result, position=(300, 400), scale="1:100")
        return sheet

    def test_export_creates_file(self, sheet_with_viewport, tmp_path):
        """Test that export creates a DXF file."""
        filepath = tmp_path / "test_sheet.dxf"

        result = sheet_with_viewport.export_dxf(str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_has_paperspace_layout(self, sheet_with_viewport, tmp_path):
        """Test that exported file has paperspace layout when flat=False."""
        import ezdxf

        filepath = tmp_path / "test_sheet.dxf"
        sheet_with_viewport.export_dxf(str(filepath), flat=False)

        doc = ezdxf.readfile(str(filepath))
        layouts = list(doc.layouts)

        # Should have Model + at least one paperspace layout
        assert len(layouts) >= 2
        # Check our layout name exists
        layout_names = [layout.name for layout in layouts]
        assert "A-101 - Test" in layout_names

    def test_export_empty_sheet(self, tmp_path):
        """Test exporting sheet with no viewports."""
        sheet = Sheet(size=SheetSize.A1, number="A-102", name="Empty")
        filepath = tmp_path / "empty_sheet.dxf"

        result = sheet.export_dxf(str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_sheet_with_multiple_viewports(self, tmp_path):
        """Test exporting sheet with multiple viewports."""
        sheet = Sheet(size=SheetSize.ARCH_D, number="A-103")

        view1 = ViewResult(lines=[Line2D(Point2D(0, 0), Point2D(3000, 0), LineStyle.default())])
        view2 = ViewResult(lines=[Line2D(Point2D(0, 0), Point2D(2000, 2000), LineStyle.default())])

        sheet.add_viewport(view1, position=(200, 300), scale="1:100")
        sheet.add_viewport(view2, position=(500, 300), scale="1:50")

        filepath = tmp_path / "multi_viewport.dxf"
        result = sheet.export_dxf(str(filepath))

        assert result is True
        assert filepath.exists()

    def test_export_sheet_with_title_block_flat(self, tmp_path):
        """Test exporting sheet with title block in flat mode."""
        import ezdxf

        sheet = Sheet(
            size=SheetSize.ANSI_D,
            number="A-101",
            name="Ground Floor",
            metadata=SheetMetadata(project="Test Project", drawn_by="BF"),
        )
        view_result = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(5000, 0), LineStyle.default())]
        )
        sheet.add_viewport(view_result, position=(300, 400), scale="1:100")

        # Add title block from sheet metadata
        tb = TitleBlock.from_sheet(sheet, template_name="standard_ansi_d")
        sheet.set_title_block(tb)

        filepath = tmp_path / "sheet_with_tb_flat.dxf"
        result = sheet.export_dxf(str(filepath), flat=True)

        assert result is True
        assert filepath.exists()

        # Verify the DXF contains title block geometry
        doc = ezdxf.readfile(str(filepath))
        msp = doc.modelspace()

        # Should have lines from title block border
        lines = list(msp.query("LINE"))
        assert len(lines) > 4  # View content + title block border + sheet border

        # Should have MTEXT from title block fields
        texts = list(msp.query("MTEXT"))
        assert len(texts) > 0

    def test_export_sheet_with_title_block_paperspace(self, tmp_path):
        """Test exporting sheet with title block in paperspace mode."""
        import ezdxf

        sheet = Sheet(
            size=SheetSize.ANSI_D,
            number="A-102",
            name="Section View",
            metadata=SheetMetadata(project="Test Project", drawn_by="BF"),
        )
        view_result = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(5000, 0), LineStyle.default())]
        )
        sheet.add_viewport(view_result, position=(300, 400), scale="1:100")

        # Add title block
        tb = TitleBlock.from_sheet(sheet, template_name="standard_ansi_d")
        sheet.set_title_block(tb)

        filepath = tmp_path / "sheet_with_tb_ps.dxf"
        result = sheet.export_dxf(str(filepath), flat=False)

        assert result is True
        assert filepath.exists()

        # Verify the DXF has block definitions
        doc = ezdxf.readfile(str(filepath))

        # Should have a title block BLOCK definition
        block_names = [b.name for b in doc.blocks]
        title_blocks = [n for n in block_names if "TITLE_BLOCK" in n]
        assert len(title_blocks) > 0

    def test_export_title_block_with_all_fields(self, tmp_path):
        """Test that all title block fields are exported."""
        import ezdxf

        sheet = Sheet(
            size=SheetSize.ANSI_D,
            number="A-105",
            name="Full Fields Test",
        )
        view_result = ViewResult(
            lines=[Line2D(Point2D(0, 0), Point2D(5000, 0), LineStyle.default())]
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

        filepath = tmp_path / "full_fields.dxf"
        result = sheet.export_dxf(str(filepath), flat=True)

        assert result is True

        # Verify all text notes are present
        doc = ezdxf.readfile(str(filepath))
        msp = doc.modelspace()
        texts = list(msp.query("MTEXT"))

        # Should have text for all the fields we set
        text_contents = [t.text for t in texts]
        assert any("Complete Project" in t for t in text_contents)
        assert any("A-105" in t for t in text_contents)
