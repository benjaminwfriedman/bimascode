"""
Ceiling element class for BIM as Code.

This module implements ceilings as horizontal covering elements
at a specified height above a level.
"""

from typing import List, Tuple, Optional, Union, TYPE_CHECKING
from bimascode.core.type_instance import ElementInstance
from bimascode.core.world_geometry import FreestandingElementMixin
from bimascode.performance.bounding_box import BoundingBox
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, normalize_length

if TYPE_CHECKING:
    from bimascode.architecture.ceiling_type import CeilingType
    from bimascode.drawing.view_base import ViewRange
    from bimascode.drawing.primitives import Line2D, Arc2D, Polyline2D, Hatch2D


class Ceiling(ElementInstance, FreestandingElementMixin):
    """
    A ceiling element.

    Ceilings are horizontal covering elements defined by a boundary polygon
    at a specified height above the level. They belong to a level and extend
    downward by their thickness.
    """

    def __init__(
        self,
        ceiling_type: 'CeilingType',
        boundary: List[Tuple[float, float]],
        level: Level,
        height: Length | float = 2700.0,
        name: Optional[str] = None
    ):
        """
        Create a ceiling.

        Args:
            ceiling_type: CeilingType defining the ceiling assembly
            boundary: List of (x, y) coordinates defining ceiling boundary
            level: Level this ceiling belongs to
            height: Height above level in millimeters (default 2700mm)
            name: Optional name for this ceiling
        """
        super().__init__(ceiling_type, name)

        self.level = level

        # Store geometric parameters
        self.set_parameter("boundary", boundary, override=False)
        self.set_parameter("height", normalize_length(height).mm, override=False)

        # Register with level
        if hasattr(level, 'add_element'):
            level.add_element(self)

    @property
    def boundary(self) -> List[Tuple[float, float]]:
        """Get ceiling boundary polygon."""
        return self.get_parameter("boundary")

    @property
    def height(self) -> float:
        """Get ceiling height above level in millimeters."""
        return self.get_parameter("height")

    @property
    def height_length(self) -> Length:
        """Get ceiling height as Length object."""
        return Length(self.height, "mm")

    @property
    def thickness(self) -> float:
        """Get ceiling thickness in millimeters."""
        return self.type.thickness

    @property
    def thickness_length(self) -> Length:
        """Get ceiling thickness as Length object."""
        return Length(self.thickness, "mm")

    @property
    def elevation(self) -> float:
        """Get absolute ceiling elevation (bottom of ceiling) in millimeters."""
        return self.level.elevation_mm + self.height - self.thickness

    @property
    def top_elevation(self) -> float:
        """Get absolute top of ceiling elevation in millimeters."""
        return self.level.elevation_mm + self.height

    @property
    def area(self) -> float:
        """
        Calculate ceiling area in square millimeters.

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
        """Get ceiling area in square meters."""
        return self.area / 1_000_000.0

    def get_centroid(self) -> Tuple[float, float]:
        """
        Calculate the centroid of the ceiling boundary.

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
        Get the 3D center point of the ceiling.

        Returns:
            (x, y, z) coordinates of ceiling center
        """
        cx, cy = self.get_centroid()
        z = self.elevation + self.thickness / 2
        return (cx, cy, z)

    def _get_world_position(self) -> Tuple[float, float, float]:
        """Get world position for ceiling geometry.

        build123d's Polygon centers vertices at the centroid, so we translate
        by the centroid to restore correct world positioning. Z is at ceiling
        elevation (level + height - thickness).

        Returns:
            (x, y, z) at ceiling centroid, with Z at ceiling elevation
        """
        cx, cy = self.get_centroid()
        return (cx, cy, self.elevation)

    def _get_world_rotation(self) -> float:
        """Get world rotation for ceiling geometry.

        Ceilings have no rotation (horizontal elements).

        Returns:
            0.0 (no rotation)
        """
        return 0.0

    def set_boundary(self, boundary: List[Tuple[float, float]]) -> None:
        """
        Set the ceiling boundary.

        Args:
            boundary: List of (x, y) coordinates
        """
        self.set_parameter("boundary", boundary, override=False)
        self.invalidate_geometry()

    def set_height(self, height: Length | float) -> None:
        """
        Set the ceiling height above level.

        Args:
            height: Height above level in millimeters
        """
        self.set_parameter("height", normalize_length(height).mm, override=False)
        self.invalidate_geometry()

    def to_ifc(self, ifc_file, ifc_building_storey):
        """
        Export ceiling to IFC.

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey to place ceiling in

        Returns:
            IfcCovering entity with CEILING predefined type
        """
        # Create covering (ceiling)
        ifc_covering = ifc_file.create_entity(
            "IfcCovering",
            GlobalId=self.guid,
            Name=self.name,
            Description=f"{self.type.name} ceiling",
            PredefinedType="CEILING"
        )

        # Set placement (at ceiling height above level)
        centroid = self.get_centroid()
        # Position at bottom of ceiling (elevation)
        z_offset = self.height - self.thickness
        location = ifc_file.createIfcCartesianPoint((float(centroid[0]), float(centroid[1]), float(z_offset)))

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0))
        )

        local_placement = ifc_file.createIfcLocalPlacement(
            ifc_building_storey.ObjectPlacement,
            axis_placement
        )

        ifc_covering.ObjectPlacement = local_placement

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

                ifc_covering.Representation = product_shape

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"Ceiling{self.name}Container",
            None,
            [ifc_covering],
            ifc_building_storey
        )

        # Associate with covering type
        ifc_covering_type = self.type.to_ifc(ifc_file)
        ifc_file.createIfcRelDefinesByType(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_covering],
            ifc_covering_type
        )

        # Associate with material if present
        if self.type.material:
            ifc_material = self.type.material.to_ifc(ifc_file)
            ifc_file.createIfcRelAssociatesMaterial(
                self._generate_guid(),
                self.level.building._ifc_owner_history,
                None,
                None,
                [ifc_covering],
                ifc_material
            )

        return ifc_covering

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this ceiling.

        Returns:
            BoundingBox encompassing the ceiling geometry
        """
        return BoundingBox.from_polygon_2d(
            self.boundary,
            self.elevation,  # Bottom of ceiling
            self.top_elevation  # Top of ceiling
        )

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: "ViewRange",
    ) -> List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]]:
        """Generate floor plan linework for this ceiling.

        Ceilings are typically shown in Reflected Ceiling Plans (RCP),
        not standard floor plans. In floor plans, they appear above
        the cut plane with dashed lines (if visible).

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters

        Returns:
            List of 2D geometry primitives
        """
        from bimascode.drawing.primitives import Point2D, Polyline2D
        from bimascode.drawing.line_styles import LineStyle, Layer

        result: List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]] = []

        # Ceilings are above the cut plane - show with dashed above-cut style
        bbox = self.get_bounding_box()

        if bbox.min_z > cut_height:
            # Ceiling is above cut plane - typical case
            style = LineStyle.above_cut()
        elif bbox.max_z < cut_height:
            # Ceiling is below cut plane - unusual, but show as visible
            style = LineStyle.visible()
        else:
            # Ceiling is at cut plane - show as cut
            style = LineStyle.cut_medium()

        # Create polyline from boundary
        boundary = self.boundary
        if len(boundary) >= 3:
            points = [Point2D(p[0], p[1]) for p in boundary]
            ceiling_outline = Polyline2D(
                points=points,
                closed=True,
                style=style,
                layer=Layer.CEILING,
            )
            result.append(ceiling_outline)

        return result

    def __repr__(self) -> str:
        return (
            f"Ceiling(name='{self.name}', type='{self.type.name}', "
            f"area={self.area_m2:.2f}m², height={self.height:.0f}mm)"
        )
