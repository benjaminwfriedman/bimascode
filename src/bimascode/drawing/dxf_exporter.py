"""DXF export for 2D views.

Provides DXFExporter class for exporting ViewResult geometry
to DXF format using ezdxf library, and DXFSheetExporter for
exporting Sheet objects with paperspace layouts.
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
    Polyline2D,
    TextNote2D,
    ViewResult,
)
from bimascode.drawing.tags import DoorTag, RoomTag, SectionSymbol, TagShape, WindowTag

if TYPE_CHECKING:
    from bimascode.drawing.sheet import Sheet


# DXF line type patterns (dash length, gap length, ...)
DXF_LINETYPES = {
    LineType.CONTINUOUS: None,  # Solid
    LineType.DASHED: [6.0, -3.0],
    LineType.HIDDEN: [3.0, -1.5],
    LineType.CENTER: [12.0, -3.0, 3.0, -3.0],
    LineType.PHANTOM: [12.0, -3.0, 3.0, -3.0, 3.0, -3.0],
    LineType.DEMOLISH: [3.0, -1.5, 0.5, -1.5],
    LineType.ABOVE_CUT: [4.0, -2.0],
}

# Map line weight to DXF line weight index (0-211)
# See: https://ezdxf.readthedocs.io/en/stable/concepts/lineweights.html
DXF_LINEWEIGHT_MAP = {
    LineWeight.EXTRA_FINE: 13,  # 0.13mm
    LineWeight.FINE: 18,  # 0.18mm
    LineWeight.NARROW: 25,  # 0.25mm
    LineWeight.MEDIUM: 35,  # 0.35mm
    LineWeight.WIDE: 50,  # 0.50mm
    LineWeight.HEAVY: 70,  # 0.70mm
}


class DXFExporter:
    """Exports ViewResult geometry to DXF format.

    Uses ezdxf library to create properly formatted DXF files
    with AIA-compliant layers, line types, and line weights.

    Example:
        >>> exporter = DXFExporter()
        >>> exporter.export(view_result, "floor_plan.dxf")
    """

    def __init__(self, dxf_version: str = "R2013"):
        """Initialize the DXF exporter.

        Args:
            dxf_version: DXF version to export (default R2013)
        """
        self.dxf_version = dxf_version
        self._check_ezdxf_available()

    def _check_ezdxf_available(self) -> bool:
        """Check if ezdxf is available."""
        try:
            import ezdxf

            self._ezdxf = ezdxf
            return True
        except ImportError:
            self._ezdxf = None
            return False

    @property
    def is_available(self) -> bool:
        """Check if DXF export is available."""
        return self._ezdxf is not None

    def export(
        self,
        view_result: ViewResult,
        filepath: str,
        scale: float = 1.0,
    ) -> bool:
        """Export a ViewResult to DXF file.

        Args:
            view_result: ViewResult to export
            filepath: Output file path
            scale: Scale factor to apply (1.0 = model space)

        Returns:
            True if export succeeded
        """
        if not self.is_available:
            raise ImportError("ezdxf is required for DXF export")

        # Create new DXF document
        doc = self._ezdxf.new(self.dxf_version)
        msp = doc.modelspace()

        # Setup layers and line types
        self._setup_layers(doc, view_result)
        self._setup_linetypes(doc)

        # Export geometry
        self._export_lines(msp, view_result.lines, scale)
        self._export_arcs(msp, view_result.arcs, scale)
        self._export_polylines(msp, view_result.polylines, scale)
        self._export_hatches(msp, view_result.hatches, scale)
        self._export_dimensions(msp, view_result.dimensions, scale)
        self._export_chain_dimensions(msp, view_result.chain_dimensions, scale)
        self._export_text_notes(msp, view_result.text_notes, scale)
        self._export_door_tags(doc, msp, view_result.door_tags, scale)
        self._export_window_tags(doc, msp, view_result.window_tags, scale)
        self._export_room_tags(doc, msp, view_result.room_tags, scale)
        self._export_section_symbols(doc, msp, view_result.section_symbols, scale)

        # Save file
        doc.saveas(filepath)
        return True

    def _setup_layers(self, doc, view_result: ViewResult) -> None:
        """Create required layers in the DXF document."""
        # Collect all unique layers from geometry
        layers = set()

        for line in view_result.lines:
            layers.add(line.layer)
        for arc in view_result.arcs:
            layers.add(arc.layer)
        for polyline in view_result.polylines:
            layers.add(polyline.layer)
        for hatch in view_result.hatches:
            layers.add(hatch.layer)
        for dim in view_result.dimensions:
            layers.add(dim.layer)
        for chain in view_result.chain_dimensions:
            layers.add(chain.layer)
        for text in view_result.text_notes:
            layers.add(text.layer)
        for tag in view_result.door_tags:
            layers.add(tag.layer)
        for tag in view_result.window_tags:
            layers.add(tag.layer)
        for tag in view_result.room_tags:
            layers.add(tag.layer)
        for symbol in view_result.section_symbols:
            layers.add(symbol.layer)

        # Create layers with standard AIA colors
        layer_colors = {
            Layer.WALL: 7,  # White
            Layer.WALL_FIRE: 1,  # Red
            Layer.DOOR: 6,  # Magenta
            Layer.WINDOW: 4,  # Cyan
            Layer.FLOOR: 8,  # Dark gray
            Layer.CEILING: 9,  # Light gray
            Layer.COLUMN: 3,  # Green
            Layer.BEAM: 3,  # Green
            Layer.ANNOTATION: 7,  # White
            Layer.DIMENSION: 7,  # White
            Layer.SYMBOL: 7,  # White (for tags)
            "0": 7,  # Default layer
        }

        for layer_name in layers:
            if layer_name not in doc.layers:
                color = layer_colors.get(layer_name, 7)
                doc.layers.add(name=layer_name, color=color)

    def _setup_linetypes(self, doc) -> None:
        """Create required line types in the DXF document."""
        for line_type, pattern in DXF_LINETYPES.items():
            if pattern is None:
                continue  # CONTINUOUS is built-in

            name = line_type.value
            if name not in doc.linetypes:
                # Create linetype with pattern
                # ezdxf pattern format: total length, elements...
                total_length = sum(abs(p) for p in pattern)
                doc.linetypes.add(
                    name=name,
                    pattern=[total_length] + pattern,
                    description=f"{name} line type",
                )

    def _get_dxf_attributes(self, style) -> dict:
        """Get DXF entity attributes from a LineStyle."""
        attrs = {}

        # Line type
        if style.type != LineType.CONTINUOUS:
            attrs["linetype"] = style.type.value

        # Line weight
        if style.weight in DXF_LINEWEIGHT_MAP:
            attrs["lineweight"] = DXF_LINEWEIGHT_MAP[style.weight]

        # Color (if specified)
        if style.color is not None:
            # Convert RGB to DXF true color
            r, g, b = style.color
            attrs["true_color"] = (r << 16) | (g << 8) | b

        return attrs

    def _export_lines(
        self,
        msp,
        lines: list[Line2D],
        scale: float,
    ) -> None:
        """Export Line2D objects to DXF."""
        for line in lines:
            attrs = self._get_dxf_attributes(line.style)
            attrs["layer"] = line.layer

            msp.add_line(
                start=(line.start.x * scale, line.start.y * scale),
                end=(line.end.x * scale, line.end.y * scale),
                dxfattribs=attrs,
            )

    def _export_arcs(
        self,
        msp,
        arcs: list[Arc2D],
        scale: float,
    ) -> None:
        """Export Arc2D objects to DXF."""
        for arc in arcs:
            attrs = self._get_dxf_attributes(arc.style)
            attrs["layer"] = arc.layer

            # Convert radians to degrees for DXF
            start_deg = math.degrees(arc.start_angle)
            end_deg = math.degrees(arc.end_angle)

            msp.add_arc(
                center=(arc.center.x * scale, arc.center.y * scale),
                radius=arc.radius * scale,
                start_angle=start_deg,
                end_angle=end_deg,
                dxfattribs=attrs,
            )

    def _export_polylines(
        self,
        msp,
        polylines: list[Polyline2D],
        scale: float,
    ) -> None:
        """Export Polyline2D objects to DXF."""
        for polyline in polylines:
            if len(polyline.points) < 2:
                continue

            attrs = self._get_dxf_attributes(polyline.style)
            attrs["layer"] = polyline.layer

            points = [(p.x * scale, p.y * scale) for p in polyline.points]

            if polyline.closed:
                msp.add_lwpolyline(
                    points,
                    close=True,
                    dxfattribs=attrs,
                )
            else:
                msp.add_lwpolyline(
                    points,
                    close=False,
                    dxfattribs=attrs,
                )

    def _export_hatches(
        self,
        msp,
        hatches: list[Hatch2D],
        scale: float,
    ) -> None:
        """Export Hatch2D objects to DXF."""
        for hatch_obj in hatches:
            if len(hatch_obj.boundary) < 3:
                continue

            # Create hatch entity
            hatch = msp.add_hatch(color=7, dxfattribs={"layer": hatch_obj.layer})

            # Set pattern
            if hatch_obj.pattern == "SOLID":
                hatch.set_solid_fill()
            else:
                # Use predefined pattern with rotation
                hatch.set_pattern_fill(
                    hatch_obj.pattern,
                    scale=hatch_obj.scale,
                    angle=hatch_obj.rotation,
                )

            # Apply RGB color if specified
            if hatch_obj.color is not None:
                r, g, b = hatch_obj.color
                hatch.rgb = (r, g, b)

            # Add boundary
            points = [(p.x * scale, p.y * scale) for p in hatch_obj.boundary]
            hatch.paths.add_polyline_path(points, is_closed=True)

    def _export_dimensions(
        self,
        msp,
        dimensions: list[LinearDimension2D],
        scale: float,
    ) -> None:
        """Export LinearDimension2D objects to DXF DIMENSION entities.

        Dimension style values (text height, arrow size, etc.) are computed
        based on the dimension offset, which scales proportionally with the
        drawing. This ensures dimensions look correct at any scale.
        """
        for dim in dimensions:
            # Use offset as a reference for sizing - typical offset is 300-1000mm
            # in model space. Scale style elements based on that.
            # For a 500mm offset in model: text=150mm (0.3x), arrows=100mm (0.2x)
            # After 1:100 scaling: offset=5mm, text=1.5mm, arrows=1mm
            scaled_offset = abs(dim.offset) * scale
            # Ensure minimum values for readability
            text_height = max(scaled_offset * 0.3, 1.5) if scaled_offset < 50 else 150 * scale
            arrow_size = max(scaled_offset * 0.2, 1.0) if scaled_offset < 50 else 100 * scale
            ext_extension = max(scaled_offset * 0.1, 0.5) if scaled_offset < 50 else 50 * scale

            dim_override = msp.add_aligned_dim(
                p1=(dim.start.x * scale, dim.start.y * scale),
                p2=(dim.end.x * scale, dim.end.y * scale),
                distance=dim.offset * scale,
                text=dim.text,
                dimstyle="Standard",
                override={
                    "dimtxt": text_height,  # Text height
                    "dimdec": dim.precision,  # Decimal places
                    "dimasz": arrow_size,  # Arrow size
                    "dimexe": ext_extension,  # Extension line extension
                    "dimexo": ext_extension,  # Extension line offset from origin
                    "dimlfac": dim.dimlfac,  # Linear scale factor for text display
                },
                dxfattribs={"layer": dim.layer},
            )
            dim_override.render()

    def _export_chain_dimensions(
        self,
        msp,
        chain_dimensions: list[ChainDimension2D],
        scale: float,
    ) -> None:
        """Export ChainDimension2D objects to DXF DIMENSION entities.

        Each chain dimension is decomposed into its LinearDimension2D
        segments and exported as individual aligned dimensions.
        """
        for chain in chain_dimensions:
            # Export each segment as a separate dimension
            self._export_dimensions(msp, chain.segments, scale)

    def _export_text_notes(
        self,
        msp,
        text_notes: list[TextNote2D],
        scale: float,
    ) -> None:
        """Export TextNote2D objects to DXF MTEXT entities."""
        # Map TextAlignment to ezdxf attachment point constants
        # ezdxf uses integers 1-9 for MTEXT attachment points
        attachment_map = {
            "TOP_LEFT": 1,
            "TOP_CENTER": 2,
            "TOP_RIGHT": 3,
            "MIDDLE_LEFT": 4,
            "MIDDLE_CENTER": 5,
            "MIDDLE_RIGHT": 6,
            "BOTTOM_LEFT": 7,
            "BOTTOM_CENTER": 8,
            "BOTTOM_RIGHT": 9,
        }

        for text in text_notes:
            attrs = {
                "layer": text.layer,
                "char_height": text.height * scale,
                "rotation": text.rotation,
                "attachment_point": attachment_map.get(text.alignment, 4),
            }

            # Set width for word wrapping (0 means no width constraint)
            if text.width > 0:
                attrs["width"] = text.width * scale

            msp.add_mtext(
                text.content,
                dxfattribs=attrs,
            ).set_location(
                insert=(text.position.x * scale, text.position.y * scale),
            )

    def _create_tag_block(
        self,
        doc,
        block_name: str,
        shape: TagShape,
        size: float,
        text_height: float,
    ) -> None:
        """Create a tag block definition if it doesn't exist.

        Args:
            doc: DXF document
            block_name: Name for the block
            shape: Tag shape (hexagon, circle, etc.)
            size: Size of the tag symbol in mm
            text_height: Height of the text in mm
        """
        if block_name in doc.blocks:
            return

        block = doc.blocks.new(name=block_name)
        half_size = size / 2

        if shape == TagShape.CIRCLE:
            # Draw circle
            block.add_circle(center=(0, 0), radius=half_size)
        elif shape == TagShape.HEXAGON:
            # Draw hexagon (6 sides)
            import math

            points = []
            for i in range(6):
                angle = math.pi / 6 + i * math.pi / 3  # Start at 30 degrees
                x = half_size * math.cos(angle)
                y = half_size * math.sin(angle)
                points.append((x, y))
            block.add_lwpolyline(points, close=True)
        elif shape == TagShape.RECTANGLE:
            # Draw rectangle
            block.add_lwpolyline(
                [
                    (-half_size, -half_size * 0.6),
                    (half_size, -half_size * 0.6),
                    (half_size, half_size * 0.6),
                    (-half_size, half_size * 0.6),
                ],
                close=True,
            )
        elif shape == TagShape.DIAMOND:
            # Draw diamond
            block.add_lwpolyline(
                [
                    (0, half_size),
                    (half_size, 0),
                    (0, -half_size),
                    (-half_size, 0),
                ],
                close=True,
            )

        # Add attribute definition for the mark text
        block.add_attdef(
            tag="MARK",
            insert=(0, 0),
            dxfattribs={
                "height": text_height,
                "halign": 4,  # Middle center
                "valign": 2,  # Middle
            },
        )

    def _export_door_tags(
        self,
        doc,
        msp,
        tags: list[DoorTag],
        scale: float,
    ) -> None:
        """Export DoorTag objects to DXF as BLOCK references with ATTRIB."""
        for tag in tags:
            # Skip tags without text
            if not tag.text:
                continue

            # Create block definition if needed
            self._create_tag_block(
                doc,
                tag.block_name,
                tag.style.shape,
                tag.style.size * scale,
                tag.style.text_height * scale,
            )

            # Insert block reference
            insert_point = (
                tag.insertion_point.x * scale,
                tag.insertion_point.y * scale,
            )

            block_ref = msp.add_blockref(
                tag.block_name,
                insert=insert_point,
                dxfattribs={
                    "layer": tag.layer,
                    "rotation": tag.rotation,
                },
            )

            # Add attribute with the mark value
            block_ref.add_auto_attribs({"MARK": tag.text})

    def _export_window_tags(
        self,
        doc,
        msp,
        tags: list[WindowTag],
        scale: float,
    ) -> None:
        """Export WindowTag objects to DXF as BLOCK references with ATTRIB."""
        for tag in tags:
            # Skip tags without text
            if not tag.text:
                continue

            # Create block definition if needed
            self._create_tag_block(
                doc,
                tag.block_name,
                tag.style.shape,
                tag.style.size * scale,
                tag.style.text_height * scale,
            )

            # Insert block reference
            insert_point = (
                tag.insertion_point.x * scale,
                tag.insertion_point.y * scale,
            )

            block_ref = msp.add_blockref(
                tag.block_name,
                insert=insert_point,
                dxfattribs={
                    "layer": tag.layer,
                    "rotation": tag.rotation,
                },
            )

            # Add attribute with the mark value
            block_ref.add_auto_attribs({"MARK": tag.text})

    def _create_room_tag_block(
        self,
        doc,
        block_name: str,
        shape: TagShape,
        size: float,
        width: float,
        text_height: float,
    ) -> None:
        """Create a room tag block definition if it doesn't exist.

        Room tags display two lines of text: room name and room number.
        The block is sized to accommodate both lines.

        Args:
            doc: DXF document
            block_name: Name for the block
            shape: Tag shape (rectangle recommended for rooms)
            size: Size of the tag symbol in mm (height for rectangle)
            width: Width of the tag symbol in mm (for rectangle)
            text_height: Height of the text in mm
        """
        if block_name in doc.blocks:
            return

        block = doc.blocks.new(name=block_name)
        half_width = width / 2
        half_height = size / 2

        if shape == TagShape.CIRCLE:
            # Draw circle (use larger of width/height as diameter)
            radius = max(half_width, half_height)
            block.add_circle(center=(0, 0), radius=radius)
        elif shape == TagShape.HEXAGON:
            import math

            # Use larger dimension for hexagon
            hex_size = max(half_width, half_height)
            points = []
            for i in range(6):
                angle = math.pi / 6 + i * math.pi / 3
                x = hex_size * math.cos(angle)
                y = hex_size * math.sin(angle)
                points.append((x, y))
            block.add_lwpolyline(points, close=True)
        elif shape == TagShape.RECTANGLE:
            # Draw rectangle (default for room tags)
            block.add_lwpolyline(
                [
                    (-half_width, -half_height),
                    (half_width, -half_height),
                    (half_width, half_height),
                    (-half_width, half_height),
                ],
                close=True,
            )
        elif shape == TagShape.DIAMOND:
            block.add_lwpolyline(
                [
                    (0, half_height),
                    (half_width, 0),
                    (0, -half_height),
                    (-half_width, 0),
                ],
                close=True,
            )

        # Add attribute definition for room NAME (upper line)
        line_spacing = text_height * 1.5
        block.add_attdef(
            tag="NAME",
            insert=(0, line_spacing / 2),
            dxfattribs={
                "height": text_height,
                "halign": 4,  # Middle center
                "valign": 2,  # Middle
            },
        )

        # Add attribute definition for room NUMBER (lower line)
        block.add_attdef(
            tag="NUMBER",
            insert=(0, -line_spacing / 2),
            dxfattribs={
                "height": text_height,
                "halign": 4,  # Middle center
                "valign": 2,  # Middle
            },
        )

    def _export_room_tags(
        self,
        doc,
        msp,
        tags: list[RoomTag],
        scale: float,
    ) -> None:
        """Export RoomTag objects to DXF as BLOCK references with ATTRIB.

        Room tags display both room name and room number as separate
        attribute values within the block.
        """
        for tag in tags:
            # Skip tags without any text
            if not tag.name_text and not tag.number_text:
                continue

            # Create block definition if needed
            self._create_room_tag_block(
                doc,
                tag.block_name,
                tag.style.shape,
                tag.style.size * scale,
                tag.calculated_width * scale,
                tag.style.text_height * scale,
            )

            # Insert block reference
            insert_point = (
                tag.insertion_point.x * scale,
                tag.insertion_point.y * scale,
            )

            block_ref = msp.add_blockref(
                tag.block_name,
                insert=insert_point,
                dxfattribs={
                    "layer": tag.layer,
                    "rotation": tag.rotation,
                },
            )

            # Add attributes with the name and number values
            block_ref.add_auto_attribs(
                {
                    "NAME": tag.name_text,
                    "NUMBER": tag.number_text,
                }
            )

    def _create_section_symbol_block(
        self,
        doc,
        block_name: str,
        bubble_radius: float,
        text_height: float,
        arrow_size: float,
    ) -> None:
        """Create a section symbol bubble block definition if it doesn't exist.

        Creates a circular reference bubble with two attribute definitions:
        - SECTION_ID: The section identifier (e.g., "A")
        - SHEET_NUMBER: The destination sheet number (e.g., "A2")

        The bubble is drawn at the origin with the specified radius.

        Args:
            doc: DXF document
            block_name: Name for the block
            bubble_radius: Radius of the bubble circle
            text_height: Height of the text
            arrow_size: Size of arrow (used for spacing calculations)
        """
        if block_name in doc.blocks:
            return

        block = doc.blocks.new(name=block_name)

        # Draw the bubble circle
        block.add_circle(center=(0, 0), radius=bubble_radius)

        # Add attribute definition for section ID (upper half)
        line_spacing = text_height * 0.8
        block.add_attdef(
            tag="SECTION_ID",
            insert=(0, line_spacing / 2),
            dxfattribs={
                "height": text_height,
                "halign": 4,  # Middle center
                "valign": 2,  # Middle
            },
        )

        # Add attribute definition for sheet number (lower half)
        block.add_attdef(
            tag="SHEET_NUMBER",
            insert=(0, -line_spacing / 2),
            dxfattribs={
                "height": text_height * 0.8,  # Slightly smaller
                "halign": 4,  # Middle center
                "valign": 2,  # Middle
            },
        )

        # Add horizontal divider line in the bubble
        block.add_line(
            start=(-bubble_radius * 0.7, 0),
            end=(bubble_radius * 0.7, 0),
        )

    def _export_section_symbols(
        self,
        doc,
        msp,
        symbols: list[SectionSymbol],
        scale: float,
    ) -> None:
        """Export SectionSymbol objects to DXF.

        Each section symbol consists of:
        1. A cut line between start and end points
        2. Arrow heads pointing in the view direction
        3. Reference bubbles (BLOCK references) at each end

        Args:
            doc: DXF document
            msp: Modelspace or layout to export to
            symbols: List of SectionSymbol objects
            scale: Scale factor
        """
        for symbol in symbols:
            # Create block definition for bubbles if needed
            self._create_section_symbol_block(
                doc,
                symbol.block_name,
                symbol.style.bubble_radius * scale,
                symbol.style.text_height * scale,
                symbol.style.arrow_size * scale,
            )

            # Draw the section cut line
            start = (symbol.start_point.x * scale, symbol.start_point.y * scale)
            end = (symbol.end_point.x * scale, symbol.end_point.y * scale)

            msp.add_line(
                start=start,
                end=end,
                dxfattribs={
                    "layer": symbol.layer,
                    "lineweight": DXF_LINEWEIGHT_MAP.get(LineWeight.MEDIUM, 35),
                },
            )

            # Draw arrow heads if enabled
            if symbol.style.show_arrows:
                arrow_angle = symbol.arrow_angle
                arrow_size = symbol.style.arrow_size * scale

                # Arrow at start point
                self._draw_section_arrow(
                    msp,
                    (symbol.start_point.x * scale, symbol.start_point.y * scale),
                    arrow_angle,
                    arrow_size,
                    symbol.layer,
                )

                # Arrow at end point
                self._draw_section_arrow(
                    msp,
                    (symbol.end_point.x * scale, symbol.end_point.y * scale),
                    arrow_angle,
                    arrow_size,
                    symbol.layer,
                )

            # Draw reference bubbles if enabled
            if symbol.style.show_bubbles:
                # Start bubble
                start_bubble = symbol.get_start_bubble_center()
                block_ref = msp.add_blockref(
                    symbol.block_name,
                    insert=(start_bubble.x * scale, start_bubble.y * scale),
                    dxfattribs={"layer": symbol.layer},
                )
                block_ref.add_auto_attribs(
                    {
                        "SECTION_ID": symbol.start_label,
                        "SHEET_NUMBER": symbol.start_sheet,
                    }
                )

                # End bubble
                end_bubble = symbol.get_end_bubble_center()
                block_ref = msp.add_blockref(
                    symbol.block_name,
                    insert=(end_bubble.x * scale, end_bubble.y * scale),
                    dxfattribs={"layer": symbol.layer},
                )
                block_ref.add_auto_attribs(
                    {
                        "SECTION_ID": symbol.end_label,
                        "SHEET_NUMBER": symbol.end_sheet,
                    }
                )

    def _draw_section_arrow(
        self,
        msp,
        point: tuple[float, float],
        angle: float,
        size: float,
        layer: str,
    ) -> None:
        """Draw a section arrow head at the specified point.

        The arrow is a filled triangle pointing in the specified direction.

        Args:
            msp: Modelspace or layout to draw on
            point: Arrow tip location (x, y)
            angle: Arrow direction in radians
            size: Arrow size (length)
            layer: CAD layer name
        """
        # Arrow head as a solid triangle
        # Calculate the three points of the triangle
        tip_x, tip_y = point

        # Back corners of the arrow
        back_angle1 = angle + math.pi + math.pi / 6  # 150 degrees from tip direction
        back_angle2 = angle + math.pi - math.pi / 6  # 210 degrees from tip direction

        back1_x = tip_x + size * math.cos(back_angle1)
        back1_y = tip_y + size * math.sin(back_angle1)
        back2_x = tip_x + size * math.cos(back_angle2)
        back2_y = tip_y + size * math.sin(back_angle2)

        # Draw as solid hatch (filled triangle)
        hatch = msp.add_hatch(color=7, dxfattribs={"layer": layer})
        hatch.set_solid_fill()
        hatch.paths.add_polyline_path(
            [(tip_x, tip_y), (back1_x, back1_y), (back2_x, back2_y)],
            is_closed=True,
        )

    def export_multiple(
        self,
        views: list[tuple[ViewResult, tuple[float, float]]],
        filepath: str,
        scale: float = 1.0,
    ) -> bool:
        """Export multiple views to a single DXF file.

        Each view is placed at a specified offset in model space.

        Args:
            views: List of (ViewResult, (x_offset, y_offset)) tuples
            filepath: Output file path
            scale: Scale factor to apply

        Returns:
            True if export succeeded
        """
        if not self.is_available:
            raise ImportError("ezdxf is required for DXF export")

        # Create new DXF document
        doc = self._ezdxf.new(self.dxf_version)
        msp = doc.modelspace()

        # Collect all layers from all views
        all_layers = set()
        for view_result, _ in views:
            for line in view_result.lines:
                all_layers.add(line.layer)
            for arc in view_result.arcs:
                all_layers.add(arc.layer)
            for polyline in view_result.polylines:
                all_layers.add(polyline.layer)
            for hatch in view_result.hatches:
                all_layers.add(hatch.layer)
            for dim in view_result.dimensions:
                all_layers.add(dim.layer)
            for chain in view_result.chain_dimensions:
                all_layers.add(chain.layer)
            for text in view_result.text_notes:
                all_layers.add(text.layer)
            for tag in view_result.door_tags:
                all_layers.add(tag.layer)
            for tag in view_result.window_tags:
                all_layers.add(tag.layer)
            for tag in view_result.room_tags:
                all_layers.add(tag.layer)
            for symbol in view_result.section_symbols:
                all_layers.add(symbol.layer)

        # Setup layers and line types
        for layer_name in all_layers:
            if layer_name not in doc.layers:
                doc.layers.add(name=layer_name, color=7)

        self._setup_linetypes(doc)

        # Export each view with offset
        for view_result, (x_offset, y_offset) in views:
            # Translate and export
            translated = view_result.translate(x_offset, y_offset)
            self._export_lines(msp, translated.lines, scale)
            self._export_arcs(msp, translated.arcs, scale)
            self._export_polylines(msp, translated.polylines, scale)
            self._export_hatches(msp, translated.hatches, scale)
            self._export_dimensions(msp, translated.dimensions, scale)
            self._export_chain_dimensions(msp, translated.chain_dimensions, scale)
            self._export_text_notes(msp, translated.text_notes, scale)
            self._export_door_tags(doc, msp, translated.door_tags, scale)
            self._export_window_tags(doc, msp, translated.window_tags, scale)
            self._export_room_tags(doc, msp, translated.room_tags, scale)
            self._export_section_symbols(doc, msp, translated.section_symbols, scale)

        # Save file
        doc.saveas(filepath)
        return True


class DXFSheetExporter:
    """Exports Sheet objects to DXF with paperspace layouts.

    Creates a proper DXF file with:
    - Modelspace containing all view geometry
    - Paperspace layout with viewports looking into modelspace
    - Title block and annotations in paperspace

    Example:
        >>> from bimascode.drawing import Sheet, SheetSize
        >>> sheet = Sheet(size=SheetSize.ANSI_D, number="A-101")
        >>> sheet.add_viewport(floor_plan_result, position=(300, 200), scale="1:100")
        >>> exporter = DXFSheetExporter()
        >>> exporter.export_sheet(sheet, "A-101.dxf")
    """

    def __init__(self, dxf_version: str = "R2013"):
        """Initialize the sheet exporter.

        Args:
            dxf_version: DXF version (R2000 or newer required for paperspace)
        """
        self.dxf_version = dxf_version
        self._check_ezdxf_available()
        self._model_exporter = DXFExporter(dxf_version)

    def _check_ezdxf_available(self) -> bool:
        """Check if ezdxf is available."""
        try:
            import ezdxf

            self._ezdxf = ezdxf
            return True
        except ImportError:
            self._ezdxf = None
            return False

    @property
    def is_available(self) -> bool:
        """Check if DXF export is available."""
        return self._ezdxf is not None

    def export_sheet(
        self,
        sheet: Sheet,
        filepath: str,
    ) -> bool:
        """Export a Sheet to DXF file with paperspace layout.

        Creates a DXF file with:
        1. All viewport contents in modelspace (offset to prevent overlap)
        2. A paperspace layout with the sheet size
        3. DXF VIEWPORT entities linking paperspace to modelspace content
        4. Title block geometry in paperspace
        5. Sheet annotations in paperspace

        Args:
            sheet: Sheet to export
            filepath: Output file path

        Returns:
            True if export succeeded
        """
        if not self.is_available:
            raise ImportError("ezdxf is required for DXF export")

        # Create new DXF document
        doc = self._ezdxf.new(self.dxf_version, setup=True)
        msp = doc.modelspace()

        # Setup layers and line types
        self._setup_layers_from_sheet(doc, sheet)
        self._model_exporter._setup_linetypes(doc)

        # Export all viewport contents to modelspace
        # Track bounds for each viewport's content in modelspace
        viewport_modelspace_data: list[dict] = []
        current_offset_x = 0.0

        for viewport in sheet.viewports:
            # Get view result bounds
            bounds = viewport.view_result.get_bounds()
            if bounds is None:
                viewport_modelspace_data.append(None)
                continue

            # Calculate center in model coordinates
            model_center_x = (bounds[0] + bounds[2]) / 2 + current_offset_x
            model_center_y = (bounds[1] + bounds[3]) / 2
            model_width = bounds[2] - bounds[0]
            model_height = bounds[3] - bounds[1]

            # Translate view content and export to modelspace
            translated = viewport.view_result.translate(current_offset_x, 0)
            self._export_view_result_to_layout(doc, msp, translated, scale=1.0)

            viewport_modelspace_data.append(
                {
                    "center_x": model_center_x,
                    "center_y": model_center_y,
                    "width": model_width,
                    "height": model_height,
                }
            )

            # Offset next viewport to prevent overlap (add margin)
            current_offset_x += model_width + 5000  # 5m gap between views

        # Create paperspace layout
        layout_name = self._get_layout_name(sheet)

        # Get or create the paperspace layout
        # ezdxf creates "Layout1" by default, we'll rename or create new
        if "Layout1" in doc.layouts:
            psp = doc.layouts.get("Layout1")
            psp.rename(layout_name)
        else:
            psp = doc.layouts.new(layout_name)

        # Setup page size
        # Note: ezdxf page_setup uses (width, height) in mm
        psp.page_setup(
            size=(sheet.size.width, sheet.size.height),
            margins=sheet.margins,  # (left, bottom, right, top)
        )

        # Create VIEWPORTS layer (will be turned off to hide viewport frames)
        if "DEFPOINTS" not in doc.layers:
            doc.layers.add("DEFPOINTS")

        # Add viewports to paperspace
        for i, viewport in enumerate(sheet.viewports):
            ms_data = viewport_modelspace_data[i]
            if ms_data is None:
                continue

            # Calculate viewport dimensions on paper
            vp_width = viewport.effective_width
            vp_height = viewport.effective_height

            # View height in modelspace units (for zoom level)
            view_height = vp_height / viewport.scale.ratio

            # Create the viewport entity
            psp.add_viewport(
                center=(viewport.position.x, viewport.position.y),
                size=(vp_width, vp_height),
                view_center_point=(ms_data["center_x"], ms_data["center_y"]),
                view_height=view_height,
                status=2,  # Enable viewport (1=off, 2=on)
                dxfattribs={"layer": "DEFPOINTS"},
            )

        # Export title block to paperspace (if present)
        if sheet.title_block and sheet.title_block.has_geometry():
            self._export_view_result_to_layout(doc, psp, sheet.title_block.geometry, scale=1.0)

        # Export sheet annotations to paperspace
        if sheet.annotations.total_geometry_count > 0:
            self._export_view_result_to_layout(doc, psp, sheet.annotations, scale=1.0)

        # Save file
        doc.saveas(filepath)
        return True

    def _get_layout_name(self, sheet: Sheet) -> str:
        """Generate a layout name from sheet properties.

        Args:
            sheet: Sheet to get name from

        Returns:
            Layout name string
        """
        if sheet.number and sheet.name:
            return f"{sheet.number} - {sheet.name}"
        elif sheet.number:
            return sheet.number
        elif sheet.name:
            return sheet.name
        else:
            return "Sheet"

    def _setup_layers_from_sheet(self, doc, sheet: Sheet) -> None:
        """Create required layers from all sheet content.

        Args:
            doc: DXF document
            sheet: Sheet containing viewports and annotations
        """
        # Collect all layers from all viewports
        all_layers = set()

        for viewport in sheet.viewports:
            self._collect_layers_from_view_result(viewport.view_result, all_layers)

        # Collect from title block
        if sheet.title_block and sheet.title_block.geometry:
            self._collect_layers_from_view_result(sheet.title_block.geometry, all_layers)

        # Collect from annotations
        self._collect_layers_from_view_result(sheet.annotations, all_layers)

        # Create layers with standard AIA colors
        layer_colors = {
            Layer.WALL: 7,
            Layer.WALL_FIRE: 1,
            Layer.DOOR: 6,
            Layer.WINDOW: 4,
            Layer.FLOOR: 8,
            Layer.CEILING: 9,
            Layer.COLUMN: 3,
            Layer.BEAM: 3,
            Layer.ANNOTATION: 7,
            Layer.DIMENSION: 7,
            Layer.SYMBOL: 7,
            "0": 7,
        }

        for layer_name in all_layers:
            if layer_name not in doc.layers:
                color = layer_colors.get(layer_name, 7)
                doc.layers.add(name=layer_name, color=color)

    def _collect_layers_from_view_result(self, view_result: ViewResult, layers: set) -> None:
        """Collect all layer names from a ViewResult.

        Args:
            view_result: ViewResult to scan
            layers: Set to add layer names to
        """
        for line in view_result.lines:
            layers.add(line.layer)
        for arc in view_result.arcs:
            layers.add(arc.layer)
        for polyline in view_result.polylines:
            layers.add(polyline.layer)
        for hatch in view_result.hatches:
            layers.add(hatch.layer)
        for dim in view_result.dimensions:
            layers.add(dim.layer)
        for chain in view_result.chain_dimensions:
            layers.add(chain.layer)
        for text in view_result.text_notes:
            layers.add(text.layer)
        for tag in view_result.door_tags:
            layers.add(tag.layer)
        for tag in view_result.window_tags:
            layers.add(tag.layer)
        for tag in view_result.room_tags:
            layers.add(tag.layer)
        for symbol in view_result.section_symbols:
            layers.add(symbol.layer)

    def _export_view_result_to_layout(
        self, doc, layout, view_result: ViewResult, scale: float
    ) -> None:
        """Export ViewResult geometry to a layout (modelspace or paperspace).

        Args:
            doc: DXF document
            layout: Layout to export to (modelspace or paperspace)
            view_result: ViewResult to export
            scale: Scale factor to apply
        """
        self._model_exporter._export_lines(layout, view_result.lines, scale)
        self._model_exporter._export_arcs(layout, view_result.arcs, scale)
        self._model_exporter._export_polylines(layout, view_result.polylines, scale)
        self._model_exporter._export_hatches(layout, view_result.hatches, scale)
        self._model_exporter._export_dimensions(layout, view_result.dimensions, scale)
        self._model_exporter._export_chain_dimensions(layout, view_result.chain_dimensions, scale)
        self._model_exporter._export_text_notes(layout, view_result.text_notes, scale)
        self._model_exporter._export_door_tags(doc, layout, view_result.door_tags, scale)
        self._model_exporter._export_window_tags(doc, layout, view_result.window_tags, scale)
        self._model_exporter._export_room_tags(doc, layout, view_result.room_tags, scale)
        self._model_exporter._export_section_symbols(
            doc, layout, view_result.section_symbols, scale
        )

    def _add_viewport_label(
        self,
        msp,
        viewport,
        scaled_view: ViewResult,
    ) -> None:
        """Add a label below a viewport with view name and scale.

        The label consists of:
        - View name (e.g., "Section A-A" or "Floor Plan")
        - Underline
        - Scale notation (e.g., "Scale: 1:50")

        Args:
            msp: Modelspace to add label to
            viewport: SheetViewport being labeled
            scaled_view: The scaled/translated view result (for bounds)
        """
        # Get the view name - prefer viewport name, fall back to view_result name
        view_name = viewport.name or viewport.view_result.view_name
        if not view_name:
            return  # No name to display

        # Get bounds of the scaled view content
        bounds = scaled_view.get_bounds()
        if bounds is None:
            return

        # Position label centered below the view
        center_x = (bounds[0] + bounds[2]) / 2
        view_bottom = bounds[1]

        # Label sizing - proportional to sheet (typical sheet text is 2.5-3.5mm)
        text_height = 3.0  # mm on sheet
        line_spacing = text_height * 1.5
        label_offset = 5.0  # Gap between view and label

        # View name position (centered, below view)
        name_y = view_bottom - label_offset - text_height

        # Add view name text
        msp.add_mtext(
            view_name,
            dxfattribs={
                "layer": Layer.ANNOTATION,
                "char_height": text_height,
                "attachment_point": 8,  # BOTTOM_CENTER
            },
        ).set_location(insert=(center_x, name_y))

        # Add underline below the name
        # Estimate text width (approximate: 0.6 * height * num_chars)
        text_width = len(view_name) * text_height * 0.6
        underline_y = name_y - text_height * 0.3
        msp.add_line(
            start=(center_x - text_width / 2, underline_y),
            end=(center_x + text_width / 2, underline_y),
            dxfattribs={"layer": Layer.ANNOTATION},
        )

        # Add scale notation below the underline
        scale_text = f"Scale: {viewport.scale.name}"
        scale_y = underline_y - line_spacing

        msp.add_mtext(
            scale_text,
            dxfattribs={
                "layer": Layer.ANNOTATION,
                "char_height": text_height * 0.8,  # Slightly smaller
                "attachment_point": 8,  # BOTTOM_CENTER
            },
        ).set_location(insert=(center_x, scale_y))

    def export_sheet_flat(
        self,
        sheet: Sheet,
        filepath: str,
    ) -> bool:
        """Export a Sheet to DXF as a flat modelspace layout.

        This exports the sheet layout directly to modelspace without using
        DXF viewports/paperspace. Each viewport's content is scaled and
        positioned at its sheet location. This works with any DXF viewer.

        Args:
            sheet: Sheet to export
            filepath: Output file path

        Returns:
            True if export succeeded
        """
        if not self.is_available:
            raise ImportError("ezdxf is required for DXF export")

        # Create new DXF document
        doc = self._ezdxf.new(self.dxf_version, setup=True)
        msp = doc.modelspace()

        # Setup layers and line types
        self._setup_layers_from_sheet(doc, sheet)
        self._model_exporter._setup_linetypes(doc)

        # Export each viewport's content, scaled and positioned on sheet
        for viewport in sheet.viewports:
            bounds = viewport.view_result.get_bounds()
            if bounds is None:
                continue

            # Calculate view center in model coordinates
            model_center_x = (bounds[0] + bounds[2]) / 2
            model_center_y = (bounds[1] + bounds[3]) / 2

            # Calculate translation to position view at viewport location on sheet
            # The viewport position is the center of where the view should appear
            # Scale factor converts model units to sheet units
            scale = viewport.scale.ratio

            # Translate: shift so model center aligns with viewport position
            # First scale, then translate
            offset_x = viewport.position.x - model_center_x * scale
            offset_y = viewport.position.y - model_center_y * scale

            # Scale and translate the view content
            scaled_view = viewport.view_result.scale_and_translate(scale, offset_x, offset_y)

            # Export to modelspace
            self._export_view_result_to_layout(doc, msp, scaled_view, scale=1.0)

            # Add viewport label below the view
            self._add_viewport_label(msp, viewport, scaled_view)

        # Export title block to modelspace (if present)
        if sheet.title_block and sheet.title_block.has_geometry():
            self._export_view_result_to_layout(doc, msp, sheet.title_block.geometry, scale=1.0)

        # Export sheet annotations to modelspace
        if sheet.annotations.total_geometry_count > 0:
            self._export_view_result_to_layout(doc, msp, sheet.annotations, scale=1.0)

        # Draw sheet border (optional - helps visualize sheet bounds)
        msp.add_line((0, 0), (sheet.size.width, 0), dxfattribs={"layer": "0", "color": 8})
        msp.add_line(
            (sheet.size.width, 0),
            (sheet.size.width, sheet.size.height),
            dxfattribs={"layer": "0", "color": 8},
        )
        msp.add_line(
            (sheet.size.width, sheet.size.height),
            (0, sheet.size.height),
            dxfattribs={"layer": "0", "color": 8},
        )
        msp.add_line((0, sheet.size.height), (0, 0), dxfattribs={"layer": "0", "color": 8})

        # Save file
        doc.saveas(filepath)
        return True


# Global exporter instance
_dxf_exporter: DXFExporter | None = None


def get_dxf_exporter() -> DXFExporter:
    """Get the global DXF exporter instance."""
    global _dxf_exporter
    if _dxf_exporter is None:
        _dxf_exporter = DXFExporter()
    return _dxf_exporter
