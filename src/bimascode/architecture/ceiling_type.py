"""
Ceiling types for BIM as Code.

This module implements the CeilingType class which defines ceiling
assemblies with thickness and material properties.
"""

from typing import Optional, List
from build123d import Box, Polygon as BD_Polygon, extrude, Location
from bimascode.core.type_instance import ElementType
from bimascode.utils.materials import Material
from bimascode.utils.units import Length, normalize_length


class CeilingType(ElementType):
    """
    Ceiling type defining thickness and material properties.

    Ceiling types specify the construction assembly that can be applied
    to multiple ceiling instances.
    """

    def __init__(
        self,
        name: str,
        thickness: Length | float = 15.0,
        material: Optional[Material] = None,
        description: Optional[str] = None
    ):
        """
        Create a ceiling type.

        Args:
            name: Name for this ceiling type
            thickness: Ceiling thickness (default 15mm for gypsum board)
            material: Material for the ceiling
            description: Optional description
        """
        super().__init__(name)
        self.material = material
        self.description = description

        # Store thickness as type parameter
        self.set_parameter("thickness", normalize_length(thickness).mm)

    @property
    def thickness(self) -> float:
        """Get ceiling thickness in millimeters."""
        return self.get_parameter("thickness")

    def create_geometry(self, instance: 'Ceiling'):
        """
        Create 3D geometry for a ceiling instance.

        The ceiling is created in LOCAL coordinates:
        - Origin at (0, 0, 0)
        - Z-axis upward
        - Ceiling extends downward from the specified height

        Args:
            instance: Ceiling instance to create geometry for

        Returns:
            build123d Solid representing the ceiling
        """
        boundary = instance.boundary
        thickness = self.thickness

        if len(boundary) < 3:
            return None

        # Create polygon outline from boundary points
        # boundary is list of (x, y) tuples
        polygon = BD_Polygon(boundary)

        # Extrude the polygon to create the ceiling slab
        # Ceiling hangs down from specified height
        ceiling_solid = extrude(polygon, thickness)

        return ceiling_solid

    def _generate_guid(self) -> str:
        """Generate a unique IFC GUID."""
        import uuid
        return str(uuid.uuid4())

    def to_ifc(self, ifc_file):
        """
        Export ceiling type to IFC.

        Creates IfcCoveringType with CEILING predefined type.

        Args:
            ifc_file: IFC file object

        Returns:
            IfcCoveringType entity
        """
        # Create IfcCoveringType
        ifc_covering_type = ifc_file.create_entity(
            "IfcCoveringType",
            GlobalId=self.guid,
            Name=self.name,
            Description=self.description,
            PredefinedType="CEILING"
        )

        # Associate material if present
        if self.material:
            ifc_material = self.material.to_ifc(ifc_file)
            ifc_file.createIfcRelAssociatesMaterial(
                self._generate_guid(),
                None,
                None,
                None,
                [ifc_covering_type],
                ifc_material
            )

        return ifc_covering_type

    def __repr__(self) -> str:
        return f"CeilingType(name='{self.name}', thickness={self.thickness:.0f}mm)"


# Common ceiling type constructors
def create_gypsum_ceiling_type(
    name: str,
    thickness: Length | float = 15.0,
    material: Optional[Material] = None
) -> CeilingType:
    """
    Create a standard gypsum board ceiling type.

    Args:
        name: Ceiling type name
        thickness: Ceiling thickness (default 15mm)
        material: Optional gypsum material

    Returns:
        CeilingType for gypsum board ceiling
    """
    return CeilingType(
        name=name,
        thickness=thickness,
        material=material,
        description=f"{name} - Gypsum Board Ceiling"
    )


def create_suspended_ceiling_type(
    name: str,
    thickness: Length | float = 20.0,
    material: Optional[Material] = None
) -> CeilingType:
    """
    Create a suspended/drop ceiling type.

    Args:
        name: Ceiling type name
        thickness: Tile thickness (default 20mm)
        material: Optional material

    Returns:
        CeilingType for suspended ceiling
    """
    return CeilingType(
        name=name,
        thickness=thickness,
        material=material,
        description=f"{name} - Suspended Ceiling"
    )
