"""
Beam element class for BIM as Code.

This module implements structural beams spanning between points
with IFC export support.
"""

from typing import Tuple, Optional, List, Union, TYPE_CHECKING
from bimascode.core.type_instance import ElementInstance
from bimascode.core.world_geometry import FreestandingElementMixin
from bimascode.performance.bounding_box import BoundingBox
from bimascode.spatial.level import Level
from bimascode.utils.units import Length, normalize_length
import math

if TYPE_CHECKING:
    from build123d import Location
    from bimascode.structure.beam_type import BeamType
    from bimascode.drawing.view_base import ViewRange
    from bimascode.drawing.primitives import Line2D, Arc2D, Polyline2D, Hatch2D


class Beam(ElementInstance, FreestandingElementMixin):
    """
    A structural beam element.

    Beams are horizontal elements defined by start and end points.
    They belong to a level and span between two points.
    """

    def __init__(
        self,
        beam_type: 'BeamType',
        level: Level,
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float],
        name: Optional[str] = None
    ):
        """
        Create a structural beam.

        Args:
            beam_type: BeamType defining the section profile
            level: Level this beam is associated with
            start_point: (x, y, z) coordinates of beam start
            end_point: (x, y, z) coordinates of beam end
            name: Optional name for this beam
        """
        super().__init__(beam_type, name)

        self.level = level

        # Store geometric parameters
        self.set_parameter("start_point", start_point, override=False)
        self.set_parameter("end_point", end_point, override=False)

        # Register with level
        if hasattr(level, 'add_element'):
            level.add_element(self)

    @property
    def start_point(self) -> Tuple[float, float, float]:
        """Get beam start point (x, y, z)."""
        return self.get_parameter("start_point")

    @property
    def end_point(self) -> Tuple[float, float, float]:
        """Get beam end point (x, y, z)."""
        return self.get_parameter("end_point")

    @property
    def length(self) -> float:
        """Get beam length in millimeters."""
        start = self.start_point
        end = self.end_point
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def length_length(self) -> Length:
        """Get beam length as Length object."""
        return Length(self.length, "mm")

    @property
    def width(self) -> float:
        """Get beam width from type in millimeters."""
        return self.type.width

    @property
    def height(self) -> float:
        """Get beam height (depth) from type in millimeters."""
        return self.type.height

    @property
    def area(self) -> float:
        """Get beam cross-sectional area in square millimeters."""
        return self.type.area

    @property
    def volume(self) -> float:
        """Get beam volume in cubic millimeters."""
        return self.area * self.length

    @property
    def volume_m3(self) -> float:
        """Get beam volume in cubic meters."""
        return self.volume / 1_000_000_000.0

    @property
    def horizontal_angle(self) -> float:
        """Get beam horizontal angle in radians (rotation about Z-axis)."""
        start = self.start_point
        end = self.end_point
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        return math.atan2(dy, dx)

    @property
    def horizontal_angle_degrees(self) -> float:
        """Get beam horizontal angle in degrees."""
        return math.degrees(self.horizontal_angle)

    @property
    def vertical_angle(self) -> float:
        """Get beam vertical angle in radians (slope)."""
        start = self.start_point
        end = self.end_point
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        horizontal_length = math.sqrt(dx * dx + dy * dy)
        return math.atan2(dz, horizontal_length)

    @property
    def vertical_angle_degrees(self) -> float:
        """Get beam vertical angle in degrees."""
        return math.degrees(self.vertical_angle)

    @property
    def is_horizontal(self) -> bool:
        """Check if beam is horizontal (within tolerance)."""
        return abs(self.vertical_angle) < 0.001  # ~0.05 degrees

    def get_midpoint(self) -> Tuple[float, float, float]:
        """
        Get the midpoint of the beam.

        Returns:
            (x, y, z) coordinates of beam midpoint
        """
        start = self.start_point
        end = self.end_point
        return (
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2,
            (start[2] + end[2]) / 2
        )

    def _get_world_position(self) -> Tuple[float, float, float]:
        """Get world position for beam geometry.

        Beam Z includes both level elevation and the beam's local Z offset.

        Returns:
            (x, y, z) at beam start point, with Z at level elevation + local Z
        """
        start = self.start_point
        level_z = self.level.elevation_mm
        return (start[0], start[1], level_z + start[2])

    def _get_world_rotation(self) -> float:
        """Get world rotation for beam geometry.

        Returns:
            Beam horizontal angle in degrees
        """
        return self.horizontal_angle_degrees

    def _get_local_transform(self) -> "Location":
        """Get local transform for beam centering.

        create_geometry() creates a box centered at origin. This transform
        shifts the start to origin so the beam extends from start to end.

        Returns:
            Location transform to shift beam start to origin
        """
        from build123d import Location
        return Location((self.length / 2, 0, 0))

    def set_start_point(self, point: Tuple[float, float, float]) -> None:
        """
        Set the beam start point.

        Args:
            point: (x, y, z) coordinates
        """
        self.set_parameter("start_point", point, override=False)
        self.invalidate_geometry()

    def set_end_point(self, point: Tuple[float, float, float]) -> None:
        """
        Set the beam end point.

        Args:
            point: (x, y, z) coordinates
        """
        self.set_parameter("end_point", point, override=False)
        self.invalidate_geometry()

    def to_ifc(self, ifc_file, ifc_building_storey):
        """
        Export beam to IFC.

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey to place beam in

        Returns:
            IfcBeam entity
        """
        # Create beam
        ifc_beam = ifc_file.create_entity(
            "IfcBeam",
            GlobalId=self.guid,
            Name=self.name,
            Description=f"{self.type.name} beam",
            PredefinedType="BEAM"
        )

        # Set placement at beam start point with correct orientation
        start = self.start_point
        location = ifc_file.createIfcCartesianPoint((float(start[0]), float(start[1]), float(start[2])))

        # Calculate beam direction
        end = self.end_point
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        length = self.length

        # Normalize direction
        if length > 1e-10:
            dir_x = dx / length
            dir_y = dy / length
            dir_z = dz / length
        else:
            dir_x, dir_y, dir_z = 1.0, 0.0, 0.0

        # Z-axis is up for the beam cross-section
        # X-axis is along the beam direction
        x_dir = (dir_x, dir_y, dir_z)

        # For horizontal beams, Z is vertical
        if abs(dir_z) < 0.999:  # Not vertical beam
            z_dir = (0.0, 0.0, 1.0)
        else:
            z_dir = (1.0, 0.0, 0.0)

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection(z_dir),
            ifc_file.createIfcDirection(x_dir)
        )

        local_placement = ifc_file.createIfcLocalPlacement(
            ifc_building_storey.ObjectPlacement,
            axis_placement
        )

        ifc_beam.ObjectPlacement = local_placement

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

                ifc_beam.Representation = product_shape

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"Beam{self.name}Container",
            None,
            [ifc_beam],
            ifc_building_storey
        )

        # Associate with beam type
        ifc_beam_type = self.type.to_ifc(ifc_file)
        ifc_file.createIfcRelDefinesByType(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_beam],
            ifc_beam_type
        )

        # Associate with material if present
        if self.type.material:
            ifc_material = self.type.material.to_ifc(ifc_file)
            ifc_file.createIfcRelAssociatesMaterial(
                self._generate_guid(),
                self.level.building._ifc_owner_history,
                None,
                None,
                [ifc_beam],
                ifc_material
            )

        return ifc_beam

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this beam.

        Takes into account beam width and height (cross-section),
        and adds level elevation to Z coordinates.

        Returns:
            BoundingBox encompassing the beam geometry
        """
        start = self.start_point
        end = self.end_point
        width = self.width
        height = self.height
        level_z = self.level.elevation_mm

        # Add half-width margin in all directions for the cross-section
        half_w = width / 2.0
        half_h = height / 2.0

        # Simple AABB from endpoints plus cross-section padding
        # Z coordinates are relative to level, so add level elevation
        min_x = min(start[0], end[0]) - half_w
        max_x = max(start[0], end[0]) + half_w
        min_y = min(start[1], end[1]) - half_w
        max_y = max(start[1], end[1]) + half_w
        min_z = level_z + min(start[2], end[2]) - half_h
        max_z = level_z + max(start[2], end[2]) + half_h

        return BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: "ViewRange",
    ) -> List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]]:
        """Generate floor plan linework for this beam.

        Beams above the cut plane are shown with dashed lines.
        Beams cut by the plane are shown with solid lines.

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters

        Returns:
            List of 2D geometry primitives
        """
        from bimascode.drawing.primitives import Point2D, Polyline2D
        from bimascode.drawing.line_styles import LineStyle, Layer

        result: List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]] = []

        # Check beam position relative to cut plane
        bbox = self.get_bounding_box()

        if bbox.max_z < cut_height:
            # Beam is below cut plane - not typically shown in floor plan
            return result
        elif bbox.min_z > cut_height:
            # Beam is above cut plane - show with dashed lines
            style = LineStyle.above_cut()
        else:
            # Beam is cut - show with solid lines
            style = LineStyle.cut_heavy()

        # Calculate beam outline in plan view
        start = self.start_point
        end = self.end_point
        width = self.width
        half_w = width / 2.0

        # Calculate perpendicular direction
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length_2d = math.sqrt(dx * dx + dy * dy)

        if length_2d < 1e-6:
            return result

        # Perpendicular unit vector
        perp_x = -dy / length_2d * half_w
        perp_y = dx / length_2d * half_w

        # Four corners of beam in plan
        corners = [
            Point2D(start[0] + perp_x, start[1] + perp_y),
            Point2D(end[0] + perp_x, end[1] + perp_y),
            Point2D(end[0] - perp_x, end[1] - perp_y),
            Point2D(start[0] - perp_x, start[1] - perp_y),
        ]

        beam_outline = Polyline2D(
            points=corners,
            closed=True,
            style=style,
            layer=Layer.BEAM,
        )
        result.append(beam_outline)

        return result

    def __repr__(self) -> str:
        start = self.start_point
        end = self.end_point
        return (
            f"Beam(name='{self.name}', type='{self.type.name}', "
            f"start=({start[0]:.0f}, {start[1]:.0f}, {start[2]:.0f}), "
            f"end=({end[0]:.0f}, {end[1]:.0f}, {end[2]:.0f}), "
            f"length={self.length:.0f}mm)"
        )
