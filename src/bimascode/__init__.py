"""
BIM as Code - A Python library for programmatic Building Information Modeling.
"""

__version__ = "0.1.0"

# Core classes
from .core import Element, ElementType, ElementInstance

# Spatial organization
from .spatial import Building, Level

# Architecture
from .architecture import (
    WallType,
    Wall,
    FloorType,
    Floor,
    Roof,
    Layer,
    LayerFunction,
)

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
