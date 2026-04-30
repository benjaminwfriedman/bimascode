"""DXF file reader for preview server.

Converts DXF files back to ViewResult JSON format that the web viewer expects.
Uses ezdxf library to parse DXF files.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    import ezdxf

    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False


def read_dxf_to_view_data(filepath: str | Path) -> dict[str, Any]:
    """Read a DXF file and convert it to ViewResult JSON format.

    Args:
        filepath: Path to the DXF file

    Returns:
        Dictionary in ViewResult.to_dict() format suitable for the web viewer

    Raises:
        ImportError: If ezdxf is not available
        FileNotFoundError: If file doesn't exist
    """
    if not EZDXF_AVAILABLE:
        raise ImportError("ezdxf is required for DXF reading")

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"DXF file not found: {filepath}")

    doc = ezdxf.readfile(str(filepath))
    msp = doc.modelspace()

    # Initialize ViewResult-compatible structure
    view_data: dict[str, Any] = {
        "view_name": filepath.stem,
        "lines": [],
        "arcs": [],
        "polylines": [],
        "hatches": [],
        "dimensions": [],
        "chain_dimensions": [],
        "text_notes": [],
        "door_tags": [],
        "window_tags": [],
        "room_tags": [],
        "section_symbols": [],
        "element_count": 0,
        "total_geometry_count": 0,
    }

    # Process all entities
    for entity in msp:
        _process_entity(entity, view_data, doc)

    # Count total geometry
    view_data["total_geometry_count"] = (
        len(view_data["lines"])
        + len(view_data["arcs"])
        + len(view_data["polylines"])
        + len(view_data["hatches"])
    )

    return view_data


def _process_entity(entity, view_data: dict, doc) -> None:
    """Process a single DXF entity and add it to view_data."""
    dxftype = entity.dxftype()

    if dxftype == "LINE":
        _process_line(entity, view_data)
    elif dxftype == "ARC":
        _process_arc(entity, view_data)
    elif dxftype == "CIRCLE":
        _process_circle(entity, view_data)
    elif dxftype == "LWPOLYLINE":
        _process_lwpolyline(entity, view_data)
    elif dxftype == "POLYLINE":
        _process_polyline(entity, view_data)
    elif dxftype == "HATCH":
        _process_hatch(entity, view_data)
    elif dxftype == "MTEXT":
        _process_mtext(entity, view_data)
    elif dxftype == "TEXT":
        _process_text(entity, view_data)
    elif dxftype == "INSERT":
        _process_insert(entity, view_data, doc)
    elif dxftype == "DIMENSION":
        _process_dimension(entity, view_data)


def _get_entity_style(entity) -> dict:
    """Extract line style information from an entity."""
    style = {
        "weight": {"name": "MEDIUM", "width_mm": 0.35},
        "type": {"name": "CONTINUOUS", "pattern": []},
        "color": None,
        "is_cut": False,
    }

    # Get lineweight if available
    try:
        lineweight = entity.dxf.lineweight
        if lineweight > 0:
            # DXF lineweight is in 1/100mm
            width_mm = lineweight / 100.0
            style["weight"]["width_mm"] = width_mm
            # Map to weight names
            if width_mm <= 0.15:
                style["weight"]["name"] = "EXTRA_FINE"
            elif width_mm <= 0.2:
                style["weight"]["name"] = "FINE"
            elif width_mm <= 0.3:
                style["weight"]["name"] = "NARROW"
            elif width_mm <= 0.4:
                style["weight"]["name"] = "MEDIUM"
            elif width_mm <= 0.55:
                style["weight"]["name"] = "WIDE"
            else:
                style["weight"]["name"] = "HEAVY"
    except AttributeError:
        pass

    # Get color
    try:
        # Check for true color first
        if hasattr(entity.dxf, "true_color") and entity.dxf.true_color:
            tc = entity.dxf.true_color
            r = (tc >> 16) & 0xFF
            g = (tc >> 8) & 0xFF
            b = tc & 0xFF
            style["color"] = [r, g, b]
        elif hasattr(entity.dxf, "color") and entity.dxf.color is not None:
            # ACI color - convert common ones to RGB
            aci = entity.dxf.color
            aci_to_rgb = {
                1: [255, 0, 0],  # Red
                2: [255, 255, 0],  # Yellow
                3: [0, 255, 0],  # Green
                4: [0, 255, 255],  # Cyan
                5: [0, 0, 255],  # Blue
                6: [255, 0, 255],  # Magenta
                7: [255, 255, 255],  # White
                8: [128, 128, 128],  # Gray
                9: [192, 192, 192],  # Light gray
            }
            if aci in aci_to_rgb:
                style["color"] = aci_to_rgb[aci]
    except AttributeError:
        pass

    # Get linetype
    try:
        linetype = entity.dxf.linetype
        if linetype and linetype.upper() != "BYLAYER" and linetype.upper() != "CONTINUOUS":
            style["type"]["name"] = linetype.upper()
            # Add common patterns
            patterns = {
                "DASHED": [6.0, 3.0],
                "HIDDEN": [3.0, 1.5],
                "CENTER": [12.0, 3.0, 3.0, 3.0],
                "PHANTOM": [12.0, 3.0, 3.0, 3.0, 3.0, 3.0],
            }
            if linetype.upper() in patterns:
                style["type"]["pattern"] = patterns[linetype.upper()]
    except AttributeError:
        pass

    return style


def _get_entity_layer(entity) -> str:
    """Get the layer name for an entity."""
    try:
        return entity.dxf.layer
    except AttributeError:
        return "0"


def _process_line(entity, view_data: dict) -> None:
    """Process a LINE entity."""
    start = entity.dxf.start
    end = entity.dxf.end

    view_data["lines"].append(
        {
            "start": {"x": start.x, "y": start.y},
            "end": {"x": end.x, "y": end.y},
            "style": _get_entity_style(entity),
            "layer": _get_entity_layer(entity),
        }
    )


def _process_arc(entity, view_data: dict) -> None:
    """Process an ARC entity."""
    center = entity.dxf.center
    radius = entity.dxf.radius
    start_angle = math.radians(entity.dxf.start_angle)
    end_angle = math.radians(entity.dxf.end_angle)

    view_data["arcs"].append(
        {
            "center": {"x": center.x, "y": center.y},
            "radius": radius,
            "start_angle": start_angle,
            "end_angle": end_angle,
            "style": _get_entity_style(entity),
            "layer": _get_entity_layer(entity),
        }
    )


def _process_circle(entity, view_data: dict) -> None:
    """Process a CIRCLE entity as a full arc."""
    center = entity.dxf.center
    radius = entity.dxf.radius

    view_data["arcs"].append(
        {
            "center": {"x": center.x, "y": center.y},
            "radius": radius,
            "start_angle": 0,
            "end_angle": 2 * math.pi,
            "style": _get_entity_style(entity),
            "layer": _get_entity_layer(entity),
        }
    )


def _process_lwpolyline(entity, view_data: dict) -> None:
    """Process an LWPOLYLINE entity."""
    points = list(entity.get_points(format="xy"))
    if len(points) < 2:
        return

    is_closed = entity.closed

    view_data["polylines"].append(
        {
            "points": [{"x": p[0], "y": p[1]} for p in points],
            "closed": is_closed,
            "style": _get_entity_style(entity),
            "layer": _get_entity_layer(entity),
        }
    )


def _process_polyline(entity, view_data: dict) -> None:
    """Process a POLYLINE entity (2D or 3D)."""
    try:
        points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
        if len(points) < 2:
            return

        is_closed = entity.is_closed

        view_data["polylines"].append(
            {
                "points": [{"x": p[0], "y": p[1]} for p in points],
                "closed": is_closed,
                "style": _get_entity_style(entity),
                "layer": _get_entity_layer(entity),
            }
        )
    except Exception:
        pass  # Skip problematic polylines


def _process_hatch(entity, view_data: dict) -> None:
    """Process a HATCH entity."""
    try:
        # Get boundary paths
        for path in entity.paths:
            if hasattr(path, "vertices"):
                # Polyline path
                boundary = [{"x": v[0], "y": v[1]} for v in path.vertices]
            elif hasattr(path, "edges"):
                # Edge path - collect edge vertices
                boundary = []
                for edge in path.edges:
                    if hasattr(edge, "start"):
                        boundary.append({"x": edge.start.x, "y": edge.start.y})
                    if hasattr(edge, "end"):
                        boundary.append({"x": edge.end.x, "y": edge.end.y})
            else:
                continue

            if len(boundary) < 3:
                continue

            # Get color
            color = None
            try:
                if hasattr(entity, "rgb") and entity.rgb:
                    color = list(entity.rgb)
                elif hasattr(entity.dxf, "true_color") and entity.dxf.true_color:
                    tc = entity.dxf.true_color
                    color = [(tc >> 16) & 0xFF, (tc >> 8) & 0xFF, tc & 0xFF]
            except Exception:
                pass

            view_data["hatches"].append(
                {
                    "boundary": boundary,
                    "pattern": (
                        entity.dxf.pattern_name if hasattr(entity.dxf, "pattern_name") else "SOLID"
                    ),
                    "scale": getattr(entity.dxf, "pattern_scale", 1.0),
                    "rotation": getattr(entity.dxf, "pattern_angle", 0.0),
                    "color": color,
                    "layer": _get_entity_layer(entity),
                }
            )
    except Exception:
        pass  # Skip problematic hatches


def _process_mtext(entity, view_data: dict) -> None:
    """Process an MTEXT entity."""
    try:
        insert = entity.dxf.insert
        content = entity.text

        # Map attachment point to alignment
        attachment = getattr(entity.dxf, "attachment_point", 1)
        alignment_map = {
            1: "TOP_LEFT",
            2: "TOP_CENTER",
            3: "TOP_RIGHT",
            4: "MIDDLE_LEFT",
            5: "MIDDLE_CENTER",
            6: "MIDDLE_RIGHT",
            7: "BOTTOM_LEFT",
            8: "BOTTOM_CENTER",
            9: "BOTTOM_RIGHT",
        }

        view_data["text_notes"].append(
            {
                "position": {"x": insert.x, "y": insert.y},
                "content": content,
                "height": entity.dxf.char_height,
                "rotation": getattr(entity.dxf, "rotation", 0.0),
                "alignment": alignment_map.get(attachment, "MIDDLE_LEFT"),
                "width": getattr(entity.dxf, "width", 0),
                "layer": _get_entity_layer(entity),
            }
        )
    except Exception:
        pass


def _process_text(entity, view_data: dict) -> None:
    """Process a TEXT entity."""
    try:
        insert = entity.dxf.insert
        content = entity.dxf.text

        view_data["text_notes"].append(
            {
                "position": {"x": insert.x, "y": insert.y},
                "content": content,
                "height": entity.dxf.height,
                "rotation": getattr(entity.dxf, "rotation", 0.0),
                "alignment": "BOTTOM_LEFT",
                "width": 0,
                "layer": _get_entity_layer(entity),
            }
        )
    except Exception:
        pass


def _process_insert(entity, view_data: dict, doc) -> None:
    """Process an INSERT (block reference) entity.

    Attempts to identify tags by block name pattern and extract attributes.
    """
    try:
        block_name = entity.dxf.name
        insert_point = entity.dxf.insert
        rotation = getattr(entity.dxf, "rotation", 0.0)

        # Get attribute values
        attribs = {}
        for attrib in entity.attribs:
            attribs[attrib.dxf.tag] = attrib.dxf.text

        # Determine tag type from block name pattern
        block_lower = block_name.lower()

        if "door" in block_lower or block_name.startswith("DoorTag"):
            # Door tag
            text = attribs.get("MARK", "")
            view_data["door_tags"].append(
                {
                    "insertion_point": {"x": insert_point.x, "y": insert_point.y},
                    "text": text,
                    "rotation": rotation,
                    "style": {"size": 300, "text_height": 100},
                    "layer": _get_entity_layer(entity),
                }
            )
        elif "window" in block_lower or block_name.startswith("WindowTag"):
            # Window tag
            text = attribs.get("MARK", "")
            view_data["window_tags"].append(
                {
                    "insertion_point": {"x": insert_point.x, "y": insert_point.y},
                    "text": text,
                    "rotation": rotation,
                    "style": {"size": 300, "text_height": 100},
                    "layer": _get_entity_layer(entity),
                }
            )
        elif "room" in block_lower or block_name.startswith("RoomTag"):
            # Room tag
            name_text = attribs.get("NAME", "")
            number_text = attribs.get("NUMBER", "")

            # Get actual dimensions from block geometry
            size = 400  # default height
            calculated_width = 600  # default width
            text_height = 100  # default text height

            if block_name in doc.blocks:
                block = doc.blocks[block_name]
                for bent in block:
                    if bent.dxftype() == "LWPOLYLINE":
                        points = list(bent.get_points(format="xy"))
                        if points:
                            xs = [p[0] for p in points]
                            ys = [p[1] for p in points]
                            calculated_width = max(xs) - min(xs)
                            size = max(ys) - min(ys)
                        break
                    elif bent.dxftype() == "CIRCLE":
                        # Circular room tag
                        size = bent.dxf.radius * 2
                        calculated_width = size
                        break

                # Get text height from attribute definitions
                for bent in block:
                    if bent.dxftype() == "ATTDEF":
                        text_height = getattr(bent.dxf, "height", 100)
                        break

            view_data["room_tags"].append(
                {
                    "insertion_point": {"x": insert_point.x, "y": insert_point.y},
                    "name_text": name_text,
                    "number_text": number_text,
                    "text": f"{name_text}\n{number_text}" if name_text or number_text else "",
                    "rotation": rotation,
                    "style": {"size": size, "text_height": text_height},
                    "calculated_width": calculated_width,
                    "layer": _get_entity_layer(entity),
                }
            )
        else:
            # Unknown block - explode it to get geometry
            _explode_block(entity, view_data, doc)

    except Exception:
        pass


def _explode_block(entity, view_data: dict, doc) -> None:
    """Explode a block reference and add its entities to view_data."""
    try:
        # Get the block definition
        block_name = entity.dxf.name
        if block_name not in doc.blocks:
            return

        block = doc.blocks[block_name]
        insert_point = entity.dxf.insert
        scale_x = getattr(entity.dxf, "xscale", 1.0)
        scale_y = getattr(entity.dxf, "yscale", 1.0)
        rotation = math.radians(getattr(entity.dxf, "rotation", 0.0))

        # Transform matrix
        cos_r = math.cos(rotation)
        sin_r = math.sin(rotation)

        def transform_point(x: float, y: float) -> tuple[float, float]:
            """Transform a point from block space to world space."""
            # Scale
            sx = x * scale_x
            sy = y * scale_y
            # Rotate
            rx = sx * cos_r - sy * sin_r
            ry = sx * sin_r + sy * cos_r
            # Translate
            return (rx + insert_point.x, ry + insert_point.y)

        # Process block entities
        for block_entity in block:
            dtype = block_entity.dxftype()

            if dtype == "LINE":
                start = block_entity.dxf.start
                end = block_entity.dxf.end
                t_start = transform_point(start.x, start.y)
                t_end = transform_point(end.x, end.y)
                view_data["lines"].append(
                    {
                        "start": {"x": t_start[0], "y": t_start[1]},
                        "end": {"x": t_end[0], "y": t_end[1]},
                        "style": _get_entity_style(block_entity),
                        "layer": _get_entity_layer(entity),
                    }
                )
            elif dtype == "ARC":
                center = block_entity.dxf.center
                t_center = transform_point(center.x, center.y)
                view_data["arcs"].append(
                    {
                        "center": {"x": t_center[0], "y": t_center[1]},
                        "radius": block_entity.dxf.radius * scale_x,
                        "start_angle": math.radians(block_entity.dxf.start_angle) + rotation,
                        "end_angle": math.radians(block_entity.dxf.end_angle) + rotation,
                        "style": _get_entity_style(block_entity),
                        "layer": _get_entity_layer(entity),
                    }
                )
            elif dtype == "CIRCLE":
                center = block_entity.dxf.center
                t_center = transform_point(center.x, center.y)
                view_data["arcs"].append(
                    {
                        "center": {"x": t_center[0], "y": t_center[1]},
                        "radius": block_entity.dxf.radius * scale_x,
                        "start_angle": 0,
                        "end_angle": 2 * math.pi,
                        "style": _get_entity_style(block_entity),
                        "layer": _get_entity_layer(entity),
                    }
                )
            elif dtype == "LWPOLYLINE":
                points = list(block_entity.get_points(format="xy"))
                if len(points) >= 2:
                    t_points = [transform_point(p[0], p[1]) for p in points]
                    view_data["polylines"].append(
                        {
                            "points": [{"x": p[0], "y": p[1]} for p in t_points],
                            "closed": block_entity.closed,
                            "style": _get_entity_style(block_entity),
                            "layer": _get_entity_layer(entity),
                        }
                    )
    except Exception:
        pass  # Skip problematic blocks


def _process_dimension(entity, view_data: dict) -> None:
    """Process a DIMENSION entity.

    Note: DXF dimensions are complex. We extract basic info but full
    reconstruction would require more work.
    """
    try:
        # Get dimension definition points
        defpoint = entity.dxf.defpoint
        defpoint2 = getattr(entity.dxf, "defpoint2", defpoint)

        # Get text override if any
        text = getattr(entity.dxf, "text", "<>")

        view_data["dimensions"].append(
            {
                "start": {"x": defpoint.x, "y": defpoint.y},
                "end": {"x": defpoint2.x, "y": defpoint2.y},
                "offset": 500,  # Default offset
                "text": text,
                "precision": 0,
                "dimlfac": 1.0,
                "layer": _get_entity_layer(entity),
            }
        )
    except Exception:
        pass
