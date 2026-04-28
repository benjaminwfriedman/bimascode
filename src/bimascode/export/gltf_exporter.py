"""
glTF export functionality for BIM as Code models.

Exports Building geometry to glTF binary format (.glb) for fast web viewing.
Element metadata (GUID, type, name) is embedded in glTF extras for selection/hover.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..spatial.building import Building


# Element type to color mapping (RGB 0-255)
ELEMENT_COLORS = {
    "Wall": (200, 200, 200),  # Light gray
    "Floor": (150, 150, 150),  # Darker gray
    "Roof": (100, 100, 100),  # Dark gray
    "Ceiling": (240, 240, 240),  # White-ish
    "Door": (139, 90, 43),  # Brown
    "Window": (173, 216, 230),  # Light blue
    "Column": (160, 160, 170),  # Steel gray
    "Beam": (160, 160, 170),  # Steel gray
    "Room": (200, 200, 255),  # Light purple (for visualization)
    "RoomSeparator": (255, 200, 200),  # Light red
}

DEFAULT_COLOR = (180, 180, 180)  # Fallback gray


class GLTFExporter:
    """
    Exports BIM as Code models to glTF binary format.

    glTF is a fast-loading 3D format ideal for web viewers. This exporter
    tessellates build123d geometry and outputs .glb files with element
    metadata preserved in mesh extras.
    """

    def __init__(self):
        """Initialize the glTF exporter."""
        self._scene = None

    def export(self, building: "Building", filepath: str | Path) -> None:
        """
        Export a building model to glTF binary file.

        Args:
            building: Building instance to export
            filepath: Output file path (should end in .glb)

        Raises:
            ImportError: If trimesh is not installed
        """
        glb_bytes = self.export_bytes(building)

        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(glb_bytes)

    def export_bytes(self, building: "Building") -> bytes:
        """
        Export a building model to glTF binary in memory.

        Args:
            building: Building instance to export

        Returns:
            glTF binary data as bytes

        Raises:
            ImportError: If trimesh is not installed
        """
        try:
            import trimesh
        except ImportError:
            raise ImportError(
                "trimesh is required for glTF export. "
                "Install it with: pip install bimascode[server]"
            )

        scene = trimesh.Scene()

        # Process each level
        for level in building.levels:
            # Process each element on the level
            for element in level.elements:
                mesh = self._element_to_mesh(element, trimesh)
                if mesh is not None:
                    # Create unique node name
                    element_type = element.__class__.__name__
                    element_name = element.name or element.guid[:8]
                    node_name = f"{element_type}_{element_name}"

                    # Add to scene
                    scene.add_geometry(mesh, node_name=node_name)

                    # Process hosted elements (doors, windows in walls)
                    if hasattr(element, "hosted_elements"):
                        for hosted in element.hosted_elements:
                            hosted_mesh = self._element_to_mesh(hosted, trimesh)
                            if hosted_mesh is not None:
                                hosted_type = hosted.__class__.__name__
                                hosted_name = hosted.name or hosted.guid[:8]
                                hosted_node_name = f"{hosted_type}_{hosted_name}"
                                scene.add_geometry(hosted_mesh, node_name=hosted_node_name)

        # Handle empty scenes
        if len(scene.geometry) == 0:
            # Add a tiny placeholder geometry for empty scenes
            placeholder = trimesh.creation.box(extents=[1, 1, 1])
            placeholder.metadata["type"] = "placeholder"
            placeholder.metadata["guid"] = "empty"
            scene.add_geometry(placeholder, node_name="placeholder")

        # Export to GLB bytes
        return scene.export(file_type="glb")

    def _element_to_mesh(self, element: Any, trimesh) -> Any | None:
        """
        Convert a BIM element to a trimesh mesh.

        Args:
            element: Element with get_world_geometry() method
            trimesh: The trimesh module

        Returns:
            trimesh.Trimesh with metadata, or None if conversion failed
        """
        # Get world geometry
        if not hasattr(element, "get_world_geometry"):
            return None

        try:
            world_geom = element.get_world_geometry()
            if world_geom is None:
                return None
        except Exception:
            # Some elements may not have valid geometry
            return None

        # Tessellate the geometry
        try:
            mesh = self._tessellate_shape(world_geom, trimesh)
            if mesh is None:
                return None
        except Exception:
            return None

        # Get element type for coloring
        element_type = element.__class__.__name__
        color = ELEMENT_COLORS.get(element_type, DEFAULT_COLOR)

        # Apply color as vertex colors (RGBA)
        if hasattr(mesh, "visual"):
            mesh.visual.face_colors = [(*color, 255)] * len(mesh.faces)

        # Store metadata in mesh extras (accessible via mesh.metadata)
        mesh.metadata["guid"] = element.guid
        mesh.metadata["type"] = element_type
        mesh.metadata["name"] = element.name or ""

        # Add level info if available
        if hasattr(element, "level") and element.level is not None:
            mesh.metadata["level"] = element.level.name

        # Add any custom properties
        if hasattr(element, "properties"):
            for key, value in element.properties.items():
                # Only include JSON-serializable values
                if isinstance(value, (str, int, float, bool)):
                    mesh.metadata[f"prop_{key}"] = value

        return mesh

    def _tessellate_shape(self, shape: Any, trimesh) -> Any | None:
        """
        Tessellate a build123d/OCCT shape to a trimesh mesh.

        Args:
            shape: build123d geometry (Part, Solid, Compound)
            trimesh: The trimesh module

        Returns:
            trimesh.Trimesh or None if tessellation failed
        """
        try:
            from OCP.BRep import BRep_Tool
            from OCP.BRepMesh import BRepMesh_IncrementalMesh
            from OCP.TopAbs import TopAbs_FACE
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopLoc import TopLoc_Location
            from OCP.TopoDS import TopoDS
        except ImportError:
            raise ImportError(
                "OCP (OpenCASCADE) is required for tessellation. "
                "This should be installed with build123d."
            )

        # Get the wrapped OCCT shape
        if hasattr(shape, "wrapped"):
            occ_shape = shape.wrapped
        else:
            occ_shape = shape

        # Mesh the shape
        # Linear deflection of 1.0mm, angular deflection 0.5 radians
        mesh = BRepMesh_IncrementalMesh(occ_shape, 1.0, False, 0.5, True)
        mesh.Perform()

        if not mesh.IsDone():
            return None

        # Extract triangles from all faces
        all_vertices = []
        all_faces = []
        vertex_offset = 0

        explorer = TopExp_Explorer(occ_shape, TopAbs_FACE)
        while explorer.More():
            # Cast to TopoDS_Face
            face = TopoDS.Face_s(explorer.Current())
            location = TopLoc_Location()

            triangulation = BRep_Tool.Triangulation_s(face, location)
            if triangulation is None:
                explorer.Next()
                continue

            # Get transformation
            transform = location.Transformation()

            # Extract vertices (OCCT indices are 1-based)
            for i in range(1, triangulation.NbNodes() + 1):
                node = triangulation.Node(i)
                # Apply transformation
                transformed = node.Transformed(transform)
                all_vertices.append([transformed.X(), transformed.Y(), transformed.Z()])

            # Extract triangles (OCCT indices are 1-based)
            for i in range(1, triangulation.NbTriangles() + 1):
                tri = triangulation.Triangle(i)
                n1, n2, n3 = tri.Get()
                # Adjust indices (OCCT is 1-based, trimesh is 0-based)
                all_faces.append(
                    [
                        n1 - 1 + vertex_offset,
                        n2 - 1 + vertex_offset,
                        n3 - 1 + vertex_offset,
                    ]
                )

            vertex_offset += triangulation.NbNodes()
            explorer.Next()

        if not all_vertices or not all_faces:
            return None

        # Create trimesh mesh
        return trimesh.Trimesh(vertices=all_vertices, faces=all_faces)
