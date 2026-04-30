"""Tag annotations for doors, windows, rooms, and section symbols in 2D drawings.

This module provides tag classes that display element marks at their locations,
with support for DXF BLOCK + ATTRIB export.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from bimascode.drawing.line_styles import Layer
from bimascode.drawing.primitives import Point2D

if TYPE_CHECKING:
    from bimascode.architecture.door import Door
    from bimascode.architecture.window import Window
    from bimascode.drawing.section_view import SectionView
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

    def scale(self, factor: float) -> TagStyle:
        """Return a scaled copy of this style.

        Scales size, text_height, and width by the given factor.

        Args:
            factor: Scale factor to apply

        Returns:
            New TagStyle with scaled dimensions
        """
        return TagStyle(
            shape=self.shape,
            size=self.size * factor,
            text_height=self.text_height * factor,
            show_border=self.show_border,
            layer=self.layer,
            width=self.width * factor if self.width is not None else None,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "shape": self.shape.value,
            "size": self.size,
            "text_height": self.text_height,
            "show_border": self.show_border,
            "layer": self.layer,
            "width": self.width,
        }

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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> DoorTag:
        """Return a scaled and translated copy of this tag."""
        new_position = self.insertion_point.scale_and_translate(scale, dx, dy)
        return DoorTag(
            door=self.door,
            position=new_position,
            style=self.style.scale(scale),
            rotation=self.rotation,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "type": "door_tag",
            "insertion_point": self.insertion_point.to_dict(),
            "text": self.text,
            "style": self.style.to_dict(),
            "rotation": self.rotation,
            "layer": self.layer,
            "block_name": self.block_name,
        }


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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> WindowTag:
        """Return a scaled and translated copy of this tag."""
        new_position = self.insertion_point.scale_and_translate(scale, dx, dy)
        return WindowTag(
            window=self.window,
            position=new_position,
            style=self.style.scale(scale),
            rotation=self.rotation,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "type": "window_tag",
            "insertion_point": self.insertion_point.to_dict(),
            "text": self.text,
            "style": self.style.to_dict(),
            "rotation": self.rotation,
            "layer": self.layer,
            "block_name": self.block_name,
        }


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
        from the room's visual center (pole of inaccessibility).
        This ensures the tag is placed inside the room even for
        concave shapes like L-shaped or U-shaped rooms.
        """
        if self.position is not None:
            return self.position

        # Get room visual center (inside polygon, good for labeling)
        center = self.room.get_visual_center()
        return Point2D(center[0], center[1])

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

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> RoomTag:
        """Return a scaled and translated copy of this tag."""
        new_position = self.insertion_point.scale_and_translate(scale, dx, dy)
        return RoomTag(
            room=self.room,
            position=new_position,
            style=self.style.scale(scale),
            rotation=self.rotation,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "type": "room_tag",
            "insertion_point": self.insertion_point.to_dict(),
            "name_text": self.name_text,
            "number_text": self.number_text,
            "text": self.text,
            "style": self.style.to_dict(),
            "rotation": self.rotation,
            "layer": self.layer,
            "block_name": self.block_name,
            "calculated_width": self.calculated_width,
        }


@dataclass(frozen=True)
class SectionSymbolStyle:
    """Style configuration for section symbols.

    A section symbol marks the location of a section cut on a plan view,
    consisting of a cut line with arrow heads and reference bubbles at each end.

    Attributes:
        bubble_radius: Radius of reference bubbles at line ends (mm)
        text_height: Height of the text in bubbles (mm)
        arrow_size: Size of arrow heads (mm)
        line_extension: Extension of cut line beyond bubbles (mm)
        show_arrows: Whether to show arrow heads
        show_bubbles: Whether to show reference bubbles
        layer: CAD layer name for the symbol
    """

    bubble_radius: float = 200.0
    text_height: float = 120.0
    arrow_size: float = 150.0
    line_extension: float = 100.0
    show_arrows: bool = True
    show_bubbles: bool = True
    layer: str = Layer.SYMBOL

    def scale(self, factor: float) -> SectionSymbolStyle:
        """Return a scaled copy of this style.

        Args:
            factor: Scale factor to apply

        Returns:
            New SectionSymbolStyle with scaled dimensions
        """
        return SectionSymbolStyle(
            bubble_radius=self.bubble_radius * factor,
            text_height=self.text_height * factor,
            arrow_size=self.arrow_size * factor,
            line_extension=self.line_extension * factor,
            show_arrows=self.show_arrows,
            show_bubbles=self.show_bubbles,
            layer=self.layer,
        )

    @classmethod
    def default(cls) -> SectionSymbolStyle:
        """Default style for section symbols."""
        return cls()

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "bubble_radius": self.bubble_radius,
            "text_height": self.text_height,
            "arrow_size": self.arrow_size,
            "line_extension": self.line_extension,
            "show_arrows": self.show_arrows,
            "show_bubbles": self.show_bubbles,
            "layer": self.layer,
        }


