"""
Curtain grid system for curtain walls.

The curtain grid defines the U/V layout of a curtain wall:
- U direction: Vertical (up the wall)
- V direction: Horizontal (along the wall base)

This matches Revit's CurtainGrid coordinate system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bimascode.architecture.curtain_wall.mullion import Mullion
    from bimascode.architecture.curtain_wall.panel import CurtainPanel


class GridLayout(Enum):
    """
    Grid layout mode for automatic grid generation.

    Matches Revit's Layout parameter options.
    """

    NONE = "none"
    """No automatic grids - manual placement only."""

    FIXED_DISTANCE = "fixed_distance"
    """Uniform spacing. Remainder panel at justified end."""

    FIXED_NUMBER = "fixed_number"
    """Exact grid count. Spacing calculated automatically."""

    MAXIMUM_SPACING = "maximum_spacing"
    """Upper bound on spacing. System distributes evenly."""


class GridJustification(Enum):
    """
    Justification for remainder panels when using FIXED_DISTANCE layout.

    Matches Revit's Justification parameter.
    """

    BEGINNING = "beginning"
    """Remainder panel at the end (right/top)."""

    CENTER = "center"
    """Remainder split between both ends."""

    END = "end"
    """Remainder panel at the beginning (left/bottom)."""


@dataclass
class GridSegment:
    """
    A segment of a grid line between intersections.

    Each segment can host a mullion. Removing a segment effectively
    merges adjacent panels into one.
    """

    start_position: float
    """Start position along the grid line (mm)."""

    end_position: float
    """End position along the grid line (mm)."""

    mullion: "Mullion | None" = None
    """The mullion placed on this segment, if any."""

    removed: bool = False
    """If True, segment is removed (no mullion, panels merge)."""

    @property
    def length(self) -> float:
        """Get segment length in mm."""
        return self.end_position - self.start_position

    @property
    def midpoint(self) -> float:
        """Get segment midpoint position."""
        return (self.start_position + self.end_position) / 2

    def __repr__(self) -> str:
        status = "removed" if self.removed else ("has mullion" if self.mullion else "empty")
        return f"GridSegment({self.start_position:.0f}-{self.end_position:.0f}mm, {status})"


@dataclass
class CurtainGridLine:
    """
    A single grid line in U or V direction.

    Grid lines divide the curtain wall into cells. Each line consists
    of segments between intersections with perpendicular lines.
    """

    direction: str
    """Direction: 'U' (vertical) or 'V' (horizontal)."""

    position: float
    """Position along perpendicular axis (mm from origin)."""

    segments: list[GridSegment] = field(default_factory=list)
    """Segments between intersections."""

    is_border: bool = False
    """True if this is an edge line (border_1 or border_2)."""

    border_type: int = 0
    """Border type: 0=interior, 1=border_1 (left/bottom), 2=border_2 (right/top)."""

    @property
    def is_vertical(self) -> bool:
        """Check if this is a vertical (U direction) grid line."""
        return self.direction == "U"

    @property
    def is_horizontal(self) -> bool:
        """Check if this is a horizontal (V direction) grid line."""
        return self.direction == "V"

    @property
    def total_length(self) -> float:
        """Get total length of all segments."""
        return sum(seg.length for seg in self.segments)

    def get_segment_at(self, position: float) -> GridSegment | None:
        """
        Get the segment containing the given position.

        Args:
            position: Position along the grid line

        Returns:
            GridSegment containing the position, or None
        """
        for segment in self.segments:
            if segment.start_position <= position <= segment.end_position:
                return segment
        return None

    def __repr__(self) -> str:
        border_str = f", border_{self.border_type}" if self.is_border else ""
        return (
            f"CurtainGridLine(direction='{self.direction}', "
            f"position={self.position:.0f}mm, "
            f"segments={len(self.segments)}{border_str})"
        )


@dataclass
class CurtainCell:
    """
    A bounded area between grid lines.

    Cells are containers for panels. Each cell is defined by its
    position in the U/V grid and its geometric bounds.
    """

    u_index: int
    """Column index (0 = leftmost)."""

    v_index: int
    """Row index (0 = bottom)."""

    x_start: float
    """Left edge position (mm)."""

    y_start: float
    """Bottom edge position (mm)."""

    width: float
    """Cell width (mm)."""

    height: float
    """Cell height (mm)."""

    panel: "CurtainPanel | None" = None
    """The panel filling this cell, if any."""

    merged_with: "CurtainCell | None" = None
    """If this cell is merged, reference to the primary cell."""

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Get cell bounds as (x_start, y_start, width, height)."""
        return (self.x_start, self.y_start, self.width, self.height)

    @property
    def center(self) -> tuple[float, float]:
        """Get cell center point (x, y)."""
        return (self.x_start + self.width / 2, self.y_start + self.height / 2)

    @property
    def x_end(self) -> float:
        """Get right edge position."""
        return self.x_start + self.width

    @property
    def y_end(self) -> float:
        """Get top edge position."""
        return self.y_start + self.height

    @property
    def area(self) -> float:
        """Get cell area in square mm."""
        return self.width * self.height

    @property
    def is_merged(self) -> bool:
        """Check if this cell is merged with another."""
        return self.merged_with is not None

    def __repr__(self) -> str:
        status = "merged" if self.is_merged else ("has panel" if self.panel else "empty")
        return (
            f"CurtainCell(u={self.u_index}, v={self.v_index}, "
            f"size={self.width:.0f}x{self.height:.0f}mm, {status})"
        )


