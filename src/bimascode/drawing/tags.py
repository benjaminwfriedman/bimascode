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
    from bimascode.spatial.room import Room


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
        size: Size of the tag in mm (diameter for circle, height for rectangle)
        text_height: Height of the text in mm
        show_border: Whether to show the tag border
        layer: CAD layer name for the tag
        width: Width of the tag in mm (only used for RECTANGLE shape, defaults to size)
    """

    shape: TagShape = TagShape.HEXAGON
    size: float = 300.0
    text_height: float = 100.0
    show_border: bool = True
    layer: str = Layer.SYMBOL
    width: float | None = None

    @property
    def effective_width(self) -> float:
        """Get the effective width (uses width if set, otherwise size)."""
        return self.width if self.width is not None else self.size

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

    @classmethod
    def room_default(cls) -> TagStyle:
        """Default style for room tags (rectangle with name and number).

        Note: width is None by default, which triggers auto-sizing based on
        text length in RoomTag. Set width explicitly to override auto-sizing.
        """
        return cls(
            shape=TagShape.RECTANGLE,
            size=400.0,  # Height
            text_height=120.0,
            show_border=True,
            layer=Layer.SYMBOL,
            width=None,  # Auto-size based on text length
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


@dataclass(frozen=True)
class RoomTag:
    """Tag annotation for a room element.

    Displays the room's name and number at the room centroid in floor plan views.
    Exports to DXF as a BLOCK reference with ATTRIB for the text content.

    The tag displays two lines of text:
    - Line 1: Room name (e.g., "Living Room")
    - Line 2: Room number (e.g., "101")

    Attributes:
        room: The room element to tag
        position: Override position (None = use room centroid)
        style: Tag style configuration
        rotation: Tag rotation in degrees

    Example:
        >>> room = Room("Living Room", "101", boundary, level)
        >>> tag = RoomTag(room=room)
        >>> tag.name_text  # "Living Room"
        >>> tag.number_text  # "101"
    """

    room: Room
    position: Point2D | None = None
    style: TagStyle = field(default_factory=TagStyle.room_default)
    rotation: float = 0.0

    @property
    def name_text(self) -> str:
        """Get the room name text."""
        return self.room.name or ""

    @property
    def number_text(self) -> str:
        """Get the room number text."""
        return self.room.number or ""

    @property
    def text(self) -> str:
        """Get combined tag text (name and number on separate lines)."""
        name = self.name_text
        number = self.number_text
        if name and number:
            return f"{name}\n{number}"
        return name or number

    @property
    def insertion_point(self) -> Point2D:
        """Get the tag insertion point.

        Returns the override position if set, otherwise calculates
        from the room's centroid.
        """
        if self.position is not None:
            return self.position

        # Get room centroid position
        centroid = self.room.get_centroid()
        return Point2D(centroid[0], centroid[1])

    @property
    def layer(self) -> str:
        """Get the layer for this tag."""
        return self.style.layer

    @property
    def calculated_width(self) -> float:
        """Calculate the tag width based on text content.

        If style.width is explicitly set, uses that value.
        Otherwise, auto-calculates based on the longest text line
        using an approximate character width ratio.

        Returns:
            Width in mm that fits the text content.
        """
        # If width is explicitly set, use it
        if self.style.width is not None:
            return self.style.width

        # Auto-calculate based on text length
        # Use the longer of name or number
        name_len = len(self.name_text)
        number_len = len(self.number_text)
        max_chars = max(name_len, number_len, 1)  # At least 1 char

        # Approximate width: each character is ~0.8x text height for typical fonts
        # Add padding on each side (2.5x text height total)
        char_width = self.style.text_height * 0.8
        padding = self.style.text_height * 2.5
        calculated = max_chars * char_width + padding

        # Minimum width to ensure tag looks reasonable
        min_width = self.style.size  # At least as wide as it is tall

        return max(calculated, min_width)

    @property
    def block_name(self) -> str:
        """Get the DXF block name for this tag type.

        Includes size, calculated width, and text_height in the name to ensure
        unique block definitions for different style configurations.
        """
        width = int(self.calculated_width)
        return f"ROOM_TAG_{self.style.shape.value}_{int(self.style.size)}_{width}_{int(self.style.text_height)}"

    def translate(self, dx: float, dy: float) -> RoomTag:
        """Return a translated copy of this tag."""
        new_position = self.insertion_point.translate(dx, dy)
        return RoomTag(
            room=self.room,
            position=new_position,
            style=self.style,
            rotation=self.rotation,
        )


# Type alias for any tag type
Tag2D = DoorTag | WindowTag | RoomTag
