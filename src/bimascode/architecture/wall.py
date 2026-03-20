"""
Wall element class for BIM as Code.

This module implements straight walls with support for hosted elements
(doors, windows) and wall joins.
"""

from typing import Tuple, Optional, List, TYPE_CHECKING
from bimascode.core.type_instance import ElementInstance
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, normalize_length
import math

if TYPE_CHECKING:
    from bimascode.architecture.door import Door
    from bimascode.architecture.window import Window


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

    def __repr__(self) -> str:
        return (
            f"Wall(name='{self.name}', type='{self.type.name}', "
            f"length={self.length:.1f}mm, height={self.height:.1f}mm)"
        )
