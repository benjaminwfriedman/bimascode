"""
Units management for BIM as Code.

This module provides unit-aware measurement classes and conversion utilities.
All internal storage uses millimeters as the base unit.
"""

from enum import Enum


class UnitSystem(Enum):
    """Supported unit systems."""

    METRIC = "metric"
    IMPERIAL = "imperial"


class LengthUnit(Enum):
    """Supported length units."""

    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    INCH = "in"
    FOOT = "ft"


class AreaUnit(Enum):
    """Supported area units."""

    SQUARE_MILLIMETER = "mm²"
    SQUARE_METER = "m²"
    SQUARE_INCH = "in²"
    SQUARE_FOOT = "ft²"


class VolumeUnit(Enum):
    """Supported volume units."""

    CUBIC_MILLIMETER = "mm³"
    CUBIC_METER = "m³"
    CUBIC_INCH = "in³"
    CUBIC_FOOT = "ft³"


class AngleUnit(Enum):
    """Supported angle units."""

    DEGREE = "deg"
    RADIAN = "rad"


# Conversion factors to millimeters (base unit)
LENGTH_TO_MM = {
    LengthUnit.MILLIMETER: 1.0,
    LengthUnit.CENTIMETER: 10.0,
    LengthUnit.METER: 1000.0,
    LengthUnit.INCH: 25.4,
    LengthUnit.FOOT: 304.8,
}

# Conversion factors to square millimeters (base unit)
AREA_TO_MM2 = {
    AreaUnit.SQUARE_MILLIMETER: 1.0,
    AreaUnit.SQUARE_METER: 1_000_000.0,
    AreaUnit.SQUARE_INCH: 645.16,
    AreaUnit.SQUARE_FOOT: 92_903.04,
}

# Conversion factors to cubic millimeters (base unit)
VOLUME_TO_MM3 = {
    VolumeUnit.CUBIC_MILLIMETER: 1.0,
    VolumeUnit.CUBIC_METER: 1_000_000_000.0,
    VolumeUnit.CUBIC_INCH: 16_387.064,
    VolumeUnit.CUBIC_FOOT: 28_316_846.592,
}

# Conversion factors to radians (base unit)
ANGLE_TO_RAD = {
    AngleUnit.RADIAN: 1.0,
    AngleUnit.DEGREE: 0.017453292519943295,  # π/180
}


class Length:
    """
    Unit-aware length measurement.

    Stores internally in millimeters for consistency.
    """

    def __init__(self, value: float, unit: str | LengthUnit = LengthUnit.MILLIMETER):
        """
        Create a length measurement.

        Args:
            value: Numeric value
            unit: Unit of measurement (default: millimeters)
        """
        if isinstance(unit, str):
            unit = LengthUnit(unit)

        self._mm = value * LENGTH_TO_MM[unit]

    @property
    def mm(self) -> float:
        """Get value in millimeters."""
        return self._mm

    @property
    def cm(self) -> float:
        """Get value in centimeters."""
        return self._mm / LENGTH_TO_MM[LengthUnit.CENTIMETER]

    @property
    def m(self) -> float:
        """Get value in meters."""
        return self._mm / LENGTH_TO_MM[LengthUnit.METER]

    @property
    def inches(self) -> float:
        """Get value in inches."""
        return self._mm / LENGTH_TO_MM[LengthUnit.INCH]

    @property
    def feet(self) -> float:
        """Get value in feet."""
        return self._mm / LENGTH_TO_MM[LengthUnit.FOOT]

    def to(self, unit: str | LengthUnit) -> float:
        """
        Convert to specified unit.

        Args:
            unit: Target unit

        Returns:
            Value in target unit
        """
        if isinstance(unit, str):
            unit = LengthUnit(unit)

        return self._mm / LENGTH_TO_MM[unit]

    def __repr__(self) -> str:
        return f"Length({self._mm} mm)"

    def __str__(self) -> str:
        return f"{self._mm} mm"

    def __float__(self) -> float:
        """Return value in millimeters when cast to float."""
        return self._mm

    def __add__(self, other):
        if isinstance(other, Length):
            return Length(self._mm + other._mm, LengthUnit.MILLIMETER)
        elif isinstance(other, (int, float)):
            return Length(self._mm + other, LengthUnit.MILLIMETER)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Length):
            return Length(self._mm - other._mm, LengthUnit.MILLIMETER)
        elif isinstance(other, (int, float)):
            return Length(self._mm - other, LengthUnit.MILLIMETER)
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Length(self._mm * other, LengthUnit.MILLIMETER)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            return Length(self._mm / other, LengthUnit.MILLIMETER)
        elif isinstance(other, Length):
            return self._mm / other._mm
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Length):
            return abs(self._mm - other._mm) < 1e-6
        return False

    def __lt__(self, other):
        if isinstance(other, Length):
            return self._mm < other._mm
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Length):
            return self._mm <= other._mm
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Length):
            return self._mm > other._mm
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Length):
            return self._mm >= other._mm
        return NotImplemented


