"""
Section profiles for structural elements.

This module defines cross-section profiles used for columns and beams.
For Sprint 4, only rectangular profiles are implemented.
Full AISC catalog is Sprint 10 scope.
"""


from build123d import Face, Rectangle

from bimascode.utils.units import Length, normalize_length


class RectangularProfile:
    """
    Rectangular cross-section profile for columns and beams.

    Represents a simple rectangular section with width and height dimensions.
    """

    def __init__(self, width: Length | float, height: Length | float, name: str | None = None):
        """
        Create a rectangular profile.

        Args:
            width: Profile width in millimeters (or Length object)
            height: Profile height in millimeters (or Length object)
            name: Optional name for the profile
        """
        self._width = normalize_length(width).mm
        self._height = normalize_length(height).mm
        self.name = name or f"Rectangular_{self._width:.0f}x{self._height:.0f}"

    @property
    def width(self) -> float:
        """Get profile width in millimeters."""
        return self._width

    @property
    def height(self) -> float:
        """Get profile height in millimeters."""
        return self._height

    @property
    def area(self) -> float:
        """Get cross-sectional area in square millimeters."""
        return self._width * self._height

    @property
    def area_m2(self) -> float:
        """Get cross-sectional area in square meters."""
        return self.area / 1_000_000.0

    @property
    def moment_of_inertia_x(self) -> float:
        """
        Get moment of inertia about the X-axis (horizontal) in mm^4.

        For a rectangle: I_x = (width * height^3) / 12
        """
        return (self._width * self._height**3) / 12.0

    @property
    def moment_of_inertia_y(self) -> float:
        """
        Get moment of inertia about the Y-axis (vertical) in mm^4.

        For a rectangle: I_y = (height * width^3) / 12
        """
        return (self._height * self._width**3) / 12.0

    @property
    def section_modulus_x(self) -> float:
        """
        Get section modulus about the X-axis in mm^3.

        S_x = I_x / (height / 2)
        """
        return self.moment_of_inertia_x / (self._height / 2)

    @property
    def section_modulus_y(self) -> float:
        """
        Get section modulus about the Y-axis in mm^3.

        S_y = I_y / (width / 2)
        """
        return self.moment_of_inertia_y / (self._width / 2)

    def to_build123d(self) -> Face:
        """
        Convert profile to a build123d Face for extrusion.

        Returns:
            build123d Rectangle face centered at origin
        """
        return Rectangle(self._width, self._height)

    def to_ifc(self, ifc_file) -> any:
        """
        Export profile to IFC as IfcRectangleProfileDef.

        Args:
            ifc_file: IFC file object

        Returns:
            IfcRectangleProfileDef entity
        """
        # Create axis placement at origin
        location = ifc_file.createIfcCartesianPoint((0.0, 0.0))
        x_axis = ifc_file.createIfcDirection((1.0, 0.0))

        axis_placement = ifc_file.createIfcAxis2Placement2D(location, x_axis)

        # Create rectangle profile
        profile = ifc_file.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            ProfileName=self.name,
            Position=axis_placement,
            XDim=float(self._width),
            YDim=float(self._height),
        )

        return profile

    def __repr__(self) -> str:
        return f"RectangularProfile(name='{self.name}', width={self._width:.0f}mm, height={self._height:.0f}mm)"

    def __eq__(self, other):
        if not isinstance(other, RectangularProfile):
            return False
        return abs(self._width - other._width) < 1e-6 and abs(self._height - other._height) < 1e-6


# Common profile constructors
def create_square_profile(size: Length | float, name: str | None = None) -> RectangularProfile:
    """
    Create a square profile.

    Args:
        size: Side dimension in millimeters
        name: Optional profile name

    Returns:
        RectangularProfile with equal width and height
    """
    size_mm = normalize_length(size).mm
    return RectangularProfile(
        width=size_mm, height=size_mm, name=name or f"Square_{size_mm:.0f}x{size_mm:.0f}"
    )


def create_column_profile(
    width: Length | float, depth: Length | float, name: str | None = None
) -> RectangularProfile:
    """
    Create a column profile.

    Args:
        width: Column width (parallel to wall)
        depth: Column depth (perpendicular to wall)
        name: Optional profile name

    Returns:
        RectangularProfile for column use
    """
    return RectangularProfile(width=width, height=depth, name=name)


def create_beam_profile(
    width: Length | float, height: Length | float, name: str | None = None
) -> RectangularProfile:
    """
    Create a beam profile.

    Args:
        width: Beam width
        height: Beam height (depth)
        name: Optional profile name

    Returns:
        RectangularProfile for beam use
    """
    return RectangularProfile(width=width, height=height, name=name)
