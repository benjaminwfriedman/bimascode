"""
Room/Space element class for BIM as Code.

This module implements rooms/spaces for spatial program definition.
Rooms are defined by boundary polygons and compute area/volume.
"""

from typing import List, Tuple, Optional, TYPE_CHECKING
from bimascode.core.element import Element
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, normalize_length

if TYPE_CHECKING:
    pass


class Room(Element):
    """
    A room/space element for spatial program definition.

    Rooms are defined by boundary polygons and belong to a level.
    They compute area and volume based on their boundary and floor-to-ceiling height.

    Note: For Sprint 4 (v1.0), room boundaries are manually specified.
    Auto-detection from enclosing walls is P1 (v1.1) scope.
    """

    def __init__(
        self,
        name: str,
        number: str,
        boundary: List[Tuple[float, float]],
        level: Level,
        floor_to_ceiling_height: Optional[Length | float] = None,
        floor_finish: Optional[str] = None,
        wall_finish: Optional[str] = None,
        ceiling_finish: Optional[str] = None,
        description: Optional[str] = None
    ):
        """
        Create a room.

        Args:
            name: Room name (e.g., "Office", "Kitchen")
            number: Room number (e.g., "101", "A-201")
            boundary: List of (x, y) coordinates defining room boundary in mm
            level: Level this room belongs to
            floor_to_ceiling_height: Height from floor to ceiling (defaults to 2700mm)
            floor_finish: Floor finish description
            wall_finish: Wall finish description
            ceiling_finish: Ceiling finish description
            description: Optional room description
        """
        super().__init__(name=name, description=description)

        self.number = number
        self._boundary = boundary
        self.level = level

        # Set floor-to-ceiling height
        if floor_to_ceiling_height is None:
            self._floor_to_ceiling_height = 2700.0  # Default ceiling height
        else:
            self._floor_to_ceiling_height = normalize_length(floor_to_ceiling_height).mm

        # Finish parameters
        self.floor_finish = floor_finish
        self.wall_finish = wall_finish
        self.ceiling_finish = ceiling_finish

        # Register with level
        if hasattr(level, 'add_element'):
            level.add_element(self)

    @property
    def boundary(self) -> List[Tuple[float, float]]:
        """Get room boundary polygon."""
        return self._boundary.copy()

    @property
    def floor_to_ceiling_height(self) -> float:
        """Get floor-to-ceiling height in millimeters."""
        return self._floor_to_ceiling_height

    @property
    def floor_to_ceiling_height_m(self) -> float:
        """Get floor-to-ceiling height in meters."""
        return self._floor_to_ceiling_height / 1000.0

    @property
    def area(self) -> float:
        """
        Calculate room area in square millimeters.

        Uses the Shoelace formula (also known as the surveyor's formula)
        for computing polygon area.

        Returns:
            Room area in mm²
        """
        boundary = self._boundary
        if len(boundary) < 3:
            return 0.0

        # Shoelace formula
        area = 0.0
        n = len(boundary)
        for i in range(n):
            j = (i + 1) % n
            area += boundary[i][0] * boundary[j][1]
            area -= boundary[j][0] * boundary[i][1]

        return abs(area) / 2.0

    @property
    def area_m2(self) -> float:
        """Get room area in square meters."""
        return self.area / 1_000_000.0

    @property
    def area_sqft(self) -> float:
        """Get room area in square feet."""
        return self.area_m2 * 10.7639

    @property
    def volume(self) -> float:
        """
        Calculate room volume in cubic millimeters.

        Volume = Area × Floor-to-Ceiling Height

        Returns:
            Room volume in mm³
        """
        return self.area * self._floor_to_ceiling_height

    @property
    def volume_m3(self) -> float:
        """Get room volume in cubic meters."""
        return self.volume / 1_000_000_000.0

    @property
    def volume_cuft(self) -> float:
        """Get room volume in cubic feet."""
        return self.volume_m3 * 35.3147

    @property
    def perimeter(self) -> float:
        """
        Calculate room perimeter in millimeters.

        Returns:
            Perimeter length in mm
        """
        import math

        boundary = self._boundary
        if len(boundary) < 2:
            return 0.0

        perimeter = 0.0
        n = len(boundary)
        for i in range(n):
            j = (i + 1) % n
            dx = boundary[j][0] - boundary[i][0]
            dy = boundary[j][1] - boundary[i][1]
            perimeter += math.sqrt(dx * dx + dy * dy)

        return perimeter

    @property
    def perimeter_m(self) -> float:
        """Get room perimeter in meters."""
        return self.perimeter / 1000.0

    def get_centroid(self) -> Tuple[float, float]:
        """
        Calculate the centroid of the room boundary.

        Returns:
            (x, y) coordinates of centroid in mm
        """
        boundary = self._boundary
        if len(boundary) == 0:
            return (0.0, 0.0)

        x_sum = sum(p[0] for p in boundary)
        y_sum = sum(p[1] for p in boundary)
        n = len(boundary)

        return (x_sum / n, y_sum / n)

    def get_center_3d(self) -> Tuple[float, float, float]:
        """
        Get the 3D center point of the room.

        Returns:
            (x, y, z) coordinates of room center
        """
        cx, cy = self.get_centroid()
        z = self.level.elevation_mm + self._floor_to_ceiling_height / 2
        return (cx, cy, z)

    def set_boundary(self, boundary: List[Tuple[float, float]]) -> None:
        """
        Set the room boundary.

        Args:
            boundary: List of (x, y) coordinates in mm
        """
        self._boundary = boundary

    def set_floor_to_ceiling_height(self, height: Length | float) -> None:
        """
        Set the floor-to-ceiling height.

        Args:
            height: New height value
        """
        self._floor_to_ceiling_height = normalize_length(height).mm

    def to_ifc(self, ifc_file, ifc_building_storey):
        """
        Export room to IFC as IfcSpace.

        Creates an IfcSpace with:
        - Geometry representation
        - Base quantities (area, volume)
        - Property sets for finishes

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey to place room in

        Returns:
            IfcSpace entity
        """
        # Create IfcSpace
        ifc_space = ifc_file.create_entity(
            "IfcSpace",
            GlobalId=self.guid,
            Name=f"{self.number} - {self.name}",
            Description=self.description,
            LongName=self.name,
            PredefinedType="SPACE"
        )

        # Set placement at room centroid
        centroid = self.get_centroid()
        location = ifc_file.createIfcCartesianPoint((float(centroid[0]), float(centroid[1]), 0.0))

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0))
        )

        local_placement = ifc_file.createIfcLocalPlacement(
            ifc_building_storey.ObjectPlacement,
            axis_placement
        )

        ifc_space.ObjectPlacement = local_placement

        # Create boundary representation as polygon
        if len(self._boundary) >= 3:
            # Create 2D polyline for boundary
            points = [ifc_file.createIfcCartesianPoint((float(p[0] - centroid[0]), float(p[1] - centroid[1])))
                     for p in self._boundary]
            # Close the polyline
            points.append(points[0])

            polyline = ifc_file.createIfcPolyline(points)

            # Create arbitrary profile
            profile = ifc_file.create_entity(
                "IfcArbitraryClosedProfileDef",
                ProfileType="AREA",
                ProfileName=f"Room_{self.number}",
                OuterCurve=polyline
            )

            # Create extruded solid
            direction = ifc_file.createIfcDirection((0.0, 0.0, 1.0))
            extruded_solid = ifc_file.create_entity(
                "IfcExtrudedAreaSolid",
                SweptArea=profile,
                Position=ifc_file.createIfcAxis2Placement3D(
                    ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                    None,
                    None
                ),
                ExtrudedDirection=direction,
                Depth=float(self._floor_to_ceiling_height)
            )

            # Create shape representation
            shape_representation = ifc_file.createIfcShapeRepresentation(
                ifc_file.by_type("IfcGeometricRepresentationContext")[0],
                "Body",
                "SweptSolid",
                [extruded_solid]
            )

            product_shape = ifc_file.createIfcProductDefinitionShape(
                None,
                None,
                [shape_representation]
            )

            ifc_space.Representation = product_shape

        # Add base quantities
        area_quantity = ifc_file.create_entity(
            "IfcQuantityArea",
            Name="NetFloorArea",
            AreaValue=float(self.area_m2)
        )

        volume_quantity = ifc_file.create_entity(
            "IfcQuantityVolume",
            Name="NetVolume",
            VolumeValue=float(self.volume_m3)
        )

        height_quantity = ifc_file.create_entity(
            "IfcQuantityLength",
            Name="Height",
            LengthValue=float(self._floor_to_ceiling_height / 1000.0)
        )

        perimeter_quantity = ifc_file.create_entity(
            "IfcQuantityLength",
            Name="GrossPerimeter",
            LengthValue=float(self.perimeter_m)
        )

        element_quantity = ifc_file.create_entity(
            "IfcElementQuantity",
            GlobalId=self._generate_guid(),
            Name="BaseQuantities",
            Quantities=[area_quantity, volume_quantity, height_quantity, perimeter_quantity]
        )

        ifc_file.createIfcRelDefinesByProperties(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_space],
            element_quantity
        )

        # Add finish property set if any finishes are defined
        finish_properties = []

        if self.floor_finish:
            finish_properties.append(ifc_file.create_entity(
                "IfcPropertySingleValue",
                Name="FloorFinish",
                NominalValue=ifc_file.create_entity("IfcText", self.floor_finish)
            ))

        if self.wall_finish:
            finish_properties.append(ifc_file.create_entity(
                "IfcPropertySingleValue",
                Name="WallFinish",
                NominalValue=ifc_file.create_entity("IfcText", self.wall_finish)
            ))

        if self.ceiling_finish:
            finish_properties.append(ifc_file.create_entity(
                "IfcPropertySingleValue",
                Name="CeilingFinish",
                NominalValue=ifc_file.create_entity("IfcText", self.ceiling_finish)
            ))

        if finish_properties:
            finish_pset = ifc_file.create_entity(
                "IfcPropertySet",
                GlobalId=self._generate_guid(),
                Name="Pset_SpaceFinishes",
                HasProperties=finish_properties
            )

            ifc_file.createIfcRelDefinesByProperties(
                self._generate_guid(),
                self.level.building._ifc_owner_history,
                None,
                None,
                [ifc_space],
                finish_pset
            )

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"Room{self.number}Container",
            None,
            [ifc_space],
            ifc_building_storey
        )

        return ifc_space

    def to_dict(self) -> dict:
        """
        Convert room to dictionary for schedule generation.

        Returns:
            Dictionary with room properties
        """
        return {
            "number": self.number,
            "name": self.name,
            "level": self.level.name,
            "area_m2": round(self.area_m2, 2),
            "area_sqft": round(self.area_sqft, 2),
            "volume_m3": round(self.volume_m3, 2),
            "height_m": round(self.floor_to_ceiling_height_m, 2),
            "perimeter_m": round(self.perimeter_m, 2),
            "floor_finish": self.floor_finish or "",
            "wall_finish": self.wall_finish or "",
            "ceiling_finish": self.ceiling_finish or ""
        }

    def __repr__(self) -> str:
        return (
            f"Room(number='{self.number}', name='{self.name}', "
            f"area={self.area_m2:.2f}m², volume={self.volume_m3:.2f}m³)"
        )
