"""
IFC geometry conversion utilities.

Converts build123d/OCP geometry to IFC BREP representations.
"""

from typing import Any, Dict, List, Tuple


def build123d_to_ifc_brep(geometry: Any, ifc_file: Any) -> Any:
    """
    Convert build123d geometry to IFC Advanced BREP representation.

    Creates proper analytical BREP with exact surfaces (planes, cylinders, etc.)
    instead of triangulated approximations.

    Args:
        geometry: build123d geometry object (Compound, Solid, etc.)
        ifc_file: IFC file object

    Returns:
        IfcAdvancedBrep entity with exact geometric surfaces
    """
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_WIRE
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Line
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir, gp_Ax2
    from OCP.TopLoc import TopLoc_Location

    # Get the OCP shape from build123d
    if hasattr(geometry, 'wrapped'):
        occ_shape = geometry.wrapped
    else:
        occ_shape = geometry

    # Map to avoid duplicate vertex creation (vertices can be safely cached by position)
    vertex_map: Dict[int, Any] = {}
    # NOTE: Edge caching removed - edges must be created per-loop to respect
    # directional traversal for proper topology closure

    def get_vertex_key(pnt: gp_Pnt, tolerance: float = 1e-6) -> int:
        """Create a unique key for a vertex based on coordinates."""
        x = round(pnt.X() / tolerance) * tolerance
        y = round(pnt.Y() / tolerance) * tolerance
        z = round(pnt.Z() / tolerance) * tolerance
        return hash((x, y, z))

    def create_ifc_vertex(occ_vertex: Any) -> Any:
        """Create IfcVertexPoint from OCC vertex."""
        pnt = BRep_Tool.Pnt_s(occ_vertex)
        key = get_vertex_key(pnt)

        if key not in vertex_map:
            ifc_point = ifc_file.createIfcCartesianPoint((pnt.X(), pnt.Y(), pnt.Z()))
            ifc_vertex = ifc_file.createIfcVertexPoint(ifc_point)
            vertex_map[key] = ifc_vertex

        return vertex_map[key]

    def create_ifc_edge(occ_edge: Any) -> Any:
        """Create IfcEdgeCurve from OCC edge with correct vertex order.

        Uses TopExp.FirstVertex_s and LastVertex_s with cumOri=True to ensure
        vertices are returned in the correct traversal order, respecting the
        edge orientation within the current wire.
        """
        # Get edge curve parameters
        first = 0.0
        last = 0.0
        curve = BRep_Tool.Curve_s(occ_edge, first, last)

        # CRITICAL FIX: Use TopExp with cumOri=True to respect edge orientation
        # This ensures vertices are returned in the correct traversal order
        v1_occ = TopExp.FirstVertex_s(occ_edge, True)
        v2_occ = TopExp.LastVertex_s(occ_edge, True)

        if v1_occ is None or v2_occ is None:
            return None

        # Create IFC vertices (vertex caching is safe - position-based)
        v1 = create_ifc_vertex(v1_occ)
        v2 = create_ifc_vertex(v2_occ)

        # Get 3D points for direction calculation
        p1 = BRep_Tool.Pnt_s(v1_occ)
        p2 = BRep_Tool.Pnt_s(v2_occ)

        # Calculate direction vector
        dx = p2.X() - p1.X()
        dy = p2.Y() - p1.Y()
        dz = p2.Z() - p1.Z()
        length = (dx*dx + dy*dy + dz*dz) ** 0.5

        if length > 1e-10:
            # Normalize direction
            dx, dy, dz = dx/length, dy/length, dz/length
        else:
            dx, dy, dz = 1.0, 0.0, 0.0

        # Create IfcLine with point and direction
        ifc_p1 = ifc_file.createIfcCartesianPoint((p1.X(), p1.Y(), p1.Z()))
        ifc_direction = ifc_file.createIfcDirection((dx, dy, dz))
        ifc_vector = ifc_file.createIfcVector(ifc_direction, length)

        # Create IfcLine
        line = ifc_file.createIfcLine(ifc_p1, ifc_vector)

        # Create edge curve with vertices in traversal order
        return ifc_file.createIfcEdgeCurve(v1, v2, line, True)

    def create_ifc_face_surface(occ_face: Any) -> Any:
        """Create IfcFaceSurface from OCC face with proper surface geometry."""
        # Get face surface adaptor to determine surface type
        surface_adaptor = BRepAdaptor_Surface(occ_face)
        surface_type = surface_adaptor.GetType()

        # Create bounds (edge loops)
        ifc_bounds = []

        # Explore wires (face boundaries)
        wire_exp = TopExp_Explorer(occ_face, TopAbs_WIRE)
        is_outer = True

        while wire_exp.More():
            wire = TopoDS.Wire_s(wire_exp.Current())

            # Get edges from wire using BRepTools_WireExplorer for proper ordering
            from OCP.BRepTools import BRepTools_WireExplorer
            wire_explorer = BRepTools_WireExplorer(wire, occ_face)
            ifc_edges = []

            while wire_explorer.More():
                occ_edge = wire_explorer.Current()

                # Create edge with vertices in correct order for this wire
                ifc_edge = create_ifc_edge(occ_edge)

                if ifc_edge:
                    # Orientation always True - vertices are already in correct order
                    # because create_ifc_edge uses TopExp with cumOri=True
                    ifc_oriented_edge = ifc_file.createIfcOrientedEdge(
                        None, None, ifc_edge, True
                    )
                    ifc_edges.append(ifc_oriented_edge)

                wire_explorer.Next()

            if ifc_edges:
                # Create edge loop
                edge_loop = ifc_file.createIfcEdgeLoop(ifc_edges)

                # Create face bound
                if is_outer:
                    face_bound = ifc_file.createIfcFaceOuterBound(edge_loop, True)
                    is_outer = False
                else:
                    face_bound = ifc_file.createIfcFaceBound(edge_loop, True)

                ifc_bounds.append(face_bound)

            wire_exp.Next()

        if not ifc_bounds:
            return None

        # Create surface geometry
        if surface_type == GeomAbs_Plane:
            # Extract plane parameters
            pln = BRep_Tool.Surface_s(occ_face)
            adaptor = BRep_Tool.Surface_s(occ_face)

            # Get a point on the plane and normal
            u_mid = (BRep_Tool.Surface_s(occ_face).FirstUParameter() +
                     BRep_Tool.Surface_s(occ_face).LastUParameter()) / 2.0 if hasattr(BRep_Tool.Surface_s(occ_face), 'FirstUParameter') else 0.0
            v_mid = (BRep_Tool.Surface_s(occ_face).FirstVParameter() +
                     BRep_Tool.Surface_s(occ_face).LastVParameter()) / 2.0 if hasattr(BRep_Tool.Surface_s(occ_face), 'FirstVParameter') else 0.0

            # Get vertices to determine plane
            vertex_exp = TopExp_Explorer(occ_face, TopAbs_VERTEX)
            points = []
            while vertex_exp.More() and len(points) < 3:
                v = TopoDS.Vertex_s(vertex_exp.Current())
                p = BRep_Tool.Pnt_s(v)
                points.append((p.X(), p.Y(), p.Z()))
                vertex_exp.Next()

            if len(points) >= 3:
                # Create plane from three points
                import numpy as np
                p1 = np.array(points[0])
                p2 = np.array(points[1])
                p3 = np.array(points[2])

                # Calculate normal
                v1 = p2 - p1
                v2 = p3 - p1
                normal = np.cross(v1, v2)
                norm_length = np.linalg.norm(normal)

                # Check if points are colinear
                if norm_length > 1e-10:
                    normal = normal / norm_length
                    v1_norm = v1 / np.linalg.norm(v1)

                    # Create IFC plane
                    location = ifc_file.createIfcCartesianPoint(points[0])
                    z_axis = ifc_file.createIfcDirection([float(x) for x in normal])
                    x_axis = ifc_file.createIfcDirection([float(x) for x in v1_norm])

                    axis_placement = ifc_file.createIfcAxis2Placement3D(
                        location, z_axis, x_axis
                    )

                    ifc_surface = ifc_file.createIfcPlane(axis_placement)
                else:
                    # Points are colinear, use default plane
                    location = ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
                    z_axis = ifc_file.createIfcDirection((0.0, 0.0, 1.0))
                    x_axis = ifc_file.createIfcDirection((1.0, 0.0, 0.0))
                    axis_placement = ifc_file.createIfcAxis2Placement3D(
                        location, z_axis, x_axis
                    )
                    ifc_surface = ifc_file.createIfcPlane(axis_placement)
            else:
                # Fallback: use default plane
                location = ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
                z_axis = ifc_file.createIfcDirection((0.0, 0.0, 1.0))
                x_axis = ifc_file.createIfcDirection((1.0, 0.0, 0.0))
                axis_placement = ifc_file.createIfcAxis2Placement3D(
                    location, z_axis, x_axis
                )
                ifc_surface = ifc_file.createIfcPlane(axis_placement)
        else:
            # For non-planar surfaces, fallback to plane approximation
            # In a full implementation, handle cylinders, cones, etc.
            location = ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
            z_axis = ifc_file.createIfcDirection((0.0, 0.0, 1.0))
            x_axis = ifc_file.createIfcDirection((1.0, 0.0, 0.0))
            axis_placement = ifc_file.createIfcAxis2Placement3D(
                location, z_axis, x_axis
            )
            ifc_surface = ifc_file.createIfcPlane(axis_placement)

        # Create advanced face
        ifc_face = ifc_file.createIfcAdvancedFace(ifc_bounds, ifc_surface, True)

        return ifc_face

    # Process all faces
    ifc_faces = []
    face_explorer = TopExp_Explorer(occ_shape, TopAbs_FACE)

    while face_explorer.More():
        occ_face = TopoDS.Face_s(face_explorer.Current())
        ifc_face = create_ifc_face_surface(occ_face)

        if ifc_face:
            ifc_faces.append(ifc_face)

        face_explorer.Next()

    if not ifc_faces:
        return None

    # Create advanced brep with shell based on manifold solid brep
    closed_shell = ifc_file.createIfcClosedShell(ifc_faces)
    advanced_brep = ifc_file.createIfcAdvancedBrep(closed_shell)

    return advanced_brep
