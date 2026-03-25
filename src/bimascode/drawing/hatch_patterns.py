"""Hatch patterns for material representation in section views.

Maps MaterialCategory to standard AIA/NCS hatch patterns for
architectural documentation.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bimascode.utils.materials import MaterialCategory

if TYPE_CHECKING:
    from bimascode.architecture.wall_type import Layer
    from bimascode.utils.materials import Material


@dataclass(frozen=True)
class HatchPattern:
    """Definition of a hatch pattern for a material.

    Attributes:
        name: DXF pattern name (e.g., "SOLID", "ANSI31", "AR-CONC")
        scale: Pattern scale factor (default 1.0)
        rotation: Pattern rotation in degrees (default 0.0)
        color: Optional RGB color tuple (0-255)
    """

    name: str
    scale: float = 1.0
    rotation: float = 0.0
    color: tuple[int, int, int] | None = None


# AIA/NCS standard material-to-hatch mappings
# Pattern names follow DXF/AutoCAD conventions
MATERIAL_HATCH_PATTERNS: dict[MaterialCategory, HatchPattern] = {
    # Structural materials
    MaterialCategory.CONCRETE: HatchPattern("AR-CONC", scale=0.02),
    MaterialCategory.STEEL: HatchPattern("ANSI31", scale=0.5),
    MaterialCategory.WOOD: HatchPattern("AR-PARQ1", scale=0.01),
    MaterialCategory.MASONRY: HatchPattern("AR-BRSTD", scale=0.02),
    # Envelope materials
    MaterialCategory.GLASS: HatchPattern("SOLID", color=(200, 230, 255)),
    MaterialCategory.INSULATION: HatchPattern("INSUL", scale=0.02),
    # Finish materials
    MaterialCategory.GYPSUM: HatchPattern("SOLID", color=(240, 240, 240)),
    MaterialCategory.METAL: HatchPattern("ANSI31", scale=0.5),
    MaterialCategory.PLASTIC: HatchPattern("ANSI34", scale=0.5),
    MaterialCategory.MEMBRANE: HatchPattern("SOLID", color=(128, 128, 128)),
    MaterialCategory.FINISH: HatchPattern("SOLID"),
    MaterialCategory.OTHER: HatchPattern("SOLID"),
}

# Default pattern when material or category is unknown
DEFAULT_HATCH_PATTERN = HatchPattern("SOLID")


def get_hatch_pattern_for_material(material: "Material | None") -> HatchPattern:
    """Get the appropriate hatch pattern for a material.

    Args:
        material: Material instance with category attribute, or None

    Returns:
        HatchPattern for the material's category, or default SOLID pattern
    """
    if material is None or material.category is None:
        return DEFAULT_HATCH_PATTERN

    return MATERIAL_HATCH_PATTERNS.get(material.category, DEFAULT_HATCH_PATTERN)


def get_hatch_pattern_for_layer(layer: "Layer") -> HatchPattern:
    """Get the hatch pattern for a wall/floor layer.

    Args:
        layer: Layer instance with material attribute

    Returns:
        HatchPattern for the layer's material
    """
    return get_hatch_pattern_for_material(layer.material)
