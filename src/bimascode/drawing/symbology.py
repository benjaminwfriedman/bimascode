"""Element symbology configuration for 2D drawing generation.

Provides configurable per-element-type visualization settings with
AIA/NCS defaults and user overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from bimascode.drawing.line_styles import LineStyle

if TYPE_CHECKING:
    from bimascode.core.element import Element


class FillMode(Enum):
    """Fill mode for cut elements in plan/section views."""

    MATERIAL = "material"  # Use material-based hatch patterns
    SOLID = "solid"  # Solid fill
    EMPTY = "empty"  # No fill (outline only)
    PATTERN = "pattern"  # Use specific named pattern


@dataclass(frozen=True)
class ElementSymbology:
    """Symbology settings for an element type.

    Defines how an element type should be visualized in 2D views,
    including line styles for different display states and fill behavior.

    Attributes:
        cut_style: Line style when element is cut by section plane
        visible_style: Line style when element is below cut plane
        above_style: Line style when element is above cut plane
        fill_mode: How to fill cut regions
        fill_pattern: Pattern name when fill_mode is PATTERN
        fill_color: Override color for SOLID fill mode
        show_swing: Show door swing arc (doors only)
        show_panel: Show door panel line (doors only)
        show_x_pattern: Show X diagonal pattern (columns only)
        outline_only: Show only outline, no internal lines (windows)
        show_hatching: Enable/disable hatching for this element
        show_jambs: Show door/window jamb lines
    """

    # Line styles for different display states
    cut_style: LineStyle | None = None
    visible_style: LineStyle | None = None
    above_style: LineStyle | None = None

    # Fill configuration
    fill_mode: FillMode = FillMode.MATERIAL
    fill_pattern: str | None = None
    fill_color: tuple[int, int, int] | None = None

    # Element-specific flags
    show_swing: bool = True
    show_panel: bool = True
    show_x_pattern: bool = True
    outline_only: bool = False
    show_hatching: bool = True
    show_jambs: bool = True


# AIA/NCS default symbology for each element type
_AIA_DEFAULTS: dict[str, ElementSymbology] = {
    "Wall": ElementSymbology(
        cut_style=LineStyle.cut_heavy(),
        visible_style=LineStyle.visible(),
        fill_mode=FillMode.MATERIAL,
        show_hatching=True,
    ),
    "Door": ElementSymbology(
        cut_style=LineStyle.cut_wide(),
        fill_mode=FillMode.EMPTY,
        show_swing=True,
        show_panel=True,
        show_jambs=True,
    ),
    "Window": ElementSymbology(
        cut_style=LineStyle.cut_wide(),
        fill_mode=FillMode.EMPTY,
        outline_only=False,
        show_jambs=True,
    ),
    "Floor": ElementSymbology(
        cut_style=LineStyle.cut_medium(),
        visible_style=LineStyle.visible(),
        fill_mode=FillMode.MATERIAL,
        show_hatching=True,
    ),
    "StructuralColumn": ElementSymbology(
        cut_style=LineStyle.cut_heavy(),
        visible_style=LineStyle.visible(),
        fill_mode=FillMode.EMPTY,
        show_x_pattern=True,
    ),
    "Ceiling": ElementSymbology(
        cut_style=LineStyle.cut_medium(),
        visible_style=LineStyle.visible(),
        above_style=LineStyle.above_cut(),
        fill_mode=FillMode.EMPTY,
    ),
    "Beam": ElementSymbology(
        cut_style=LineStyle.cut_heavy(),
        above_style=LineStyle.above_cut(),
        fill_mode=FillMode.EMPTY,
    ),
}

# Fallback symbology for unknown element types
_DEFAULT_SYMBOLOGY = ElementSymbology(
    cut_style=LineStyle.cut_medium(),
    visible_style=LineStyle.visible(),
    above_style=LineStyle.above_cut(),
    fill_mode=FillMode.EMPTY,
)


def get_default_symbology(element_type_name: str) -> ElementSymbology:
    """Get AIA/NCS default symbology for an element type.

    Args:
        element_type_name: Class name of the element (e.g., "Wall", "Door")

    Returns:
        Default ElementSymbology for the type
    """
    return _AIA_DEFAULTS.get(element_type_name, _DEFAULT_SYMBOLOGY)


class SymbologySettings:
    """Collection of symbology settings for element types.

    Provides AIA/NCS defaults with the ability to override symbology
    for specific element types. Tracks a version number for cache
    invalidation when settings change.

    Example:
        >>> from bimascode.architecture import Window, Door
        >>> settings = SymbologySettings()
        >>> settings.set(Window, ElementSymbology(outline_only=True))
        >>> window_symbology = settings.get(Window)
    """

    def __init__(self) -> None:
        """Initialize with empty overrides (uses AIA defaults)."""
        self._overrides: dict[str, ElementSymbology] = {}
        self._version: int = 0

    @property
    def version(self) -> int:
        """Version counter, incremented on any change.

        Used for cache invalidation when symbology settings change.
        """
        return self._version

    def get(self, element_type: type) -> ElementSymbology:
        """Get symbology for an element class.

        Args:
            element_type: Element class (e.g., Wall, Door)

        Returns:
            ElementSymbology for the type (override or AIA default)
        """
        type_name = element_type.__name__
        if type_name in self._overrides:
            return self._overrides[type_name]
        return get_default_symbology(type_name)

    def get_for_element(self, element: Element) -> ElementSymbology:
        """Get symbology for an element instance.

        Args:
            element: Element instance

        Returns:
            ElementSymbology for the element's type
        """
        return self.get(type(element))

    def set(self, element_type: type, symbology: ElementSymbology) -> None:
        """Set symbology override for an element class.

        Args:
            element_type: Element class (e.g., Wall, Door)
            symbology: Symbology settings to use
        """
        self._overrides[element_type.__name__] = symbology
        self._version += 1

    def reset(self, element_type: type | None = None) -> None:
        """Reset symbology to AIA defaults.

        Args:
            element_type: Element class to reset, or None to reset all
        """
        if element_type is not None:
            type_name = element_type.__name__
            if type_name in self._overrides:
                del self._overrides[type_name]
                self._version += 1
        else:
            if self._overrides:
                self._overrides.clear()
                self._version += 1

    @classmethod
    def aia_defaults(cls) -> SymbologySettings:
        """Create settings with all AIA defaults (no overrides).

        Returns:
            New SymbologySettings instance with default settings
        """
        return cls()

    @classmethod
    def simplified(cls) -> SymbologySettings:
        """Create simplified symbology (no hatching, minimal details).

        Useful for small scale views or schematic diagrams where
        detailed representation is not needed.

        Returns:
            SymbologySettings with simplified visualization
        """
        # Import here to avoid circular imports
        from bimascode.architecture.ceiling import Ceiling
        from bimascode.architecture.door import Door
        from bimascode.architecture.floor import Floor
        from bimascode.architecture.wall import Wall
        from bimascode.structure.column import StructuralColumn

        settings = cls()

        # Disable hatching for compound elements
        settings.set(
            Wall,
            ElementSymbology(
                cut_style=LineStyle.cut_heavy(),
                visible_style=LineStyle.visible(),
                fill_mode=FillMode.EMPTY,
                show_hatching=False,
            ),
        )
        settings.set(
            Floor,
            ElementSymbology(
                cut_style=LineStyle.cut_medium(),
                visible_style=LineStyle.visible(),
                fill_mode=FillMode.EMPTY,
                show_hatching=False,
            ),
        )
        settings.set(
            Ceiling,
            ElementSymbology(
                cut_style=LineStyle.cut_medium(),
                above_style=LineStyle.above_cut(),
                fill_mode=FillMode.EMPTY,
            ),
        )

        # Disable column X pattern
        settings.set(
            StructuralColumn,
            ElementSymbology(
                cut_style=LineStyle.cut_heavy(),
                visible_style=LineStyle.visible(),
                fill_mode=FillMode.EMPTY,
                show_x_pattern=False,
            ),
        )

        # Disable door swing
        settings.set(
            Door,
            ElementSymbology(
                cut_style=LineStyle.cut_wide(),
                fill_mode=FillMode.EMPTY,
                show_swing=False,
                show_panel=True,
                show_jambs=True,
            ),
        )

        return settings
