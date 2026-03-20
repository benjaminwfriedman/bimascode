"""
Floor/Slab element class for BIM as Code.

Floors are horizontal elements defined by a boundary polygon.
They can have slope for drainage (flat roofs, accessibility ramps).
"""

from typing import List, Tuple, Optional
from bimascode.core.type_instance import ElementInstance
from bimascode.spatial.level import Level
from bimascode.utils.units import normalize_length, Length
import math


class Floor(ElementInstance):
    """
    A floor/slab element.

    Floors are horizontal elements defined by a boundary polygon.
    They belong to a level and extend upward by their thickness.
    """

    def __init__(
        self,
        floor_type: 'FloorType',
        boundary: List[Tuple[float, float]],
        level: Level,
        slope: float = 0.0,
        name: Optional[str] = None
    ):
        """
        Create a floor.

        Args:
            floor_type: FloorType defining the floor assembly
            boundary: List of (x, y) coordinates defining floor boundary
            level: Level this floor sits on
            slope: Floor slope in degrees (for drainage, ramps, etc.)
            name: Optional name for this floor
        """
        super().__init__(floor_type, name)

        self.level = level

        # Store geometric parameters
        self.set_parameter("boundary", boundary, override=False)
        self.set_parameter("slope", slope, override=False)

        # Register with level
        if hasattr(level, 'add_element'):
            level.add_element(self)

    @property
    def boundary(self) -> List[Tuple[float, float]]:
        """Get floor boundary polygon."""
        return self.get_parameter("boundary")

    @property
    def slope(self) -> float:
        """Get floor slope in degrees."""
        return self.get_parameter("slope")

    @property
    def thickness(self) -> float:
        """Get floor thickness in millimeters."""
        return self.get_parameter("thickness")

    @property
    def thickness_length(self) -> Length:
        """Get floor thickness as Length object."""
        return Length(self.thickness, "mm")

    @property
    def area(self) -> float:
        """
        Calculate floor area in square millimeters.

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
        """Get floor area in square meters."""
        return self.area / 1_000_000.0

    def get_centroid(self) -> Tuple[float, float]:
        """
        Calculate the centroid of the floor boundary.

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
        Get the 3D center point of the floor.

        Returns:
            (x, y, z) coordinates of floor center
        """
        cx, cy = self.get_centroid()
        z = self.level.elevation_mm + self.thickness / 2
        return (cx, cy, z)

    def set_boundary(self, boundary: List[Tuple[float, float]]) -> None:
        """
        Set the floor boundary.

        Args:
            boundary: List of (x, y) coordinates
        """
        self.set_parameter("boundary", boundary, override=False)
        self.invalidate_geometry()

    def set_slope(self, slope: float) -> None:
        """
        Set the floor slope.

        Args:
            slope: Slope in degrees
        """
        self.set_parameter("slope", slope, override=False)
        self.invalidate_geometry()

    def add_opening(self, opening_boundary: List[Tuple[float, float]]) -> None:
        """
        Add an opening (void) in the floor.

        Args:
            opening_boundary: List of (x, y) coordinates for opening

        Note: Full opening support will be implemented in Sprint 3
        """
        # Store openings for future implementation
        openings = self.get_parameter("openings", [])
        openings.append(opening_boundary)
        self.set_parameter("openings", openings, override=False)
        self.invalidate_geometry()

    def to_ifc(self, ifc_file, ifc_building_storey):
        """
        Export floor to IFC.

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey to place floor in

        Returns:
            IfcSlab entity
        """
        # Create slab
        ifc_slab = ifc_file.create_entity(
            "IfcSlab",
            GlobalId=self.guid,
            Name=self.name,
            Description=f"{self.type.name} floor",
            PredefinedType="FLOOR"
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

        ifc_slab.ObjectPlacement = local_placement

        # Associate with building storey
        ifc_file.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=ifc_file.create_entity("IfcGloballyUniqueId", ifc_file.create_guid()).wrappedValue,
            RelatedElements=[ifc_slab],
            RelatingStructure=ifc_building_storey
        )

        # Associate with material layer set
        material_layer_set = self.type.to_ifc(ifc_file)

        ifc_file.create_entity(
            "IfcRelAssociatesMaterial",
            GlobalId=ifc_file.create_entity("IfcGloballyUniqueId", ifc_file.create_guid()).wrappedValue,
            RelatedObjects=[ifc_slab],
            RelatingMaterial=material_layer_set
        )

        return ifc_slab

    def __repr__(self) -> str:
        return (
            f"Floor(name='{self.name}', type='{self.type.name}', "
            f"area={self.area_m2:.2f}m², thickness={self.thickness:.1f}mm)"
        )