@dataclass(frozen=True)
class SectionSymbol:
    """Symbol marking a section cut on a plan view.

    Displays a section cut line with arrow heads indicating view direction
    and circular reference bubbles at each end containing section/sheet numbers.
    Exports to DXF as BLOCK references with ATTRIB.

    The symbol consists of:
    - A cut line between start_point and end_point
    - Arrow heads pointing in the view direction
    - Reference bubbles (circles) at each end with identifiers

    Attributes:
        start_point: Start point of cut line on plan (mm)
        end_point: End point of cut line on plan (mm)
        section_id: Section identifier (e.g., "A", "1")
        sheet_number: Destination sheet number (e.g., "A2", "S-101")
        look_direction: Direction the view looks ("left" or "right" of line)
        section_view: Optional reference to the SectionView being marked
        style: Symbol style configuration
        rotation: Symbol rotation in degrees (0 = auto from line direction)

    Example:
        >>> symbol = SectionSymbol(
        ...     start_point=Point2D(5000, 0),
        ...     end_point=Point2D(5000, 10000),
        ...     section_id="A",
        ...     sheet_number="A2",
        ...     look_direction="right",
        ... )
    """

    start_point: Point2D
    end_point: Point2D
    section_id: str = "A"
    sheet_number: str = ""
    look_direction: str = "right"  # "left" or "right" of line direction
    section_view: SectionView | None = None
    style: SectionSymbolStyle = field(default_factory=SectionSymbolStyle.default)
    rotation: float = 0.0

    @property
    def line_angle(self) -> float:
        """Get the angle of the section line in radians."""
        dx = self.end_point.x - self.start_point.x
        dy = self.end_point.y - self.start_point.y
        return math.atan2(dy, dx)

    @property
    def line_length(self) -> float:
        """Get the length of the section line."""
        return self.start_point.distance_to(self.end_point)

    @property
    def arrow_angle(self) -> float:
        """Get the arrow direction angle in radians.

        Arrow points perpendicular to the line in the look direction.
        """
        line_angle = self.line_angle
        if self.look_direction == "right":
            # Clockwise perpendicular
            return line_angle - math.pi / 2
        else:
            # Counter-clockwise perpendicular
            return line_angle + math.pi / 2

    @property
    def midpoint(self) -> Point2D:
        """Get the midpoint of the section line."""
        return Point2D(
            (self.start_point.x + self.end_point.x) / 2,
            (self.start_point.y + self.end_point.y) / 2,
        )

    @property
    def start_label(self) -> str:
        """Get the label text for the start bubble."""
        return self.section_id

    @property
    def end_label(self) -> str:
        """Get the label text for the end bubble."""
        return self.section_id

    @property
    def start_sheet(self) -> str:
        """Get the sheet number text for the start bubble."""
        return self.sheet_number

    @property
    def end_sheet(self) -> str:
        """Get the sheet number text for the end bubble."""
        return self.sheet_number

    @property
    def layer(self) -> str:
        """Get the layer for this symbol."""
        return self.style.layer

    @property
    def block_name(self) -> str:
        """Get the DXF block name for this symbol type.

        Includes style parameters in the name to ensure unique
        block definitions for different configurations.
        """
        return (
            f"SECTION_SYMBOL_{int(self.style.bubble_radius)}_"
            f"{int(self.style.text_height)}_{int(self.style.arrow_size)}"
        )

    def get_start_bubble_center(self) -> Point2D:
        """Get the center point of the start reference bubble.

        The bubble is offset from the line endpoint by the bubble radius.
        """
        angle = self.line_angle + math.pi  # Opposite direction from line
        offset = self.style.bubble_radius + self.style.line_extension
        return Point2D(
            self.start_point.x + offset * math.cos(angle),
            self.start_point.y + offset * math.sin(angle),
        )

    def get_end_bubble_center(self) -> Point2D:
        """Get the center point of the end reference bubble.

        The bubble is offset from the line endpoint by the bubble radius.
        """
        angle = self.line_angle  # Same direction as line
        offset = self.style.bubble_radius + self.style.line_extension
        return Point2D(
            self.end_point.x + offset * math.cos(angle),
            self.end_point.y + offset * math.sin(angle),
        )

    def translate(self, dx: float, dy: float) -> SectionSymbol:
        """Return a translated copy of this symbol."""
        return SectionSymbol(
            start_point=self.start_point.translate(dx, dy),
            end_point=self.end_point.translate(dx, dy),
            section_id=self.section_id,
            sheet_number=self.sheet_number,
            look_direction=self.look_direction,
            section_view=self.section_view,
            style=self.style,
            rotation=self.rotation,
        )

    def scale_and_translate(self, scale: float, dx: float, dy: float) -> SectionSymbol:
        """Return a scaled and translated copy of this symbol."""
        return SectionSymbol(
            start_point=self.start_point.scale_and_translate(scale, dx, dy),
            end_point=self.end_point.scale_and_translate(scale, dx, dy),
            section_id=self.section_id,
            sheet_number=self.sheet_number,
            look_direction=self.look_direction,
            section_view=self.section_view,
            style=self.style.scale(scale),
            rotation=self.rotation,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "type": "section_symbol",
            "start_point": self.start_point.to_dict(),
            "end_point": self.end_point.to_dict(),
            "section_id": self.section_id,
            "sheet_number": self.sheet_number,
            "look_direction": self.look_direction,
            "style": self.style.to_dict(),
            "rotation": self.rotation,
            "layer": self.layer,
            "block_name": self.block_name,
            "line_angle": self.line_angle,
            "line_length": self.line_length,
            "arrow_angle": self.arrow_angle,
            "midpoint": self.midpoint.to_dict(),
            "start_bubble_center": self.get_start_bubble_center().to_dict(),
            "end_bubble_center": self.get_end_bubble_center().to_dict(),
        }

    @classmethod
    def from_section_view(
        cls,
        section_view: SectionView,
        start_point: Point2D,
        end_point: Point2D,
        section_id: str = "A",
        sheet_number: str = "",
        style: SectionSymbolStyle | None = None,
    ) -> SectionSymbol:
        """Create a section symbol from a SectionView.

        Automatically determines the look direction from the section view's
        plane normal.

        Args:
            section_view: The SectionView being marked
            start_point: Start point of cut line on plan
            end_point: End point of cut line on plan
            section_id: Section identifier (e.g., "A", "1")
            sheet_number: Destination sheet number
            style: Optional style override

        Returns:
            SectionSymbol configured for the section view

        Example:
            >>> section = SectionView.from_section_line(
            ...     "Section A-A",
            ...     start_point=(5000, 0),
            ...     end_point=(5000, 10000),
            ...     look_direction="right",
            ... )
            >>> symbol = SectionSymbol.from_section_view(
            ...     section,
            ...     Point2D(5000, 0),
            ...     Point2D(5000, 10000),
            ...     section_id="A",
            ...     sheet_number="A2",
            ... )
        """
        # Determine look direction from section view's plane normal
        # The plane normal points in the view direction
        nx, ny, nz = section_view.plane_normal

        # Calculate line direction vector
        line_dx = end_point.x - start_point.x
        line_dy = end_point.y - start_point.y
        line_length = math.sqrt(line_dx * line_dx + line_dy * line_dy)
        if line_length > 0:
            line_dx /= line_length
            line_dy /= line_length

        # Cross product of line direction and normal determines side
        # If cross product Z component is positive, looking left; negative, looking right
        cross_z = line_dx * ny - line_dy * nx
        look_direction = "left" if cross_z > 0 else "right"

        return cls(
            start_point=start_point,
            end_point=end_point,
            section_id=section_id,
            sheet_number=sheet_number,
            look_direction=look_direction,
            section_view=section_view,
            style=style or SectionSymbolStyle.default(),
        )


# Type alias for any tag type
Tag2D = DoorTag | WindowTag | RoomTag | SectionSymbol
