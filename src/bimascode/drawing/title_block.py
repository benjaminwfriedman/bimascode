"""Title block for drawing sheets.

Defines TitleBlock class and TitleBlockTemplate for sheet title blocks.
Supports DXF BLOCK/ATTDEF/ATTRIB export with standard and custom templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from bimascode.drawing.line_styles import Layer, LineStyle
from bimascode.drawing.primitives import Line2D, Point2D, TextNote2D, ViewResult

if TYPE_CHECKING:
    from bimascode.drawing.sheet import Sheet


class TitleBlockField(Enum):
    """Standard title block field identifiers."""

    PROJECT_NAME = "PROJECT_NAME"
    PROJECT_NUMBER = "PROJECT_NUMBER"
    PROJECT_ADDRESS = "PROJECT_ADDRESS"
    CLIENT_NAME = "CLIENT_NAME"
    SHEET_NUMBER = "SHEET_NUMBER"
    SHEET_NAME = "SHEET_NAME"
    DATE = "DATE"
    DRAWN_BY = "DRAWN_BY"
    CHECKED_BY = "CHECKED_BY"
    APPROVED_BY = "APPROVED_BY"
    REVISION = "REVISION"
    SCALE = "SCALE"
    COMPANY_NAME = "COMPANY_NAME"
    COMPANY_ADDRESS = "COMPANY_ADDRESS"


@dataclass(frozen=True)
class TitleBlockFieldDefinition:
    """Definition for a title block attribute field.

    Defines where a text field appears in the title block and its formatting.

    Attributes:
        tag: DXF attribute tag name (e.g., "PROJECT_NAME")
        prompt: Prompt text shown when inserting block
        position: Position relative to title block origin (mm)
        height: Text height in mm
        alignment: Text alignment ("LEFT", "CENTER", "RIGHT")
        default_value: Default value if not provided
        max_width: Maximum text width for wrapping (0 = no limit)
    """

    tag: str
    prompt: str
    position: Point2D
    height: float = 2.5
    alignment: str = "MIDDLE_LEFT"
    default_value: str = ""
    max_width: float = 0.0


@dataclass
class TitleBlockTemplate:
    """Template for title block geometry and fields.

    Defines the graphical layout and field positions for a title block.
    Templates can be reused across multiple sheets.

    Attributes:
        name: Template identifier (e.g., "standard_ansi_d")
        width: Title block width in mm
        height: Title block height in mm
        fields: List of field definitions
        border_offset: Offset from sheet edge to title block border (mm)
        layer: CAD layer for title block geometry
    """

    name: str
    width: float
    height: float
    fields: list[TitleBlockFieldDefinition] = field(default_factory=list)
    border_offset: float = 5.0
    layer: str = Layer.ANNOTATION

    def generate_geometry(self) -> ViewResult:
        """Generate the title block border and field geometry.

        Returns:
            ViewResult containing title block linework
        """
        lines: list[Line2D] = []
        style = LineStyle.default()

        # Outer border
        lines.extend(
            [
                Line2D(Point2D(0, 0), Point2D(self.width, 0), style, self.layer),
                Line2D(
                    Point2D(self.width, 0),
                    Point2D(self.width, self.height),
                    style,
                    self.layer,
                ),
                Line2D(
                    Point2D(self.width, self.height),
                    Point2D(0, self.height),
                    style,
                    self.layer,
                ),
                Line2D(Point2D(0, self.height), Point2D(0, 0), style, self.layer),
            ]
        )

        return ViewResult(lines=lines)

    def get_field_definition(self, tag: str) -> TitleBlockFieldDefinition | None:
        """Get field definition by tag name.

        Args:
            tag: Field tag to find

        Returns:
            Field definition or None if not found
        """
        for field_def in self.fields:
            if field_def.tag == tag:
                return field_def
        return None


# Standard title block templates
def _create_standard_ansi_d_template() -> TitleBlockTemplate:
    """Create standard ANSI D (22x34) title block template.

    Layout with separate rows to prevent text overlap:
    - Row 1 (top): PROJECT_NAME (full width)
    - Row 2: PROJECT_ADDRESS
    - Row 3: CLIENT_NAME (left) | SHEET_NAME (right)
    - Row 4: DRAWN_BY | CHECKED_BY | DATE | SHEET_NUMBER (right box)
    - Row 5 (bottom): SCALE | REVISION
    """
    fields = [
        # Top row - Project name (full width)
        TitleBlockFieldDefinition(
            tag=TitleBlockField.PROJECT_NAME.value,
            prompt="Project Name",
            position=Point2D(5.0, 43.0),
            height=4.0,
            alignment="MIDDLE_LEFT",
            max_width=170.0,
        ),
        # Second row - Project address
        TitleBlockFieldDefinition(
            tag=TitleBlockField.PROJECT_ADDRESS.value,
            prompt="Project Address",
            position=Point2D(5.0, 36.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
            max_width=170.0,
        ),
        # Third row - Client (left) and Sheet name (right)
        TitleBlockFieldDefinition(
            tag=TitleBlockField.CLIENT_NAME.value,
            prompt="Client Name",
            position=Point2D(5.0, 29.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
            max_width=80.0,
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SHEET_NAME.value,
            prompt="Sheet Name",
            position=Point2D(90.0, 29.0),
            height=3.0,
            alignment="MIDDLE_LEFT",
            max_width=85.0,
        ),
        # Fourth row - Personnel info (left) and Sheet number (right, prominent)
        TitleBlockFieldDefinition(
            tag=TitleBlockField.DRAWN_BY.value,
            prompt="Drawn By",
            position=Point2D(5.0, 18.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.CHECKED_BY.value,
            prompt="Checked By",
            position=Point2D(35.0, 18.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.DATE.value,
            prompt="Date",
            position=Point2D(65.0, 18.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SHEET_NUMBER.value,
            prompt="Sheet Number",
            position=Point2D(155.0, 18.0),
            height=5.0,
            alignment="MIDDLE_CENTER",
        ),
        # Bottom row - Scale and Revision
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SCALE.value,
            prompt="Scale",
            position=Point2D(5.0, 8.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.REVISION.value,
            prompt="Revision",
            position=Point2D(155.0, 8.0),
            height=3.0,
            alignment="MIDDLE_CENTER",
        ),
    ]

    return TitleBlockTemplate(
        name="standard_ansi_d",
        width=180.0,
        height=50.0,
        fields=fields,
    )


def _create_standard_arch_d_template() -> TitleBlockTemplate:
    """Create standard ARCH D (24x36) title block template.

    Layout with separate rows to prevent text overlap:
    - Row 1 (top): PROJECT_NAME (full width)
    - Row 2: PROJECT_ADDRESS
    - Row 3: CLIENT_NAME (left) | SHEET_NAME (right)
    - Row 4: DRAWN_BY | CHECKED_BY | DATE | SHEET_NUMBER (right box)
    - Row 5 (bottom): SCALE | REVISION
    """
    fields = [
        # Top row - Project name (full width)
        TitleBlockFieldDefinition(
            tag=TitleBlockField.PROJECT_NAME.value,
            prompt="Project Name",
            position=Point2D(5.0, 48.0),
            height=4.5,
            alignment="MIDDLE_LEFT",
            max_width=190.0,
        ),
        # Second row - Project address
        TitleBlockFieldDefinition(
            tag=TitleBlockField.PROJECT_ADDRESS.value,
            prompt="Project Address",
            position=Point2D(5.0, 40.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
            max_width=190.0,
        ),
        # Third row - Client (left) and Sheet name (right)
        TitleBlockFieldDefinition(
            tag=TitleBlockField.CLIENT_NAME.value,
            prompt="Client Name",
            position=Point2D(5.0, 32.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
            max_width=90.0,
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SHEET_NAME.value,
            prompt="Sheet Name",
            position=Point2D(100.0, 32.0),
            height=3.0,
            alignment="MIDDLE_LEFT",
            max_width=95.0,
        ),
        # Fourth row - Personnel info (left) and Sheet number (right, prominent)
        TitleBlockFieldDefinition(
            tag=TitleBlockField.DRAWN_BY.value,
            prompt="Drawn By",
            position=Point2D(5.0, 20.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.CHECKED_BY.value,
            prompt="Checked By",
            position=Point2D(40.0, 20.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.DATE.value,
            prompt="Date",
            position=Point2D(75.0, 20.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SHEET_NUMBER.value,
            prompt="Sheet Number",
            position=Point2D(170.0, 20.0),
            height=6.0,
            alignment="MIDDLE_CENTER",
        ),
        # Bottom row - Scale and Revision
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SCALE.value,
            prompt="Scale",
            position=Point2D(5.0, 8.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.REVISION.value,
            prompt="Revision",
            position=Point2D(170.0, 8.0),
            height=3.0,
            alignment="MIDDLE_CENTER",
        ),
    ]

    return TitleBlockTemplate(
        name="standard_arch_d",
        width=200.0,
        height=55.0,
        fields=fields,
    )


def _create_standard_iso_a1_template() -> TitleBlockTemplate:
    """Create standard ISO A1 (594x841) title block template.

    ISO standard title block with metric dimensions.
    """
    fields = [
        TitleBlockFieldDefinition(
            tag=TitleBlockField.PROJECT_NAME.value,
            prompt="Project Name",
            position=Point2D(5.0, 35.0),
            height=4.0,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.PROJECT_NUMBER.value,
            prompt="Project Number",
            position=Point2D(5.0, 27.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SHEET_NAME.value,
            prompt="Sheet Name",
            position=Point2D(90.0, 35.0),
            height=3.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SHEET_NUMBER.value,
            prompt="Sheet Number",
            position=Point2D(155.0, 35.0),
            height=5.0,
            alignment="MIDDLE_CENTER",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.DRAWN_BY.value,
            prompt="Drawn By",
            position=Point2D(90.0, 10.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.CHECKED_BY.value,
            prompt="Checked By",
            position=Point2D(115.0, 10.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.DATE.value,
            prompt="Date",
            position=Point2D(140.0, 10.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SCALE.value,
            prompt="Scale",
            position=Point2D(90.0, 4.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.REVISION.value,
            prompt="Revision",
            position=Point2D(155.0, 4.0),
            height=3.0,
            alignment="MIDDLE_CENTER",
        ),
    ]

    return TitleBlockTemplate(
        name="standard_iso_a1",
        width=170.0,
        height=45.0,
        fields=fields,
    )


def _create_minimal_template() -> TitleBlockTemplate:
    """Create minimal title block template.

    Simple title block with essential fields only.
    """
    fields = [
        TitleBlockFieldDefinition(
            tag=TitleBlockField.PROJECT_NAME.value,
            prompt="Project Name",
            position=Point2D(5.0, 22.0),
            height=3.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SHEET_NAME.value,
            prompt="Sheet Name",
            position=Point2D(70.0, 22.0),
            height=3.0,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SHEET_NUMBER.value,
            prompt="Sheet Number",
            position=Point2D(115.0, 22.0),
            height=4.0,
            alignment="MIDDLE_CENTER",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.DATE.value,
            prompt="Date",
            position=Point2D(70.0, 5.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
        TitleBlockFieldDefinition(
            tag=TitleBlockField.SCALE.value,
            prompt="Scale",
            position=Point2D(100.0, 5.0),
            height=2.5,
            alignment="MIDDLE_LEFT",
        ),
    ]

    return TitleBlockTemplate(
        name="minimal",
        width=130.0,
        height=30.0,
        fields=fields,
    )


# Registry of built-in templates
_TITLE_BLOCK_TEMPLATES: dict[str, TitleBlockTemplate] = {}


def _init_templates() -> None:
    """Initialize the built-in template registry."""
    global _TITLE_BLOCK_TEMPLATES
    if not _TITLE_BLOCK_TEMPLATES:
        _TITLE_BLOCK_TEMPLATES = {
            "standard_ansi_d": _create_standard_ansi_d_template(),
            "standard_arch_d": _create_standard_arch_d_template(),
            "standard_iso_a1": _create_standard_iso_a1_template(),
            "minimal": _create_minimal_template(),
        }


def get_title_block_template(name: str) -> TitleBlockTemplate | None:
    """Get a registered title block template by name.

    Args:
        name: Template name (e.g., "standard_ansi_d")

    Returns:
        Template if found, None otherwise
    """
    _init_templates()
    return _TITLE_BLOCK_TEMPLATES.get(name)


def register_title_block_template(template: TitleBlockTemplate) -> None:
    """Register a custom title block template.

    Args:
        template: Template to register
    """
    _init_templates()
    _TITLE_BLOCK_TEMPLATES[template.name] = template


def list_title_block_templates() -> list[str]:
    """Get list of all registered template names.

    Returns:
        List of template names
    """
    _init_templates()
    return list(_TITLE_BLOCK_TEMPLATES.keys())


@dataclass
class TitleBlock:
    """Title block for sheets.

    A title block contains project information, sheet metadata, and
    graphical elements placed at a standard location on sheets.

    Can be created from a template or with custom geometry.

    Attributes:
        name: Title block name/template identifier
        position: Insertion point on sheet (typically lower-right corner)
        fields: Dictionary of field names to values
        geometry: Optional 2D linework for the title block border/graphics
        template: Optional template this title block is based on

    Example:
        >>> # From template
        >>> title_block = TitleBlock.from_template(
        ...     "standard_ansi_d",
        ...     fields={
        ...         "project_name": "One Harbor Place",
        ...         "sheet_number": "A-101",
        ...         "sheet_name": "Ground Floor Plan",
        ...         "date": "2026-03-17",
        ...         "drawn_by": "BF",
        ...     }
        ... )

        >>> # Manual creation
        >>> title_block = TitleBlock(
        ...     name="custom",
        ...     fields={
        ...         "project_name": "My Project",
        ...         "sheet_number": "A-101",
        ...     }
        ... )
    """

    name: str
    position: Point2D = field(default_factory=lambda: Point2D(0, 0))
    fields: dict[str, str] = field(default_factory=dict)
    geometry: ViewResult | None = None
    template: TitleBlockTemplate | None = None

    @classmethod
    def from_template(
        cls,
        template_name: str,
        fields: dict[str, str] | None = None,
        position: Point2D | tuple[float, float] | None = None,
    ) -> TitleBlock:
        """Create a title block from a template.

        Args:
            template_name: Name of registered template
            fields: Field values to set
            position: Optional position override

        Returns:
            TitleBlock configured from template

        Raises:
            ValueError: If template not found
        """
        template = get_title_block_template(template_name)
        if template is None:
            available = ", ".join(list_title_block_templates())
            raise ValueError(
                f"Unknown title block template: {template_name}. "
                f"Available templates: {available}"
            )

        if isinstance(position, tuple):
            position = Point2D(position[0], position[1])
        elif position is None:
            position = Point2D(0, 0)

        # Generate geometry from template
        geometry = template.generate_geometry()

        # Create title block
        tb = cls(
            name=template_name,
            position=position,
            fields=fields.copy() if fields else {},
            geometry=geometry,
            template=template,
        )

        return tb

    @classmethod
    def from_sheet(
        cls,
        sheet: Sheet,
        template_name: str = "standard_ansi_d",
    ) -> TitleBlock:
        """Create a title block pre-populated from sheet metadata.

        Creates a title block positioned at the lower-right corner of the
        sheet and populates fields from the sheet's metadata.

        Args:
            sheet: Sheet to get metadata from
            template_name: Template to use

        Returns:
            TitleBlock positioned and populated for the sheet
        """
        template = get_title_block_template(template_name)
        if template is None:
            raise ValueError(f"Unknown title block template: {template_name}")

        # Position at lower-right corner of sheet
        # Title block origin is at its lower-left corner
        margin = template.border_offset
        x = sheet.size.width - template.width - margin
        y = margin

        # Build fields from sheet metadata
        fields: dict[str, str] = {
            TitleBlockField.SHEET_NUMBER.value: sheet.number,
            TitleBlockField.SHEET_NAME.value: sheet.name,
        }

        # Add metadata fields
        metadata = sheet.metadata
        if metadata.project:
            fields[TitleBlockField.PROJECT_NAME.value] = metadata.project
        if metadata.drawn_by:
            fields[TitleBlockField.DRAWN_BY.value] = metadata.drawn_by
        if metadata.checked_by:
            fields[TitleBlockField.CHECKED_BY.value] = metadata.checked_by
        if metadata.date:
            fields[TitleBlockField.DATE.value] = metadata.date
        if metadata.revision:
            fields[TitleBlockField.REVISION.value] = metadata.revision
        if metadata.scale:
            fields[TitleBlockField.SCALE.value] = metadata.scale

        return cls.from_template(
            template_name,
            fields=fields,
            position=(x, y),
        )

    # Common field accessors for convenience
    @property
    def project_name(self) -> str:
        """Get project name field value."""
        return self.fields.get(TitleBlockField.PROJECT_NAME.value, "")

    @project_name.setter
    def project_name(self, value: str) -> None:
        """Set project name field value."""
        self.fields[TitleBlockField.PROJECT_NAME.value] = value

    @property
    def project_number(self) -> str:
        """Get project number field value."""
        return self.fields.get(TitleBlockField.PROJECT_NUMBER.value, "")

    @project_number.setter
    def project_number(self, value: str) -> None:
        """Set project number field value."""
        self.fields[TitleBlockField.PROJECT_NUMBER.value] = value

    @property
    def sheet_number(self) -> str:
        """Get sheet number field value."""
        return self.fields.get(TitleBlockField.SHEET_NUMBER.value, "")

    @sheet_number.setter
    def sheet_number(self, value: str) -> None:
        """Set sheet number field value."""
        self.fields[TitleBlockField.SHEET_NUMBER.value] = value

    @property
    def sheet_name(self) -> str:
        """Get sheet name field value."""
        return self.fields.get(TitleBlockField.SHEET_NAME.value, "")

    @sheet_name.setter
    def sheet_name(self, value: str) -> None:
        """Set sheet name field value."""
        self.fields[TitleBlockField.SHEET_NAME.value] = value

    @property
    def date(self) -> str:
        """Get date field value."""
        return self.fields.get(TitleBlockField.DATE.value, "")

    @date.setter
    def date(self, value: str) -> None:
        """Set date field value."""
        self.fields[TitleBlockField.DATE.value] = value

    @property
    def drawn_by(self) -> str:
        """Get drawn by field value."""
        return self.fields.get(TitleBlockField.DRAWN_BY.value, "")

    @drawn_by.setter
    def drawn_by(self, value: str) -> None:
        """Set drawn by field value."""
        self.fields[TitleBlockField.DRAWN_BY.value] = value

    @property
    def checked_by(self) -> str:
        """Get checked by field value."""
        return self.fields.get(TitleBlockField.CHECKED_BY.value, "")

    @checked_by.setter
    def checked_by(self, value: str) -> None:
        """Set checked by field value."""
        self.fields[TitleBlockField.CHECKED_BY.value] = value

    @property
    def revision(self) -> str:
        """Get revision field value."""
        return self.fields.get(TitleBlockField.REVISION.value, "")

    @revision.setter
    def revision(self, value: str) -> None:
        """Set revision field value."""
        self.fields[TitleBlockField.REVISION.value] = value

    @property
    def scale(self) -> str:
        """Get scale field value."""
        return self.fields.get(TitleBlockField.SCALE.value, "")

    @scale.setter
    def scale(self, value: str) -> None:
        """Set scale field value."""
        self.fields[TitleBlockField.SCALE.value] = value

    @property
    def width(self) -> float:
        """Get title block width from template or default."""
        if self.template:
            return self.template.width
        return 180.0  # Default width

    @property
    def height(self) -> float:
        """Get title block height from template or default."""
        if self.template:
            return self.template.height
        return 50.0  # Default height

    @property
    def block_name(self) -> str:
        """Get the DXF block name for this title block.

        Includes template name and dimensions to ensure unique blocks.
        """
        return f"TITLE_BLOCK_{self.name}_{int(self.width)}_{int(self.height)}"

    def get_field(self, name: str, default: str = "") -> str:
        """Get a field value by name.

        Args:
            name: Field name (can be TitleBlockField enum value or string)
            default: Default value if field not found

        Returns:
            Field value or default
        """
        if isinstance(name, TitleBlockField):
            name = name.value
        return self.fields.get(name, default)

    def set_field(self, name: str, value: str) -> None:
        """Set a field value by name.

        Args:
            name: Field name (can be TitleBlockField enum value or string)
            value: Field value
        """
        if isinstance(name, TitleBlockField):
            name = name.value
        self.fields[name] = value

    def has_geometry(self) -> bool:
        """Check if title block has graphical geometry.

        Returns:
            True if geometry is defined and non-empty
        """
        return self.geometry is not None and self.geometry.total_geometry_count > 0

    def get_text_notes(self) -> list[TextNote2D]:
        """Generate text notes for all field values.

        Creates TextNote2D objects positioned according to the template
        field definitions.

        Returns:
            List of TextNote2D for each field with a value
        """
        if self.template is None:
            return []

        notes: list[TextNote2D] = []
        for field_def in self.template.fields:
            value = self.fields.get(field_def.tag, "")
            if not value:
                continue

            # Calculate absolute position (template position + title block position)
            abs_x = self.position.x + field_def.position.x
            abs_y = self.position.y + field_def.position.y

            notes.append(
                TextNote2D(
                    position=Point2D(abs_x, abs_y),
                    content=value,
                    height=field_def.height,
                    alignment=field_def.alignment,
                    width=field_def.max_width,
                    layer=self.template.layer,
                )
            )

        return notes

    def get_positioned_geometry(self) -> ViewResult:
        """Get title block geometry translated to its position.

        Returns:
            ViewResult with geometry at the title block's position
        """
        if self.geometry is None:
            return ViewResult()

        # Translate geometry to title block position
        return self.geometry.translate(self.position.x, self.position.y)

    def get_full_geometry(self) -> ViewResult:
        """Get complete title block geometry including text fields.

        Returns:
            ViewResult with border geometry and field text notes
        """
        result = self.get_positioned_geometry()
        text_notes = self.get_text_notes()
        if text_notes:
            result.text_notes.extend(text_notes)
        return result
