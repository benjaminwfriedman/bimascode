"""Standard sheet sizes for drawing sheets.

Defines SheetSize frozen dataclass with standard ISO, ANSI, and ARCH sizes.
All dimensions are in millimeters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class SheetSize:
    """Standard sheet size definition.

    Attributes:
        name: Human-readable name (e.g., "A1", "ANSI D")
        width: Sheet width in mm
        height: Sheet height in mm

    Example:
        >>> size = SheetSize.ANSI_D
        >>> print(f"{size.name}: {size.width}mm x {size.height}mm")
        ANSI D: 863.6mm x 558.8mm
    """

    name: str
    width: float  # mm
    height: float  # mm

    # ISO sizes (mm)
    A0: ClassVar[SheetSize]
    A1: ClassVar[SheetSize]
    A2: ClassVar[SheetSize]
    A3: ClassVar[SheetSize]
    A4: ClassVar[SheetSize]

    # ANSI sizes (converted to mm)
    ANSI_A: ClassVar[SheetSize]
    ANSI_B: ClassVar[SheetSize]
    ANSI_C: ClassVar[SheetSize]
    ANSI_D: ClassVar[SheetSize]
    ANSI_E: ClassVar[SheetSize]

    # ARCH sizes (converted to mm)
    ARCH_A: ClassVar[SheetSize]
    ARCH_B: ClassVar[SheetSize]
    ARCH_C: ClassVar[SheetSize]
    ARCH_D: ClassVar[SheetSize]
    ARCH_E: ClassVar[SheetSize]

    @property
    def size_tuple(self) -> tuple[float, float]:
        """Return (width, height) tuple."""
        return (self.width, self.height)

    @property
    def landscape(self) -> bool:
        """Check if sheet is landscape orientation."""
        return self.width > self.height

    @property
    def portrait(self) -> bool:
        """Check if sheet is portrait orientation."""
        return self.height > self.width

    @property
    def area(self) -> float:
        """Get sheet area in square mm."""
        return self.width * self.height

    @classmethod
    def from_string(cls, name: str) -> SheetSize:
        """Look up sheet size by name.

        Supports various name formats:
        - "A1", "A2", etc. for ISO sizes
        - "ANSI D", "ANSI_D", "ANSI-D" for ANSI sizes
        - "ARCH D", "ARCH_D", "ARCH-D" for ARCH sizes

        Args:
            name: Sheet size name

        Returns:
            Matching SheetSize

        Raises:
            ValueError: If size name is not recognized
        """
        # Normalize name: uppercase, replace spaces/hyphens with underscores
        normalized = name.upper().replace(" ", "_").replace("-", "_")

        # Map of normalized names to sizes
        size_map = {
            # ISO
            "A0": cls.A0,
            "A1": cls.A1,
            "A2": cls.A2,
            "A3": cls.A3,
            "A4": cls.A4,
            # ANSI
            "ANSI_A": cls.ANSI_A,
            "ANSI_B": cls.ANSI_B,
            "ANSI_C": cls.ANSI_C,
            "ANSI_D": cls.ANSI_D,
            "ANSI_E": cls.ANSI_E,
            # ARCH
            "ARCH_A": cls.ARCH_A,
            "ARCH_B": cls.ARCH_B,
            "ARCH_C": cls.ARCH_C,
            "ARCH_D": cls.ARCH_D,
            "ARCH_E": cls.ARCH_E,
        }

        if normalized in size_map:
            return size_map[normalized]

        raise ValueError(
            f"Unknown sheet size: '{name}'. " f"Valid sizes: {', '.join(sorted(size_map.keys()))}"
        )

    @classmethod
    def custom(cls, width: float, height: float, name: str = "Custom") -> SheetSize:
        """Create a custom sheet size.

        Args:
            width: Sheet width in mm
            height: Sheet height in mm
            name: Optional name for the custom size

        Returns:
            Custom SheetSize instance
        """
        return cls(name=name, width=width, height=height)


# Initialize ISO sizes (mm)
# ISO 216 standard: A0 = 841 x 1189, each subsequent size is half the previous
SheetSize.A0 = SheetSize("A0", 841.0, 1189.0)
SheetSize.A1 = SheetSize("A1", 594.0, 841.0)
SheetSize.A2 = SheetSize("A2", 420.0, 594.0)
SheetSize.A3 = SheetSize("A3", 297.0, 420.0)
SheetSize.A4 = SheetSize("A4", 210.0, 297.0)

# Initialize ANSI sizes (inches converted to mm, 1 inch = 25.4 mm)
# ANSI/ASME Y14.1 standard
SheetSize.ANSI_A = SheetSize("ANSI A", 215.9, 279.4)  # 8.5" x 11"
SheetSize.ANSI_B = SheetSize("ANSI B", 279.4, 431.8)  # 11" x 17"
SheetSize.ANSI_C = SheetSize("ANSI C", 431.8, 558.8)  # 17" x 22"
SheetSize.ANSI_D = SheetSize("ANSI D", 558.8, 863.6)  # 22" x 34"
SheetSize.ANSI_E = SheetSize("ANSI E", 863.6, 1117.6)  # 34" x 44"

# Initialize ARCH sizes (inches converted to mm)
# Architectural paper sizes
SheetSize.ARCH_A = SheetSize("ARCH A", 228.6, 304.8)  # 9" x 12"
SheetSize.ARCH_B = SheetSize("ARCH B", 304.8, 457.2)  # 12" x 18"
SheetSize.ARCH_C = SheetSize("ARCH C", 457.2, 609.6)  # 18" x 24"
SheetSize.ARCH_D = SheetSize("ARCH D", 609.6, 914.4)  # 24" x 36"
SheetSize.ARCH_E = SheetSize("ARCH E", 914.4, 1219.2)  # 36" x 48"
