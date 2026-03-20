"""
Beam types for BIM as Code.

This module implements the BeamType class which defines structural beam
properties including section profile and materials.
"""

from typing import Optional
from build123d import Box, Location
from bimascode.core.type_instance import ElementType
from bimascode.structure.profile import RectangularProfile
from bimascode.utils.materials import Material
from bimascode.utils.units import Length, normalize_length


class BeamType(ElementType):
    """
    Structural beam type defining section profile and properties.

    Beam types specify the cross-section profile and material properties
    that are shared across multiple beam instances.
    """

    def __init__(
        self,
        name: str,
        profile: RectangularProfile,
        material: Optional[Material] = None,
        description: Optional[str] = None
    ):
        """
        Create a beam type.

        Args:
            name: Name for this beam type
            profile: Section profile (RectangularProfile)
            material: Material for the beam
            description: Optional description
        """
        super().__init__(name)
        self.profile = profile
        self.material = material
        self.description = description

        # Store profile dimensions as type parameters
        # For beams: width is horizontal dimension, height is vertical
        self.set_parameter("width", profile.width)
        self.set_parameter("height", profile.height)

    @property
    def width(self) -> float:
        """Get beam width in millimeters."""
        return self.get_parameter("width")

    @property
    def height(self) -> float:
        """Get beam height (depth) in millimeters."""
        return self.get_parameter("height")

    @property
    def area(self) -> float:
        """Get cross-sectional area in square millimeters."""
        return self.profile.area

    def create_geometry(self, instance: 'Beam'):
        """
        Create 3D geometry for a beam instance.

        The beam is created in LOCAL coordinates along the X-axis:
        - Origin at beam start point
        - X-axis along beam length
        - Y-axis along width (horizontal)
        - Z-axis along height (vertical)

        Args:
            instance: Beam instance to create geometry for

        Returns:
            build123d Solid representing the beam
        """
        # Get beam length from instance
        length = instance.length

        # Create beam as a box extruded along X-axis
        # Width is Y dimension, Height is Z dimension
        beam_box = Box(length, self.width, self.height)

        # Position so beam runs from start (0,0,0) along X-axis
        # Center the profile in Y and Z
        beam_box = beam_box.locate(Location(
            (length / 2, 0, 0),
            (0, 0, 1), 0
        ))

        return beam_box

    def _generate_guid(self) -> str:
        """Generate a unique IFC GUID."""
        import uuid
        return str(uuid.uuid4())

    def to_ifc(self, ifc_file):
        """
        Export beam type to IFC.

        Creates IfcBeamType with profile and material association.

        Args:
            ifc_file: IFC file object

        Returns:
            IfcBeamType entity
        """
        # Create IFC profile
        ifc_profile = self.profile.to_ifc(ifc_file)

        # Create IfcBeamType
        ifc_beam_type = ifc_file.create_entity(
            "IfcBeamType",
            GlobalId=self.guid,
            Name=self.name,
            Description=self.description,
            PredefinedType="BEAM"
        )

        # Associate material if present
        if self.material:
            ifc_material = self.material.to_ifc(ifc_file)
            ifc_file.createIfcRelAssociatesMaterial(
                self._generate_guid(),
                None,
                None,
                None,
                [ifc_beam_type],
                ifc_material
            )

        return ifc_beam_type

    def __repr__(self) -> str:
        return (
            f"BeamType(name='{self.name}', profile={self.profile.name}, "
            f"width={self.width:.0f}mm, height={self.height:.0f}mm)"
        )


# Common beam type constructors
def create_rectangular_beam_type(
    name: str,
    width: Length | float,
    height: Length | float,
    material: Optional[Material] = None
) -> BeamType:
    """
    Create a rectangular beam type.

    Args:
        name: Beam type name
        width: Beam width (horizontal dimension)
        height: Beam height (vertical/depth dimension)
        material: Optional material

    Returns:
        BeamType with rectangular profile
    """
    profile = RectangularProfile(width=width, height=height)
    return BeamType(name=name, profile=profile, material=material)


def create_standard_beam_type(
    name: str,
    size: str = "300x600",
    material: Optional[Material] = None
) -> BeamType:
    """
    Create a standard beam type from common size string.

    Args:
        name: Beam type name
        size: Size string in "WIDTHxHEIGHT" format (e.g., "300x600")
        material: Optional material

    Returns:
        BeamType with parsed dimensions
    """
    parts = size.lower().replace("mm", "").split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid size format: {size}. Use 'WIDTHxHEIGHT' format.")

    width = float(parts[0])
    height = float(parts[1])

    profile = RectangularProfile(width=width, height=height, name=f"Beam_{size}")
    return BeamType(name=name, profile=profile, material=material)
