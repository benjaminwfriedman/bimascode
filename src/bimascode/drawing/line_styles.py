"""Line weight and line type standards for 2D drawing generation.

Implements AIA/NCS-compliant line weights and standard line types
for architectural and structural drawings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LineWeight(Enum):
    """Standard line weights per AIA/NCS standards.

    Values are in millimeters and correspond to standard pen widths.
    """

    HEAVY = 0.70  # Cut lines (walls, columns) - primary cut elements
    WIDE = 0.50  # Secondary cut (doors, windows)
    MEDIUM = 0.35  # Detail lines, projection lines
    NARROW = 0.25  # Visible projection lines
    FINE = 0.18  # Patterns, secondary projection
    EXTRA_FINE = 0.13  # Annotations, dimension lines

    @classmethod
    def for_cut_element(cls, is_structural: bool = False) -> LineWeight:
        """Get line weight for a cut element.

        Args:
            is_structural: Whether the element is structural

        Returns:
            Appropriate line weight
        """
        return cls.HEAVY if is_structural else cls.WIDE

    @classmethod
    def for_projection(cls, is_hidden: bool = False) -> LineWeight:
        """Get line weight for projected elements.

        Args:
            is_hidden: Whether the element is hidden behind others

        Returns:
            Appropriate line weight
        """
        return cls.FINE if is_hidden else cls.NARROW


class LineType(Enum):
    """Standard line types for architectural drawings."""

    CONTINUOUS = "CONTINUOUS"  # Solid line - cut lines, visible edges
    DASHED = "DASHED"  # Long dash - hidden lines
    HIDDEN = "HIDDEN"  # Short dash - hidden below cut plane
    CENTER = "CENTER"  # Long-short-long - center lines
    PHANTOM = "PHANTOM"  # Long-short-short - alternate positions
    DEMOLISH = "DEMOLISH"  # Short dash with X - demolition
    ABOVE_CUT = "ABOVE"  # Dashed - elements above cut plane

    @property
    def pattern(self) -> tuple[float, ...]:
        """Get dash pattern as tuple of lengths (mm).

        Positive values are dashes, negative values are gaps.
        """
        patterns = {
            LineType.CONTINUOUS: (),
            LineType.DASHED: (6.0, 3.0),
            LineType.HIDDEN: (3.0, 1.5),
            LineType.CENTER: (12.0, 3.0, 3.0, 3.0),
            LineType.PHANTOM: (12.0, 3.0, 3.0, 3.0, 3.0, 3.0),
            LineType.DEMOLISH: (3.0, 1.5, 1.5, 1.5),
            LineType.ABOVE_CUT: (4.0, 2.0),
        }
        return patterns.get(self, ())


@dataclass(frozen=True)
class LineStyle:
    """Complete line styling including weight, type, and color.

    Attributes:
        weight: Line weight (thickness)
        type: Line type (solid, dashed, etc.)
        color: Optional RGB color tuple (0-255)
        is_cut: Whether this is a cut (section) line
    """

    weight: LineWeight
    type: LineType = LineType.CONTINUOUS
    color: tuple[int, int, int] | None = None
    is_cut: bool = False

    @classmethod
    def cut_heavy(cls) -> LineStyle:
        """Heavy cut line for primary structural elements (walls, columns)."""
        return cls(
            weight=LineWeight.HEAVY,
            type=LineType.CONTINUOUS,
            is_cut=True,
        )

    @classmethod
    def cut_wide(cls) -> LineStyle:
        """Wide cut line for secondary elements (doors, windows)."""
        return cls(
            weight=LineWeight.WIDE,
            type=LineType.CONTINUOUS,
            is_cut=True,
        )

    @classmethod
    def cut_medium(cls) -> LineStyle:
        """Medium cut line for detail elements."""
        return cls(
            weight=LineWeight.MEDIUM,
            type=LineType.CONTINUOUS,
            is_cut=True,
        )

    @classmethod
    def visible(cls) -> LineStyle:
        """Visible projection line (below cut plane in floor plan)."""
        return cls(
            weight=LineWeight.NARROW,
            type=LineType.CONTINUOUS,
            is_cut=False,
        )

    @classmethod
    def hidden(cls) -> LineStyle:
        """Hidden line (obscured by other elements)."""
        return cls(
            weight=LineWeight.FINE,
            type=LineType.HIDDEN,
            is_cut=False,
        )

    @classmethod
    def above_cut(cls) -> LineStyle:
        """Line for elements above the cut plane."""
        return cls(
            weight=LineWeight.FINE,
            type=LineType.ABOVE_CUT,
            is_cut=False,
        )

    @classmethod
    def center(cls) -> LineStyle:
        """Center line for symmetry axes."""
        return cls(
            weight=LineWeight.EXTRA_FINE,
            type=LineType.CENTER,
            is_cut=False,
        )

    @classmethod
    def default(cls) -> LineStyle:
        """Default line style for unspecified elements."""
        return cls(
            weight=LineWeight.NARROW,
            type=LineType.CONTINUOUS,
            is_cut=False,
        )

    def with_color(self, color: tuple[int, int, int]) -> LineStyle:
        """Return a copy with the specified color."""
        return LineStyle(
            weight=self.weight,
            type=self.type,
            color=color,
            is_cut=self.is_cut,
        )

    def with_weight(self, weight: LineWeight) -> LineStyle:
        """Return a copy with the specified weight."""
        return LineStyle(
            weight=weight,
            type=self.type,
            color=self.color,
            is_cut=self.is_cut,
        )


# Standard AIA layer naming conventions
class Layer:
    """Standard AIA layer names for architectural drawings."""

    # Architecture
    WALL = "A-WALL"
    WALL_FIRE = "A-WALL-FIRE"
    WALL_CORE = "A-WALL-CORE"
    DOOR = "A-DOOR"
    WINDOW = "A-GLAZ"
    FLOOR = "A-FLOR"
    CEILING = "A-CLNG"
    ROOF = "A-ROOF"
    STAIR = "A-STRS"
    FURNITURE = "A-FURN"

    # Structure
    COLUMN = "S-COLS"
    BEAM = "S-BEAM"
    SLAB = "S-SLAB"
    FOUNDATION = "S-FNDN"

    # Common
    ANNOTATION = "G-ANNO"
    DIMENSION = "G-ANNO-DIMS"
    SYMBOL = "G-ANNO-SYMB"
    GRID = "G-GRID"

    @classmethod
    def for_element_type(cls, element_type: str) -> str:
        """Get the appropriate layer for an element type.

        Args:
            element_type: Element class name (e.g., "Wall", "Door")

        Returns:
            AIA layer name
        """
        mapping = {
            "Wall": cls.WALL,
            "Door": cls.DOOR,
            "Window": cls.WINDOW,
            "Floor": cls.FLOOR,
            "Ceiling": cls.CEILING,
            "Roof": cls.ROOF,
            "Column": cls.COLUMN,
            "Beam": cls.BEAM,
            "Room": cls.ANNOTATION,
        }
        return mapping.get(element_type, "0")
