"""
Door element class for BIM as Code.

Doors are hosted in walls and create openings (voids) in their host.
They define position along the wall and sill height.
"""

import math
from typing import TYPE_CHECKING, Union

from bimascode.core.type_instance import ElementInstance
from bimascode.core.world_geometry import HostedElementMixin
from bimascode.performance.bounding_box import BoundingBox
from bimascode.utils.units import Length, normalize_length

if TYPE_CHECKING:
    from build123d import Location

    from bimascode.architecture.door_type import DoorType
    from bimascode.architecture.wall import Wall
    from bimascode.drawing.primitives import Arc2D, Hatch2D, Line2D, Polyline2D
    from bimascode.drawing.view_base import ViewRange


class Door(ElementInstance, HostedElementMixin):
    """
    A door element hosted in a wall.

    Doors are positioned along a wall by an offset from the wall's
    start point and a sill height (typically 0 for doors).
    """

    def __init__(
        self,
        door_type: "DoorType",
        host_wall: "Wall",
        offset: Length | float,
        sill_height: Length | float = 0.0,
        name: str | None = None,
    ):
        """
        Create a door.

        Args:
            door_type: DoorType defining the door assembly
            host_wall: Wall that hosts this door
            offset: Distance from wall start point to door start
            sill_height: Height from floor to bottom of door (usually 0)
            name: Optional name for this door
        """
        super().__init__(door_type, name)

        self._host_wall = host_wall

        # Store geometric parameters
        self.set_parameter("offset", normalize_length(offset).mm, override=False)
        self.set_parameter("sill_height", normalize_length(sill_height).mm, override=False)

        # Register with host wall
        if hasattr(host_wall, "add_hosted_element"):
            host_wall.add_hosted_element(self)

    @property
    def host_wall(self) -> "Wall":
        """Get the host wall."""
        return self._host_wall

    @property
    def offset(self) -> float:
        """Get offset from wall start in millimeters."""
        return self.get_parameter("offset")

    @property
    def sill_height(self) -> float:
        """Get sill height in millimeters."""
        return self.get_parameter("sill_height")

    @property
    def width(self) -> float:
        """Get door width in millimeters."""
        return self.type.overall_width

    @property
    def height(self) -> float:
        """Get door height in millimeters."""
        return self.type.overall_height

    @property
    def level(self):
        """Get the level from the host wall."""
        return self._host_wall.level

    def get_opening_geometry(self):
        """
        Get the void geometry for cutting into the host wall.

        Returns:
            build123d Box in wall's local coordinates
        """
        return self.type.create_opening_geometry(self)

    def get_world_position(self):
        """
        Get the door's position in world coordinates.

        Returns:
            (x, y, z) coordinates of door center
        """
        wall = self._host_wall
        wall_start = wall.start_point
        wall_angle = wall.angle

        # Calculate position along wall
        offset = self.offset + self.width / 2

        # Transform to world coordinates
        x = wall_start[0] + offset * math.cos(wall_angle)
        y = wall_start[1] + offset * math.sin(wall_angle)
        z = wall.level.elevation_mm + self.sill_height + self.height / 2

        return (x, y, z)

    def _get_host_transform(self) -> "Location":
        """Get the host wall's world transform.

        Returns:
            Location for wall position/rotation at door's Z elevation
        """
        from build123d import Location

        wall = self._host_wall
        wall_start = wall.start_point
        wall_angle_deg = wall.angle_degrees
        z = wall.level.elevation_mm + self.sill_height

        return Location((wall_start[0], wall_start[1], z), (0, 0, 1), wall_angle_deg)

    def _get_local_transform(self) -> "Location":
        """Get door's position within the host wall.

        Door is positioned by offset along wall and centered in wall thickness.

        Returns:
            Location for door position in wall-local coordinates
        """
        from build123d import Location

        # Door local geometry: origin at bottom-left of frame, extends +X (width), +Y (depth), +Z (height)
        # Door frame_depth is how deep the door is (Y extent in door local coords)
        frame_depth = self.type.frame_depth

        # In wall-local coordinates:
        # - X runs along the wall length (from start to end)
        # - Y runs perpendicular to wall, with Y=0 at the wall centerline
        # - The wall extends from Y = -wall_thickness/2 to Y = +wall_thickness/2
        #
        # The door should be centered in the wall thickness:
        # - Door center Y should be at wall center Y (which is 0 in wall-local)
        # - So door Y ranges from -frame_depth/2 to +frame_depth/2
        # - Door local origin (Y=0) should map to wall-local Y = -frame_depth/2
        y_offset = -frame_depth / 2

        return Location((self.offset, y_offset, 0))

    def set_offset(self, offset: Length | float) -> None:
        """
        Set the offset from wall start.

        Args:
            offset: New offset value
        """
        self.set_parameter("offset", normalize_length(offset).mm, override=False)
        self.invalidate_geometry()
        self._host_wall.invalidate_geometry()

    def set_sill_height(self, sill_height: Length | float) -> None:
        """
        Set the sill height.

        Args:
            sill_height: New sill height value
        """
        self.set_parameter("sill_height", normalize_length(sill_height).mm, override=False)
        self.invalidate_geometry()
        self._host_wall.invalidate_geometry()

    def validate_position(self) -> bool:
        """
        Validate that the door fits within the host wall.

        Returns:
            True if door position is valid
        """
        wall = self._host_wall
        offset = self.offset
        width = self.width
        height = self.height
        sill = self.sill_height

        # Check horizontal bounds
        if offset < 0:
            return False
        if offset + width > wall.length:
            return False

        # Check vertical bounds
        if sill < 0:
            return False
        if sill + height > wall.height:
            return False

        return True

    def to_ifc(self, ifc_file, ifc_building_storey, ifc_wall):
        """
        Export door to IFC.

        Creates:
        - IfcOpeningElement (the void)
        - IfcRelVoidsElement (links opening to wall)
        - IfcDoor (the door element)
        - IfcRelFillsElement (links door to opening)

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey
            ifc_wall: IFC wall entity that hosts this door

        Returns:
            IfcDoor entity
        """
        from bimascode.export.ifc_geometry import build123d_to_ifc_brep

        wall = self._host_wall
        building = wall.level.building

        # Calculate door placement relative to wall
        # Door is placed in wall's local coordinate system
        offset = self.offset
        sill = self.sill_height

        # Create placement for opening (relative to wall)
        opening_location = ifc_file.createIfcCartesianPoint(
            (float(offset + self.width / 2), float(wall.width / 2), float(sill + self.height / 2))
        )

        opening_axis_placement = ifc_file.createIfcAxis2Placement3D(
            opening_location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0)),
        )

        opening_placement = ifc_file.createIfcLocalPlacement(
            ifc_wall.ObjectPlacement, opening_axis_placement
        )

        # Create opening element
        ifc_opening = ifc_file.create_entity(
            "IfcOpeningElement",
            GlobalId=self._generate_guid(),
            OwnerHistory=building._ifc_owner_history,
            Name=f"{self.name}_Opening",
            Description="Door opening",
            ObjectPlacement=opening_placement,
            PredefinedType="OPENING",
        )

        # Create opening geometry (void box)
        opening_geom = self.get_opening_geometry()
        if opening_geom:
            # Create a simple box representation for the opening
            opening_box = ifc_file.create_entity(
                "IfcBoundingBox",
                Corner=ifc_file.createIfcCartesianPoint(
                    (-self.width / 2, -wall.width / 2 - 1, -self.height / 2)
                ),
                XDim=self.width,
                YDim=wall.width + 2,
                ZDim=self.height,
            )

            box_representation = ifc_file.createIfcShapeRepresentation(
                ifc_file.by_type("IfcGeometricRepresentationContext")[0],
                "Body",
                "BoundingBox",
                [opening_box],
            )

            opening_shape = ifc_file.createIfcProductDefinitionShape(
                None, None, [box_representation]
            )
            ifc_opening.Representation = opening_shape

        # Link opening to wall (IfcRelVoidsElement)
        ifc_file.createIfcRelVoidsElement(
            self._generate_guid(),
            building._ifc_owner_history,
            f"{self.name}VoidsWall",
            None,
            ifc_wall,
            ifc_opening,
        )

        # Create door element
        # Door placement is at the bottom-left corner of the frame
        door_location = ifc_file.createIfcCartesianPoint((float(offset), 0.0, float(sill)))

        door_axis_placement = ifc_file.createIfcAxis2Placement3D(
            door_location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0)),
        )

        door_placement = ifc_file.createIfcLocalPlacement(
            ifc_wall.ObjectPlacement, door_axis_placement
        )

        ifc_door = ifc_file.create_entity(
            "IfcDoor",
            GlobalId=self.guid,
            OwnerHistory=building._ifc_owner_history,
            Name=self.name,
            Description=f"{self.type.name} door",
            ObjectPlacement=door_placement,
            OverallHeight=self.height,
            OverallWidth=self.width,
            PredefinedType="DOOR",
        )

        # Create door geometry
        door_geom = self.get_geometry()
        if door_geom:
            ifc_brep = build123d_to_ifc_brep(door_geom, ifc_file)
            if ifc_brep:
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ifc_file.by_type("IfcGeometricRepresentationContext")[0],
                    "Body",
                    "Brep",
                    [ifc_brep],
                )

                product_shape = ifc_file.createIfcProductDefinitionShape(
                    None, None, [shape_representation]
                )
                ifc_door.Representation = product_shape

        # Link door to opening (IfcRelFillsElement)
        ifc_file.createIfcRelFillsElement(
            self._generate_guid(),
            building._ifc_owner_history,
            f"{self.name}FillsOpening",
            None,
            ifc_opening,
            ifc_door,
        )

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            building._ifc_owner_history,
            f"Door{self.name}Container",
            None,
            [ifc_door],
            ifc_building_storey,
        )

        # Associate with door type
        door_type_ifc = self.type.to_ifc(ifc_file)
        ifc_file.createIfcRelDefinesByType(
            self._generate_guid(),
            building._ifc_owner_history,
            None,
            None,
            [ifc_door],
            door_type_ifc,
        )

        return ifc_door

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this door.

        The bounding box is calculated from the door's position
        in world coordinates relative to the host wall.

        Returns:
            BoundingBox encompassing the door geometry
        """
        wall = self._host_wall
        wall_start = wall.start_point
        wall_angle = wall.angle

        # Door position along wall
        offset = self.offset
        width = self.width
        height = self.height
        sill = self.sill_height

        # Calculate bounding box corners in world coordinates
        # Door starts at offset and extends to offset + width along wall
        cos_a = math.cos(wall_angle)
        sin_a = math.sin(wall_angle)

        # Wall thickness for perpendicular extent
        wall_width = wall.width
        half_wall_width = wall_width / 2.0

        # Calculate the four corner points of the door footprint
        x1 = wall_start[0] + offset * cos_a - half_wall_width * sin_a
        y1 = wall_start[1] + offset * sin_a + half_wall_width * cos_a
        x2 = wall_start[0] + (offset + width) * cos_a - half_wall_width * sin_a
        y2 = wall_start[1] + (offset + width) * sin_a + half_wall_width * cos_a
        x3 = wall_start[0] + offset * cos_a + half_wall_width * sin_a
        y3 = wall_start[1] + offset * sin_a - half_wall_width * cos_a
        x4 = wall_start[0] + (offset + width) * cos_a + half_wall_width * sin_a
        y4 = wall_start[1] + (offset + width) * sin_a - half_wall_width * cos_a

        min_x = min(x1, x2, x3, x4)
        max_x = max(x1, x2, x3, x4)
        min_y = min(y1, y2, y3, y4)
        max_y = max(y1, y2, y3, y4)

        # Z coordinates
        base_z = wall.level.elevation_mm + sill
        top_z = base_z + height

        return BoundingBox(min_x, min_y, base_z, max_x, max_y, top_z)

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: "ViewRange",
    ) -> list[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]]:
        """Generate floor plan linework for this door.

        Creates a door swing arc and door panel rectangle.

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters

        Returns:
            List of 2D geometry primitives
        """
        from bimascode.drawing.line_styles import Layer, LineStyle
        from bimascode.drawing.primitives import Arc2D, Line2D, Point2D

        result: list[Line2D | Arc2D | Polyline2D | Hatch2D] = []

        # Check if door is at the cut plane (doors typically start at floor)
        bbox = self.get_bounding_box()
        is_cut = bbox.min_z <= cut_height <= bbox.max_z

        if not is_cut:
            return result

        # Door style (cut lines for openings)
        style = LineStyle.cut_wide()

        wall = self._host_wall
        wall_start = wall.start_point
        wall_angle = wall.angle

        # Calculate door position in world coordinates
        cos_a = math.cos(wall_angle)
        sin_a = math.sin(wall_angle)

        # Door frame corners
        offset = self.offset
        width = self.width

        # Door panel hinge point (at one side of opening)
        hinge_x = wall_start[0] + offset * cos_a
        hinge_y = wall_start[1] + offset * sin_a

        # Door swing point (at other side of opening)
        swing_x = wall_start[0] + (offset + width) * cos_a
        swing_y = wall_start[1] + (offset + width) * sin_a

        # Draw door swing arc (90 degree arc from closed to open position)
        # Arc center is at hinge point, radius is door width
        # Start angle is wall angle, end angle is wall angle + 90 degrees
        swing_arc = Arc2D(
            center=Point2D(hinge_x, hinge_y),
            radius=width,
            start_angle=wall_angle,
            end_angle=wall_angle + math.pi / 2,
            style=LineStyle.visible().with_weight(LineStyle.visible().weight),
            layer=Layer.DOOR,
        )
        result.append(swing_arc)

        # Draw door panel in open position (perpendicular to wall)
        panel_end_x = hinge_x - width * sin_a  # Perpendicular to wall
        panel_end_y = hinge_y + width * cos_a

        panel_line = Line2D(
            start=Point2D(hinge_x, hinge_y),
            end=Point2D(panel_end_x, panel_end_y),
            style=style,
            layer=Layer.DOOR,
        )
        result.append(panel_line)

        # Draw opening threshold lines (sides of the opening)
        half_wall = wall.width / 2.0

        # Left jamb line
        left_jamb = Line2D(
            start=Point2D(hinge_x - half_wall * sin_a, hinge_y + half_wall * cos_a),
            end=Point2D(hinge_x + half_wall * sin_a, hinge_y - half_wall * cos_a),
            style=style,
            layer=Layer.DOOR,
        )
        result.append(left_jamb)

        # Right jamb line
        right_jamb = Line2D(
            start=Point2D(swing_x - half_wall * sin_a, swing_y + half_wall * cos_a),
            end=Point2D(swing_x + half_wall * sin_a, swing_y - half_wall * cos_a),
            style=style,
            layer=Layer.DOOR,
        )
        result.append(right_jamb)

        return result

    def __repr__(self) -> str:
        return (
            f"Door(name='{self.name}', type='{self.type.name}', "
            f"offset={self.offset:.1f}mm, host='{self._host_wall.name}')"
        )
