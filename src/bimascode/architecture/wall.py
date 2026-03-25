"""
Wall element class for BIM as Code.

This module implements straight walls with support for hosted elements
(doors, windows) and wall joins.
"""

import math
from typing import TYPE_CHECKING, Union

from bimascode.core.type_instance import ElementInstance
from bimascode.core.world_geometry import FreestandingElementMixin
from bimascode.performance.bounding_box import BoundingBox
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, normalize_length

if TYPE_CHECKING:
    from bimascode.architecture.wall_type import WallType
    from bimascode.drawing.primitives import Arc2D, Hatch2D, Line2D, Polyline2D
    from bimascode.drawing.symbology import ElementSymbology
    from bimascode.drawing.view_base import ViewRange


class Wall(ElementInstance, FreestandingElementMixin):
    """
    A straight wall element.

    Walls are linear elements defined by start and end points.
    They belong to a level and extend upward by a specified height.
    """

    def __init__(
        self,
        wall_type: "WallType",
        start_point: tuple[float, float],
        end_point: tuple[float, float],
        level: Level,
        height: Length | float | None = None,
        structural: bool = False,
        name: str | None = None,
    ):
        """
        Create a wall.

        Args:
            wall_type: WallType defining the wall assembly
            start_point: (x, y) coordinates of wall start point
            end_point: (x, y) coordinates of wall end point
            level: Level this wall sits on
            height: Wall height (defaults to level height or 3000mm)
            structural: If True, wall is structural (shear wall)
            name: Optional name for this wall
        """
        super().__init__(wall_type, name)

        self.level = level

        # Hosted elements (doors, windows)
        self._hosted_elements: list = []

        # Wall join trim adjustments
        self._trim_adjustments: dict = {}

        # Structural flag
        self._structural = structural

        # Store geometric parameters
        self.set_parameter("start_point", start_point, override=False)
        self.set_parameter("end_point", end_point, override=False)

        # Set height (default to 3000mm if not specified)
        if height is None:
            height = 3000.0

        self.set_parameter("height", normalize_length(height).mm, override=False)

        # Register with level
        if hasattr(level, "add_element"):
            level.add_element(self)

    @property
    def start_point(self) -> tuple[float, float]:
        """Get wall start point."""
        return self.get_parameter("start_point")

    @property
    def end_point(self) -> tuple[float, float]:
        """Get wall end point."""
        return self.get_parameter("end_point")

    @property
    def height(self) -> float:
        """Get wall height in millimeters."""
        return self.get_parameter("height")

    @property
    def height_length(self) -> Length:
        """Get wall height as Length object."""
        return Length(self.height, "mm")

    @property
    def length(self) -> float:
        """Get wall length in millimeters."""
        start = self.start_point
        end = self.end_point
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        return math.sqrt(dx * dx + dy * dy)

    @property
    def length_length(self) -> Length:
        """Get wall length as Length object."""
        return Length(self.length, "mm")

    @property
    def width(self) -> float:
        """Get wall width (thickness) in millimeters."""
        return self.get_parameter("width")

    @property
    def width_length(self) -> Length:
        """Get wall width as Length object."""
        return Length(self.width, "mm")

    @property
    def angle(self) -> float:
        """Get wall angle in radians."""
        start = self.start_point
        end = self.end_point
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        return math.atan2(dy, dx)

    @property
    def angle_degrees(self) -> float:
        """Get wall angle in degrees."""
        return math.degrees(self.angle)

    def _get_world_position(self) -> tuple[float, float, float]:
        """Get world position for wall geometry.

        Returns:
            (x, y, z) at wall start point, with Z at level elevation
        """
        start = self.start_point
        return (start[0], start[1], self.level.elevation_mm)

    def _get_world_rotation(self) -> float:
        """Get world rotation for wall geometry.

        Returns:
            Wall angle in degrees
        """
        return self.angle_degrees

    @property
    def structural(self) -> bool:
        """Check if wall is marked as structural (shear wall)."""
        return self._structural

    @structural.setter
    def structural(self, value: bool) -> None:
        """Set the structural flag."""
        self._structural = value

    @property
    def is_structural(self) -> bool:
        """Check if wall has structural layers or is marked as structural."""
        return self._structural or len(self.type.get_structural_layers()) > 0

    @property
    def hosted_elements(self) -> list:
        """Get all hosted elements (doors, windows)."""
        return self._hosted_elements.copy()

    @property
    def openings(self) -> list:
        """Get opening geometries from hosted elements."""
        opening_geoms = []
        for element in self._hosted_elements:
            if hasattr(element, "get_opening_geometry"):
                opening_geoms.append(element.get_opening_geometry())
        return opening_geoms

    def add_hosted_element(self, element) -> None:
        """
        Add a hosted element (door or window) to this wall.

        Args:
            element: Door or Window to host
        """
        if element not in self._hosted_elements:
            self._hosted_elements.append(element)
            self.invalidate_geometry()

    def remove_hosted_element(self, element) -> None:
        """
        Remove a hosted element from this wall.

        Args:
            element: Door or Window to remove
        """
        if element in self._hosted_elements:
            self._hosted_elements.remove(element)
            self.invalidate_geometry()

    def get_midpoint(self) -> tuple[float, float]:
        """
        Get the midpoint of the wall.

        Returns:
            (x, y) coordinates of wall centerpoint
        """
        start = self.start_point
        end = self.end_point
        return ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)

    def get_center_3d(self) -> tuple[float, float, float]:
        """
        Get the 3D center point of the wall.

        Returns:
            (x, y, z) coordinates of wall center
        """
        mid_x, mid_y = self.get_midpoint()
        z = self.level.elevation_mm + self.height / 2
        return (mid_x, mid_y, z)

    def reverse(self) -> None:
        """Reverse the wall direction (swap start and end points)."""
        start = self.start_point
        end = self.end_point
        self.set_parameter("start_point", end, override=False)
        self.set_parameter("end_point", start, override=False)
        self.invalidate_geometry()

    def set_start_point(self, point: tuple[float, float]) -> None:
        """
        Set the wall start point.

        Args:
            point: (x, y) coordinates
        """
        self.set_parameter("start_point", point, override=False)
        self.invalidate_geometry()

    def set_end_point(self, point: tuple[float, float]) -> None:
        """
        Set the wall end point.

        Args:
            point: (x, y) coordinates
        """
        self.set_parameter("end_point", point, override=False)
        self.invalidate_geometry()

    def set_height(self, height: Length | float) -> None:
        """
        Set the wall height.

        Args:
            height: New wall height
        """
        self.set_parameter("height", normalize_length(height).mm, override=False)
        self.invalidate_geometry()

    def to_ifc(self, ifc_file, ifc_building_storey):
        """
        Export wall to IFC.

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey to place wall in

        Returns:
            IfcWall entity
        """
        # Determine predefined type based on structural flag
        predefined_type = "SHEAR" if self._structural else "STANDARD"

        # Create wall
        ifc_wall = ifc_file.create_entity(
            "IfcWall",
            GlobalId=self.guid,
            Name=self.name,
            Description=f"{self.type.name} wall",
            PredefinedType=predefined_type,
        )

        # Set placement (local to building storey)
        start = self.start_point
        location = ifc_file.createIfcCartesianPoint((float(start[0]), float(start[1]), 0.0))

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((math.cos(self.angle), math.sin(self.angle), 0.0)),
        )

        local_placement = ifc_file.createIfcLocalPlacement(
            ifc_building_storey.ObjectPlacement, axis_placement
        )

        ifc_wall.ObjectPlacement = local_placement

        # Create geometry representation using BREP
        geom = self.get_geometry()

        if geom:
            from bimascode.export.ifc_geometry import build123d_to_ifc_brep

            # Convert build123d geometry to IFC BREP
            ifc_brep = build123d_to_ifc_brep(geom, ifc_file)

            if ifc_brep:
                # Create shape representation with BREP
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ifc_file.by_type("IfcGeometricRepresentationContext")[0],
                    "Body",
                    "Brep",
                    [ifc_brep],
                )

                # Create product definition shape
                product_shape = ifc_file.createIfcProductDefinitionShape(
                    None, None, [shape_representation]
                )

                ifc_wall.Representation = product_shape

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"Wall{self.name}Container",
            None,
            [ifc_wall],
            ifc_building_storey,
        )

        # Associate with material layer set
        material_layer_set = self.type.to_ifc(ifc_file)

        # Create material layer set usage
        material_layer_set_usage = ifc_file.create_entity(
            "IfcMaterialLayerSetUsage",
            ForLayerSet=material_layer_set,
            LayerSetDirection="AXIS2",
            DirectionSense="POSITIVE",
            OffsetFromReferenceLine=0.0,
        )

        ifc_file.createIfcRelAssociatesMaterial(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_wall],
            material_layer_set_usage,
        )

        return ifc_wall

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this wall.

        Returns:
            BoundingBox encompassing the wall geometry
        """
        start = self.start_point
        end = self.end_point
        width = self.width
        height = self.height

        # Calculate perpendicular offset for wall thickness
        half_width = width / 2.0

        # Get min/max from start and end points
        min_x = min(start[0], end[0]) - half_width
        max_x = max(start[0], end[0]) + half_width
        min_y = min(start[1], end[1]) - half_width
        max_y = max(start[1], end[1]) + half_width

        # Z coordinates from level elevation
        min_z = self.level.elevation_mm
        max_z = min_z + height

        return BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: "ViewRange",
        symbology: "ElementSymbology | None" = None,
    ) -> list[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]]:
        """Generate floor plan linework for this wall.

        Creates polylines representing the wall outline, accounting for:
        - Wall join trim adjustments at corners
        - Openings from hosted doors and windows

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters
            symbology: Optional symbology settings (None uses AIA defaults)

        Returns:
            List of 2D geometry primitives
        """
        from bimascode.drawing.hatch_patterns import get_hatch_pattern_for_layer
        from bimascode.drawing.line_styles import Layer, LineStyle
        from bimascode.drawing.primitives import Hatch2D, Point2D, Polyline2D
        from bimascode.drawing.symbology import FillMode, get_default_symbology

        # Use provided symbology or get default
        if symbology is None:
            symbology = get_default_symbology("Wall")

        # Check if wall is cut by the section plane
        bbox = self.get_bounding_box()
        is_cut = bbox.min_z <= cut_height <= bbox.max_z

        if not is_cut:
            style = symbology.visible_style or LineStyle.visible()
        else:
            style = symbology.cut_style or LineStyle.cut_heavy()

        # Wall geometry
        start = self.start_point
        end = self.end_point
        half_width = self.width / 2.0
        angle = self.angle
        wall_length = self.length

        # Direction vectors
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Perpendicular offset vectors (left side is positive)
        perp_x = -sin_a * half_width
        perp_y = cos_a * half_width

        # Apply trim adjustments from wall joins
        # start_offset: negative = extend start backwards, positive = trim start forward
        # end_offset: positive = extend end forward, negative = trim end back
        start_offset = 0.0
        end_offset = 0.0
        if hasattr(self, "_trim_adjustments") and self._trim_adjustments:
            start_offset = self._trim_adjustments.get("start_offset", 0.0)
            end_offset = self._trim_adjustments.get("end_offset", 0.0)

        # Adjusted start and end points along centerline
        adj_start_x = start[0] + start_offset * cos_a
        adj_start_y = start[1] + start_offset * sin_a
        adj_end_x = end[0] + end_offset * cos_a
        adj_end_y = end[1] + end_offset * sin_a

        # Collect openings (doors/windows) that are cut by the section plane
        openings = []
        for element in self._hosted_elements:
            elem_bbox = element.get_bounding_box() if hasattr(element, "get_bounding_box") else None
            if elem_bbox and elem_bbox.min_z <= cut_height <= elem_bbox.max_z:
                # Opening is cut - get its position along wall
                offset = element.offset if hasattr(element, "offset") else 0
                width = element.width if hasattr(element, "width") else 0
                openings.append((offset, offset + width))

        # Sort openings by start position
        openings.sort(key=lambda x: x[0])

        result: list[Line2D | Arc2D | Polyline2D | Hatch2D] = []

        # If no openings, draw wall as single polyline
        if not openings:
            corners = [
                Point2D(adj_start_x + perp_x, adj_start_y + perp_y),
                Point2D(adj_end_x + perp_x, adj_end_y + perp_y),
                Point2D(adj_end_x - perp_x, adj_end_y - perp_y),
                Point2D(adj_start_x - perp_x, adj_start_y - perp_y),
            ]
            wall_outline = Polyline2D(
                points=corners,
                closed=True,
                style=style,
                layer=Layer.WALL,
            )
            result.append(wall_outline)
            # Add fill for cut walls based on symbology
            if is_cut:
                if symbology.fill_mode == FillMode.SOLID:
                    # Solid fill hatch using wall outline
                    solid_hatch = Hatch2D(
                        boundary=corners,
                        pattern=None,  # Solid fill
                        layer=Layer.WALL,
                        color=symbology.fill_color or (0, 0, 0),
                    )
                    result.append(solid_hatch)
                elif symbology.show_hatching and symbology.fill_mode == FillMode.MATERIAL:
                    result.extend(
                        self._generate_layer_hatches(
                            adj_start_x,
                            adj_start_y,
                            adj_end_x,
                            adj_end_y,
                            cos_a,
                            sin_a,
                            half_width,
                            get_hatch_pattern_for_layer,
                        )
                    )
        else:
            # Draw wall segments between openings
            # Build list of solid segments: (start_offset, end_offset)
            segments = []
            current_pos = 0.0

            for open_start, open_end in openings:
                if open_start > current_pos:
                    segments.append((current_pos, open_start))
                current_pos = max(current_pos, open_end)

            # Add final segment after last opening
            if current_pos < wall_length:
                segments.append((current_pos, wall_length))

            # Draw each segment as a closed polyline
            for seg_start, seg_end in segments:
                # Account for trim adjustments at wall ends
                actual_start = seg_start
                actual_end = seg_end

                if seg_start == 0:
                    actual_start = start_offset  # May be negative (extension)
                if seg_end == wall_length:
                    actual_end = wall_length + end_offset

                # Segment corners
                s_x = start[0] + actual_start * cos_a
                s_y = start[1] + actual_start * sin_a
                e_x = start[0] + actual_end * cos_a
                e_y = start[1] + actual_end * sin_a

                corners = [
                    Point2D(s_x + perp_x, s_y + perp_y),
                    Point2D(e_x + perp_x, e_y + perp_y),
                    Point2D(e_x - perp_x, e_y - perp_y),
                    Point2D(s_x - perp_x, s_y - perp_y),
                ]
                seg_outline = Polyline2D(
                    points=corners,
                    closed=True,
                    style=style,
                    layer=Layer.WALL,
                )
                result.append(seg_outline)
                # Add fill for cut wall segments based on symbology
                if is_cut:
                    if symbology.fill_mode == FillMode.SOLID:
                        # Solid fill hatch using segment outline
                        solid_hatch = Hatch2D(
                            boundary=corners,
                            pattern=None,  # Solid fill
                            layer=Layer.WALL,
                            color=symbology.fill_color or (0, 0, 0),
                        )
                        result.append(solid_hatch)
                    elif symbology.show_hatching and symbology.fill_mode == FillMode.MATERIAL:
                        result.extend(
                            self._generate_layer_hatches(
                                s_x,
                                s_y,
                                e_x,
                                e_y,
                                cos_a,
                                sin_a,
                                half_width,
                                get_hatch_pattern_for_layer,
                            )
                        )

        return result

    def _generate_layer_hatches(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        cos_a: float,
        sin_a: float,
        half_width: float,
        get_hatch_pattern_for_layer,
    ) -> list:
        """Generate per-layer hatches for a wall segment.

        Creates one hatch per material layer, positioned from exterior to interior.

        Args:
            start_x, start_y: Segment start point on centerline
            end_x, end_y: Segment end point on centerline
            cos_a, sin_a: Direction cosines for wall angle
            half_width: Half of total wall width
            get_hatch_pattern_for_layer: Function to get hatch pattern for a layer

        Returns:
            List of Hatch2D objects, one per layer
        """
        from bimascode.drawing.line_styles import Layer
        from bimascode.drawing.primitives import Hatch2D, Point2D

        hatches = []

        # Current offset from centerline, starting at exterior edge
        current_offset = -half_width

        for layer in self.type.layers:
            layer_thickness = layer.thickness_mm

            # Calculate perpendicular offsets for this layer's edges
            # Exterior edge of this layer
            ext_offset = current_offset
            # Interior edge of this layer
            int_offset = current_offset + layer_thickness

            # Perpendicular vectors for each edge
            ext_perp_x = -sin_a * ext_offset
            ext_perp_y = cos_a * ext_offset
            int_perp_x = -sin_a * int_offset
            int_perp_y = cos_a * int_offset

            # Layer boundary corners (exterior edge first, then interior)
            layer_corners = [
                Point2D(start_x - ext_perp_x, start_y - ext_perp_y),
                Point2D(end_x - ext_perp_x, end_y - ext_perp_y),
                Point2D(end_x - int_perp_x, end_y - int_perp_y),
                Point2D(start_x - int_perp_x, start_y - int_perp_y),
            ]

            # Get material-based hatch pattern
            pattern = get_hatch_pattern_for_layer(layer)

            hatch = Hatch2D(
                boundary=layer_corners,
                pattern=pattern.name,
                scale=pattern.scale,
                rotation=pattern.rotation,
                color=pattern.color,
                layer=Layer.WALL,
            )
            hatches.append(hatch)

            # Move to next layer
            current_offset += layer_thickness

        return hatches

    def __repr__(self) -> str:
        return (
            f"Wall(name='{self.name}', type='{self.type.name}', "
            f"length={self.length:.1f}mm, height={self.height:.1f}mm)"
        )
