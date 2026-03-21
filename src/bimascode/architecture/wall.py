"""
Wall element class for BIM as Code.

This module implements straight walls with support for hosted elements
(doors, windows) and wall joins.
"""

from typing import Tuple, Optional, List, TYPE_CHECKING, Union
from bimascode.core.type_instance import ElementInstance
from bimascode.performance.bounding_box import BoundingBox
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, normalize_length
import math

if TYPE_CHECKING:
    from bimascode.architecture.door import Door
    from bimascode.architecture.window import Window
    from bimascode.drawing.view_base import ViewRange
    from bimascode.drawing.primitives import Line2D, Arc2D, Polyline2D, Hatch2D


class Wall(ElementInstance):
    """
    A straight wall element.

    Walls are linear elements defined by start and end points.
    They belong to a level and extend upward by a specified height.
    """

    def __init__(
        self,
        wall_type: 'WallType',
        start_point: Tuple[float, float],
        end_point: Tuple[float, float],
        level: Level,
        height: Optional[Length | float] = None,
        structural: bool = False,
        name: Optional[str] = None
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
        self._hosted_elements: List = []

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
        if hasattr(level, 'add_element'):
            level.add_element(self)

    @property
    def start_point(self) -> Tuple[float, float]:
        """Get wall start point."""
        return self.get_parameter("start_point")

    @property
    def end_point(self) -> Tuple[float, float]:
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

    def get_world_geometry(self):
        """Get wall geometry transformed to world coordinates.

        The base get_geometry() returns geometry in local wall coordinates
        (X along wall, Y perpendicular, Z up). This method transforms it
        to world coordinates using the wall's position and rotation.

        Returns:
            build123d geometry in world coordinates, or None
        """
        from build123d import Location

        local_geom = self.get_geometry()
        if local_geom is None:
            return None

        # Transform from local to world coordinates:
        # - Translate to wall start point
        # - Rotate by wall angle around Z axis
        start = self.start_point
        angle_deg = self.angle_degrees

        # Create transform: rotate around Z, then translate to start point
        # Location takes (position, axis, angle_degrees)
        world_transform = Location(
            (start[0], start[1], 0),  # Translation to wall start
            (0, 0, 1),                 # Rotation axis (Z)
            angle_deg                  # Rotation angle in degrees
        )

        return local_geom.locate(world_transform)

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
    def hosted_elements(self) -> List:
        """Get all hosted elements (doors, windows)."""
        return self._hosted_elements.copy()

    @property
    def openings(self) -> List:
        """Get opening geometries from hosted elements."""
        opening_geoms = []
        for element in self._hosted_elements:
            if hasattr(element, 'get_opening_geometry'):
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

    def get_midpoint(self) -> Tuple[float, float]:
        """
        Get the midpoint of the wall.

        Returns:
            (x, y) coordinates of wall centerpoint
        """
        start = self.start_point
        end = self.end_point
        return (
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2
        )

    def get_center_3d(self) -> Tuple[float, float, float]:
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

    def set_start_point(self, point: Tuple[float, float]) -> None:
        """
        Set the wall start point.

        Args:
            point: (x, y) coordinates
        """
        self.set_parameter("start_point", point, override=False)
        self.invalidate_geometry()

    def set_end_point(self, point: Tuple[float, float]) -> None:
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
            PredefinedType=predefined_type
        )

        # Set placement (local to building storey)
        start = self.start_point
        location = ifc_file.createIfcCartesianPoint((float(start[0]), float(start[1]), 0.0))

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((math.cos(self.angle), math.sin(self.angle), 0.0))
        )

        local_placement = ifc_file.createIfcLocalPlacement(
            ifc_building_storey.ObjectPlacement,
            axis_placement
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
                    [ifc_brep]
                )

                # Create product definition shape
                product_shape = ifc_file.createIfcProductDefinitionShape(
                    None,
                    None,
                    [shape_representation]
                )

                ifc_wall.Representation = product_shape

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"Wall{self.name}Container",
            None,
            [ifc_wall],
            ifc_building_storey
        )

        # Associate with material layer set
        material_layer_set = self.type.to_ifc(ifc_file)

        # Create material layer set usage
        material_layer_set_usage = ifc_file.create_entity(
            "IfcMaterialLayerSetUsage",
            ForLayerSet=material_layer_set,
            LayerSetDirection="AXIS2",
            DirectionSense="POSITIVE",
            OffsetFromReferenceLine=0.0
        )

        ifc_file.createIfcRelAssociatesMaterial(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_wall],
            material_layer_set_usage
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
    ) -> List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]]:
        """Generate floor plan linework for this wall.

        Creates polylines representing the wall outline, accounting for:
        - Wall join trim adjustments at corners
        - Openings from hosted doors and windows

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters

        Returns:
            List of 2D geometry primitives
        """
        from bimascode.drawing.primitives import Point2D, Line2D, Polyline2D, Hatch2D
        from bimascode.drawing.line_styles import LineStyle, Layer

        # Check if wall is cut by the section plane
        bbox = self.get_bounding_box()
        is_cut = bbox.min_z <= cut_height <= bbox.max_z

        if not is_cut:
            style = LineStyle.visible()
        else:
            style = LineStyle.cut_heavy()

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
        if hasattr(self, '_trim_adjustments') and self._trim_adjustments:
            start_offset = self._trim_adjustments.get('start_offset', 0.0)
            end_offset = self._trim_adjustments.get('end_offset', 0.0)

        # Adjusted start and end points along centerline
        adj_start_x = start[0] + start_offset * cos_a
        adj_start_y = start[1] + start_offset * sin_a
        adj_end_x = end[0] + end_offset * cos_a
        adj_end_y = end[1] + end_offset * sin_a

        # Collect openings (doors/windows) that are cut by the section plane
        openings = []
        for element in self._hosted_elements:
            elem_bbox = element.get_bounding_box() if hasattr(element, 'get_bounding_box') else None
            if elem_bbox and elem_bbox.min_z <= cut_height <= elem_bbox.max_z:
                # Opening is cut - get its position along wall
                offset = element.offset if hasattr(element, 'offset') else 0
                width = element.width if hasattr(element, 'width') else 0
                openings.append((offset, offset + width))

        # Sort openings by start position
        openings.sort(key=lambda x: x[0])

        result: List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]] = []

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
            # Add solid fill for cut walls
            if is_cut:
                hatch = Hatch2D(
                    boundary=corners,
                    pattern="SOLID",
                    scale=1.0,
                    layer=Layer.WALL,
                )
                result.append(hatch)
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
                # Add solid fill for cut wall segments
                if is_cut:
                    hatch = Hatch2D(
                        boundary=corners,
                        pattern="SOLID",
                        scale=1.0,
                        layer=Layer.WALL,
                    )
                    result.append(hatch)

        return result

    def __repr__(self) -> str:
        return (
            f"Wall(name='{self.name}', type='{self.type.name}', "
            f"length={self.length:.1f}mm, height={self.height:.1f}mm)"
        )
