"""OCCT Hidden Line Removal (HLR) processor for section and elevation views.

Provides wrappers around OpenCASCADE HLRBRep_Algo for computing
visible and hidden edge projections from 3D geometry.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, Optional, Tuple

from bimascode.drawing.line_styles import LineStyle
from bimascode.drawing.primitives import Arc2D, Line2D, Point2D

if TYPE_CHECKING:
    pass


class HLRProcessor:
    """Hidden Line Removal processor using OpenCASCADE.

    Computes visible and hidden edge projections of 3D geometry
    from a given view direction. Used for section and elevation
    view generation.
    """

    def __init__(self):
        """Initialize the HLR processor."""
        self._occt_available = self._check_occt_available()

    def _check_occt_available(self) -> bool:
        """Check if OCP (OpenCASCADE Python) HLR modules are available."""
        try:
            from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
            from OCP.HLRAlgo import HLRAlgo_Projector
            from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

            return True
        except ImportError:
            return False

    @property
    def is_available(self) -> bool:
        """Check if HLR processing is available."""
        return self._occt_available

    def process(
        self,
        geometry,
        view_direction: Tuple[float, float, float],
        view_up: Tuple[float, float, float] = (0, 0, 1),
        show_hidden: bool = True,
        visible_style: Optional[LineStyle] = None,
        hidden_style: Optional[LineStyle] = None,
        layer: str = "0",
    ) -> Tuple[List[Line2D], List[Line2D]]:
        """Process geometry through HLR to get visible and hidden edges.

        Args:
            geometry: build123d geometry to process
            view_direction: Direction vector the viewer is looking
            view_up: Up direction for the view
            show_hidden: Whether to compute hidden lines
            visible_style: Style for visible lines
            hidden_style: Style for hidden lines
            layer: Layer name for output geometry

        Returns:
            Tuple of (visible_lines, hidden_lines)
        """
        if visible_style is None:
            visible_style = LineStyle.visible()
        if hidden_style is None:
            hidden_style = LineStyle.hidden()

        if not self._occt_available:
            return [], []

        try:
            return self._occt_hlr(
                geometry,
                view_direction,
                view_up,
                show_hidden,
                visible_style,
                hidden_style,
                layer,
            )
        except Exception:
            return [], []

    def _occt_hlr(
        self,
        geometry,
        view_direction: Tuple[float, float, float],
        view_up: Tuple[float, float, float],
        show_hidden: bool,
        visible_style: LineStyle,
        hidden_style: LineStyle,
        layer: str,
    ) -> Tuple[List[Line2D], List[Line2D]]:
        """Perform OCCT-based HLR processing."""
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Curve
        from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Line
        from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
        from OCP.HLRAlgo import HLRAlgo_Projector
        from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
        from OCP.TopAbs import TopAbs_EDGE
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopoDS import TopoDS

        # Get the OCC shape
        if hasattr(geometry, "wrapped"):
            shape = geometry.wrapped
        else:
            shape = geometry

        # Create HLR algorithm
        hlr = HLRBRep_Algo()
        hlr.Add(shape)

        # Set up projector (orthographic projection)
        # For HLR, we need a proper coordinate system:
        # - Z axis = view direction (into the screen)
        # - Y axis = up direction
        # - X axis = right direction (computed from Z cross Y)
        view_origin = gp_Pnt(0, 0, 0)
        view_dir = gp_Dir(*view_direction)
        up_dir = gp_Dir(*view_up)

        # Compute X axis as cross product of view direction and up
        # X = view_dir × up (gives right-hand coordinate system)
        # For West view (-1,0,0) with up (0,0,1): X = (-1,0,0) × (0,0,1) = (0,1,0) = +Y
        up_vec = gp_Vec(up_dir)
        view_vec = gp_Vec(view_dir)
        x_vec = view_vec.Crossed(up_vec)

        # Normalize and create X direction
        if x_vec.Magnitude() > 1e-10:
            x_dir = gp_Dir(x_vec)
        else:
            # Fallback if up and view are parallel
            x_dir = gp_Dir(1, 0, 0) if abs(view_direction[0]) < 0.9 else gp_Dir(0, 1, 0)

        # Create axis system: origin, Z-axis (view dir), X-axis
        ax2 = gp_Ax2(view_origin, view_dir, x_dir)
        projector = HLRAlgo_Projector(ax2)

        hlr.Projector(projector)
        hlr.Update()
        hlr.Hide()

        # Extract results
        hlr_shapes = HLRBRep_HLRToShape(hlr)

        visible_lines: List[Line2D] = []
        hidden_lines: List[Line2D] = []

        # Extract visible sharp edges
        visible_compound = hlr_shapes.VCompound()
        if visible_compound is not None:
            visible_lines.extend(
                self._extract_edges(
                    visible_compound, visible_style, layer, view_direction
                )
            )

        # Extract visible smooth edges
        visible_smooth = hlr_shapes.Rg1LineVCompound()
        if visible_smooth is not None:
            visible_lines.extend(
                self._extract_edges(
                    visible_smooth, visible_style, layer, view_direction
                )
            )

        # Extract hidden edges if requested
        if show_hidden:
            hidden_compound = hlr_shapes.HCompound()
            if hidden_compound is not None:
                hidden_lines.extend(
                    self._extract_edges(
                        hidden_compound, hidden_style, layer, view_direction
                    )
                )

        return visible_lines, hidden_lines

    def _extract_edges(
        self,
        shape,
        style: LineStyle,
        layer: str,
        view_direction: Tuple[float, float, float],
    ) -> List[Line2D]:
        """Extract edges from a shape as 2D lines.

        Args:
            shape: OCC shape containing edges
            style: Line style
            layer: Layer name
            view_direction: View direction for coordinate mapping

        Returns:
            List of Line2D
        """
        from OCP.BRepAdaptor import BRepAdaptor_Curve
        from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Line
        from OCP.TopAbs import TopAbs_EDGE
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopoDS import TopoDS

        result: List[Line2D] = []

        explorer = TopExp_Explorer(shape, TopAbs_EDGE)

        while explorer.More():
            edge_shape = explorer.Current()
            explorer.Next()

            try:
                # Cast Shape to Edge
                edge = TopoDS.Edge_s(edge_shape)
                curve = BRepAdaptor_Curve(edge)
                curve_type = curve.GetType()

                if curve_type == GeomAbs_Line:
                    p1 = curve.Value(curve.FirstParameter())
                    p2 = curve.Value(curve.LastParameter())

                    # HLR output is in projection plane coordinates:
                    # - X = horizontal extent (perpendicular to view and up)
                    # - Y = vertical extent (negated due to gp_Ax2 convention)
                    # Negate Y to get correct vertical orientation (up = positive)
                    result.append(
                        Line2D(
                            start=Point2D(p1.X(), -p1.Y()),
                            end=Point2D(p2.X(), -p2.Y()),
                            style=style,
                            layer=layer,
                        )
                    )
                else:
                    # Tessellate other curve types
                    lines = self._tessellate_edge(curve, style, layer)
                    result.extend(lines)

            except Exception:
                continue

        return result

    def _tessellate_edge(
        self,
        curve,
        style: LineStyle,
        layer: str,
        num_segments: int = 32,
    ) -> List[Line2D]:
        """Tessellate a curve edge into line segments.

        HLR output is in projection plane coordinates - map directly to 2D.
        """
        result = []

        first = curve.FirstParameter()
        last = curve.LastParameter()
        step = (last - first) / num_segments

        prev_point = None
        for i in range(num_segments + 1):
            param = first + i * step
            pnt = curve.Value(param)

            # HLR output: X=horizontal, Y=vertical (negated due to gp_Ax2 convention)
            # Negate Y to get correct vertical orientation
            current = Point2D(pnt.X(), -pnt.Y())

            if prev_point is not None:
                result.append(
                    Line2D(start=prev_point, end=current, style=style, layer=layer)
                )

            prev_point = current

        return result

    def _project_point(
        self,
        point_3d: Tuple[float, float, float],
        view_direction: Tuple[float, float, float],
    ) -> Tuple[float, float]:
        """Project a 3D point to 2D based on view direction.

        For orthographic projection, we drop the coordinate
        aligned with the view direction.

        Args:
            point_3d: 3D point (x, y, z)
            view_direction: View direction vector

        Returns:
            2D point (x, y)
        """
        # Normalize view direction
        vx, vy, vz = view_direction
        length = math.sqrt(vx * vx + vy * vy + vz * vz)
        if length < 1e-10:
            return (point_3d[0], point_3d[1])

        vx, vy, vz = vx / length, vy / length, vz / length

        # Determine primary view direction
        abs_vx, abs_vy, abs_vz = abs(vx), abs(vy), abs(vz)

        if abs_vz >= abs_vx and abs_vz >= abs_vy:
            # Looking along Z (plan view)
            return (point_3d[0], point_3d[1])
        elif abs_vy >= abs_vx:
            # Looking along Y (elevation, north/south)
            return (point_3d[0], point_3d[2])
        else:
            # Looking along X (elevation, east/west)
            return (point_3d[1], point_3d[2])

    def process_elements(
        self,
        elements: list,
        view_direction: Tuple[float, float, float],
        view_up: Tuple[float, float, float] = (0, 0, 1),
        show_hidden: bool = True,
        visible_style: Optional[LineStyle] = None,
        hidden_style: Optional[LineStyle] = None,
    ) -> Tuple[List[Line2D], List[Line2D]]:
        """Process multiple elements through HLR with proper occlusion.

        All geometry is combined into a single compound shape before HLR
        processing, so that elements properly occlude each other (e.g.,
        a wall in front hides doors behind it).

        Args:
            elements: List of elements with get_geometry() method
            view_direction: Direction vector
            view_up: Up vector
            show_hidden: Whether to show hidden lines
            visible_style: Style for visible lines
            hidden_style: Style for hidden lines

        Returns:
            Tuple of (visible_lines, hidden_lines)
        """
        if visible_style is None:
            visible_style = LineStyle.visible()
        if hidden_style is None:
            hidden_style = LineStyle.hidden()

        if not self._occt_available:
            return [], []

        # Collect all geometry shapes
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Compound

        builder = BRep_Builder()
        compound = TopoDS_Compound()
        builder.MakeCompound(compound)

        has_geometry = False
        for element in elements:
            # Prefer world geometry if available (includes transform to world coordinates)
            if hasattr(element, "get_world_geometry"):
                geometry = element.get_world_geometry()
            elif hasattr(element, "get_geometry"):
                geometry = element.get_geometry()
            else:
                geometry = None

            if geometry is not None:
                # Get the OCC shape
                if hasattr(geometry, "wrapped"):
                    shape = geometry.wrapped
                else:
                    shape = geometry
                builder.Add(compound, shape)
                has_geometry = True

        if not has_geometry:
            return [], []

        # Run HLR on the combined compound - this computes proper occlusion
        try:
            return self._process_compound_hlr(
                compound,
                view_direction,
                view_up,
                show_hidden,
                visible_style,
                hidden_style,
            )
        except Exception:
            return [], []

    def _process_compound_hlr(
        self,
        compound,
        view_direction: Tuple[float, float, float],
        view_up: Tuple[float, float, float],
        show_hidden: bool,
        visible_style: LineStyle,
        hidden_style: LineStyle,
    ) -> Tuple[List[Line2D], List[Line2D]]:
        """Run HLR on a compound shape with all geometry combined."""
        from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
        from OCP.HLRAlgo import HLRAlgo_Projector
        from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

        # Create HLR algorithm with combined geometry
        hlr = HLRBRep_Algo()
        hlr.Add(compound)

        # Set up projector (same as in process())
        view_origin = gp_Pnt(0, 0, 0)
        view_dir = gp_Dir(*view_direction)
        up_dir = gp_Dir(*view_up)

        up_vec = gp_Vec(up_dir)
        view_vec = gp_Vec(view_dir)
        x_vec = view_vec.Crossed(up_vec)

        if x_vec.Magnitude() > 1e-10:
            x_dir = gp_Dir(x_vec)
        else:
            x_dir = gp_Dir(1, 0, 0) if abs(view_direction[0]) < 0.9 else gp_Dir(0, 1, 0)

        ax2 = gp_Ax2(view_origin, view_dir, x_dir)
        projector = HLRAlgo_Projector(ax2)

        hlr.Projector(projector)
        hlr.Update()
        hlr.Hide()

        # Extract results
        hlr_shapes = HLRBRep_HLRToShape(hlr)

        visible_lines: List[Line2D] = []
        hidden_lines: List[Line2D] = []

        # Use a default layer for combined output
        layer = "0"

        # Extract visible sharp edges
        visible_compound = hlr_shapes.VCompound()
        if visible_compound is not None:
            visible_lines.extend(
                self._extract_edges(visible_compound, visible_style, layer, view_direction)
            )

        # Extract visible smooth edges
        visible_smooth = hlr_shapes.Rg1LineVCompound()
        if visible_smooth is not None:
            visible_lines.extend(
                self._extract_edges(visible_smooth, visible_style, layer, view_direction)
            )

        # Extract hidden edges if requested
        if show_hidden:
            hidden_compound = hlr_shapes.HCompound()
            if hidden_compound is not None:
                hidden_lines.extend(
                    self._extract_edges(hidden_compound, hidden_style, layer, view_direction)
                )

        return visible_lines, hidden_lines

    def _get_layer_for_element(self, element) -> str:
        """Get appropriate layer for an element."""
        from bimascode.drawing.line_styles import Layer

        element_type = type(element).__name__
        return Layer.for_element_type(element_type)


# Global HLR processor instance
_hlr_processor: Optional[HLRProcessor] = None


def get_hlr_processor() -> HLRProcessor:
    """Get the global HLR processor instance."""
    global _hlr_processor
    if _hlr_processor is None:
        _hlr_processor = HLRProcessor()
    return _hlr_processor
