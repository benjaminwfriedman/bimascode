"""DXF export for 2D views.

Provides DXFExporter class for exporting ViewResult geometry
to DXF format using ezdxf library.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from bimascode.drawing.line_styles import Layer, LineType, LineWeight
from bimascode.drawing.primitives import Arc2D, Hatch2D, Line2D, Polyline2D, ViewResult

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

    def _get_dxf_attributes(self, style) -> Dict:
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
        lines: List[Line2D],
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
        arcs: List[Arc2D],
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
        polylines: List[Polyline2D],
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
        hatches: List[Hatch2D],
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
                # Use predefined pattern
                hatch.set_pattern_fill(
                    hatch_obj.pattern,
                    scale=hatch_obj.scale,
                )

            # Add boundary
            points = [(p.x * scale, p.y * scale) for p in hatch_obj.boundary]
            hatch.paths.add_polyline_path(points, is_closed=True)

    def export_multiple(
        self,
        views: List[Tuple[ViewResult, Tuple[float, float]]],
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

        # Save file
        doc.saveas(filepath)
        return True


# Global exporter instance
_dxf_exporter: Optional[DXFExporter] = None


def get_dxf_exporter() -> DXFExporter:
    """Get the global DXF exporter instance."""
    global _dxf_exporter
    if _dxf_exporter is None:
        _dxf_exporter = DXFExporter()
    return _dxf_exporter
