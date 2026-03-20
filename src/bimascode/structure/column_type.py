"""
Column types for BIM as Code.

This module implements the ColumnType class which defines structural column
properties including section profile and materials.
"""

from typing import Optional
from build123d import Box, Location, extrude
from bimascode.core.type_instance import ElementType
from bimascode.structure.profile import RectangularProfile
from bimascode.utils.materials import Material
from bimascode.utils.units import Length, normalize_length


class ColumnType(ElementType):
    """
    Structural column type defining section profile and properties.

    Column types specify the cross-section profile and material properties
    that are shared across multiple column instances.
    """

    def __init__(
        self,
        name: str,
        profile: RectangularProfile,
        material: Optional[Material] = None,
        description: Optional[str] = None
    ):
        """
        Create a column type.

        Args:
            name: Name for this column type
            profile: Section profile (RectangularProfile)
            material: Material for the column
            description: Optional description
        """
        super().__init__(name)
        self.profile = profile
        self.material = material
        self.description = description

        # Store profile dimensions as type parameters
        self.set_parameter("width", profile.width)
        self.set_parameter("depth", profile.height)

    @property
    def width(self) -> float:
        """Get column width in millimeters."""
        return self.get_parameter("width")

    @property
    def depth(self) -> float:
        """Get column depth in millimeters."""
        return self.get_parameter("depth")

    @property
    def area(self) -> float:
        """Get cross-sectional area in square millimeters."""
        return self.profile.area

    def create_geometry(self, instance: 'StructuralColumn'):
        """
        Create 3D geometry for a column instance.

        The column is created in LOCAL coordinates:
        - Origin at column base center
        - X-axis along width
        - Y-axis along depth
        - Z-axis upward (column height)

        Args:
            instance: Column instance to create geometry for

        Returns:
            build123d Solid representing the column
        """
        # Get column height from instance
        height = instance.get_parameter("height", 3000.0)

        # Create column as extruded profile
        # Use Box for simple rectangular profile
        column_box = Box(self.width, self.depth, height)

        # Position so base is at Z=0 and column is centered in XY
        column_box = column_box.locate(Location(
            (0, 0, height / 2),
            (0, 0, 1), 0
        ))

        return column_box

    def _generate_guid(self) -> str:
        """Generate a unique IFC GUID."""
        import uuid
        return str(uuid.uuid4())

    def to_ifc(self, ifc_file):
        """
        Export column type to IFC.

        Creates IfcColumnType with profile and material association.

        Args:
            ifc_file: IFC file object

        Returns:
            IfcColumnType entity
        """
        # Create IFC profile
        ifc_profile = self.profile.to_ifc(ifc_file)

        # Create IfcColumnType
        ifc_column_type = ifc_file.create_entity(
            "IfcColumnType",
            GlobalId=self.guid,
            Name=self.name,
            Description=self.description,
            PredefinedType="COLUMN"
        )

        # Associate material if present
        if self.material:
            ifc_material = self.material.to_ifc(ifc_file)
            ifc_file.createIfcRelAssociatesMaterial(
                self._generate_guid(),
                None,
                None,
                None,
                [ifc_column_type],
                ifc_material
            )

        return ifc_column_type

    def __repr__(self) -> str:
        return (
            f"ColumnType(name='{self.name}', profile={self.profile.name}, "
            f"width={self.width:.0f}mm, depth={self.depth:.0f}mm)"
        )


# Common column type constructors
def create_rectangular_column_type(
    name: str,
    width: Length | float,
    depth: Length | float,
    material: Optional[Material] = None
) -> ColumnType:
    """
    Create a rectangular column type.

    Args:
        name: Column type name
        width: Column width
        depth: Column depth
        material: Optional material

    Returns:
        ColumnType with rectangular profile
    """
    profile = RectangularProfile(width=width, height=depth)
    return ColumnType(name=name, profile=profile, material=material)


def create_square_column_type(
    name: str,
    size: Length | float,
    material: Optional[Material] = None
) -> ColumnType:
    """
    Create a square column type.

    Args:
        name: Column type name
        size: Column side dimension
        material: Optional material

    Returns:
        ColumnType with square profile
    """
    size_mm = normalize_length(size).mm
    profile = RectangularProfile(width=size_mm, height=size_mm)
    return ColumnType(name=name, profile=profile, material=material)
