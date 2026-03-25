"""DXF export for 2D views.

Provides DXFExporter class for exporting ViewResult geometry
to DXF format using ezdxf library.
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
from bimascode.drawing.tags import DoorTag, TagShape, WindowTag

if TYPE_CHECKING:
    pass


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
        """Export LinearDimension2D objects to DXF DIMENSION entities."""
        for dim in dimensions:
            dim_override = msp.add_aligned_dim(
                p1=(dim.start.x * scale, dim.start.y * scale),
                p2=(dim.end.x * scale, dim.end.y * scale),
                distance=dim.offset * scale,
                text=dim.text,
                dimstyle="Standard",
                override={
                    "dimtxt": 150,  # Text height in drawing units (mm)
                    "dimdec": dim.precision,  # Decimal places
                    "dimasz": 100,  # Arrow size
                    "dimexe": 50,  # Extension line extension
                    "dimexo": 50,  # Extension line offset from origin
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
