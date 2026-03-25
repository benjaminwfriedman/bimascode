"""Tag annotations for doors and windows in 2D drawings.

This module provides tag classes that display element marks at their locations,
with support for DXF BLOCK + ATTRIB export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from bimascode.drawing.line_styles import Layer
from bimascode.drawing.primitives import Point2D

if TYPE_CHECKING:
    from bimascode.architecture.door import Door
    from bimascode.architecture.window import Window


class TagShape(Enum):
    """Shape of the tag symbol."""

    HEXAGON = "HEXAGON"
    CIRCLE = "CIRCLE"
    RECTANGLE = "RECTANGLE"
    DIAMOND = "DIAMOND"


@dataclass(frozen=True)
class TagStyle:
    """Style configuration for tags.

    Attributes:
        shape: Shape of the tag symbol
        size: Size of the tag in mm (diameter for circle, width for others)
        text_height: Height of the text in mm
        show_border: Whether to show the tag border
        layer: CAD layer name for the tag
    """

    shape: TagShape = TagShape.HEXAGON
    size: float = 300.0
    text_height: float = 100.0
    show_border: bool = True
    layer: str = Layer.SYMBOL

    @classmethod
    def door_default(cls) -> TagStyle:
        """Default style for door tags (hexagon)."""
        return cls(
            shape=TagShape.HEXAGON,
            size=500.0,
            text_height=150.0,
            show_border=True,
            layer=Layer.SYMBOL,
        )

    @classmethod
    def window_default(cls) -> TagStyle:
        """Default style for window tags (circle)."""
        return cls(
            shape=TagShape.CIRCLE,
            size=450.0,
            text_height=150.0,
            show_border=True,
            layer=Layer.SYMBOL,
        )


@dataclass(frozen=True)
class DoorTag:
    """Tag annotation for a door element.

    Displays the door's mark at the door location in floor plan views.
    Exports to DXF as a BLOCK reference with ATTRIB for the mark text.

    Attributes:
        door: The door element to tag
        position: Override position (None = use door center)
        style: Tag style configuration
        rotation: Tag rotation in degrees

    Example:
        >>> door = Door(door_type, wall, offset=3400, mark="101")
        >>> tag = DoorTag(door=door)
        >>> tag.text  # "101"
    """

    door: Door
    position: Point2D | None = None
    style: TagStyle = field(default_factory=TagStyle.door_default)
    rotation: float = 0.0

    @property
    def text(self) -> str:
        """Get the tag text from the door's mark."""
        return self.door.mark or ""

    @property
    def insertion_point(self) -> Point2D:
        """Get the tag insertion point.

        Returns the override position if set, otherwise calculates
        from the door's world position.
        """
        if self.position is not None:
            return self.position

        # Get door center position (x, y from world position)
        world_pos = self.door.get_world_position()
        return Point2D(world_pos[0], world_pos[1])

    @property
    def layer(self) -> str:
        """Get the layer for this tag."""
        return self.style.layer

    @property
    def block_name(self) -> str:
        """Get the DXF block name for this tag type.

        Includes size and text_height in the name to ensure unique
        block definitions for different style configurations.
        """
        return f"DOOR_TAG_{self.style.shape.value}_{int(self.style.size)}_{int(self.style.text_height)}"

    def translate(self, dx: float, dy: float) -> DoorTag:
        """Return a translated copy of this tag."""
        new_position = self.insertion_point.translate(dx, dy)
        return DoorTag(
            door=self.door,
            position=new_position,
            style=self.style,
            rotation=self.rotation,
        )


@dataclass(frozen=True)
class WindowTag:
    """Tag annotation for a window element.

    Displays the window's mark at the window location in floor plan views.
    Exports to DXF as a BLOCK reference with ATTRIB for the mark text.

    Attributes:
        window: The window element to tag
        position: Override position (None = use window center)
        style: Tag style configuration
        rotation: Tag rotation in degrees

    Example:
        >>> window = Window(window_type, wall, offset=2000, mark="W-1")
        >>> tag = WindowTag(window=window)
        >>> tag.text  # "W-1"
    """

    window: Window
    position: Point2D | None = None
    style: TagStyle = field(default_factory=TagStyle.window_default)
    rotation: float = 0.0

    @property
    def text(self) -> str:
        """Get the tag text from the window's mark."""
        return self.window.mark or ""

    @property
    def insertion_point(self) -> Point2D:
        """Get the tag insertion point.

        Returns the override position if set, otherwise calculates
        from the window's world position.
        """
        if self.position is not None:
            return self.position

        # Get window center position (x, y from world position)
        world_pos = self.window.get_world_position()
        return Point2D(world_pos[0], world_pos[1])

    @property
    def layer(self) -> str:
        """Get the layer for this tag."""
        return self.style.layer

    @property
    def block_name(self) -> str:
        """Get the DXF block name for this tag type.

        Includes size and text_height in the name to ensure unique
        block definitions for different style configurations.
        """
        return f"WINDOW_TAG_{self.style.shape.value}_{int(self.style.size)}_{int(self.style.text_height)}"

    def translate(self, dx: float, dy: float) -> WindowTag:
        """Return a translated copy of this tag."""
        new_position = self.insertion_point.translate(dx, dy)
        return WindowTag(
            window=self.window,
            position=new_position,
            style=self.style,
            rotation=self.rotation,
        )


# Type alias for any tag type
Tag2D = DoorTag | WindowTag
