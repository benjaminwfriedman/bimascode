"""
Roof element class for BIM as Code.

Sprint 2: Flat roofs only (with slope for drainage).
Pitched roofs deferred to P1 (v1.1).
"""

from typing import List, Tuple, Optional
from bimascode.core.type_instance import ElementInstance
from bimascode.spatial.level import Level
from bimascode.architecture.floor_type import FloorType
from bimascode.utils.units import Length


class Roof(ElementInstance):
    """
    A flat roof element.

    Roofs are similar to floors but located at the top of a building.
    They support slope for drainage (typically 1-2%).

    Note: Sprint 2 supports flat roofs only. Pitched roofs are P1.
    """

    def __init__(
        self,
        roof_type: FloorType,  # Reuse FloorType for roof assemblies
        boundary: List[Tuple[float, float]],
        level: Level,
        slope: float = 0.0,
        name: Optional[str] = None
    ):
        """
        Create a flat roof.

        Args:
            roof_type: FloorType defining the roof assembly
            boundary: List of (x, y) coordinates defining roof boundary
            level: Level this roof sits on
            slope: Roof slope in degrees (for drainage, typically 1-2%)
            name: Optional name for this roof
        """
        super().__init__(roof_type, name)

        self.level = level

        # Store geometric parameters
        self.set_parameter("boundary", boundary, override=False)
        self.set_parameter("slope", slope, override=False)

        # Register with level
        if hasattr(level, 'add_element'):
            level.add_element(self)

    @property
    def boundary(self) -> List[Tuple[float, float]]:
        """Get roof boundary polygon."""
        return self.get_parameter("boundary")

    @property
    def slope(self) -> float:
        """Get roof slope in degrees."""
        return self.get_parameter("slope")

    @property
    def thickness(self) -> float:
        """Get roof thickness in millimeters."""
        return self.get_parameter("thickness")

    @property
    def thickness_length(self) -> Length:
        """Get roof thickness as Length object."""
        return Length(self.thickness, "mm")

    @property
    def area(self) -> float:
        """
        Calculate roof area in square millimeters.

        Uses the Shoelace formula for polygon area.
        """
        boundary = self.boundary
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
        """Get roof area in square meters."""
        return self.area / 1_000_000.0

    def get_centroid(self) -> Tuple[float, float]:
        """
        Calculate the centroid of the roof boundary.

        Returns:
            (x, y) coordinates of centroid
        """
        boundary = self.boundary
        if len(boundary) == 0:
            return (0.0, 0.0)

        x_sum = sum(p[0] for p in boundary)
        y_sum = sum(p[1] for p in boundary)
        n = len(boundary)

        return (x_sum / n, y_sum / n)

    def get_center_3d(self) -> Tuple[float, float, float]:
        """
        Get the 3D center point of the roof.

        Returns:
            (x, y, z) coordinates of roof center
        """
        cx, cy = self.get_centroid()
        z = self.level.elevation_mm + self.thickness / 2
        return (cx, cy, z)

    def set_boundary(self, boundary: List[Tuple[float, float]]) -> None:
        """
        Set the roof boundary.

        Args:
            boundary: List of (x, y) coordinates
        """
        self.set_parameter("boundary", boundary, override=False)
        self.invalidate_geometry()

    def set_slope(self, slope: float) -> None:
        """
        Set the roof slope.

        Args:
            slope: Slope in degrees (typical drainage slope is 1-2 degrees)
        """
        self.set_parameter("slope", slope, override=False)
        self.invalidate_geometry()

    def add_opening(self, opening_boundary: List[Tuple[float, float]]) -> None:
        """
        Add an opening (skylight, hatch, etc.) in the roof.

        Args:
            opening_boundary: List of (x, y) coordinates for opening

        Note: Full opening support will be implemented in Sprint 3
        """
        openings = self.get_parameter("openings", [])
        openings.append(opening_boundary)
        self.set_parameter("openings", openings, override=False)
        self.invalidate_geometry()

    def to_ifc(self, ifc_file, ifc_building_storey):
        """
        Export roof to IFC.

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey to place roof in

        Returns:
            IfcRoof entity
        """
        # Create roof
        ifc_roof = ifc_file.create_entity(
            "IfcRoof",
            GlobalId=self.guid,
            Name=self.name,
            Description=f"{self.type.name} roof",
            PredefinedType="FLAT_ROOF"
        )

        # Set placement (at level elevation)
        centroid = self.get_centroid()
        location = ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=(centroid[0], centroid[1], 0.0)
        )

        axis_placement = ifc_file.create_entity(
            "IfcAxis2Placement3D",
            Location=location,
            Axis=ifc_file.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
        )

        local_placement = ifc_file.create_entity(
            "IfcLocalPlacement",
            PlacementRelTo=ifc_building_storey.ObjectPlacement,
            RelativePlacement=axis_placement
        )

        ifc_roof.ObjectPlacement = local_placement

        # Associate with building storey
        ifc_file.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=ifc_file.create_entity("IfcGloballyUniqueId", ifc_file.create_guid()).wrappedValue,
            RelatedElements=[ifc_roof],
            RelatingStructure=ifc_building_storey
        )

        # Associate with material layer set
        material_layer_set = self.type.to_ifc(ifc_file)

        ifc_file.create_entity(
            "IfcRelAssociatesMaterial",
            GlobalId=ifc_file.create_entity("IfcGloballyUniqueId", ifc_file.create_guid()).wrappedValue,
            RelatedObjects=[ifc_roof],
            RelatingMaterial=material_layer_set
        )

        return ifc_roof

    def __repr__(self) -> str:
        return (
            f"Roof(name='{self.name}', type='{self.type.name}', "
            f"area={self.area_m2:.2f}m², slope={self.slope:.2f}°)"
        )
