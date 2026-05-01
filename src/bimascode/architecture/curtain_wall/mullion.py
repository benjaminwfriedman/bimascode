"""
Mullion types and instances for curtain walls.

Mullions are the framing members that run along grid lines in a curtain wall.
They are categorized as:
- Interior mullions: On internal grid lines
- Border mullions: On the edges of the curtain wall (Border 1 = left/bottom, Border 2 = right/top)
"""

from __future__ import annotations

import copy
import uuid
from typing import TYPE_CHECKING, Any

from build123d import Compound, Location, Pos, RotationLike, extrude

from bimascode.architecture.curtain_wall.mullion_profile import MullionProfile
from bimascode.core.type_instance import ElementType, ElementInstance
from bimascode.utils.materials import Material

if TYPE_CHECKING:
    from bimascode.architecture.curtain_wall.curtain_grid import GridSegment


class MullionType(ElementType):
    """
    Type definition for curtain wall mullions.

    Mullion types define the cross-section profile, material, and appearance
    properties shared by all mullion instances of this type.
    """

    def __init__(
        self,
        name: str,
        profile: MullionProfile,
        material: Material | None = None,
        thermal_break: bool = False,
        finish: str = "mill",
        color: tuple[int, int, int] | None = None,
    ):
        """
        Create a mullion type.

        Args:
            name: Type name
            profile: Cross-section profile
            material: Material (typically aluminum)
            thermal_break: Whether mullion has thermal break
            finish: Surface finish ('mill', 'anodized', 'painted')
            color: RGB color for painted finish
        """
        super().__init__(name)
        self._profile = profile
        self._material = material
        self._thermal_break = thermal_break
        self._finish = finish
        self._color = color

        # Store in type parameters for instance access
        self.set_parameter("profile", profile)
        self.set_parameter("material", material)
        self.set_parameter("thermal_break", thermal_break)
        self.set_parameter("finish", finish)
        self.set_parameter("color", color)

    @property
    def profile(self) -> MullionProfile:
        """Get the mullion cross-section profile."""
        return self._profile

    @property
    def material(self) -> Material | None:
        """Get the mullion material."""
        return self._material

    @property
    def thermal_break(self) -> bool:
        """Check if mullion has thermal break."""
        return self._thermal_break

    @property
    def finish(self) -> str:
        """Get the surface finish."""
        return self._finish

    @property
    def color(self) -> tuple[int, int, int] | None:
        """Get the color for painted finish."""
        return self._color

    @property
    def width(self) -> float:
        """Get mullion face width in mm."""
        return self._profile.width

    @property
    def depth(self) -> float:
        """Get mullion depth in mm."""
        return self._profile.depth

    def create_geometry(self, instance: "Mullion") -> Compound:
        """
        Create 3D geometry for a mullion instance.

        The geometry is created in local coordinates where:
        - The mullion runs along the Z axis (0 to length)
        - X axis is the face width direction
        - Y axis is the depth direction
        - Origin is at the start of the mullion, centered on the profile

        Args:
            instance: The mullion instance to create geometry for

        Returns:
            build123d Compound containing the mullion solid
        """
        # Get the 2D profile face
        profile_face = self._profile.to_build123d()

        # Extrude along Z axis for the mullion length
        length = instance.length
        mullion_solid = extrude(profile_face, length)

        return Compound(children=[mullion_solid])

    def to_ifc(self, ifc_file, instance: "Mullion") -> Any:
        """
        Export mullion type and instance to IFC.

        Creates IfcMemberType for the type and IfcMember for the instance.

        Args:
            ifc_file: IFC file object
            instance: The mullion instance

        Returns:
            IfcMember entity
        """
        # Get profile definition
        ifc_profile = self._profile.to_ifc(ifc_file)

        # Create member type if not already created
        # (In production, we'd cache this per type)
        ifc_member_type = ifc_file.create_entity(
            "IfcMemberType",
            GlobalId=self.guid,
            Name=self.name,
            PredefinedType="MULLION",
        )

        # Create member instance
        ifc_member = ifc_file.create_entity(
            "IfcMember",
            GlobalId=instance.guid,
            Name=instance.name,
            PredefinedType="MULLION",
        )

        return ifc_member

    def __repr__(self) -> str:
        return (
            f"MullionType(name='{self.name}', "
            f"profile={self._profile.name}, "
            f"finish='{self._finish}')"
        )


