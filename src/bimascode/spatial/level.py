"""
Level / Building Storey implementation.
"""

from typing import Optional, Union, TYPE_CHECKING

from ..core.element import Element
from ..utils.units import Length, LengthUnit, normalize_length

if TYPE_CHECKING:
    from .building import Building


class Level(Element):
    """
    Represents a horizontal datum plane (building storey) in the BIM model.

    Every element in the model must be associated with a level.
    Maps to IfcBuildingStorey in IFC export.
    """

    def __init__(
        self,
        building: "Building",
        name: str,
        elevation: Union[float, Length],
        description: Optional[str] = None
    ):
        """
        Create a new level.

        Args:
            building: Parent building
            name: Level name (e.g., "Ground Floor", "Level 1")
            elevation: Elevation above project base point
            description: Optional description
        """
        super().__init__(name=name, description=description)

        self.building = building
        self._elevation = normalize_length(elevation, building.length_unit)
        self._elements = []  # Elements hosted on this level

        # Register with building
        building._add_level(self)

    @property
    def elevation(self) -> Length:
        """Get the level elevation as a Length object."""
        return self._elevation

    @property
    def elevation_mm(self) -> float:
        """Get the level elevation in millimeters."""
        return self._elevation.mm

    def set_elevation(self, elevation: Union[float, Length]) -> None:
        """
        Set the level elevation.

        Args:
            elevation: New elevation value
        """
        self._elevation = normalize_length(elevation, self.building.length_unit)

    def add_element(self, element) -> None:
        """
        Add an element to this level.

        Args:
            element: Element to add (Wall, Floor, etc.)
        """
        if element not in self._elements:
            self._elements.append(element)

    @property
    def elements(self):
        """Get all elements on this level."""
        return self._elements.copy()

    def get_walls(self):
        """Get all walls on this level."""
        from bimascode.architecture.wall import Wall
        return [e for e in self._elements if isinstance(e, Wall)]

    def process_wall_joins(self, end_cap_type=None):
        """
        Process wall joins for all walls on this level.

        Detects wall joins (corners, T-junctions, crosses) and calculates
        trim adjustments for clean connections.

        Args:
            end_cap_type: How to trim wall ends (default: FLUSH)
                         Use EndCapType.EXTERIOR to extend walls to outer face
                         Use EndCapType.INTERIOR to trim to inner face
        """
        from bimascode.architecture.wall_joins import (
            detect_and_process_wall_joins,
            EndCapType
        )

        if end_cap_type is None:
            end_cap_type = EndCapType.FLUSH

        walls = self.get_walls()
        if not walls:
            return

        # Detect and process joins
        adjustments = detect_and_process_wall_joins(walls, end_cap_type)

        # Apply adjustments to walls
        for wall, adj in adjustments.items():
            wall._trim_adjustments = adj
            wall.invalidate_geometry()

    def to_ifc(self, ifc_file):
        """
        Export this level to IFC as IfcBuildingStorey.

        Args:
            ifc_file: IfcOpenShell file object

        Returns:
            IfcBuildingStorey instance
        """
        # Create placement at elevation
        elevation_mm = self.elevation_mm
        location = ifc_file.createIfcCartesianPoint((0.0, 0.0, elevation_mm))
        axis = ifc_file.createIfcDirection((0.0, 0.0, 1.0))
        ref_direction = ifc_file.createIfcDirection((1.0, 0.0, 0.0))

        axis3d = ifc_file.createIfcAxis2Placement3D(location, axis, ref_direction)
        placement = ifc_file.createIfcLocalPlacement(
            self.building._ifc_building.ObjectPlacement if hasattr(self.building, '_ifc_building') else None,
            axis3d
        )

        # Create building storey
        storey = ifc_file.createIfcBuildingStorey(
            self.guid,
            self.building._ifc_owner_history,
            self.name,
            self.description,
            None,  # ObjectType
            placement,
            None,  # Representation
            None,  # LongName
            None,  # CompositionType
            elevation_mm  # Elevation
        )

        # Add to building's spatial structure
        ifc_file.createIfcRelAggregates(
            self._generate_guid(),
            self.building._ifc_owner_history,
            f"Building{self.building.name}Container",
            None,
            self.building._ifc_building,
            [storey]
        )

        return storey

    def __repr__(self) -> str:
        return f"Level(name='{self.name}', elevation={self.elevation_mm}mm)"