class CurtainGrid:
    """
    UV grid defining the cell layout of a curtain wall.

    The grid consists of:
    - U lines: Vertical grid lines (running up the wall)
    - V lines: Horizontal grid lines (running along the wall base)
    - Cells: Bounded areas between grid lines

    This matches Revit's CurtainGrid object.
    """

    def __init__(self, width: float, height: float):
        """
        Create an empty curtain grid.

        Args:
            width: Total curtain wall width (mm)
            height: Total curtain wall height (mm)
        """
        self._width = width
        self._height = height
        self._u_lines: list[CurtainGridLine] = []  # Vertical lines
        self._v_lines: list[CurtainGridLine] = []  # Horizontal lines
        self._cells: list[list[CurtainCell]] = []  # 2D array [u][v]

    @property
    def width(self) -> float:
        """Get total grid width in mm."""
        return self._width

    @property
    def height(self) -> float:
        """Get total grid height in mm."""
        return self._height

    @property
    def u_lines(self) -> list[CurtainGridLine]:
        """Get all U (vertical) grid lines."""
        return self._u_lines

    @property
    def v_lines(self) -> list[CurtainGridLine]:
        """Get all V (horizontal) grid lines."""
        return self._v_lines

    @property
    def cells(self) -> list[list[CurtainCell]]:
        """Get 2D array of cells [u_index][v_index]."""
        return self._cells

    @property
    def u_count(self) -> int:
        """Get number of U divisions (columns of panels)."""
        return max(0, len(self._u_lines) - 1)

    @property
    def v_count(self) -> int:
        """Get number of V divisions (rows of panels)."""
        return max(0, len(self._v_lines) - 1)

    @property
    def cell_count(self) -> int:
        """Get total number of cells."""
        return self.u_count * self.v_count

    def get_cell(self, u_index: int, v_index: int) -> CurtainCell | None:
        """
        Get a cell by its grid indices.

        Args:
            u_index: Column index (0 = leftmost)
            v_index: Row index (0 = bottom)

        Returns:
            CurtainCell at the given indices, or None if out of range
        """
        if 0 <= u_index < len(self._cells) and 0 <= v_index < len(self._cells[u_index]):
            return self._cells[u_index][v_index]
        return None

    def get_u_position(self, index: int) -> float:
        """
        Get the X position of a U (vertical) grid line.

        Args:
            index: U line index (0 = left edge)

        Returns:
            X position in mm
        """
        if 0 <= index < len(self._u_lines):
            return self._u_lines[index].position
        raise IndexError(f"U line index {index} out of range")

    def get_v_position(self, index: int) -> float:
        """
        Get the Y position of a V (horizontal) grid line.

        Args:
            index: V line index (0 = bottom edge)

        Returns:
            Y position in mm
        """
        if 0 <= index < len(self._v_lines):
            return self._v_lines[index].position
        raise IndexError(f"V line index {index} out of range")

    def generate_fixed_distance(
        self,
        u_spacing: float,
        v_spacing: float,
        u_justification: GridJustification = GridJustification.BEGINNING,
        v_justification: GridJustification = GridJustification.BEGINNING,
    ) -> None:
        """
        Generate grid with fixed distance spacing.

        Creates uniform grid spacing with remainder panels at the
        justified end.

        Args:
            u_spacing: Horizontal spacing between vertical lines (mm)
            v_spacing: Vertical spacing between horizontal lines (mm)
            u_justification: Where to place remainder in U direction
            v_justification: Where to place remainder in V direction
        """
        self._u_lines = self._generate_lines_fixed_distance(
            total=self._width,
            spacing=u_spacing,
            justification=u_justification,
            direction="U",
        )
        self._v_lines = self._generate_lines_fixed_distance(
            total=self._height,
            spacing=v_spacing,
            justification=v_justification,
            direction="V",
        )
        self._generate_cells()
        self._generate_segments()

    def generate_fixed_number(
        self,
        u_divisions: int,
        v_divisions: int,
    ) -> None:
        """
        Generate grid with fixed number of divisions.

        Creates exact number of panels with calculated spacing.

        Args:
            u_divisions: Number of horizontal divisions (panel columns)
            v_divisions: Number of vertical divisions (panel rows)
        """
        self._u_lines = self._generate_lines_fixed_number(
            total=self._width,
            divisions=u_divisions,
            direction="U",
        )
        self._v_lines = self._generate_lines_fixed_number(
            total=self._height,
            divisions=v_divisions,
            direction="V",
        )
        self._generate_cells()
        self._generate_segments()

    def generate_maximum_spacing(
        self,
        u_max_spacing: float,
        v_max_spacing: float,
    ) -> None:
        """
        Generate grid with maximum spacing constraint.

        Creates evenly distributed grid lines with spacing not exceeding
        the maximum.

        Args:
            u_max_spacing: Maximum horizontal spacing (mm)
            v_max_spacing: Maximum vertical spacing (mm)
        """
        self._u_lines = self._generate_lines_max_spacing(
            total=self._width,
            max_spacing=u_max_spacing,
            direction="U",
        )
        self._v_lines = self._generate_lines_max_spacing(
            total=self._height,
            max_spacing=v_max_spacing,
            direction="V",
        )
        self._generate_cells()
        self._generate_segments()

    def _generate_lines_fixed_distance(
        self,
        total: float,
        spacing: float,
        justification: GridJustification,
        direction: str,
    ) -> list[CurtainGridLine]:
        """Generate grid lines with fixed distance spacing."""
        if spacing <= 0:
            # No interior lines, just borders
            return [
                CurtainGridLine(direction=direction, position=0, is_border=True, border_type=1),
                CurtainGridLine(direction=direction, position=total, is_border=True, border_type=2),
            ]

        # Calculate number of full-size panels
        num_full_panels = int(total // spacing)
        remainder = total - (num_full_panels * spacing)

        # Generate positions based on justification
        positions = []
        if justification == GridJustification.BEGINNING:
            # Start from 0, remainder at end
            pos = 0.0
            for i in range(num_full_panels + 1):
                positions.append(pos)
                if i < num_full_panels:
                    pos += spacing
            if remainder > 1e-6:
                positions.append(total)
        elif justification == GridJustification.END:
            # Start with remainder, then full panels
            pos = 0.0
            positions.append(pos)
            if remainder > 1e-6:
                pos = remainder
                positions.append(pos)
            for i in range(num_full_panels):
                pos += spacing
                positions.append(pos)
        else:  # CENTER
            # Split remainder between start and end
            half_remainder = remainder / 2
            pos = 0.0
            positions.append(pos)
            if half_remainder > 1e-6:
                pos = half_remainder
                positions.append(pos)
            for i in range(num_full_panels - 1):
                pos += spacing
                positions.append(pos)
            if half_remainder > 1e-6:
                pos += spacing
                positions.append(pos)
            positions.append(total)

        # Ensure unique sorted positions
        positions = sorted(set(positions))

        # Create grid lines
        lines = []
        for i, pos in enumerate(positions):
            is_border = (i == 0) or (i == len(positions) - 1)
            border_type = 1 if i == 0 else (2 if i == len(positions) - 1 else 0)
            lines.append(
                CurtainGridLine(
                    direction=direction,
                    position=pos,
                    is_border=is_border,
                    border_type=border_type,
                )
            )
        return lines

    def _generate_lines_fixed_number(
        self,
        total: float,
        divisions: int,
        direction: str,
    ) -> list[CurtainGridLine]:
        """Generate grid lines with fixed number of divisions."""
        if divisions < 1:
            divisions = 1

        spacing = total / divisions
        positions = [i * spacing for i in range(divisions + 1)]

        lines = []
        for i, pos in enumerate(positions):
            is_border = (i == 0) or (i == len(positions) - 1)
            border_type = 1 if i == 0 else (2 if i == len(positions) - 1 else 0)
            lines.append(
                CurtainGridLine(
                    direction=direction,
                    position=pos,
                    is_border=is_border,
                    border_type=border_type,
                )
            )
        return lines

    def _generate_lines_max_spacing(
        self,
        total: float,
        max_spacing: float,
        direction: str,
    ) -> list[CurtainGridLine]:
        """Generate grid lines with maximum spacing constraint."""
        if max_spacing <= 0:
            max_spacing = total

        # Calculate minimum number of divisions needed
        num_divisions = max(1, int((total + max_spacing - 1) // max_spacing))

        # Use fixed number with calculated divisions
        return self._generate_lines_fixed_number(total, num_divisions, direction)

    def _generate_cells(self) -> None:
        """Generate cells from grid lines."""
        self._cells = []

        if len(self._u_lines) < 2 or len(self._v_lines) < 2:
            return

        for u in range(len(self._u_lines) - 1):
            column = []
            x_start = self._u_lines[u].position
            x_end = self._u_lines[u + 1].position
            width = x_end - x_start

            for v in range(len(self._v_lines) - 1):
                y_start = self._v_lines[v].position
                y_end = self._v_lines[v + 1].position
                height = y_end - y_start

                cell = CurtainCell(
                    u_index=u,
                    v_index=v,
                    x_start=x_start,
                    y_start=y_start,
                    width=width,
                    height=height,
                )
                column.append(cell)
            self._cells.append(column)

    def _generate_segments(self) -> None:
        """Generate segments for all grid lines."""
        # Vertical lines (U) get segments based on V line positions
        for u_line in self._u_lines:
            u_line.segments = []
            for v in range(len(self._v_lines) - 1):
                start_pos = self._v_lines[v].position
                end_pos = self._v_lines[v + 1].position
                u_line.segments.append(GridSegment(start_position=start_pos, end_position=end_pos))

        # Horizontal lines (V) get segments based on U line positions
        for v_line in self._v_lines:
            v_line.segments = []
            for u in range(len(self._u_lines) - 1):
                start_pos = self._u_lines[u].position
                end_pos = self._u_lines[u + 1].position
                v_line.segments.append(GridSegment(start_position=start_pos, end_position=end_pos))

    def add_grid_line(self, direction: str, position: float) -> CurtainGridLine | None:
        """
        Add a new grid line at the specified position.

        Args:
            direction: 'U' (vertical) or 'V' (horizontal)
            position: Position along perpendicular axis (mm)

        Returns:
            The new CurtainGridLine, or None if position is invalid
        """
        if direction == "U":
            if not (0 < position < self._width):
                return None
            new_line = CurtainGridLine(direction=direction, position=position)
            self._u_lines.append(new_line)
            self._u_lines.sort(key=lambda line: line.position)
        elif direction == "V":
            if not (0 < position < self._height):
                return None
            new_line = CurtainGridLine(direction=direction, position=position)
            self._v_lines.append(new_line)
            self._v_lines.sort(key=lambda line: line.position)
        else:
            return None

        # Regenerate cells and segments
        self._generate_cells()
        self._generate_segments()
        return new_line

    def remove_segment(self, grid_line: CurtainGridLine, segment: GridSegment) -> bool:
        """
        Remove a grid segment, effectively merging adjacent panels.

        Args:
            grid_line: The grid line containing the segment
            segment: The segment to remove

        Returns:
            True if segment was removed, False otherwise
        """
        if segment not in grid_line.segments:
            return False

        segment.removed = True
        segment.mullion = None

        # Mark affected cells as merged
        # TODO: Implement cell merging logic

        return True

    def get_all_segments(self) -> list[tuple[CurtainGridLine, GridSegment]]:
        """
        Get all grid segments with their parent lines.

        Returns:
            List of (grid_line, segment) tuples
        """
        segments = []
        for line in self._u_lines + self._v_lines:
            for segment in line.segments:
                segments.append((line, segment))
        return segments

    def __repr__(self) -> str:
        return (
            f"CurtainGrid(size={self._width:.0f}x{self._height:.0f}mm, "
            f"u_lines={len(self._u_lines)}, v_lines={len(self._v_lines)}, "
            f"cells={self.cell_count})"
        )