class Mullion(ElementInstance):
    """
    A mullion instance placed on a grid segment.

    Mullions are not placed directly by users - they are created automatically
    by the curtain wall based on its grid configuration. Each mullion is
    associated with a grid segment (portion of a grid line between intersections).
    """

    def __init__(
        self,
        mullion_type: MullionType,
        start_point: tuple[float, float, float],
        end_point: tuple[float, float, float],
        segment: "GridSegment | None" = None,
        name: str | None = None,
    ):
        """
        Create a mullion instance.

        Args:
            mullion_type: The mullion type
            start_point: Start point in local curtain wall coordinates (x, y, z)
            end_point: End point in local curtain wall coordinates (x, y, z)
            segment: The grid segment this mullion is placed on (optional)
            name: Optional instance name
        """
        super().__init__(mullion_type, name)
        self._start_point = start_point
        self._end_point = end_point
        self._segment = segment

    @property
    def start_point(self) -> tuple[float, float, float]:
        """Get mullion start point in local coordinates."""
        return self._start_point

    @property
    def end_point(self) -> tuple[float, float, float]:
        """Get mullion end point in local coordinates."""
        return self._end_point

    @property
    def segment(self) -> "GridSegment | None":
        """Get the grid segment this mullion is placed on."""
        return self._segment

    @property
    def length(self) -> float:
        """Get mullion length in mm."""
        dx = self._end_point[0] - self._start_point[0]
        dy = self._end_point[1] - self._start_point[1]
        dz = self._end_point[2] - self._start_point[2]
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    @property
    def direction(self) -> str:
        """
        Get mullion direction: 'vertical' or 'horizontal'.

        Determined by which axis has the largest delta.
        """
        dx = abs(self._end_point[0] - self._start_point[0])
        dy = abs(self._end_point[1] - self._start_point[1])
        dz = abs(self._end_point[2] - self._start_point[2])

        if dz > dx and dz > dy:
            return "vertical"
        else:
            return "horizontal"

    def get_local_geometry(self) -> Compound:
        """
        Get mullion geometry in local coordinates.

        The geometry is positioned and rotated to align with the
        start/end points.

        Returns:
            build123d Compound with positioned mullion geometry
        """
        # Get base geometry (along Z axis)
        base_geom = self.get_geometry()

        # Copy before transforming
        geom_copy = copy.copy(base_geom)

        # Calculate rotation to align with direction
        import math

        dx = self._end_point[0] - self._start_point[0]
        dy = self._end_point[1] - self._start_point[1]
        dz = self._end_point[2] - self._start_point[2]
        length = self.length

        if length < 1e-6:
            return geom_copy

        # Normalize direction
        dir_x = dx / length
        dir_y = dy / length
        dir_z = dz / length

        # Calculate rotation angles
        # For vertical mullions (Z-dominant), minimal rotation needed
        # For horizontal mullions, rotate from Z to XY plane
        if abs(dir_z) > 0.99:
            # Nearly vertical - just translate
            transform = Location(Pos(*self._start_point))
        else:
            # Horizontal or diagonal - need rotation
            # Angle from Z axis in XZ plane
            angle_from_z = math.degrees(math.acos(dir_z))
            # Angle around Z axis
            angle_around_z = math.degrees(math.atan2(dir_y, dir_x))

            from build123d import Rotation

            # First rotate around Y to tilt from Z, then around Z to orient
            transform = Location(
                Pos(*self._start_point),
                Rotation(0, angle_from_z, angle_around_z),
            )

        geom_copy = geom_copy.locate(transform)
        return geom_copy

    def __repr__(self) -> str:
        return (
            f"Mullion(name='{self.name}', "
            f"type='{self.type.name}', "
            f"length={self.length:.0f}mm, "
            f"direction='{self.direction}')"
        )


# Factory functions for common mullion types


def create_rectangular_mullion_type(
    name: str,
    width: float,
    depth: float,
    material: Material | None = None,
    finish: str = "mill",
) -> MullionType:
    """
    Create a mullion type with rectangular profile.

    Args:
        name: Type name
        width: Face width in mm
        depth: Depth in mm
        material: Optional material
        finish: Surface finish

    Returns:
        MullionType with rectangular profile
    """
    from bimascode.architecture.curtain_wall.mullion_profile import (
        create_rectangular_mullion_profile,
    )

    profile = create_rectangular_mullion_profile(width, depth)
    return MullionType(name=name, profile=profile, material=material, finish=finish)
