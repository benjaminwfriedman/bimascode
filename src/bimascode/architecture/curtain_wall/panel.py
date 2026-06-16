"""
Panel types for curtain walls.

Panels fill the cells created by the curtain grid. Types include:
- GlazedPanelType: Glass vision panels
- OpaquePanelType: Spandrel/solid panels
- EmptyPanelType: Open cells with no infill
- OperablePanelType: Panels containing operable windows (future)
"""

from __future__ import annotations

import copy
import uuid
from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from build123d import Box, Compound, Location, Pos

from bimascode.core.type_instance import ElementType, ElementInstance
from bimascode.utils.materials import Material
from bimascode.utils.units import Length, normalize_length

if TYPE_CHECKING:
    from bimascode.architecture.curtain_wall.curtain_grid import CurtainCell


class CurtainPanelType(ElementType):
    """
    Base class for curtain wall panel types.

    Panels fill the cells created by the curtain grid. Each panel type
    defines the thickness, offset from the grid plane, and material
    properties of the infill.

    This matches Revit's System Panel concept.
    """

    def __init__(
        self,
        name: str,
        thickness: Length | float = 24.0,
        offset: Length | float = 0.0,
    ):
        """
        Create a panel type.

        Args:
            name: Type name
            thickness: Total panel thickness in mm (default 24mm for double glazing)
            offset: Offset from grid plane in mm (positive = exterior)
        """
        super().__init__(name)
        self._thickness = normalize_length(thickness).mm
        self._offset = normalize_length(offset).mm

        self.set_parameter("thickness", self._thickness)
        self.set_parameter("offset", self._offset)

    @property
    def thickness(self) -> float:
        """Get panel thickness in mm."""
        return self._thickness

    @property
    def offset(self) -> float:
        """Get panel offset from grid plane in mm."""
        return self._offset

    @abstractmethod
    def create_geometry(self, instance: "CurtainPanel") -> Compound | None:
        """
        Create 3D geometry for a panel instance.

        The geometry is created in local coordinates where:
        - X axis is panel width (horizontal)
        - Y axis is panel thickness (depth, perpendicular to facade)
        - Z axis is panel height (vertical)
        - Origin is at the bottom-left corner of the panel

        Args:
            instance: The panel instance to create geometry for

        Returns:
            build123d Compound containing the panel solid, or None for empty panels
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', thickness={self._thickness:.1f}mm)"


class GlazedPanelType(CurtainPanelType):
    """
    Glass vision panel type.

    Represents transparent glazing with configurable glass layers,
    air gaps, and coatings.
    """

    def __init__(
        self,
        name: str,
        glazing_type: str = "double",
        glass_thickness: Length | float = 6.0,
        air_gap: Length | float = 12.0,
        low_e: bool = False,
        tint: str | None = None,
        thickness: Length | float | None = None,
        offset: Length | float = 0.0,
    ):
        """
        Create a glazed panel type.

        Args:
            name: Type name
            glazing_type: 'single', 'double', or 'triple'
            glass_thickness: Thickness of each glass lite in mm
            air_gap: Gap between glass lites in mm
            low_e: Whether panel has low-E coating
            tint: Glass tint ('clear', 'gray', 'bronze', 'blue', or None)
            thickness: Total panel thickness (calculated if None)
            offset: Offset from grid plane in mm
        """
        self._glazing_type = glazing_type
        self._glass_thickness = normalize_length(glass_thickness).mm
        self._air_gap = normalize_length(air_gap).mm
        self._low_e = low_e
        self._tint = tint

        # Calculate total thickness if not provided
        if thickness is None:
            if glazing_type == "single":
                thickness = self._glass_thickness
            elif glazing_type == "double":
                thickness = 2 * self._glass_thickness + self._air_gap
            elif glazing_type == "triple":
                thickness = 3 * self._glass_thickness + 2 * self._air_gap
            else:
                thickness = 24.0  # Default

        super().__init__(name, thickness=thickness, offset=offset)

        self.set_parameter("glazing_type", glazing_type)
        self.set_parameter("glass_thickness", self._glass_thickness)
        self.set_parameter("air_gap", self._air_gap)
        self.set_parameter("low_e", low_e)
        self.set_parameter("tint", tint)

    @property
    def glazing_type(self) -> str:
        """Get glazing type: 'single', 'double', or 'triple'."""
        return self._glazing_type

    @property
    def glass_thickness(self) -> float:
        """Get individual glass lite thickness in mm."""
        return self._glass_thickness

    @property
    def air_gap(self) -> float:
        """Get air gap between lites in mm."""
        return self._air_gap

    @property
    def low_e(self) -> bool:
        """Check if panel has low-E coating."""
        return self._low_e

    @property
    def tint(self) -> str | None:
        """Get glass tint."""
        return self._tint

    @property
    def num_lites(self) -> int:
        """Get number of glass lites."""
        if self._glazing_type == "single":
            return 1
        elif self._glazing_type == "double":
            return 2
        elif self._glazing_type == "triple":
            return 3
        return 1

    def create_geometry(self, instance: "CurtainPanel") -> Compound:
        """
        Create glass panel geometry.

        Creates individual glass lites with air gaps between them.

        Args:
            instance: The panel instance

        Returns:
            Compound containing glass lite solids
        """
        width = instance.width
        height = instance.height
        parts = []

        # Calculate lite positions
        num_lites = self.num_lites
        total_glass = num_lites * self._glass_thickness
        total_gaps = (num_lites - 1) * self._air_gap
        total_thickness = total_glass + total_gaps

        # Start from exterior
        y_position = -total_thickness / 2 + self._glass_thickness / 2

        for i in range(num_lites):
            lite = Box(width, self._glass_thickness, height)
            # Position: center of panel in X, offset in Y, bottom at Z=0
            lite_positioned = lite.locate(
                Location(Pos(width / 2, y_position + self._offset, height / 2))
            )
            parts.append(lite_positioned)

            # Move to next lite position
            y_position += self._glass_thickness + self._air_gap

        return Compound(children=parts)

    def __repr__(self) -> str:
        return (
            f"GlazedPanelType(name='{self.name}', "
            f"glazing='{self._glazing_type}', "
            f"thickness={self._thickness:.1f}mm)"
        )


class OpaquePanelType(CurtainPanelType):
    """
    Opaque spandrel or solid panel type.

    Used for areas that need to be non-transparent, typically
    at floor lines to hide structure or services.
    """

    def __init__(
        self,
        name: str,
        material: Material,
        insulation_thickness: Length | float = 50.0,
        backing_thickness: Length | float = 12.0,
        face_thickness: Length | float = 6.0,
        offset: Length | float = 0.0,
    ):
        """
        Create an opaque panel type.

        Args:
            name: Type name
            material: Face material (metal, stone, etc.)
            insulation_thickness: Insulation layer thickness in mm
            backing_thickness: Interior backing thickness in mm
            face_thickness: Exterior face thickness in mm
            offset: Offset from grid plane in mm
        """
        self._material = material
        self._insulation_thickness = normalize_length(insulation_thickness).mm
        self._backing_thickness = normalize_length(backing_thickness).mm
        self._face_thickness = normalize_length(face_thickness).mm

        total_thickness = (
            self._face_thickness + self._insulation_thickness + self._backing_thickness
        )

        super().__init__(name, thickness=total_thickness, offset=offset)

        self.set_parameter("material", material)
        self.set_parameter("insulation_thickness", self._insulation_thickness)
        self.set_parameter("backing_thickness", self._backing_thickness)
        self.set_parameter("face_thickness", self._face_thickness)

    @property
    def material(self) -> Material:
        """Get the face material."""
        return self._material

    @property
    def insulation_thickness(self) -> float:
        """Get insulation layer thickness in mm."""
        return self._insulation_thickness

    def create_geometry(self, instance: "CurtainPanel") -> Compound:
        """
        Create opaque panel geometry.

        Creates layered panel with face, insulation, and backing.

        Args:
            instance: The panel instance

        Returns:
            Compound containing panel layer solids
        """
        width = instance.width
        height = instance.height
        parts = []

        # Calculate layer positions (exterior to interior)
        y_start = -self._thickness / 2 + self._offset

        # Exterior face
        face = Box(width, self._face_thickness, height)
        face_y = y_start + self._face_thickness / 2
        face = face.locate(Location(Pos(width / 2, face_y, height / 2)))
        parts.append(face)

        # Insulation
        insulation = Box(width, self._insulation_thickness, height)
        insulation_y = y_start + self._face_thickness + self._insulation_thickness / 2
        insulation = insulation.locate(
            Location(Pos(width / 2, insulation_y, height / 2))
        )
        parts.append(insulation)

        # Backing
        backing = Box(width, self._backing_thickness, height)
        backing_y = (
            y_start
            + self._face_thickness
            + self._insulation_thickness
            + self._backing_thickness / 2
        )
        backing = backing.locate(Location(Pos(width / 2, backing_y, height / 2)))
        parts.append(backing)

        return Compound(children=parts)

    def __repr__(self) -> str:
        return (
            f"OpaquePanelType(name='{self.name}', "
            f"material='{self._material.name if self._material else 'None'}', "
            f"thickness={self._thickness:.1f}mm)"
        )


class EmptyPanelType(CurtainPanelType):
    """
    Empty panel type - no infill.

    Represents an open cell in the curtain wall grid,
    like Revit's Empty System Panel.
    """

    def __init__(self, name: str = "Empty"):
        """
        Create an empty panel type.

        Args:
            name: Type name (default 'Empty')
        """
        super().__init__(name, thickness=0.0, offset=0.0)

    def create_geometry(self, instance: "CurtainPanel") -> None:
        """
        Empty panels have no geometry.

        Args:
            instance: The panel instance

        Returns:
            None
        """
        return None

    def __repr__(self) -> str:
        return f"EmptyPanelType(name='{self.name}')"


class CurtainPanel(ElementInstance):
    """
    A panel instance placed in a curtain grid cell.

    Panels are not placed directly by users - they are created automatically
    by the curtain wall based on its grid and panel type settings.
    """

    def __init__(
        self,
        panel_type: CurtainPanelType,
        width: float,
        height: float,
        cell: "CurtainCell | None" = None,
        name: str | None = None,
    ):
        """
        Create a panel instance.

        Args:
            panel_type: The panel type
            width: Panel width in mm
            height: Panel height in mm
            cell: The curtain cell this panel fills (optional)
            name: Optional instance name
        """
        super().__init__(panel_type, name)
        self._width = width
        self._height = height
        self._cell = cell

    @property
    def width(self) -> float:
        """Get panel width in mm."""
        return self._width

    @property
    def height(self) -> float:
        """Get panel height in mm."""
        return self._height

    @property
    def cell(self) -> "CurtainCell | None":
        """Get the curtain cell this panel fills."""
        return self._cell

    @property
    def area(self) -> float:
        """Get panel area in square mm."""
        return self._width * self._height

    @property
    def area_m2(self) -> float:
        """Get panel area in square meters."""
        return self.area / 1_000_000.0

    def get_local_geometry(self, origin: tuple[float, float, float]) -> Compound | None:
        """
        Get panel geometry positioned at the given origin.

        Args:
            origin: Bottom-left corner position (x, y, z) in local coordinates

        Returns:
            Positioned panel geometry, or None for empty panels
        """
        base_geom = self.get_geometry()
        if base_geom is None:
            return None

        # Copy before transforming
        geom_copy = copy.copy(base_geom)

        # Position at origin (geometry is created with origin at bottom-left)
        transform = Location(Pos(*origin))
        geom_copy = geom_copy.locate(transform)

        return geom_copy

    def __repr__(self) -> str:
        return (
            f"CurtainPanel(name='{self.name}', "
            f"type='{self.type.name}', "
            f"size={self._width:.0f}x{self._height:.0f}mm)"
        )


# Factory functions for common panel types


def create_double_glazed_panel_type(
    name: str = "Double Glazed",
    glass_thickness: float = 6.0,
    air_gap: float = 12.0,
    low_e: bool = False,
) -> GlazedPanelType:
    """
    Create a standard double-glazed panel type.

    Args:
        name: Type name
        glass_thickness: Glass lite thickness in mm
        air_gap: Air gap between lites in mm
        low_e: Whether to include low-E coating

    Returns:
        GlazedPanelType configured for double glazing
    """
    return GlazedPanelType(
        name=name,
        glazing_type="double",
        glass_thickness=glass_thickness,
        air_gap=air_gap,
        low_e=low_e,
    )


def create_triple_glazed_panel_type(
    name: str = "Triple Glazed",
    glass_thickness: float = 6.0,
    air_gap: float = 12.0,
    low_e: bool = True,
) -> GlazedPanelType:
    """
    Create a triple-glazed panel type for high-performance facades.

    Args:
        name: Type name
        glass_thickness: Glass lite thickness in mm
        air_gap: Air gap between lites in mm
        low_e: Whether to include low-E coating

    Returns:
        GlazedPanelType configured for triple glazing
    """
    return GlazedPanelType(
        name=name,
        glazing_type="triple",
        glass_thickness=glass_thickness,
        air_gap=air_gap,
        low_e=low_e,
    )
