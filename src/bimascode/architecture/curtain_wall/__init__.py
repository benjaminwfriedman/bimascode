"""
Curtain wall system for BIM as Code.

This module implements a Revit-compatible curtain wall system with:
- U/V grid layout (U = vertical, V = horizontal)
- Multiple grid layout modes (Fixed Distance, Fixed Number, Maximum Spacing)
- Border and interior mullion types
- Glazed, opaque, empty, and operable panel types
- Freestanding and wall-hosted placement modes
"""

from bimascode.architecture.curtain_wall.mullion_profile import MullionProfile
from bimascode.architecture.curtain_wall.mullion import MullionType, Mullion
from bimascode.architecture.curtain_wall.panel import (
    CurtainPanelType,
    GlazedPanelType,
    OpaquePanelType,
    EmptyPanelType,
    CurtainPanel,
)
from bimascode.architecture.curtain_wall.curtain_grid import (
    GridLayout,
    GridJustification,
    CurtainGridLine,
    GridSegment,
    CurtainCell,
    CurtainGrid,
)
from bimascode.architecture.curtain_wall.curtain_wall_type import CurtainWallType
from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall

__all__ = [
    # Profile
    "MullionProfile",
    # Mullion
    "MullionType",
    "Mullion",
    # Panel types
    "CurtainPanelType",
    "GlazedPanelType",
    "OpaquePanelType",
    "EmptyPanelType",
    "CurtainPanel",
    # Grid
    "GridLayout",
    "GridJustification",
    "CurtainGridLine",
    "GridSegment",
    "CurtainCell",
    "CurtainGrid",
    # Curtain wall
    "CurtainWallType",
    "CurtainWall",
]
