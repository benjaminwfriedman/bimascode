"""
BIM as Code - A Python library for programmatic Building Information Modeling.
"""

__version__ = "0.1.0"

# Core classes
# Architecture
from .architecture import (
    Floor,
    FloorType,
    Layer,
    LayerFunction,
    Roof,
    Wall,
    WallType,
)
from .core import Element, ElementInstance, ElementType

# Spatial organization
from .spatial import Building, Level

# Units
from .utils import (
    Angle,
    Area,
    Length,
    LengthUnit,
    UnitSystem,
    Volume,
)

__all__ = [
    # Core
    "Element",
    "ElementType",
    "ElementInstance",
    # Spatial
    "Building",
    "Level",
    # Architecture
    "WallType",
    "Wall",
    "FloorType",
    "Floor",
    "Roof",
    "Layer",
    "LayerFunction",
    # Units
    "UnitSystem",
    "LengthUnit",
    "Length",
    "Area",
    "Volume",
    "Angle",
]