class Area:
    """
    Unit-aware area measurement.

    Stores internally in square millimeters for consistency.
    """

    def __init__(self, value: float, unit: str | AreaUnit = AreaUnit.SQUARE_MILLIMETER):
        """
        Create an area measurement.

        Args:
            value: Numeric value
            unit: Unit of measurement (default: square millimeters)
        """
        if isinstance(unit, str):
            unit = AreaUnit(unit)

        self._mm2 = value * AREA_TO_MM2[unit]

    @property
    def mm2(self) -> float:
        """Get value in square millimeters."""
        return self._mm2

    @property
    def m2(self) -> float:
        """Get value in square meters."""
        return self._mm2 / AREA_TO_MM2[AreaUnit.SQUARE_METER]

    @property
    def square_inches(self) -> float:
        """Get value in square inches."""
        return self._mm2 / AREA_TO_MM2[AreaUnit.SQUARE_INCH]

    @property
    def square_feet(self) -> float:
        """Get value in square feet."""
        return self._mm2 / AREA_TO_MM2[AreaUnit.SQUARE_FOOT]

    def to(self, unit: str | AreaUnit) -> float:
        """
        Convert to specified unit.

        Args:
            unit: Target unit

        Returns:
            Value in target unit
        """
        if isinstance(unit, str):
            unit = AreaUnit(unit)

        return self._mm2 / AREA_TO_MM2[unit]

    def __repr__(self) -> str:
        return f"Area({self._mm2} mm²)"

    def __str__(self) -> str:
        return f"{self._mm2} mm²"


class Volume:
    """
    Unit-aware volume measurement.

    Stores internally in cubic millimeters for consistency.
    """

    def __init__(self, value: float, unit: str | VolumeUnit = VolumeUnit.CUBIC_MILLIMETER):
        """
        Create a volume measurement.

        Args:
            value: Numeric value
            unit: Unit of measurement (default: cubic millimeters)
        """
        if isinstance(unit, str):
            unit = VolumeUnit(unit)

        self._mm3 = value * VOLUME_TO_MM3[unit]

    @property
    def mm3(self) -> float:
        """Get value in cubic millimeters."""
        return self._mm3

    @property
    def m3(self) -> float:
        """Get value in cubic meters."""
        return self._mm3 / VOLUME_TO_MM3[VolumeUnit.CUBIC_METER]

    @property
    def cubic_inches(self) -> float:
        """Get value in cubic inches."""
        return self._mm3 / VOLUME_TO_MM3[VolumeUnit.CUBIC_INCH]

    @property
    def cubic_feet(self) -> float:
        """Get value in cubic feet."""
        return self._mm3 / VOLUME_TO_MM3[VolumeUnit.CUBIC_FOOT]

    def to(self, unit: str | VolumeUnit) -> float:
        """
        Convert to specified unit.

        Args:
            unit: Target unit

        Returns:
            Value in target unit
        """
        if isinstance(unit, str):
            unit = VolumeUnit(unit)

        return self._mm3 / VOLUME_TO_MM3[unit]

    def __repr__(self) -> str:
        return f"Volume({self._mm3} mm³)"

    def __str__(self) -> str:
        return f"{self._mm3} mm³"


class Angle:
    """
    Unit-aware angle measurement.

    Stores internally in radians for consistency.
    """

    def __init__(self, value: float, unit: str | AngleUnit = AngleUnit.RADIAN):
        """
        Create an angle measurement.

        Args:
            value: Numeric value
            unit: Unit of measurement (default: radians)
        """
        if isinstance(unit, str):
            unit = AngleUnit(unit)

        self._rad = value * ANGLE_TO_RAD[unit]

    @property
    def radians(self) -> float:
        """Get value in radians."""
        return self._rad

    @property
    def degrees(self) -> float:
        """Get value in degrees."""
        return self._rad / ANGLE_TO_RAD[AngleUnit.DEGREE]

    def to(self, unit: str | AngleUnit) -> float:
        """
        Convert to specified unit.

        Args:
            unit: Target unit

        Returns:
            Value in target unit
        """
        if isinstance(unit, str):
            unit = AngleUnit(unit)

        return self._rad / ANGLE_TO_RAD[unit]

    def __repr__(self) -> str:
        return f"Angle({self._rad} rad)"

    def __str__(self) -> str:
        return f"{self._rad} rad"


def normalize_length(
    value: float | int | Length, default_unit: LengthUnit = LengthUnit.MILLIMETER
) -> Length:
    """
    Normalize a value to a Length object.

    Args:
        value: Numeric value or Length object
        default_unit: Unit to use if value is numeric (default: millimeters)

    Returns:
        Length object
    """
    if isinstance(value, Length):
        return value
    elif isinstance(value, (int, float)):
        return Length(value, default_unit)
    else:
        raise TypeError(f"Cannot convert {type(value)} to Length")


def normalize_angle(
    value: float | int | Angle, default_unit: AngleUnit = AngleUnit.RADIAN
) -> Angle:
    """
    Normalize a value to an Angle object.

    Args:
        value: Numeric value or Angle object
        default_unit: Unit to use if value is numeric (default: radians)

    Returns:
        Angle object
    """
    if isinstance(value, Angle):
        return value
    elif isinstance(value, (int, float)):
        return Angle(value, default_unit)
    else:
        raise TypeError(f"Cannot convert {type(value)} to Angle")
