"""
Room Separator element class for BIM as Code.

This module implements room separators - non-physical boundary elements
used to define room boundaries where no wall exists.
"""

import math
from typing import TYPE_CHECKING

from bimascode.core.element import Element
from bimascode.drawing.line_styles import LineStyle, LineType, LineWeight
from bimascode.drawing.primitives import Line2D, Point2D
from bimascode.performance.bounding_box import BoundingBox

if TYPE_CHECKING:
    from bimascode.drawing.symbology import ElementSymbology
    from bimascode.drawing.view_base import ViewRange
    from bimascode.spatial.level import Level


class RoomSeparator(Element):
    """
    A non-physical line element that defines room boundaries.

    Room separators are used to define room boundaries where no wall exists,
    such as:
    - Open office areas divided into separate program spaces
    - L-shaped rooms that need to be split for area calculations
    - Virtual boundaries between spaces connected by large openings
    - Separating rentable area from common area

    Room separators have no 3D geometry and appear in floor plans as
    dashed lines with light weight (non-printing or light gray).
    """

    def __init__(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        level: "Level",
        name: str = "",
    ):
        """
        Create a room separator.

        Args:
            start: Start point (x, y) coordinates in mm
            end: End point (x, y) coordinates in mm
            level: Level this room separator belongs to
            name: Optional name for the separator
        """
        super().__init__(name=name or "Room Separator")

        self._start = start
        self._end = end
        self.level = level

        # Register with level
        if hasattr(level, "add_element"):
            level.add_element(self)

    @property
    def start(self) -> tuple[float, float]:
        """Get start point (x, y) in mm."""
        return self._start

    @start.setter
    def start(self, value: tuple[float, float]) -> None:
        """Set start point."""
        self._start = value
        self._invalidate_cache()

    @property
    def end(self) -> tuple[float, float]:
        """Get end point (x, y) in mm."""
        return self._end

    @end.setter
    def end(self, value: tuple[float, float]) -> None:
        """Set end point."""
        self._end = value
        self._invalidate_cache()

    @property
    def length(self) -> float:
        """Get the length of the separator in mm."""
        dx = self._end[0] - self._start[0]
        dy = self._end[1] - self._start[1]
        return math.sqrt(dx * dx + dy * dy)

    @property
    def length_m(self) -> float:
        """Get the length of the separator in meters."""
        return self.length / 1000.0

    @property
    def midpoint(self) -> tuple[float, float]:
        """Get the midpoint of the separator."""
        return (
            (self._start[0] + self._end[0]) / 2,
            (self._start[1] + self._end[1]) / 2,
        )

    @property
    def angle(self) -> float:
        """Get the angle of the separator in radians."""
        dx = self._end[0] - self._start[0]
        dy = self._end[1] - self._start[1]
        return math.atan2(dy, dx)

    @property
    def angle_degrees(self) -> float:
        """Get the angle of the separator in degrees."""
        return math.degrees(self.angle)

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this room separator.

        Room separators are 2D elements, so the bounding box has
        zero height at the level elevation.

        Returns:
            BoundingBox encompassing the separator
        """
        min_x = min(self._start[0], self._end[0])
        max_x = max(self._start[0], self._end[0])
        min_y = min(self._start[1], self._end[1])
        max_y = max(self._start[1], self._end[1])
        z = self.level.elevation_mm

        return BoundingBox(
            min_x=min_x,
            min_y=min_y,
            min_z=z,
            max_x=max_x,
            max_y=max_y,
            max_z=z,
        )

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: "ViewRange",
        symbology: "ElementSymbology | None" = None,
    ) -> list[Line2D]:
        """Generate floor plan linework.

        Room separators appear as dashed lines with fine weight
        to indicate non-physical boundaries.

        Args:
            cut_height: Z coordinate of the section cut (unused for 2D elements)
            view_range: View range parameters (unused for 2D elements)
            symbology: Optional symbology settings (unused - uses fixed style)

        Returns:
            List containing a single dashed Line2D
        """
        # Room separators use a light dashed line style
        # Fine weight + dashed = clearly a non-physical element
        style = LineStyle(
            weight=LineWeight.FINE,
            type=LineType.DASHED,
            is_cut=False,
        )

        line = Line2D(
            start=Point2D(self._start[0], self._start[1]),
            end=Point2D(self._end[0], self._end[1]),
            style=style,
            layer="A-AREA-BNDY",  # AIA layer for area boundaries
        )

        return [line]

    def to_ifc(self, ifc_file, ifc_building_storey):
        """
        Export room separator to IFC as IfcVirtualElement.

        IfcVirtualElement is the correct IFC entity for non-physical
        boundary elements like room separators.

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey to place separator in

        Returns:
            IfcVirtualElement entity
        """
        # Create IfcVirtualElement for the non-physical boundary
        ifc_virtual = ifc_file.create_entity(
            "IfcVirtualElement",
            GlobalId=self.guid,
            Name=self.name,
            Description=self.description or "Room separation line",
        )

        # Create placement at start point
        location = ifc_file.createIfcCartesianPoint(
            (float(self._start[0]), float(self._start[1]), 0.0)
        )

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0)),
        )

        local_placement = ifc_file.createIfcLocalPlacement(
            ifc_building_storey.ObjectPlacement, axis_placement
        )

        ifc_virtual.ObjectPlacement = local_placement

        # Create curve geometry (polyline from start to end)
        start_pt = ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        end_pt = ifc_file.createIfcCartesianPoint(
            (
                float(self._end[0] - self._start[0]),
                float(self._end[1] - self._start[1]),
                0.0,
            )
        )

        polyline = ifc_file.createIfcPolyline([start_pt, end_pt])

        # Create geometric curve set representation
        geom_set = ifc_file.createIfcGeometricCurveSet([polyline])

        # Get the geometric representation context
        contexts = ifc_file.by_type("IfcGeometricRepresentationContext")
        context = contexts[0] if contexts else None

        if context:
            shape_representation = ifc_file.createIfcShapeRepresentation(
                context,
                "Annotation",
                "GeometricCurveSet",
                [geom_set],
            )

            product_shape = ifc_file.createIfcProductDefinitionShape(
                None, None, [shape_representation]
            )

            ifc_virtual.Representation = product_shape

        # Add property set with length
        length_property = ifc_file.create_entity(
            "IfcPropertySingleValue",
            Name="Length",
            NominalValue=ifc_file.create_entity("IfcLengthMeasure", self.length / 1000.0),
        )

        property_set = ifc_file.create_entity(
            "IfcPropertySet",
            GlobalId=self._generate_guid(),
            Name="Pset_RoomSeparator",
            HasProperties=[length_property],
        )

        ifc_file.createIfcRelDefinesByProperties(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_virtual],
            property_set,
        )

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"RoomSeparator_{self.name}Container",
            None,
            [ifc_virtual],
            ifc_building_storey,
        )

        return ifc_virtual

    def __repr__(self) -> str:
        return (
            f"RoomSeparator(start={self._start}, end={self._end}, " f"length={self.length_m:.2f}m)"
        )
