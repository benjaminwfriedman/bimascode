"""OCCT-based section cutting for 2D view generation.

Provides wrappers around OpenCASCADE BRepAlgoAPI_Section for
computing horizontal and vertical section cuts through 3D geometry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bimascode.drawing.line_styles import LineStyle
from bimascode.drawing.primitives import Arc2D, Line2D, Point2D

if TYPE_CHECKING:
    pass


class SectionCutter:
    """OCCT-based section cutter for computing 2D section cuts.

    Uses OpenCASCADE BRepAlgoAPI_Section to compute intersections
    between 3D geometry and planes.
    """

    def __init__(self):
        """Initialize the section cutter."""
        self._occt_available = self._check_occt_available()

    def _check_occt_available(self) -> bool:
        """Check if OCP (OpenCASCADE Python) is available."""
        try:
            from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
            from OCP.gp import gp_Dir, gp_Pln, gp_Pnt

            return True
        except ImportError:
            return False

    @property
    def is_available(self) -> bool:
        """Check if OCCT section cutting is available."""
        return self._occt_available

    def horizontal_cut(
        self,
        geometry,
        z_height: float,
        style: LineStyle | None = None,
        layer: str = "0",
    ) -> list[Line2D | Arc2D]:
        """Compute a horizontal section cut at a given Z height.

        Args:
            geometry: build123d geometry to cut
            z_height: Z coordinate of the cut plane
            style: Line style for resulting geometry
            layer: Layer name for resulting geometry

        Returns:
            List of 2D geometry primitives (lines and arcs)
        """
        if style is None:
            style = LineStyle.cut_heavy()

        if not self._occt_available:
            return self._fallback_horizontal_cut(geometry, z_height, style, layer)

        try:
            return self._occt_horizontal_cut(geometry, z_height, style, layer)
        except Exception:
            return self._fallback_horizontal_cut(geometry, z_height, style, layer)

    def _occt_horizontal_cut(
        self,
        geometry,
        z_height: float,
        style: LineStyle,
        layer: str,
    ) -> list[Line2D | Arc2D]:
        """Perform OCCT-based horizontal section cut."""
        from OCP.BRepAdaptor import BRepAdaptor_Curve
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
        from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Line
        from OCP.gp import gp_Dir, gp_Pln, gp_Pnt
        from OCP.TopAbs import TopAbs_EDGE
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopoDS import TopoDS

        # Get the OCC shape from build123d geometry
        if hasattr(geometry, "wrapped"):
            shape = geometry.wrapped
        else:
            shape = geometry

        # Create horizontal plane at z_height
        plane = gp_Pln(gp_Pnt(0, 0, z_height), gp_Dir(0, 0, 1))

        # Compute section
        section = BRepAlgoAPI_Section(shape, plane)
        section.Build()

        if not section.IsDone():
            return []

        result_shape = section.Shape()
        result: list[Line2D | Arc2D] = []

        # Extract edges from section result
        explorer = TopExp_Explorer(result_shape, TopAbs_EDGE)

        while explorer.More():
            edge_shape = explorer.Current()
            explorer.Next()

            # Get curve adapter - must cast Shape to Edge
            try:
                edge = TopoDS.Edge_s(edge_shape)
                curve = BRepAdaptor_Curve(edge)
                curve_type = curve.GetType()

                if curve_type == GeomAbs_Line:
                    # Extract line endpoints
                    p1 = curve.Value(curve.FirstParameter())
                    p2 = curve.Value(curve.LastParameter())

                    result.append(
                        Line2D(
                            start=Point2D(p1.X(), p1.Y()),
                            end=Point2D(p2.X(), p2.Y()),
                            style=style,
                            layer=layer,
                        )
                    )

                elif curve_type == GeomAbs_Circle:
                    # Extract arc parameters
                    circle = curve.Circle()
                    center = circle.Location()
                    radius = circle.Radius()

                    start_param = curve.FirstParameter()
                    end_param = curve.LastParameter()

                    result.append(
                        Arc2D(
                            center=Point2D(center.X(), center.Y()),
                            radius=radius,
                            start_angle=start_param,
                            end_angle=end_param,
                            style=style,
                            layer=layer,
                        )
                    )
                else:
                    # Tessellate other curve types
                    lines = self._tessellate_curve(curve, style, layer)
                    result.extend(lines)

            except Exception:
                continue

        return result

    def _tessellate_curve(
        self,
        curve,
        style: LineStyle,
        layer: str,
        num_segments: int = 32,
    ) -> list[Line2D]:
        """Tessellate a curve into line segments.

        Args:
            curve: BRepAdaptor_Curve
            style: Line style
            layer: Layer name
            num_segments: Number of segments for tessellation

        Returns:
            List of Line2D approximating the curve
        """
        result = []

        first = curve.FirstParameter()
        last = curve.LastParameter()
        step = (last - first) / num_segments

        prev_point = None
        for i in range(num_segments + 1):
            param = first + i * step
            pnt = curve.Value(param)
            current = Point2D(pnt.X(), pnt.Y())

            if prev_point is not None:
                result.append(Line2D(start=prev_point, end=current, style=style, layer=layer))

            prev_point = current

        return result

    def _fallback_horizontal_cut(
        self,
        geometry,
        z_height: float,
        style: LineStyle,
        layer: str,
    ) -> list[Line2D | Arc2D]:
        """Fallback when OCCT is not available.

        Returns empty list - elements should implement Drawable2D
        for proper 2D generation without OCCT.
        """
        return []

    def vertical_cut(
        self,
        geometry,
        plane_point: tuple[float, float, float],
        plane_normal: tuple[float, float, float],
        style: LineStyle | None = None,
        layer: str = "0",
    ) -> list[Line2D | Arc2D]:
        """Compute a vertical section cut through geometry.

        Args:
            geometry: build123d geometry to cut
            plane_point: Point on the section plane
            plane_normal: Normal vector of the section plane
            style: Line style for resulting geometry
            layer: Layer name for resulting geometry

        Returns:
            List of 2D geometry primitives
        """
        if style is None:
            style = LineStyle.cut_heavy()

        if not self._occt_available:
            return []

        try:
            return self._occt_vertical_cut(geometry, plane_point, plane_normal, style, layer)
        except Exception:
            return []

    def _occt_vertical_cut(
        self,
        geometry,
        plane_point: tuple[float, float, float],
        plane_normal: tuple[float, float, float],
        style: LineStyle,
        layer: str,
    ) -> list[Line2D | Arc2D]:
        """Perform OCCT-based vertical section cut."""
        from OCP.BRepAdaptor import BRepAdaptor_Curve
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
        from OCP.GeomAbs import GeomAbs_Line
        from OCP.gp import gp_Dir, gp_Pln, gp_Pnt
        from OCP.TopAbs import TopAbs_EDGE
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopoDS import TopoDS

        # Get the OCC shape
        if hasattr(geometry, "wrapped"):
            shape = geometry.wrapped
        else:
            shape = geometry

        # Create vertical section plane
        plane = gp_Pln(
            gp_Pnt(*plane_point),
            gp_Dir(*plane_normal),
        )

        # Compute section
        section = BRepAlgoAPI_Section(shape, plane)
        section.Build()

        if not section.IsDone():
            return []

        result_shape = section.Shape()
        result: list[Line2D | Arc2D] = []

        # For vertical sections, we need to project to 2D
        # The section result is in 3D; we project based on plane orientation
        # Z is always vertical in the section
        # Horizontal axis depends on which way the plane faces:
        # - If normal is primarily in X direction: use Y for horizontal
        # - If normal is primarily in Y direction: use X for horizontal
        #
        # The horizontal axis sign must match HLR convention:
        # HLR x_axis = view_direction × up = normal × (0,0,1)
        # For east view (1,0,0): x_axis = (0,-1,0), so HLR X = -world_Y
        # For west view (-1,0,0): x_axis = (0,1,0), so HLR X = +world_Y
        # For north view (0,1,0): x_axis = (1,0,0), so HLR X = +world_X
        # For south view (0,-1,0): x_axis = (-1,0,0), so HLR X = -world_X
        nx, ny, nz = plane_normal
        use_y_for_horizontal = abs(nx) > abs(ny)

        # Determine sign for horizontal axis to match HLR convention
        # HLR x_axis = view × up, where view = plane_normal, up = (0,0,1)
        # Cross product (nx,ny,0) × (0,0,1) = (ny, -nx, 0)
        # So HLR X-axis direction is (ny, -nx, 0)
        # If use_y_for_horizontal: HLR X ~ -nx * world_Y (sign is -nx)
        # If use_x_for_horizontal: HLR X ~ ny * world_X (sign is ny)
        if use_y_for_horizontal:
            h_sign = -1 if nx > 0 else 1  # -nx sign
        else:
            h_sign = 1 if ny > 0 else -1  # ny sign

        explorer = TopExp_Explorer(result_shape, TopAbs_EDGE)

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

                    # Project to section plane based on orientation
                    # Apply sign to match HLR coordinate system
                    if use_y_for_horizontal:
                        result.append(
                            Line2D(
                                start=Point2D(h_sign * p1.Y(), p1.Z()),
                                end=Point2D(h_sign * p2.Y(), p2.Z()),
                                style=style,
                                layer=layer,
                            )
                        )
                    else:
                        result.append(
                            Line2D(
                                start=Point2D(h_sign * p1.X(), p1.Z()),
                                end=Point2D(h_sign * p2.X(), p2.Z()),
                                style=style,
                                layer=layer,
                            )
                        )
                else:
                    # Tessellate and project
                    lines = self._tessellate_curve_vertical(
                        curve, style, layer, use_y_for_horizontal, h_sign
                    )
                    result.extend(lines)

            except Exception:
                continue

        return result

    def _tessellate_curve_vertical(
        self,
        curve,
        style: LineStyle,
        layer: str,
        use_y_for_horizontal: bool = False,
        h_sign: float = 1.0,
        num_segments: int = 32,
    ) -> list[Line2D]:
        """Tessellate a curve for vertical sections.

        Args:
            curve: BRepAdaptor_Curve to tessellate
            style: Line style
            layer: Layer name
            use_y_for_horizontal: If True, use Y for horizontal axis; else use X
            h_sign: Sign multiplier for horizontal axis to match HLR convention
            num_segments: Number of segments for tessellation
        """
        result = []

        first = curve.FirstParameter()
        last = curve.LastParameter()
        step = (last - first) / num_segments

        prev_point = None
        for i in range(num_segments + 1):
            param = first + i * step
            pnt = curve.Value(param)
            if use_y_for_horizontal:
                current = Point2D(h_sign * pnt.Y(), pnt.Z())
            else:
                current = Point2D(h_sign * pnt.X(), pnt.Z())

            if prev_point is not None:
                result.append(Line2D(start=prev_point, end=current, style=style, layer=layer))

            prev_point = current

        return result


# Global section cutter instance
_section_cutter: SectionCutter | None = None


def get_section_cutter() -> SectionCutter:
    """Get the global section cutter instance."""
    global _section_cutter
    if _section_cutter is None:
        _section_cutter = SectionCutter()
    return _section_cutter
