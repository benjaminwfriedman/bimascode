"""Title block for drawing sheets.

Defines TitleBlock dataclass for sheet title blocks.
This is a stub implementation for Issue #40 - full title block features
including DXF BLOCK/ATTDEF support will be implemented separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bimascode.drawing.primitives import Point2D, ViewResult

if TYPE_CHECKING:
    pass


@dataclass
class TitleBlock:
    """Title block for sheets.

    A title block contains project information, sheet metadata, and
    graphical elements placed at a standard location on sheets.

    NOTE: This is a placeholder for Issue #40. Full implementation
    will include parametric fields, company logos, standard templates,
    and DXF BLOCK/ATTDEF/ATTRIB support.

    Attributes:
        name: Title block name/template identifier
        position: Insertion point on sheet (typically lower-right corner)
        fields: Dictionary of field names to values
        geometry: Optional 2D linework for the title block border/graphics

    Example:
        >>> title_block = TitleBlock(
        ...     name="standard_ansi_d",
        ...     fields={
        ...         "project_name": "One Harbor Place",
        ...         "sheet_number": "A-101",
        ...         "sheet_name": "Ground Floor Plan",
        ...         "date": "2026-03-25",
        ...         "drawn_by": "BF",
        ...     }
        ... )
    """

    name: str
    position: Point2D = field(default_factory=lambda: Point2D(0, 0))
    fields: dict[str, str] = field(default_factory=dict)
    geometry: ViewResult | None = None

    # Common field accessors for convenience
    @property
    def project_name(self) -> str:
        """Get project name field value."""
        return self.fields.get("project_name", "")

    @project_name.setter
    def project_name(self, value: str) -> None:
        """Set project name field value."""
        self.fields["project_name"] = value

    @property
    def sheet_number(self) -> str:
        """Get sheet number field value."""
        return self.fields.get("sheet_number", "")

    @sheet_number.setter
    def sheet_number(self, value: str) -> None:
        """Set sheet number field value."""
        self.fields["sheet_number"] = value

    @property
    def sheet_name(self) -> str:
        """Get sheet name field value."""
        return self.fields.get("sheet_name", "")

    @sheet_name.setter
    def sheet_name(self, value: str) -> None:
        """Set sheet name field value."""
        self.fields["sheet_name"] = value

    @property
    def date(self) -> str:
        """Get date field value."""
        return self.fields.get("date", "")

    @date.setter
    def date(self, value: str) -> None:
        """Set date field value."""
        self.fields["date"] = value

    @property
    def drawn_by(self) -> str:
        """Get drawn by field value."""
        return self.fields.get("drawn_by", "")

    @drawn_by.setter
    def drawn_by(self, value: str) -> None:
        """Set drawn by field value."""
        self.fields["drawn_by"] = value

    @property
    def checked_by(self) -> str:
        """Get checked by field value."""
        return self.fields.get("checked_by", "")

    @checked_by.setter
    def checked_by(self, value: str) -> None:
        """Set checked by field value."""
        self.fields["checked_by"] = value

    @property
    def revision(self) -> str:
        """Get revision field value."""
        return self.fields.get("revision", "")

    @revision.setter
    def revision(self, value: str) -> None:
        """Set revision field value."""
        self.fields["revision"] = value

    @property
    def scale(self) -> str:
        """Get scale field value."""
        return self.fields.get("scale", "")

    @scale.setter
    def scale(self, value: str) -> None:
        """Set scale field value."""
        self.fields["scale"] = value

    def get_field(self, name: str, default: str = "") -> str:
        """Get a field value by name.

        Args:
            name: Field name
            default: Default value if field not found

        Returns:
            Field value or default
        """
        return self.fields.get(name, default)

    def set_field(self, name: str, value: str) -> None:
        """Set a field value by name.

        Args:
            name: Field name
            value: Field value
        """
        self.fields[name] = value

    def has_geometry(self) -> bool:
        """Check if title block has graphical geometry.

        Returns:
            True if geometry is defined and non-empty
        """
        return self.geometry is not None and self.geometry.total_geometry_count > 0
