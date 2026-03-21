"""
Floor/Slab element class for BIM as Code.

Floors are horizontal elements defined by a boundary polygon.
They can have slope for drainage (flat roofs, accessibility ramps).
They support openings for stairs, shafts, and other penetrations.
"""

from typing import List, Tuple, Optional, Union, TYPE_CHECKING
from bimascode.core.type_instance import ElementInstance
from bimascode.core.world_geometry import FreestandingElementMixin
from bimascode.performance.bounding_box import BoundingBox
from bimascode.spatial.level import Level
from bimascode.utils.units import normalize_length, Length
import math

if TYPE_CHECKING:
    from bimascode.architecture.opening import Opening
    from bimascode.drawing.view_base import ViewRange
    from bimascode.drawing.primitives import Line2D, Arc2D, Polyline2D, Hatch2D


class Floor(ElementInstance, FreestandingElementMixin):
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
        structural: bool = False,
        name: Optional[str] = None
    ):
        """
        Create a floor.

        Args:
            floor_type: FloorType defining the floor assembly
            boundary: List of (x, y) coordinates defining floor boundary
            level: Level this floor sits on
            slope: Floor slope in degrees (for drainage, ramps, etc.)
            structural: If True, floor is a structural slab (base slab)
            name: Optional name for this floor
        """
        super().__init__(floor_type, name)

        self.level = level

        # Openings in this floor
        self._openings: List['Opening'] = []

        # Structural flag
        self._structural = structural

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
    def structural(self) -> bool:
        """Check if floor is marked as structural (base slab)."""
        return self._structural

    @structural.setter
    def structural(self, value: bool) -> None:
        """Set the structural flag."""
        self._structural = value

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

    def _get_world_position(self) -> Tuple[float, float, float]:
        """Get world position for floor geometry.

        build123d's Polygon centers vertices at the centroid, so we translate
        by the centroid to restore correct world positioning.

        Returns:
            (x, y, z) at floor centroid, with Z at level elevation
        """
        cx, cy = self.get_centroid()
        return (cx, cy, self.level.elevation_mm)

    def _get_world_rotation(self) -> float:
        """Get world rotation for floor geometry.

        Floors have no rotation (horizontal elements).

        Returns:
            0.0 (no rotation)
        """
        return 0.0

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

    @property
    def openings(self) -> List['Opening']:
        """Get all openings in this floor."""
        return self._openings.copy()

    def add_opening(self, opening_boundary: List[Tuple[float, float]], name: Optional[str] = None) -> 'Opening':
        """
        Add an opening (void) in the floor.

        Args:
            opening_boundary: List of (x, y) coordinates for opening
            name: Optional name for the opening

        Returns:
            The created Opening object
        """
        from bimascode.architecture.opening import Opening

        opening = Opening(
            host_element=self,
            boundary=opening_boundary,
            depth=self.thickness + 2,  # +2mm for clean cut
            name=name or f"Opening_{len(self._openings) + 1}"
        )
        self._openings.append(opening)
        self.invalidate_geometry()
        return opening

    def remove_opening(self, opening: 'Opening') -> None:
        """
        Remove an opening from this floor.

        Args:
            opening: Opening to remove
        """
        if opening in self._openings:
            self._openings.remove(opening)
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
        # Determine predefined type based on structural flag
        predefined_type = "BASESLAB" if self._structural else "FLOOR"

        # Create slab
        ifc_slab = ifc_file.create_entity(
            "IfcSlab",
            GlobalId=self.guid,
            Name=self.name,
            Description=f"{self.type.name} floor",
            PredefinedType=predefined_type
        )

        # Set placement (at level elevation)
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

        ifc_slab.ObjectPlacement = local_placement

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

                ifc_slab.Representation = product_shape

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"Floor{self.name}Container",
            None,
            [ifc_slab],
            ifc_building_storey
        )

        # Associate with material layer set
        material_layer_set = self.type.to_ifc(ifc_file)

        ifc_file.createIfcRelAssociatesMaterial(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_slab],
            material_layer_set
        )

        return ifc_slab

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this floor.

        Returns:
            BoundingBox encompassing the floor geometry
        """
        return BoundingBox.from_polygon_2d(
            self.boundary,
            self.level.elevation_mm,
            self.level.elevation_mm + self.thickness
        )

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: "ViewRange",
    ) -> List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]]:
        """Generate floor plan linework for this floor.

        Floors are typically shown with their boundary outline.

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters

        Returns:
            List of 2D geometry primitives
        """
        from bimascode.drawing.primitives import Point2D, Polyline2D
        from bimascode.drawing.line_styles import LineStyle, Layer

        result: List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]] = []

        # Floors are below the cut plane - show with visible (not cut) style
        bbox = self.get_bounding_box()
        is_cut = bbox.min_z <= cut_height <= bbox.max_z

        if is_cut:
            style = LineStyle.cut_medium()
        else:
            style = LineStyle.visible()

        # Create polyline from boundary
        boundary = self.boundary
        if len(boundary) >= 3:
            points = [Point2D(p[0], p[1]) for p in boundary]
            floor_outline = Polyline2D(
                points=points,
                closed=True,
                style=style,
                layer=Layer.FLOOR,
            )
            result.append(floor_outline)

        return result

    def __repr__(self) -> str:
        return (
            f"Floor(name='{self.name}', type='{self.type.name}', "
            f"area={self.area_m2:.2f}m², thickness={self.thickness:.1f}mm)"
        )
