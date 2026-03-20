"""
Door element class for BIM as Code.

Doors are hosted in walls and create openings (voids) in their host.
They define position along the wall and sill height.
"""

from typing import Optional, TYPE_CHECKING
from bimascode.core.type_instance import ElementInstance
from bimascode.utils.units import Length, normalize_length
import math

if TYPE_CHECKING:
    from bimascode.architecture.door_type import DoorType
    from bimascode.architecture.wall import Wall


class Door(ElementInstance):
    """
    A door element hosted in a wall.

    Doors are positioned along a wall by an offset from the wall's
    start point and a sill height (typically 0 for doors).
    """

    def __init__(
        self,
        door_type: 'DoorType',
        host_wall: 'Wall',
        offset: Length | float,
        sill_height: Length | float = 0.0,
        name: Optional[str] = None
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
        if hasattr(host_wall, 'add_hosted_element'):
            host_wall.add_hosted_element(self)

    @property
    def host_wall(self) -> 'Wall':
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
            ifc_file.createIfcDirection((1.0, 0.0, 0.0))
        )

        opening_placement = ifc_file.createIfcLocalPlacement(
            ifc_wall.ObjectPlacement,
            opening_axis_placement
        )

        # Create opening element
        ifc_opening = ifc_file.create_entity(
            "IfcOpeningElement",
            GlobalId=self._generate_guid(),
            OwnerHistory=building._ifc_owner_history,
            Name=f"{self.name}_Opening",
            Description="Door opening",
            ObjectPlacement=opening_placement,
            PredefinedType="OPENING"
        )

        # Create opening geometry (void box)
        opening_geom = self.get_opening_geometry()
        if opening_geom:
            # Create a simple box representation for the opening
            opening_box = ifc_file.create_entity(
                "IfcBoundingBox",
                Corner=ifc_file.createIfcCartesianPoint((-self.width/2, -wall.width/2 - 1, -self.height/2)),
                XDim=self.width,
                YDim=wall.width + 2,
                ZDim=self.height
            )

            box_representation = ifc_file.createIfcShapeRepresentation(
                ifc_file.by_type("IfcGeometricRepresentationContext")[0],
                "Body",
                "BoundingBox",
                [opening_box]
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
            ifc_opening
        )

        # Create door element
        # Door placement is at the bottom-left corner of the frame
        door_location = ifc_file.createIfcCartesianPoint(
            (float(offset), 0.0, float(sill))
        )

        door_axis_placement = ifc_file.createIfcAxis2Placement3D(
            door_location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0))
        )

        door_placement = ifc_file.createIfcLocalPlacement(
            ifc_wall.ObjectPlacement,
            door_axis_placement
        )

        # Map operation type
        operation_map = {
            "SINGLE_SWING_LEFT": "SINGLE_SWING_LEFT",
            "SINGLE_SWING_RIGHT": "SINGLE_SWING_RIGHT",
            "DOUBLE_DOOR_SINGLE_SWING": "DOUBLE_DOOR_SINGLE_SWING",
        }

        ifc_door = ifc_file.create_entity(
            "IfcDoor",
            GlobalId=self.guid,
            OwnerHistory=building._ifc_owner_history,
            Name=self.name,
            Description=f"{self.type.name} door",
            ObjectPlacement=door_placement,
            OverallHeight=self.height,
            OverallWidth=self.width,
            PredefinedType="DOOR"
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
                    [ifc_brep]
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
            ifc_door
        )

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            building._ifc_owner_history,
            f"Door{self.name}Container",
            None,
            [ifc_door],
            ifc_building_storey
        )

        # Associate with door type
        door_type_ifc = self.type.to_ifc(ifc_file)
        ifc_file.createIfcRelDefinesByType(
            self._generate_guid(),
            building._ifc_owner_history,
            None,
            None,
            [ifc_door],
            door_type_ifc
        )

        return ifc_door

    def __repr__(self) -> str:
        return (
            f"Door(name='{self.name}', type='{self.type.name}', "
            f"offset={self.offset:.1f}mm, host='{self._host_wall.name}')"
        )
