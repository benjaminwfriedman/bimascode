"""
BIM as Code - A Python library for programmatic Building Information Modeling.
"""

__version__ = "0.1.0"

# Core classes
from .core import Element

# Spatial organization
from .spatial import Building, Level

# Units
from .utils import (
    UnitSystem,
    LengthUnit,
    Length,
    Area,
    Volume,
    Angle,
)

__all__ = [
    # Core
    "Element",
    # Spatial
    "Building",
    "Level",
    # Units
    "UnitSystem",
    "LengthUnit",
    "Length",
    "Area",
    "Volume",
    "Angle",
]
