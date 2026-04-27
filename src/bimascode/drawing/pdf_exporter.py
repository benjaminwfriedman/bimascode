"""PDF export for 2D views and sheets.

Provides PDFExporter class for exporting ViewResult geometry and Sheet objects
to PDF format using matplotlib as the rendering backend.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from bimascode.drawing.line_styles import Layer, LineType, LineWeight
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
from bimascode.drawing.tags import DoorTag, RoomTag, SectionSymbol, TagShape, WindowTag

if TYPE_CHECKING:
    from bimascode.drawing.sheet import Sheet
    from bimascode.drawing.title_block import TitleBlock


# Map line weight to matplotlib linewidth in points (1pt = 1/72 inch)
# These weights are designed for screen/PDF viewing
# Convert mm to points: 1mm ≈ 2.83pt
LINEWEIGHT_TO_POINTS = {
    LineWeight.EXTRA_FINE: 0.35,  # 0.13mm ≈ 0.35pt
    LineWeight.FINE: 0.5,  # 0.18mm ≈ 0.5pt
    LineWeight.NARROW: 0.7,  # 0.25mm ≈ 0.7pt
    LineWeight.MEDIUM: 1.0,  # 0.35mm ≈ 1pt
    LineWeight.WIDE: 1.4,  # 0.50mm ≈ 1.4pt
    LineWeight.HEAVY: 2.0,  # 0.70mm ≈ 2pt
}

# Map line type to matplotlib dash pattern
# Format: (dash, gap, dash, gap, ...) in points
LINETYPE_TO_DASH = {
    LineType.CONTINUOUS: None,  # Solid line
    LineType.DASHED: (6, 3),  # Long dash
    LineType.HIDDEN: (3, 1.5),  # Short dash
    LineType.CENTER: (12, 3, 3, 3),  # Long-short-long
    LineType.PHANTOM: (12, 3, 3, 3, 3, 3),  # Long-short-short
    LineType.DEMOLISH: (3, 1.5, 0.5, 1.5),  # Short dash with X
    LineType.ABOVE_CUT: (4, 2),  # Dashed
}

# Default colors by layer (RGB tuples, 0-1 range)
LAYER_COLORS = {
    Layer.WALL: (0.0, 0.0, 0.0),  # Black
    Layer.WALL_FIRE: (0.8, 0.0, 0.0),  # Red
    Layer.DOOR: (0.5, 0.0, 0.5),  # Magenta
    Layer.WINDOW: (0.0, 0.5, 0.5),  # Cyan
    Layer.FLOOR: (0.3, 0.3, 0.3),  # Dark gray
    Layer.CEILING: (0.5, 0.5, 0.5),  # Light gray
    Layer.COLUMN: (0.0, 0.5, 0.0),  # Green
    Layer.BEAM: (0.0, 0.5, 0.0),  # Green
    Layer.ANNOTATION: (0.0, 0.0, 0.0),  # Black
    Layer.DIMENSION: (0.0, 0.0, 0.0),  # Black
    Layer.SYMBOL: (0.0, 0.0, 0.0),  # Black
}


class PDFExporter:
    """Exports ViewResult geometry and Sheets to PDF format.

    Uses matplotlib as the rendering backend to produce high-quality
    vector PDF output suitable for printing and client review.

    Example:
        >>> exporter = PDFExporter()
        >>> exporter.export(view_result, "floor_plan.pdf")
        >>> exporter.export_sheet(sheet, "A-101.pdf")
    """

    def __init__(
        self,
        color_mode: str = "color",
        background: str = "white",
        dpi: int = 300,
    ):
        """Initialize the PDF exporter.

        Args:
            color_mode: "color" for full color, "grayscale" for black and white
            background: Background color ("white" or "transparent")
            dpi: Resolution for rasterized elements (default 300)
        """
        self.color_mode = color_mode
        self.background = background
        self.dpi = dpi
        self._check_matplotlib_available()

    def _check_matplotlib_available(self) -> bool:
        """Check if matplotlib is available."""
        try:
            import matplotlib

            matplotlib.use("Agg")  # Non-interactive backend for PDF
            import matplotlib.pyplot as plt
            from matplotlib.patches import Arc as MplArc
            from matplotlib.patches import Polygon, Wedge

            self._plt = plt
            self._MplArc = MplArc
            self._Polygon = Polygon
            self._Wedge = Wedge
            return True
        except ImportError:
            self._plt = None
            return False

    @property
    def is_available(self) -> bool:
        """Check if PDF export is available."""
        return self._plt is not None

    def _get_line_style(self, style) -> dict:
        """Convert LineStyle to matplotlib line properties."""
        props = {
            "linewidth": LINEWEIGHT_TO_POINTS.get(style.weight, 1.0),
        }

        # Line type (dashes)
        dash = LINETYPE_TO_DASH.get(style.type)
        if dash is not None:
            props["linestyle"] = (0, dash)
        else:
            props["linestyle"] = "solid"

        # Color
        if style.color is not None:
            r, g, b = style.color
            props["color"] = (r / 255, g / 255, b / 255)
        elif self.color_mode == "grayscale":
            props["color"] = "black"
        else:
            props["color"] = "black"  # Default to black

        return props

    def _get_layer_color(self, layer: str) -> tuple[float, float, float]:
        """Get color for a layer."""
        if self.color_mode == "grayscale":
            return (0.0, 0.0, 0.0)  # Black
        return LAYER_COLORS.get(layer, (0.0, 0.0, 0.0))

    def export(
        self,
        view_result: ViewResult,
        filepath: str,
        scale: float = 1.0,
        paper_size: tuple[float, float] | None = None,
    ) -> bool:
        """Export a ViewResult to PDF file.

        Args:
            view_result: ViewResult to export
            filepath: Output file path
            scale: Scale factor to apply (1.0 = model space)
            paper_size: Optional paper size (width, height) in mm.
                       If None, auto-sizes to content.

        Returns:
            True if export succeeded
        """
        if not self.is_available:
            raise ImportError("matplotlib is required for PDF export")

        # Get bounds of content
        bounds = view_result.get_bounds()
        if bounds is None:
            bounds = (0, 0, 100, 100)  # Default for empty view

        min_x, min_y, max_x, max_y = bounds
        content_width = (max_x - min_x) * scale
        content_height = (max_y - min_y) * scale

        # Determine figure size (in inches, 1 inch = 25.4mm)
        if paper_size is not None:
            fig_width = paper_size[0] / 25.4
            fig_height = paper_size[1] / 25.4
        else:
            # Auto-size with 10mm margin
            margin = 10 * scale
            fig_width = (content_width + 2 * margin) / 25.4
            fig_height = (content_height + 2 * margin) / 25.4

        # Create figure
        fig, ax = self._plt.subplots(figsize=(fig_width, fig_height))

        # Set background
        if self.background == "white":
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
        else:
            fig.patch.set_alpha(0)
            ax.set_facecolor("none")

        # Remove axes decorations
        ax.set_aspect("equal")
        ax.axis("off")

        # Set view limits
        if paper_size is not None:
            # Center content on paper
            center_x = (min_x + max_x) / 2 * scale
            center_y = (min_y + max_y) / 2 * scale
            ax.set_xlim(center_x - paper_size[0] / 2, center_x + paper_size[0] / 2)
            ax.set_ylim(center_y - paper_size[1] / 2, center_y + paper_size[1] / 2)
        else:
            margin = 10 * scale
            ax.set_xlim(min_x * scale - margin, max_x * scale + margin)
            ax.set_ylim(min_y * scale - margin, max_y * scale + margin)

        # Draw geometry
        self._draw_hatches(ax, view_result.hatches, scale)
        self._draw_lines(ax, view_result.lines, scale)
        self._draw_arcs(ax, view_result.arcs, scale)
        self._draw_polylines(ax, view_result.polylines, scale)
        self._draw_dimensions(ax, view_result.dimensions, scale)
        self._draw_chain_dimensions(ax, view_result.chain_dimensions, scale)
        self._draw_text_notes(ax, view_result.text_notes, scale)
        self._draw_door_tags(ax, view_result.door_tags, scale)
        self._draw_window_tags(ax, view_result.window_tags, scale)
        self._draw_room_tags(ax, view_result.room_tags, scale)
        self._draw_section_symbols(ax, view_result.section_symbols, scale)

        # Save to PDF
        fig.savefig(
            filepath,
            format="pdf",
            bbox_inches="tight",
            pad_inches=0,
            dpi=self.dpi,
        )
        self._plt.close(fig)

        return True

    def export_sheet(
        self,
        sheet: Sheet,
        filepath: str,
    ) -> bool:
        """Export a Sheet to PDF file.

        Creates a PDF at the exact sheet size with all viewports,
        title block, and annotations rendered.

        Args:
            sheet: Sheet to export
            filepath: Output file path

        Returns:
            True if export succeeded
        """
        if not self.is_available:
            raise ImportError("matplotlib is required for PDF export")

        # Figure size in inches (sheet size is in mm)
        fig_width = sheet.size.width / 25.4
        fig_height = sheet.size.height / 25.4

        # Create figure with exact paper size
        fig, ax = self._plt.subplots(figsize=(fig_width, fig_height))

        # Set background
        if self.background == "white":
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
        else:
            fig.patch.set_alpha(0)
            ax.set_facecolor("none")

        # Remove axes decorations
        ax.set_aspect("equal")
        ax.axis("off")

        # Set limits to sheet bounds (origin at bottom-left)
        ax.set_xlim(0, sheet.size.width)
        ax.set_ylim(0, sheet.size.height)

        # Draw sheet border
        self._draw_sheet_border(ax, sheet)

        # Draw each viewport
        for viewport in sheet.viewports:
            self._draw_viewport(ax, viewport, sheet)

        # Draw title block
        if sheet.title_block:
            self._draw_title_block(ax, sheet.title_block)

        # Draw annotations
        if sheet.annotations.total_geometry_count > 0:
            self._draw_view_result(ax, sheet.annotations, scale=1.0)

        # Save to PDF
        fig.savefig(
            filepath,
            format="pdf",
            bbox_inches="tight",
            pad_inches=0,
            dpi=self.dpi,
        )
        self._plt.close(fig)

        return True

    def _draw_sheet_border(self, ax, sheet: Sheet) -> None:
        """Draw the sheet border."""
        # Light gray border
        border = self._plt.Rectangle(
            (0, 0),
            sheet.size.width,
            sheet.size.height,
            fill=False,
            edgecolor=(0.7, 0.7, 0.7),
            linewidth=0.5,
        )
        ax.add_patch(border)

    def _draw_viewport(self, ax, viewport, sheet: Sheet) -> None:
        """Draw a viewport's content on the sheet."""
        view_result = viewport.view_result
        bounds = view_result.get_bounds()
        if bounds is None:
            return

        # Calculate transformation from model to sheet coordinates
        model_center_x = (bounds[0] + bounds[2]) / 2
        model_center_y = (bounds[1] + bounds[3]) / 2
        scale = viewport.scale.ratio

        # Offset to position view at viewport location on sheet
        offset_x = viewport.position.x - model_center_x * scale
        offset_y = viewport.position.y - model_center_y * scale

        # Transform and draw the view content
        scaled_view = view_result.scale_and_translate(scale, offset_x, offset_y)
        self._draw_view_result(ax, scaled_view, scale=1.0)

        # Draw viewport label
        self._draw_viewport_label(ax, viewport, scaled_view)

    def _draw_viewport_label(self, ax, viewport, scaled_view: ViewResult) -> None:
        """Draw a label below the viewport."""
        view_name = viewport.name or viewport.view_result.view_name
        if not view_name:
            return

        bounds = scaled_view.get_bounds()
        if bounds is None:
            return

        center_x = (bounds[0] + bounds[2]) / 2
        view_bottom = bounds[1]

        # Label sizing
        text_height = 3.0  # mm on sheet
        label_offset = 5.0

        # View name
        ax.text(
            center_x,
            view_bottom - label_offset,
            view_name,
            fontsize=text_height * 2.83,  # Convert mm to points
            ha="center",
            va="top",
            color="black",
        )

        # Underline
        text_width = len(view_name) * text_height * 0.6
        underline_y = view_bottom - label_offset - text_height
        ax.plot(
            [center_x - text_width / 2, center_x + text_width / 2],
            [underline_y, underline_y],
            color="black",
            linewidth=0.5,
        )

        # Scale notation
        scale_text = f"Scale: {viewport.scale.name}"
        ax.text(
            center_x,
            underline_y - text_height * 0.5,
            scale_text,
            fontsize=text_height * 2.83 * 0.8,
            ha="center",
            va="top",
            color="black",
        )

    def _draw_title_block(self, ax, title_block: TitleBlock) -> None:
        """Draw the title block."""
        # Get full geometry including text
        full_geometry = title_block.get_full_geometry()
        self._draw_view_result(ax, full_geometry, scale=1.0)

    def _draw_view_result(self, ax, view_result: ViewResult, scale: float) -> None:
        """Draw all geometry from a ViewResult."""
        self._draw_hatches(ax, view_result.hatches, scale)
        self._draw_lines(ax, view_result.lines, scale)
        self._draw_arcs(ax, view_result.arcs, scale)
        self._draw_polylines(ax, view_result.polylines, scale)
        self._draw_dimensions(ax, view_result.dimensions, scale)
        self._draw_chain_dimensions(ax, view_result.chain_dimensions, scale)
        self._draw_text_notes(ax, view_result.text_notes, scale)
        self._draw_door_tags(ax, view_result.door_tags, scale)
        self._draw_window_tags(ax, view_result.window_tags, scale)
        self._draw_room_tags(ax, view_result.room_tags, scale)
        self._draw_section_symbols(ax, view_result.section_symbols, scale)

    def _draw_lines(self, ax, lines: list[Line2D], scale: float) -> None:
        """Draw Line2D objects."""
        for line in lines:
            props = self._get_line_style(line.style)
            ax.plot(
                [line.start.x * scale, line.end.x * scale],
                [line.start.y * scale, line.end.y * scale],
                **props,
            )

    def _draw_arcs(self, ax, arcs: list[Arc2D], scale: float) -> None:
        """Draw Arc2D objects."""
        for arc in arcs:
            props = self._get_line_style(arc.style)

            # Convert angles to degrees
            start_deg = math.degrees(arc.start_angle)
            end_deg = math.degrees(arc.end_angle)

            # Ensure proper sweep direction
            if end_deg < start_deg:
                end_deg += 360

            # Create arc patch
            arc_patch = self._MplArc(
                (arc.center.x * scale, arc.center.y * scale),
                2 * arc.radius * scale,
                2 * arc.radius * scale,
                angle=0,
                theta1=start_deg,
                theta2=end_deg,
                fill=False,
                linewidth=props["linewidth"],
                linestyle=props.get("linestyle", "solid"),
                edgecolor=props["color"],
            )
            ax.add_patch(arc_patch)

    def _draw_polylines(self, ax, polylines: list[Polyline2D], scale: float) -> None:
        """Draw Polyline2D objects."""
        for polyline in polylines:
            if len(polyline.points) < 2:
                continue

            props = self._get_line_style(polyline.style)
            xs = [p.x * scale for p in polyline.points]
            ys = [p.y * scale for p in polyline.points]

            if polyline.closed:
                xs.append(xs[0])
                ys.append(ys[0])

            ax.plot(xs, ys, **props)

    def _draw_hatches(self, ax, hatches: list[Hatch2D], scale: float) -> None:
        """Draw Hatch2D objects."""
        for hatch in hatches:
            if len(hatch.boundary) < 3:
                continue

            points = [(p.x * scale, p.y * scale) for p in hatch.boundary]

            # Determine fill color
            if hatch.color is not None:
                fill_color = (hatch.color[0] / 255, hatch.color[1] / 255, hatch.color[2] / 255)
            elif self.color_mode == "grayscale":
                fill_color = (0.8, 0.8, 0.8)  # Light gray
            else:
                fill_color = self._get_layer_color(hatch.layer)
                # Make slightly transparent for hatches
                fill_color = (*fill_color, 0.3)

            # Create polygon
            polygon = self._Polygon(
                points,
                closed=True,
                facecolor=fill_color,
                edgecolor="none",
            )
            ax.add_patch(polygon)

    def _draw_dimensions(self, ax, dimensions: list[LinearDimension2D], scale: float) -> None:
        """Draw LinearDimension2D objects."""
        for dim in dimensions:
            self._draw_single_dimension(ax, dim, scale)

    def _draw_single_dimension(self, ax, dim: LinearDimension2D, scale: float) -> None:
        """Draw a single dimension."""
        # Calculate dimension line position
        start_x = dim.start.x * scale
        start_y = dim.start.y * scale
        end_x = dim.end.x * scale
        end_y = dim.end.y * scale

        # Baseline angle and perpendicular
        angle = dim.angle
        perp_angle = angle + math.pi / 2
        offset = dim.offset * scale

        # Dimension line endpoints
        dim_start_x = start_x + offset * math.cos(perp_angle)
        dim_start_y = start_y + offset * math.sin(perp_angle)
        dim_end_x = end_x + offset * math.cos(perp_angle)
        dim_end_y = end_y + offset * math.sin(perp_angle)

        # Draw dimension line
        props = self._get_line_style(dim.style)
        ax.plot(
            [dim_start_x, dim_end_x],
            [dim_start_y, dim_end_y],
            color="black",
            linewidth=props["linewidth"],
        )

        # Draw extension lines
        ext_gap = abs(offset) * 0.1  # Small gap at origin
        ext_extend = abs(offset) * 0.15  # Extend beyond dimension line

        # Extension line 1
        ax.plot(
            [
                start_x + ext_gap * math.cos(perp_angle),
                dim_start_x + ext_extend * math.cos(perp_angle),
            ],
            [
                start_y + ext_gap * math.sin(perp_angle),
                dim_start_y + ext_extend * math.sin(perp_angle),
            ],
            color="black",
            linewidth=props["linewidth"] * 0.7,
        )

        # Extension line 2
        ax.plot(
            [
                end_x + ext_gap * math.cos(perp_angle),
                dim_end_x + ext_extend * math.cos(perp_angle),
            ],
            [
                end_y + ext_gap * math.sin(perp_angle),
                dim_end_y + ext_extend * math.sin(perp_angle),
            ],
            color="black",
            linewidth=props["linewidth"] * 0.7,
        )

        # Draw arrow heads
        arrow_size = abs(offset) * 0.15
        self._draw_arrow(ax, dim_start_x, dim_start_y, angle, arrow_size)
        self._draw_arrow(ax, dim_end_x, dim_end_y, angle + math.pi, arrow_size)

        # Draw dimension text
        mid_x = (dim_start_x + dim_end_x) / 2
        mid_y = (dim_start_y + dim_end_y) / 2

        # Calculate display value
        if dim.text == "<>":
            display_value = dim.start.distance_to(dim.end) * dim.dimlfac
            text = f"{display_value:.{dim.precision}f}"
        else:
            text = dim.text

        # Text rotation (keep text upright)
        text_angle = math.degrees(angle)
        if text_angle > 90:
            text_angle -= 180
        elif text_angle < -90:
            text_angle += 180

        # Text size based on offset
        text_height = max(abs(offset) * 0.25, 1.5)

        ax.text(
            mid_x,
            mid_y,
            text,
            fontsize=text_height * 2.83,
            ha="center",
            va="center",
            rotation=text_angle,
            color="black",
            bbox={"boxstyle": "square,pad=0.1", "facecolor": "white", "edgecolor": "none"},
        )

    def _draw_arrow(self, ax, x: float, y: float, angle: float, size: float) -> None:
        """Draw an arrow head at the specified position."""
        # Arrow head as a filled triangle
        back_angle1 = angle + math.pi + math.pi / 6
        back_angle2 = angle + math.pi - math.pi / 6

        points = [
            (x, y),
            (x + size * math.cos(back_angle1), y + size * math.sin(back_angle1)),
            (x + size * math.cos(back_angle2), y + size * math.sin(back_angle2)),
        ]

        polygon = self._Polygon(points, closed=True, facecolor="black", edgecolor="none")
        ax.add_patch(polygon)

    def _draw_chain_dimensions(
        self, ax, chain_dimensions: list[ChainDimension2D], scale: float
    ) -> None:
        """Draw ChainDimension2D objects."""
        for chain in chain_dimensions:
            for segment in chain.segments:
                self._draw_single_dimension(ax, segment, scale)

    def _draw_text_notes(self, ax, text_notes: list[TextNote2D], scale: float) -> None:
        """Draw TextNote2D objects."""
        alignment_map = {
            "TOP_LEFT": ("left", "top"),
            "TOP_CENTER": ("center", "top"),
            "TOP_RIGHT": ("right", "top"),
            "MIDDLE_LEFT": ("left", "center"),
            "MIDDLE_CENTER": ("center", "center"),
            "MIDDLE_RIGHT": ("right", "center"),
            "BOTTOM_LEFT": ("left", "bottom"),
            "BOTTOM_CENTER": ("center", "bottom"),
            "BOTTOM_RIGHT": ("right", "bottom"),
        }

        for text in text_notes:
            ha, va = alignment_map.get(text.alignment, ("left", "center"))

            ax.text(
                text.position.x * scale,
                text.position.y * scale,
                text.content,
                fontsize=text.height * scale * 2.83,  # Convert mm to points
                ha=ha,
                va=va,
                rotation=text.rotation,
                color="black",
            )

    def _draw_tag(
        self,
        ax,
        position: Point2D,
        text: str,
        shape: TagShape,
        size: float,
        text_height: float,
        scale: float,
    ) -> None:
        """Draw a tag symbol with text."""
        x = position.x * scale
        y = position.y * scale
        r = size * scale / 2

        if shape == TagShape.CIRCLE:
            circle = self._plt.Circle((x, y), r, fill=False, edgecolor="black", linewidth=0.5)
            ax.add_patch(circle)
        elif shape == TagShape.HEXAGON:
            points = []
            for i in range(6):
                angle = math.pi / 6 + i * math.pi / 3
                px = x + r * math.cos(angle)
                py = y + r * math.sin(angle)
                points.append((px, py))
            polygon = self._Polygon(
                points, closed=True, fill=False, edgecolor="black", linewidth=0.5
            )
            ax.add_patch(polygon)
        elif shape == TagShape.RECTANGLE:
            rect = self._plt.Rectangle(
                (x - r, y - r * 0.6),
                2 * r,
                1.2 * r,
                fill=False,
                edgecolor="black",
                linewidth=0.5,
            )
            ax.add_patch(rect)
        elif shape == TagShape.DIAMOND:
            points = [(x, y + r), (x + r, y), (x, y - r), (x - r, y)]
            polygon = self._Polygon(
                points, closed=True, fill=False, edgecolor="black", linewidth=0.5
            )
            ax.add_patch(polygon)

        # Draw text
        ax.text(
            x,
            y,
            text,
            fontsize=text_height * scale * 2.83,
            ha="center",
            va="center",
            color="black",
        )

    def _draw_door_tags(self, ax, tags: list[DoorTag], scale: float) -> None:
        """Draw DoorTag objects."""
        for tag in tags:
            if not tag.text:
                continue
            self._draw_tag(
                ax,
                tag.insertion_point,
                tag.text,
                tag.style.shape,
                tag.style.size,
                tag.style.text_height,
                scale,
            )

    def _draw_window_tags(self, ax, tags: list[WindowTag], scale: float) -> None:
        """Draw WindowTag objects."""
        for tag in tags:
            if not tag.text:
                continue
            self._draw_tag(
                ax,
                tag.insertion_point,
                tag.text,
                tag.style.shape,
                tag.style.size,
                tag.style.text_height,
                scale,
            )

    def _draw_room_tags(self, ax, tags: list[RoomTag], scale: float) -> None:
        """Draw RoomTag objects."""
        for tag in tags:
            if not tag.name_text and not tag.number_text:
                continue

            x = tag.insertion_point.x * scale
            y = tag.insertion_point.y * scale
            r = tag.style.size * scale / 2
            text_height = tag.style.text_height * scale

            # Draw shape
            if tag.style.shape == TagShape.RECTANGLE:
                width = tag.calculated_width * scale
                rect = self._plt.Rectangle(
                    (x - width / 2, y - r),
                    width,
                    2 * r,
                    fill=False,
                    edgecolor="black",
                    linewidth=0.5,
                )
                ax.add_patch(rect)
            else:
                # Default to circle for other shapes
                circle = self._plt.Circle((x, y), r, fill=False, edgecolor="black", linewidth=0.5)
                ax.add_patch(circle)

            # Draw text (two lines)
            line_spacing = text_height * 1.2
            if tag.name_text:
                ax.text(
                    x,
                    y + line_spacing / 2,
                    tag.name_text,
                    fontsize=text_height * 2.83,
                    ha="center",
                    va="center",
                    color="black",
                )
            if tag.number_text:
                ax.text(
                    x,
                    y - line_spacing / 2,
                    tag.number_text,
                    fontsize=text_height * 2.83,
                    ha="center",
                    va="center",
                    color="black",
                )

    def _draw_section_symbols(self, ax, symbols: list[SectionSymbol], scale: float) -> None:
        """Draw SectionSymbol objects."""
        for symbol in symbols:
            # Draw section line
            start = (symbol.start_point.x * scale, symbol.start_point.y * scale)
            end = (symbol.end_point.x * scale, symbol.end_point.y * scale)
            ax.plot(
                [start[0], end[0]],
                [start[1], end[1]],
                color="black",
                linewidth=1.0,
            )

            # Draw arrows if enabled
            if symbol.style.show_arrows:
                arrow_size = symbol.style.arrow_size * scale
                arrow_angle = symbol.arrow_angle

                # Arrow at start
                self._draw_arrow(ax, start[0], start[1], arrow_angle, arrow_size)
                # Arrow at end
                self._draw_arrow(ax, end[0], end[1], arrow_angle, arrow_size)

            # Draw bubbles if enabled
            if symbol.style.show_bubbles:
                bubble_radius = symbol.style.bubble_radius * scale
                text_height = symbol.style.text_height * scale

                # Start bubble
                start_bubble = symbol.get_start_bubble_center()
                self._draw_section_bubble(
                    ax,
                    start_bubble.x * scale,
                    start_bubble.y * scale,
                    bubble_radius,
                    symbol.start_label,
                    symbol.start_sheet,
                    text_height,
                )

                # End bubble
                end_bubble = symbol.get_end_bubble_center()
                self._draw_section_bubble(
                    ax,
                    end_bubble.x * scale,
                    end_bubble.y * scale,
                    bubble_radius,
                    symbol.end_label,
                    symbol.end_sheet,
                    text_height,
                )

    def _draw_section_bubble(
        self,
        ax,
        x: float,
        y: float,
        radius: float,
        section_id: str,
        sheet_number: str,
        text_height: float,
    ) -> None:
        """Draw a section reference bubble."""
        # Draw circle
        circle = self._plt.Circle((x, y), radius, fill=False, edgecolor="black", linewidth=0.5)
        ax.add_patch(circle)

        # Draw horizontal divider
        ax.plot(
            [x - radius * 0.7, x + radius * 0.7],
            [y, y],
            color="black",
            linewidth=0.5,
        )

        # Draw text
        line_spacing = text_height * 0.8
        ax.text(
            x,
            y + line_spacing / 2,
            section_id,
            fontsize=text_height * 2.83,
            ha="center",
            va="center",
            color="black",
        )
        ax.text(
            x,
            y - line_spacing / 2,
            sheet_number,
            fontsize=text_height * 2.83 * 0.8,
            ha="center",
            va="center",
            color="black",
        )


# Global exporter instance
_pdf_exporter: PDFExporter | None = None


def get_pdf_exporter() -> PDFExporter:
    """Get the global PDF exporter instance."""
    global _pdf_exporter
    if _pdf_exporter is None:
        _pdf_exporter = PDFExporter()
    return _pdf_exporter
