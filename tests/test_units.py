"""
Unit tests for units system.
"""

from bimascode.utils.units import (
    Length,
    LengthUnit,
    UnitSystem,
    normalize_length,
)


class TestLength:
    """Test Length class."""

    def test_creation_mm(self):
        """Test creating length in millimeters."""
        length = Length(100, "mm")
        assert length.mm == 100

    def test_creation_meters(self):
        """Test creating length in meters."""
        length = Length(1, "m")
        assert length.mm == 1000
        assert length.m == 1

    def test_creation_feet(self):
        """Test creating length in feet."""
        length = Length(1, "ft")
        assert abs(length.mm - 304.8) < 0.01
        assert abs(length.feet - 1) < 0.0001

    def test_conversion(self):
        """Test unit conversions."""
        length = Length(1000, "mm")
        assert length.cm == 100
        assert length.m == 1
        assert abs(length.inches - 39.37) < 0.01
        assert abs(length.feet - 3.28) < 0.01

    def test_arithmetic_add(self):
        """Test addition."""
        l1 = Length(100, "mm")
        l2 = Length(50, "mm")
        result = l1 + l2
        assert result.mm == 150

    def test_arithmetic_subtract(self):
        """Test subtraction."""
        l1 = Length(100, "mm")
        l2 = Length(30, "mm")
        result = l1 - l2
        assert result.mm == 70

    def test_arithmetic_multiply(self):
        """Test multiplication."""
        length = Length(100, "mm")
        result = length * 2
        assert result.mm == 200

    def test_arithmetic_divide(self):
        """Test division."""
        length = Length(100, "mm")
        result = length / 2
        assert result.mm == 50

    def test_comparison(self):
        """Test comparison operations."""
        l1 = Length(100, "mm")
        l2 = Length(10, "cm")
        l3 = Length(50, "mm")

        assert l1 == l2
        assert l1 > l3
        assert l3 < l1


class TestNormalization:
    """Test normalization functions."""

    def test_normalize_length_from_length(self):
        """Test normalizing a Length object."""
        length = Length(100, "mm")
        normalized = normalize_length(length)
        assert normalized.mm == 100

    def test_normalize_length_from_float(self):
        """Test normalizing a float."""
        normalized = normalize_length(100.0, LengthUnit.MILLIMETER)
        assert normalized.mm == 100

    def test_normalize_length_default_unit(self):
        """Test normalization with default unit."""
        normalized = normalize_length(100)
        assert normalized.mm == 100


class TestUnitSystem:
    """Test unit system enum."""

    def test_unit_system_values(self):
        """Test unit system enum values."""
        assert UnitSystem.METRIC.value == "metric"
        assert UnitSystem.IMPERIAL.value == "imperial"

    def test_unit_system_from_string(self):
        """Test creating unit system from string."""
        metric = UnitSystem("metric")
        assert metric == UnitSystem.METRIC

        imperial = UnitSystem("imperial")
        assert imperial == UnitSystem.IMPERIAL
