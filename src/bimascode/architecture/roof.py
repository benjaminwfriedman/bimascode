"""
Roof element class for BIM as Code.

Sprint 2: Flat roofs only (with slope for drainage).
Pitched roofs deferred to P1 (v1.1).
Supports openings for skylights, hatches, and other penetrations.
"""

from typing import TYPE_CHECKING

from bimascode.architecture.floor_type import FloorType
from bimascode.core.type_instance import ElementInstance
from bimascode.performance.bounding_box import BoundingBox
from bimascode.spatial.level import Level
from bimascode.utils.units import Length

if TYPE_CHECKING:
    from bimascode.architecture.opening import Opening


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
        boundary: list[tuple[float, float]],
        level: Level,
        slope: float = 0.0,
        name: str | None = None,
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

        # Openings in this roof
        self._openings: list[Opening] = []

        # Store geometric parameters
        self.set_parameter("boundary", boundary, override=False)
        self.set_parameter("slope", slope, override=False)

        # Register with level
        if hasattr(level, "add_element"):
            level.add_element(self)

    @property
    def boundary(self) -> list[tuple[float, float]]:
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

    def get_centroid(self) -> tuple[float, float]:
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

    def get_center_3d(self) -> tuple[float, float, float]:
        """
        Get the 3D center point of the roof.

        Returns:
            (x, y, z) coordinates of roof center
        """
        cx, cy = self.get_centroid()
        z = self.level.elevation_mm + self.thickness / 2
        return (cx, cy, z)

    def set_boundary(self, boundary: list[tuple[float, float]]) -> None:
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

    @property
    def openings(self) -> list["Opening"]:
        """Get all openings in this roof."""
        return self._openings.copy()

    def add_opening(
        self, opening_boundary: list[tuple[float, float]], name: str | None = None
    ) -> "Opening":
        """
        Add an opening (skylight, hatch, etc.) in the roof.

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
            name=name or f"Opening_{len(self._openings) + 1}",
        )
        self._openings.append(opening)
        self.invalidate_geometry()
        return opening

    def remove_opening(self, opening: "Opening") -> None:
        """
        Remove an opening from this roof.

        Args:
            opening: Opening to remove
        """
        if opening in self._openings:
            self._openings.remove(opening)
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
            PredefinedType="FLAT_ROOF",
        )

        # Set placement (at level elevation)
        centroid = self.get_centroid()
        location = ifc_file.createIfcCartesianPoint((float(centroid[0]), float(centroid[1]), 0.0))

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0)),
        )

        local_placement = ifc_file.createIfcLocalPlacement(
            ifc_building_storey.ObjectPlacement, axis_placement
        )

        ifc_roof.ObjectPlacement = local_placement

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
                    [ifc_brep],
                )

                # Create product definition shape
                product_shape = ifc_file.createIfcProductDefinitionShape(
                    None, None, [shape_representation]
                )

                ifc_roof.Representation = product_shape

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            f"Roof{self.name}Container",
            None,
            [ifc_roof],
            ifc_building_storey,
        )

        # Associate with material layer set
        material_layer_set = self.type.to_ifc(ifc_file)

        ifc_file.createIfcRelAssociatesMaterial(
            self._generate_guid(),
            self.level.building._ifc_owner_history,
            None,
            None,
            [ifc_roof],
            material_layer_set,
        )

        return ifc_roof

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this roof.

        Returns:
            BoundingBox encompassing the roof geometry
        """
        return BoundingBox.from_polygon_2d(
            self.boundary, self.level.elevation_mm, self.level.elevation_mm + self.thickness
        )

    def __repr__(self) -> str:
        return (
            f"Roof(name='{self.name}', type='{self.type.name}', "
            f"area={self.area_m2:.2f}m², slope={self.slope:.2f}°)"
        )
