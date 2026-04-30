"""Debug rendering utilities for generating visual debug images.

These utilities help visualize 2D views and 3D models with element highlighting,
useful for debugging and verification.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from bimascode.drawing.view_base import ViewResult


def render_2d_debug(
    view_result: "ViewResult",
    output_path: str | Path,
    highlight_layers: dict[str, tuple[int, int, int]] | None = None,
    highlight_elements: dict[str, tuple[int, int, int]] | None = None,
    title: str = "2D Debug View",
    img_size: tuple[int, int] = (800, 600),
    background_color: tuple[int, int, int] = (10, 10, 26),
    show_axes: bool = True,
    show_bounds: bool = True,
) -> Path:
    """Render a 2D ViewResult to a debug PNG image.

    Args:
        view_result: ViewResult from a floor plan, section, or elevation view
        output_path: Path to save the PNG image
        highlight_layers: Dict mapping layer names to RGB colors
                         e.g. {'A-WALL': (255, 0, 0), 'A-DOOR': (0, 255, 0)}
        highlight_elements: Dict mapping element name/type patterns to RGB colors.
                           Matches against primitive metadata if available, or layer names.
                           e.g. {'Wall': (255, 0, 0), 'Door': (0, 255, 0)}
        title: Title text for the image
        img_size: Output image dimensions (width, height)
        background_color: RGB background color
        show_axes: Whether to show XY axis gizmo
        show_bounds: Whether to show bounds information

    Returns:
        Path to the saved image
    """
    output_path = Path(output_path)
    highlight_layers = highlight_layers or {}
    highlight_elements = highlight_elements or {}

    # Get bounds
    bounds = view_result.get_bounds()
    if not bounds:
        # Create empty image
        img = Image.new("RGB", img_size, background_color)
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"{title} - No geometry", fill=(200, 200, 200))
        img.save(output_path)
        return output_path

    min_x, min_y, max_x, max_y = bounds

    # Calculate transform with extra padding for axis gizmo
    padding = 80 if show_axes else 50
    view_w = max_x - min_x
    view_h = max_y - min_y
    scale = min(
        (img_size[0] - padding * 2) / view_w, (img_size[1] - padding * 2) / view_h
    )

    def to_screen(x: float, y: float) -> tuple[float, float]:
        sx = padding + (x - min_x) * scale
        sy = img_size[1] - padding - (y - min_y) * scale
        return (sx, sy)

    def get_color(
        layer: str,
        default: tuple[int, int, int],
        metadata: dict | None = None,
    ) -> tuple[int, int, int]:
        # Check element highlighting first (higher priority)
        if highlight_elements:
            # Check metadata fields if available
            check_strings = [layer]
            if metadata:
                if "element_type" in metadata:
                    check_strings.append(str(metadata["element_type"]))
                if "element_name" in metadata:
                    check_strings.append(str(metadata["element_name"]))
                if "source_element" in metadata:
                    check_strings.append(str(metadata["source_element"]))

            for check_str in check_strings:
                for pattern, color in highlight_elements.items():
                    if pattern.lower() in check_str.lower():
                        return color

        # Fall back to layer-based highlighting
        for pattern, color in highlight_layers.items():
            if pattern.lower() in layer.lower():
                return color
        return default

    # Create image
    img = Image.new("RGB", img_size, background_color)
    draw = ImageDraw.Draw(img)

    # Draw hatches
    for hatch in view_result.hatches:
        if len(hatch.boundary) < 3:
            continue
        pts = [to_screen(p.x, p.y) for p in hatch.boundary]
        color = get_color(hatch.layer, (58, 58, 90))
        # Make hatches semi-transparent by blending
        blend_color = tuple(int(c * 0.5) for c in color)
        draw.polygon(pts, fill=blend_color)

    # Draw polylines
    for pl in view_result.polylines:
        if len(pl.points) < 2:
            continue
        pts = [to_screen(p.x, p.y) for p in pl.points]
        default_color = (224, 224, 224) if pl.style.is_cut else (128, 128, 144)
        color = get_color(pl.layer, default_color)
        width = max(1, int(pl.style.weight.value * 3))
        draw.line(pts, fill=color, width=width)
        if pl.closed and len(pts) > 2:
            draw.line([pts[-1], pts[0]], fill=color, width=width)

    # Draw lines
    for line in view_result.lines:
        p1 = to_screen(line.start.x, line.start.y)
        p2 = to_screen(line.end.x, line.end.y)
        default_color = (224, 224, 224) if line.style.is_cut else (128, 128, 144)
        color = get_color(line.layer, default_color)
        width = max(1, int(line.style.weight.value * 3))
        draw.line([p1, p2], fill=color, width=width)

    # Draw arcs
    for arc in view_result.arcs:
        num_segments = max(8, int(abs(arc.sweep_angle) * arc.radius / 100))
        pts = []
        for i in range(num_segments + 1):
            t = i / num_segments
            angle = arc.start_angle + t * arc.sweep_angle
            x = arc.center.x + arc.radius * math.cos(angle)
            y = arc.center.y + arc.radius * math.sin(angle)
            pts.append(to_screen(x, y))
        default_color = (224, 224, 224) if arc.style.is_cut else (128, 128, 144)
        color = get_color(arc.layer, default_color)
        if len(pts) > 1:
            draw.line(pts, fill=color, width=1)

    # Draw 2D axis gizmo
    if show_axes:
        # Position gizmo in bottom-left corner
        gizmo_origin = (50, img_size[1] - 50)
        axis_length = 40

        # X axis (East) - Red, pointing right
        x_end = (gizmo_origin[0] + axis_length, gizmo_origin[1])
        draw.line([gizmo_origin, x_end], fill=(255, 80, 80), width=3)
        # Arrow head
        draw.polygon(
            [
                x_end,
                (x_end[0] - 8, x_end[1] - 5),
                (x_end[0] - 8, x_end[1] + 5),
            ],
            fill=(255, 80, 80),
        )
        draw.text((x_end[0] + 5, x_end[1] - 7), "X (East)", fill=(255, 80, 80))

        # Y axis (North) - Green, pointing up
        y_end = (gizmo_origin[0], gizmo_origin[1] - axis_length)
        draw.line([gizmo_origin, y_end], fill=(80, 255, 80), width=3)
        # Arrow head
        draw.polygon(
            [
                y_end,
                (y_end[0] - 5, y_end[1] + 8),
                (y_end[0] + 5, y_end[1] + 8),
            ],
            fill=(80, 255, 80),
        )
        draw.text((y_end[0] + 5, y_end[1] - 5), "Y (North)", fill=(80, 255, 80))

        # Origin label
        draw.ellipse(
            [
                gizmo_origin[0] - 4,
                gizmo_origin[1] - 4,
                gizmo_origin[0] + 4,
                gizmo_origin[1] + 4,
            ],
            fill=(200, 200, 200),
        )

    # Title and info
    draw.text((10, 10), title, fill=(200, 200, 200))
    draw.text(
        (10, 28),
        f"Lines: {len(view_result.lines)}, Arcs: {len(view_result.arcs)}, "
        f"Polylines: {len(view_result.polylines)}, Hatches: {len(view_result.hatches)}",
        fill=(150, 150, 150),
    )

    # Legend
    y_offset = 50
    if highlight_elements:
        draw.text((10, y_offset), "Elements:", fill=(150, 150, 150))
        y_offset += 15
        for pattern, color in highlight_elements.items():
            draw.rectangle([15, y_offset, 30, y_offset + 12], fill=color)
            draw.text((35, y_offset - 2), pattern, fill=color)
            y_offset += 18

    if highlight_layers:
        draw.text((10, y_offset), "Layers:", fill=(150, 150, 150))
        y_offset += 15
        for pattern, color in highlight_layers.items():
            draw.rectangle([15, y_offset, 30, y_offset + 12], fill=color)
            draw.text((35, y_offset - 2), pattern, fill=color)
            y_offset += 18

    # Bounds information
    if show_bounds:
        y_offset += 5
        draw.text((10, y_offset), "Bounds:", fill=(150, 150, 150))
        y_offset += 15
        draw.text(
            (15, y_offset), f"X: {min_x:.0f} to {max_x:.0f}", fill=(255, 80, 80)
        )
        y_offset += 15
        draw.text(
            (15, y_offset), f"Y: {min_y:.0f} to {max_y:.0f}", fill=(80, 255, 80)
        )

    img.save(output_path)
    return output_path


def render_3d_debug(
    glb_path: str | Path,
    output_path: str | Path,
    highlight_elements: dict[str, tuple[int, int, int]] | None = None,
    title: str = "3D Debug View",
    show_axes: bool = True,
    img_size: tuple[int, int] = (900, 700),
    background_color: tuple[int, int, int] = (10, 10, 26),
    view_angles: tuple[float, float] = (-45, -35),
    render_mode: str = "solid",
    show_edges: bool = True,
) -> Path:
    """Render a 3D glTF model to a debug PNG image with isometric projection.

    Args:
        glb_path: Path to glTF/GLB file
        output_path: Path to save the PNG image
        highlight_elements: Dict mapping element name patterns to RGB colors
                           e.g. {'Door': (255, 0, 0), 'Wall': (0, 255, 0)}
        title: Title text for the image
        show_axes: Whether to show XYZ axis gizmo
        img_size: Output image dimensions (width, height)
        background_color: RGB background color
        view_angles: (z_rotation, x_rotation) in degrees for isometric view
        render_mode: "solid" for filled faces, "wireframe" for edges only
        show_edges: Whether to show edges on solid faces (only applies to solid mode)

    Returns:
        Path to the saved image
    """
    import trimesh

    glb_path = Path(glb_path)
    output_path = Path(output_path)
    highlight_elements = highlight_elements or {}

    scene = trimesh.load(str(glb_path))

    # Collect geometry with colors
    all_vertices = []
    all_faces = []  # (v0, v1, v2, color, mesh_name)
    mesh_names = []

    vertex_offset = 0
    for name, geom in scene.geometry.items():
        mesh_names.append(name)

        # Get transform
        transform = np.eye(4)
        for node_name in scene.graph.nodes_geometry:
            if scene.graph[node_name][1] == name:
                transform = scene.graph[node_name][0]
                break

        # Transform vertices
        verts = geom.vertices.copy()
        verts_homogeneous = np.hstack([verts, np.ones((len(verts), 1))])
        transformed = (transform @ verts_homogeneous.T).T[:, :3]
        all_vertices.extend(transformed)

        # Determine color for this mesh
        base_color = (80, 80, 100)  # Default gray-blue
        for pattern, highlight_color in highlight_elements.items():
            if pattern.lower() in name.lower():
                base_color = highlight_color
                break

        # Get faces
        for face in geom.faces:
            all_faces.append(
                (
                    face[0] + vertex_offset,
                    face[1] + vertex_offset,
                    face[2] + vertex_offset,
                    base_color,
                    name,
                )
            )

        vertex_offset += len(geom.vertices)

    all_vertices = np.array(all_vertices)

    if len(all_vertices) == 0:
        img = Image.new("RGB", img_size, background_color)
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"{title} - No geometry", fill=(200, 200, 200))
        img.save(output_path)
        return output_path

    model_min = all_vertices.min(axis=0)
    model_max = all_vertices.max(axis=0)

    # Isometric projection
    angle_z = math.radians(view_angles[0])
    angle_x = math.radians(view_angles[1])

    Rz = np.array(
        [
            [math.cos(angle_z), -math.sin(angle_z), 0],
            [math.sin(angle_z), math.cos(angle_z), 0],
            [0, 0, 1],
        ]
    )
    Rx = np.array(
        [
            [1, 0, 0],
            [0, math.cos(angle_x), -math.sin(angle_x)],
            [0, math.sin(angle_x), math.cos(angle_x)],
        ]
    )
    R = Rx @ Rz

    projected = (R @ all_vertices.T).T
    screen_x = projected[:, 0]
    screen_y = projected[:, 1]
    depth = projected[:, 2]  # For depth sorting

    # Axis gizmo points
    axis_length = max(model_max - model_min) * 0.25
    axis_points = [
        R @ np.array([0, 0, 0]),
        R @ np.array([axis_length, 0, 0]),
        R @ np.array([0, axis_length, 0]),
        R @ np.array([0, 0, axis_length]),
    ]

    # Bounds
    all_x = np.concatenate([screen_x, [p[0] for p in axis_points]])
    all_y = np.concatenate([screen_y, [p[1] for p in axis_points]])

    padding = 100
    x_min, x_max = all_x.min(), all_x.max()
    y_min, y_max = all_y.min(), all_y.max()

    scale = (
        min(
            (img_size[0] - 2 * padding) / (x_max - x_min),
            (img_size[1] - 2 * padding) / (y_max - y_min),
        )
        * 0.8
    )

    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    def to_screen(pt):
        x = img_size[0] / 2 + (pt[0] - center_x) * scale
        y = img_size[1] / 2 - (pt[1] - center_y) * scale
        return (x, y)

    # Create image
    img = Image.new("RGB", img_size, background_color)
    draw = ImageDraw.Draw(img)

    if render_mode == "solid":
        # Sort faces by depth (painter's algorithm - draw far faces first)
        face_depths = []
        for f in all_faces:
            avg_depth = (depth[f[0]] + depth[f[1]] + depth[f[2]]) / 3
            face_depths.append((avg_depth, f))
        face_depths.sort(key=lambda x: x[0])  # Sort by depth (far to near)

        # Draw filled faces
        for _, face in face_depths:
            v0, v1, v2, color, name = face
            p0 = to_screen([screen_x[v0], screen_y[v0]])
            p1 = to_screen([screen_x[v1], screen_y[v1]])
            p2 = to_screen([screen_x[v2], screen_y[v2]])

            # Calculate face normal for simple lighting
            edge1 = np.array([screen_x[v1] - screen_x[v0], screen_y[v1] - screen_y[v0]])
            edge2 = np.array([screen_x[v2] - screen_x[v0], screen_y[v2] - screen_y[v0]])
            cross = edge1[0] * edge2[1] - edge1[1] * edge2[0]

            # Simple lighting: faces pointing toward camera are brighter
            if cross > 0:  # Front-facing
                brightness = 1.0
            else:  # Back-facing (slightly darker)
                brightness = 0.7

            # Apply brightness to color
            lit_color = tuple(int(c * brightness) for c in color)

            # Draw filled triangle
            draw.polygon([p0, p1, p2], fill=lit_color)

            # Draw edges if requested
            if show_edges:
                edge_color = tuple(min(255, int(c * 1.3)) for c in color)
                draw.line([p0, p1], fill=edge_color, width=1)
                draw.line([p1, p2], fill=edge_color, width=1)
                draw.line([p2, p0], fill=edge_color, width=1)

    else:  # wireframe mode
        # Collect unique edges
        edges_set = set()
        edge_colors = {}
        for face in all_faces:
            v0, v1, v2, color, name = face
            for e in [(v0, v1), (v1, v2), (v2, v0)]:
                edge = tuple(sorted(e))
                edges_set.add(edge)
                edge_colors[edge] = color

        # Draw edges
        for edge in edges_set:
            p1 = to_screen([screen_x[edge[0]], screen_y[edge[0]]])
            p2 = to_screen([screen_x[edge[1]], screen_y[edge[1]]])
            draw.line([p1, p2], fill=edge_colors[edge], width=1)

    # Draw axis gizmo
    if show_axes:
        origin = to_screen(axis_points[0][:2])
        x_end = to_screen(axis_points[1][:2])
        y_end = to_screen(axis_points[2][:2])
        z_end = to_screen(axis_points[3][:2])

        draw.line([origin, x_end], fill=(255, 80, 80), width=3)
        draw.line([origin, y_end], fill=(80, 255, 80), width=3)
        draw.line([origin, z_end], fill=(80, 80, 255), width=3)

        draw.text((x_end[0] + 10, x_end[1] - 5), "X (East)", fill=(255, 80, 80))
        draw.text((y_end[0] + 10, y_end[1] - 5), "Y (North)", fill=(80, 255, 80))
        draw.text((z_end[0] + 10, z_end[1] - 5), "Z (Up)", fill=(80, 80, 255))

    # Title and mode info
    mode_text = f"[{render_mode}]"
    draw.text((10, 10), f"{title} {mode_text}", fill=(200, 200, 200))

    # Legend for highlighted elements
    y_offset = 35
    for pattern, color in highlight_elements.items():
        draw.rectangle([10, y_offset, 25, y_offset + 12], fill=color)
        draw.text((30, y_offset - 2), pattern, fill=color)
        y_offset += 18

    # Mesh list
    y_offset += 10
    draw.text((10, y_offset), "Meshes:", fill=(150, 150, 150))
    y_offset += 15
    for name in mesh_names:
        color = (80, 80, 100)
        for pattern, c in highlight_elements.items():
            if pattern.lower() in name.lower():
                color = c
                break
        draw.text((15, y_offset), f"- {name}", fill=color)
        y_offset += 15

    # Model bounds
    y_offset += 10
    draw.text((10, y_offset), "Bounds:", fill=(150, 150, 150))
    y_offset += 15
    draw.text(
        (15, y_offset), f"X: {model_min[0]:.0f} to {model_max[0]:.0f}", fill=(255, 80, 80)
    )
    y_offset += 15
    draw.text(
        (15, y_offset), f"Y: {model_min[1]:.0f} to {model_max[1]:.0f}", fill=(80, 255, 80)
    )
    y_offset += 15
    draw.text(
        (15, y_offset), f"Z: {model_min[2]:.0f} to {model_max[2]:.0f}", fill=(80, 80, 255)
    )

    img.save(output_path)
    return output_path


def render_building_debug(
    building,
    output_dir: str | Path,
    level_name: str | None = None,
    highlight_elements: dict[str, tuple[int, int, int]] | None = None,
    highlight_layers: dict[str, tuple[int, int, int]] | None = None,
    render_3d_modes: list[str] | None = None,
) -> dict[str, Path]:
    """Render both 2D floor plan and 3D model debug images for a building.

    Args:
        building: Building object to render
        output_dir: Directory to save debug images
        level_name: Specific level to render (None = first level)
        highlight_elements: Dict for 3D element highlighting
        highlight_layers: Dict for 2D layer highlighting
        render_3d_modes: List of 3D render modes to generate.
                        Options: "solid", "wireframe". Default: ["solid", "wireframe"]

    Returns:
        Dict with paths: {'2d': Path, '3d_solid': Path, '3d_wireframe': Path, 'glb': Path}
    """
    from bimascode.drawing.floor_plan_view import FloorPlanView
    from bimascode.drawing.view_base import ViewRange
    from bimascode.export.gltf_exporter import GLTFExporter
    from bimascode.performance.representation_cache import RepresentationCache
    from bimascode.performance.spatial_index import SpatialIndex

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if render_3d_modes is None:
        render_3d_modes = ["solid", "wireframe"]

    # Find level
    level = None
    for lvl in building.levels:
        if level_name is None or lvl.name == level_name:
            level = lvl
            break

    if level is None:
        raise ValueError(f"Level not found: {level_name}")

    # Generate floor plan
    spatial_index = SpatialIndex()
    for element in level.elements:
        spatial_index.insert(element)
        # Also insert hosted elements (doors, windows)
        if hasattr(element, "hosted_elements"):
            for hosted in element.hosted_elements:
                spatial_index.insert(hosted)

    cache = RepresentationCache()
    view_range = ViewRange(cut_height=1200, top=3000, bottom=0, view_depth=0)
    floor_plan = FloorPlanView(
        name=f"{level.name} - Debug", level=level, view_range=view_range
    )
    view_result = floor_plan.generate(spatial_index, cache)

    # Export glTF
    glb_path = output_dir / "building.glb"
    exporter = GLTFExporter()
    exporter.export(building, str(glb_path))

    # Render 2D
    path_2d = render_2d_debug(
        view_result,
        output_dir / "floor_plan_2d.png",
        highlight_layers=highlight_layers,
        highlight_elements=highlight_elements,
        title=f"2D Floor Plan - {level.name}",
        show_axes=True,
        show_bounds=True,
    )

    result = {"2d": path_2d, "glb": glb_path}

    # Render 3D in each mode
    for mode in render_3d_modes:
        path_3d = render_3d_debug(
            glb_path,
            output_dir / f"building_3d_{mode}.png",
            highlight_elements=highlight_elements,
            title=f"3D Model - {building.name}",
            render_mode=mode,
            show_edges=(mode == "solid"),
        )
        result[f"3d_{mode}"] = path_3d

    return result
