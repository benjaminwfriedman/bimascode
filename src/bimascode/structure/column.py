"""
Structural column element class for BIM as Code.

This module implements structural columns with support for grid placement
and IFC export.
"""

from typing import Tuple, Optional, List, Union, TYPE_CHECKING
from bimascode.core.type_instance import ElementInstance
from bimascode.performance.bounding_box import BoundingBox
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, normalize_length
import math

if TYPE_CHECKING:
    from bimascode.structure.column_type import ColumnType
    from bimascode.drawing.view_base import ViewRange
    from bimascode.drawing.primitives import Line2D, Arc2D, Polyline2D, Hatch2D


class StructuralColumn(ElementInstance):
    """
    A structural column element.

    Columns are vertical elements defined by a base point, height, and
    section profile. They belong to a level and extend upward.
    """

    def __init__(
        self,
        column_type: 'ColumnType',
        level: Level,
        position: Tuple[float, float],
        height: Optional[Length | float] = None,
        rotation: float = 0.0,
        name: Optional[str] = None
    ):
        """
        Create a structural column.

        Args:
            column_type: ColumnType defining the section profile
            level: Level this column sits on
            position: (x, y) coordinates of column center
            height: Column height (defaults to level-to-level or 3000mm)
            rotation: Rotation angle in degrees around Z-axis
            name: Optional name for this column
        """
        super().__init__(column_type, name)

        self.level = level

        # Store geometric parameters
        self.set_parameter("position", position, override=False)
        self.set_parameter("rotation", rotation, override=False)

        # Set height (default to 3000mm if not specified)
        if height is None:
            height = 3000.0

        self.set_parameter("height", normalize_length(height).mm, override=False)

        # Register with level
        if hasattr(level, 'add_element'):
            level.add_element(self)

    @property
    def position(self) -> Tuple[float, float]:
        """Get column center position (x, y)."""
        return self.get_parameter("position")

    @property
    def height(self) -> float:
        """Get column height in millimeters."""
        return self.get_parameter("height")

    @property
    def height_length(self) -> Length:
        """Get column height as Length object."""
        return Length(self.height, "mm")

    @property
    def rotation(self) -> float:
        """Get column rotation in degrees."""
        return self.get_parameter("rotation")

    @property
    def rotation_radians(self) -> float:
        """Get column rotation in radians."""
        return math.radians(self.rotation)

    @property
    def width(self) -> float:
        """Get column width from type in millimeters."""
        return self.type.width

    @property
    def depth(self) -> float:
        """Get column depth from type in millimeters."""
        return self.type.depth

    @property
    def area(self) -> float:
        """Get column cross-sectional area in square millimeters."""
        return self.type.area

    @property
    def volume(self) -> float:
        """Get column volume in cubic millimeters."""
        return self.area * self.height

    @property
    def volume_m3(self) -> float:
        """Get column volume in cubic meters."""
        return self.volume / 1_000_000_000.0

    def get_base_center(self) -> Tuple[float, float, float]:
        """
        Get the 3D base center point of the column.

        Returns:
            (x, y, z) coordinates of column base center
        """
        pos = self.position
        z = self.level.elevation_mm
        return (pos[0], pos[1], z)

    def get_top_center(self) -> Tuple[float, float, float]:
        """
        Get the 3D top center point of the column.

        Returns:
            (x, y, z) coordinates of column top center
        """
        pos = self.position
        z = self.level.elevation_mm + self.height
        return (pos[0], pos[1], z)

    def get_center_3d(self) -> Tuple[float, float, float]:
        """
        Get the 3D center point of the column.

        Returns:
            (x, y, z) coordinates of column center
        """
        pos = self.position
        z = self.level.elevation_mm + self.height / 2
        return (pos[0], pos[1], z)

    def set_position(self, position: Tuple[float, float]) -> None:
        """
        Set the column position.

        Args:
            position: (x, y) coordinates
        """
        self.set_parameter("position", position, override=False)
        self.invalidate_geometry()

    def set_height(self, height: Length | float) -> None:
        """
        Set the column height.

        Args:
            height: New column height
        """
        self.set_parameter("height", normalize_length(height).mm, override=False)
        self.invalidate_geometry()

    def set_rotation(self, rotation: float) -> None:
        """
        Set the column rotation.

        Args:
            rotation: Rotation angle in degrees
        """
        self.set_parameter("rotation", rotation, override=False)
        self.invalidate_geometry()

    def to_ifc(self, ifc_file, ifc_building_storey):
        """
        Export column to IFC.

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey to place column in

        Returns:
            IfcColumn entity
        """
        # Create column
        ifc_column = ifc_file.create_entity(
            "IfcColumn",
            GlobalId=self.guid,
            Name=self.name,
            Description=f"{self.type.name} column",
            PredefinedType="COLUMN"
        )

        # Set placement (local to building storey)
        pos = self.position
        location = ifc_file.createIfcCartesianPoint((float(pos[0]), float(pos[1]), 0.0))

        # Create rotation direction
        angle_rad = self.rotation_radians
        x_dir = (math.cos(angle_rad), math.sin(angle_rad), 0.0)

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection(x_dir)
        )

        local_placement = ifc_file.createIfcLocalPlacement(
            ifc_building_storey.ObjectPlacement,
            axis_placement
        )

        ifc_column.ObjectPlacement = local_placement

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

                ifc_column.Representation = product_shape

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"Column{self.name}Container",
            None,
            [ifc_column],
            ifc_building_storey
        )

        # Associate with column type
        ifc_column_type = self.type.to_ifc(ifc_file)
        ifc_file.createIfcRelDefinesByType(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_column],
            ifc_column_type
        )

        # Associate with material if present
        if self.type.material:
            ifc_material = self.type.material.to_ifc(ifc_file)
            ifc_file.createIfcRelAssociatesMaterial(
                self._generate_guid(),
                self.level.building._ifc_owner_history,
                None,
                None,
                [ifc_column],
                ifc_material
            )

        return ifc_column

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this column.

        Takes into account column rotation.

        Returns:
            BoundingBox encompassing the column geometry
        """
        pos = self.position
        width = self.width
        depth = self.depth
        rotation_rad = self.rotation_radians

        # For a rotated rectangle, compute the corners
        cos_r = math.cos(rotation_rad)
        sin_r = math.sin(rotation_rad)
        half_w = width / 2.0
        half_d = depth / 2.0

        # Compute the four corners relative to center
        corners_x = [
            pos[0] + half_w * cos_r - half_d * sin_r,
            pos[0] - half_w * cos_r - half_d * sin_r,
            pos[0] + half_w * cos_r + half_d * sin_r,
            pos[0] - half_w * cos_r + half_d * sin_r,
        ]
        corners_y = [
            pos[1] + half_w * sin_r + half_d * cos_r,
            pos[1] - half_w * sin_r + half_d * cos_r,
            pos[1] + half_w * sin_r - half_d * cos_r,
            pos[1] - half_w * sin_r - half_d * cos_r,
        ]

        min_x = min(corners_x)
        max_x = max(corners_x)
        min_y = min(corners_y)
        max_y = max(corners_y)

        # Z coordinates
        min_z = self.level.elevation_mm
        max_z = min_z + self.height

        return BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: "ViewRange",
    ) -> List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]]:
        """Generate floor plan linework for this column.

        Columns are shown with a rectangular outline and optional X pattern.

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters

        Returns:
            List of 2D geometry primitives
        """
        from bimascode.drawing.primitives import Point2D, Line2D, Polyline2D, Hatch2D
        from bimascode.drawing.line_styles import LineStyle, Layer

        result: List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]] = []

        # Check if column is cut by the section plane
        bbox = self.get_bounding_box()
        is_cut = bbox.min_z <= cut_height <= bbox.max_z

        if is_cut:
            style = LineStyle.cut_heavy()
        else:
            style = LineStyle.visible()

        # Calculate column corners with rotation
        pos = self.position
        width = self.width
        depth = self.depth
        rotation_rad = self.rotation_radians

        cos_r = math.cos(rotation_rad)
        sin_r = math.sin(rotation_rad)
        half_w = width / 2.0
        half_d = depth / 2.0

        # Four corners of the column
        corners = [
            Point2D(
                pos[0] + half_w * cos_r - half_d * sin_r,
                pos[1] + half_w * sin_r + half_d * cos_r,
            ),
            Point2D(
                pos[0] - half_w * cos_r - half_d * sin_r,
                pos[1] - half_w * sin_r + half_d * cos_r,
            ),
            Point2D(
                pos[0] - half_w * cos_r + half_d * sin_r,
                pos[1] - half_w * sin_r - half_d * cos_r,
            ),
            Point2D(
                pos[0] + half_w * cos_r + half_d * sin_r,
                pos[1] + half_w * sin_r - half_d * cos_r,
            ),
        ]

        # Create column outline
        column_outline = Polyline2D(
            points=corners,
            closed=True,
            style=style,
            layer=Layer.COLUMN,
        )
        result.append(column_outline)

        # Add X pattern for cut columns (structural convention)
        if is_cut:
            # Diagonal from corner 0 to corner 2
            diag1 = Line2D(
                start=corners[0],
                end=corners[2],
                style=LineStyle.cut_medium(),
                layer=Layer.COLUMN,
            )
            result.append(diag1)

            # Diagonal from corner 1 to corner 3
            diag2 = Line2D(
                start=corners[1],
                end=corners[3],
                style=LineStyle.cut_medium(),
                layer=Layer.COLUMN,
            )
            result.append(diag2)

        return result

    def __repr__(self) -> str:
        pos = self.position
        return (
            f"StructuralColumn(name='{self.name}', type='{self.type.name}', "
            f"position=({pos[0]:.0f}, {pos[1]:.0f}), height={self.height:.0f}mm)"
        )
