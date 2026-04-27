"""Drawing sheet for DXF paperspace layouts.

Defines Sheet class for assembling views, title blocks, and annotations
into a printable sheet layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bimascode.drawing.primitives import Point2D, ViewResult
from bimascode.drawing.sheet_sizes import SheetSize
from bimascode.drawing.view_base import ViewScale
from bimascode.drawing.viewport import SheetViewport

if TYPE_CHECKING:
    from bimascode.drawing.title_block import TitleBlock


@dataclass
class SheetMetadata:
    """Metadata for a sheet.

    Contains project and drawing information that may be displayed
    in the title block or used for document management.

    Attributes:
        project: Project name
        drawn_by: Name of person who created the drawing
        checked_by: Name of reviewer
        date: Drawing date (string format, e.g., "2026-03-25")
        revision: Revision number/letter
        scale: Primary scale notation (informational, e.g., "1:100")
        custom_fields: Additional metadata fields
    """

    project: str = ""
    drawn_by: str = ""
    checked_by: str = ""
    date: str = ""
    revision: str = ""
    scale: str = ""
    custom_fields: dict[str, str] = field(default_factory=dict)


class Sheet:
    """A drawing sheet with viewports and title block.

    Represents a single plottable sheet in DXF paperspace. Contains
    viewports (scaled windows into modelspace views), a title block,
    and sheet-level annotations.

    Following the "Expose Parameters to Driver" pattern, all settings
    have sensible defaults but can be overridden from driver code.

    Attributes:
        size: Sheet dimensions (SheetSize)
        number: Sheet number (e.g., "A-101")
        name: Sheet name (e.g., "Ground Floor Plan")
        metadata: Additional sheet metadata
        margins: Sheet margins (left, bottom, right, top) in mm

    Example:
        >>> from bimascode.drawing import Sheet, SheetSize
        >>> sheet = Sheet(
        ...     size=SheetSize.ANSI_D,
        ...     number="A-101",
        ...     name="Ground Floor Plan",
        ... )
        >>> sheet.add_viewport(floor_plan_result, position=(300, 200), scale="1:100")
        >>> sheet.export_dxf("A-101.dxf")
    """

    def __init__(
        self,
        size: SheetSize | str,
        number: str = "",
        name: str = "",
        metadata: SheetMetadata | None = None,
        margins: tuple[float, float, float, float] = (10.0, 10.0, 10.0, 10.0),
    ):
        """Initialize a sheet.

        Args:
            size: Sheet size (SheetSize instance or string like "ANSI D")
            number: Sheet number (e.g., "A-101")
            name: Sheet name (e.g., "Ground Floor Plan")
            metadata: Optional metadata
            margins: Sheet margins (left, bottom, right, top) in mm
        """
        if isinstance(size, str):
            self._size = SheetSize.from_string(size)
        else:
            self._size = size

        self._number = number
        self._name = name
        self._metadata = metadata or SheetMetadata()
        self._margins = margins

        self._viewports: list[SheetViewport] = []
        self._title_block: TitleBlock | None = None
        self._annotations: ViewResult = ViewResult()

    # --- Properties ---

    @property
    def size(self) -> SheetSize:
        """Get sheet size."""
        return self._size

    @property
    def number(self) -> str:
        """Get sheet number."""
        return self._number

    @number.setter
    def number(self, value: str) -> None:
        """Set sheet number."""
        self._number = value

    @property
    def name(self) -> str:
        """Get sheet name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Set sheet name."""
        self._name = value

    @property
    def metadata(self) -> SheetMetadata:
        """Get sheet metadata."""
        return self._metadata

    @metadata.setter
    def metadata(self, value: SheetMetadata) -> None:
        """Set sheet metadata."""
        self._metadata = value

    @property
    def viewports(self) -> list[SheetViewport]:
        """Get list of viewports on this sheet (copy)."""
        return list(self._viewports)

    @property
    def title_block(self) -> TitleBlock | None:
        """Get title block."""
        return self._title_block

    @property
    def margins(self) -> tuple[float, float, float, float]:
        """Get margins (left, bottom, right, top) in mm."""
        return self._margins

    @margins.setter
    def margins(self, value: tuple[float, float, float, float]) -> None:
        """Set margins (left, bottom, right, top) in mm."""
        self._margins = value

    @property
    def printable_area(self) -> tuple[float, float, float, float]:
        """Get printable area bounds (min_x, min_y, max_x, max_y) in mm."""
        left, bottom, right, top = self._margins
        return (
            left,
            bottom,
            self._size.width - right,
            self._size.height - top,
        )

    @property
    def printable_width(self) -> float:
        """Get printable width in mm."""
        bounds = self.printable_area
        return bounds[2] - bounds[0]

    @property
    def printable_height(self) -> float:
        """Get printable height in mm."""
        bounds = self.printable_area
        return bounds[3] - bounds[1]

    @property
    def annotations(self) -> ViewResult:
        """Get sheet annotations."""
        return self._annotations

    # --- Viewport Management ---

    def add_viewport(
        self,
        view_result: ViewResult,
        position: tuple[float, float] | Point2D,
        scale: ViewScale | str,
        width: float | None = None,
        height: float | None = None,
        name: str = "",
    ) -> SheetViewport:
        """Add a viewport to the sheet.

        Args:
            view_result: Generated view content to display
            position: Center point of viewport on sheet (mm)
            scale: Display scale (ViewScale or string like "1:100")
            width: Optional viewport width in mm (auto if None)
            height: Optional viewport height in mm (auto if None)
            name: Optional viewport name

        Returns:
            The created SheetViewport
        """
        if isinstance(position, tuple):
            position = Point2D(position[0], position[1])

        if isinstance(scale, str):
            scale = ViewScale.from_string(scale)

        viewport = SheetViewport(
            view_result=view_result,
            position=position,
            scale=scale,
            width=width,
            height=height,
            name=name,
        )

        self._viewports.append(viewport)
        return viewport

    def remove_viewport(self, viewport: SheetViewport) -> bool:
        """Remove a viewport from the sheet.

        Args:
            viewport: Viewport to remove

        Returns:
            True if viewport was removed, False if not found
        """
        if viewport in self._viewports:
            self._viewports.remove(viewport)
            return True
        return False

    def clear_viewports(self) -> None:
        """Remove all viewports from the sheet."""
        self._viewports.clear()

    def get_viewport_by_name(self, name: str) -> SheetViewport | None:
        """Find a viewport by name.

        Args:
            name: Viewport name to find

        Returns:
            Matching viewport or None
        """
        for vp in self._viewports:
            if vp.name == name:
                return vp
        return None

    # --- Title Block ---

    def set_title_block(
        self,
        title_block: TitleBlock,
        position: tuple[float, float] | Point2D | None = None,
    ) -> None:
        """Set the sheet's title block.

        Args:
            title_block: Title block to use
            position: Optional override position (uses title_block.position if None)
        """
        from bimascode.drawing.title_block import TitleBlock as TB

        if position is not None:
            if isinstance(position, tuple):
                position = Point2D(position[0], position[1])
            # Create new title block with updated position
            title_block = TB(
                name=title_block.name,
                position=position,
                fields=title_block.fields.copy(),
                geometry=title_block.geometry,
            )

        self._title_block = title_block

    def remove_title_block(self) -> None:
        """Remove the title block from the sheet."""
        self._title_block = None

    # --- Annotations ---

    def add_annotation(self, geometry: ViewResult) -> None:
        """Add annotation geometry to the sheet.

        Annotations are placed directly on the sheet in paperspace,
        not through a viewport.

        Args:
            geometry: 2D geometry to add
        """
        self._annotations.extend(geometry)

    def clear_annotations(self) -> None:
        """Remove all annotations from the sheet."""
        self._annotations = ViewResult()

    # --- Export ---

    def export_dxf(
        self,
        filepath: str,
        dxf_version: str = "R2013",
        flat: bool = True,
    ) -> bool:
        """Export sheet to DXF file.

        Args:
            filepath: Output file path
            dxf_version: DXF version (R2000 or newer for paperspace)
            flat: If True (default), export as flat modelspace layout that
                works with any DXF viewer. If False, export with proper
                paperspace/viewport structure (requires viewer support).

        Returns:
            True if export succeeded
        """
        from bimascode.drawing.dxf_exporter import DXFSheetExporter

        exporter = DXFSheetExporter(dxf_version=dxf_version)
        if flat:
            return exporter.export_sheet_flat(self, filepath)
        else:
            return exporter.export_sheet(self, filepath)

    def export_pdf(
        self,
        filepath: str,
        color_mode: str = "color",
        background: str = "white",
        dpi: int = 300,
    ) -> bool:
        """Export sheet to PDF file.

        Creates a high-quality vector PDF at the exact sheet size,
        suitable for printing and client review.

        Args:
            filepath: Output file path
            color_mode: "color" for full color, "grayscale" for black/white
            background: Background color ("white" or "transparent")
            dpi: Resolution for rasterized elements (default 300)

        Returns:
            True if export succeeded

        Example:
            >>> sheet.export_pdf("A-101.pdf")
            >>> sheet.export_pdf("A-101-bw.pdf", color_mode="grayscale")
        """
        from bimascode.drawing.pdf_exporter import PDFExporter

        exporter = PDFExporter(
            color_mode=color_mode,
            background=background,
            dpi=dpi,
        )
        return exporter.export_sheet(self, filepath)

    # --- String Representation ---

    def __repr__(self) -> str:
        return (
            f"Sheet(number='{self._number}', name='{self._name}', "
            f"size={self._size.name}, viewports={len(self._viewports)})"
        )
