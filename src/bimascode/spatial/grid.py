"""
Grid Lines implementation for architectural layout.
"""

from typing import TYPE_CHECKING

from shapely.geometry import LineString

from ..core.element import Element
from ..utils.units import Length, normalize_length

if TYPE_CHECKING:
    from .building import Building


class GridLine(Element):
    """
    Represents a grid line used for architectural layout coordination.

    Grid lines are labeled axes (A, B, C or 1, 2, 3) that define the
    structural and architectural organization of a building. They span
    vertically through all levels.

    Maps to IfcGridAxis within IfcGrid in IFC export.
    """

    def __init__(
        self,
        building: "Building",
        label: str,
        start_point: tuple[float | Length, float | Length],
        end_point: tuple[float | Length, float | Length],
        description: str | None = None,
    ):
        """
        Create a new grid line.

        Args:
            building: Parent building
            label: Grid line label (e.g., "A", "1", "B.1")
            start_point: (x, y) coordinates of start point
            end_point: (x, y) coordinates of end point
            description: Optional description
        """
        super().__init__(name=f"Grid {label}", description=description)

        self.building = building
        self.label = label

        # Normalize coordinates to mm
        self._start_x = normalize_length(start_point[0], building.length_unit)
        self._start_y = normalize_length(start_point[1], building.length_unit)
        self._end_x = normalize_length(end_point[0], building.length_unit)
        self._end_y = normalize_length(end_point[1], building.length_unit)

        # Create shapely LineString for geometric operations
        self._geometry = LineString(
            [(self._start_x.mm, self._start_y.mm), (self._end_x.mm, self._end_y.mm)]
        )

        # Register with building
        building._grids.append(self)

    @property
    def start_point(self) -> tuple[Length, Length]:
        """Get the start point as (x, y) Length objects."""
        return (self._start_x, self._start_y)

    @property
    def end_point(self) -> tuple[Length, Length]:
        """Get the end point as (x, y) Length objects."""
        return (self._end_x, self._end_y)

    @property
    def start_point_mm(self) -> tuple[float, float]:
        """Get the start point in millimeters."""
        return (self._start_x.mm, self._start_y.mm)

    @property
    def end_point_mm(self) -> tuple[float, float]:
        """Get the end point in millimeters."""
        return (self._end_x.mm, self._end_y.mm)

    @property
    def geometry(self) -> LineString:
        """Get the grid line as a shapely LineString."""
        return self._geometry

    @property
    def length(self) -> Length:
        """Get the length of the grid line."""
        return Length(self._geometry.length, "mm")

    def is_vertical(self, tolerance: float = 0.01) -> bool:
        """
        Check if the grid line is vertical (parallel to Y axis).

        Args:
            tolerance: Tolerance for angle comparison (degrees)

        Returns:
            True if grid line is vertical
        """
        dx = abs(self._end_x.mm - self._start_x.mm)
        dy = abs(self._end_y.mm - self._start_y.mm)

        if dy == 0:
            return False

        # Check if slope is very steep (close to vertical)
        return dx / dy < tolerance

    def is_horizontal(self, tolerance: float = 0.01) -> bool:
        """
        Check if the grid line is horizontal (parallel to X axis).

        Args:
            tolerance: Tolerance for angle comparison (degrees)

        Returns:
            True if grid line is horizontal
        """
        dx = abs(self._end_x.mm - self._start_x.mm)
        dy = abs(self._end_y.mm - self._start_y.mm)

        if dx == 0:
            return False

        # Check if slope is very shallow (close to horizontal)
        return dy / dx < tolerance

    def to_ifc(self, ifc_file):
        """
        Export this grid line to IFC as part of IfcGrid.

        Note: Grid axes are typically exported as a group within an IfcGrid.
        This method creates an IfcGridAxis that can be collected into an IfcGrid.

        Args:
            ifc_file: IfcOpenShell file object

        Returns:
            IfcGridAxis instance
        """
        # Create 2D polyline for the grid axis
        points = [
            ifc_file.createIfcCartesianPoint((self._start_x.mm, self._start_y.mm)),
            ifc_file.createIfcCartesianPoint((self._end_x.mm, self._end_y.mm)),
        ]

        polyline = ifc_file.createIfcPolyline(points)

        # Create grid axis
        # Determine if U or V axis based on orientation
        same_sense = True  # Direction from start to end

        grid_axis = ifc_file.createIfcGridAxis(
            self.label, polyline, same_sense  # AxisTag  # AxisCurve  # SameSense
        )

        return grid_axis

    def __repr__(self) -> str:
        return (
            f"GridLine(label='{self.label}', "
            f"start={self.start_point_mm}, end={self.end_point_mm})"
        )


def create_orthogonal_grid(
    building: "Building",
    x_grid_labels: list,
    x_grid_positions: list,
    y_grid_labels: list,
    y_grid_positions: list,
    x_extent: tuple[float | Length, float | Length],
    y_extent: tuple[float | Length, float | Length],
) -> list:
    """
    Create an orthogonal grid system (common in buildings).

    Args:
        building: Parent building
        x_grid_labels: Labels for vertical grid lines (e.g., ["A", "B", "C"])
        x_grid_positions: X positions for vertical grid lines
        y_grid_labels: Labels for horizontal grid lines (e.g., ["1", "2", "3"])
        y_grid_positions: Y positions for horizontal grid lines
        x_extent: (min_x, max_x) for horizontal grid lines
        y_extent: (min_y, max_y) for vertical grid lines

    Returns:
        List of created GridLine objects
    """
    grids = []

    # Create vertical grid lines (parallel to Y axis)
    for label, x_pos in zip(x_grid_labels, x_grid_positions):
        grid = GridLine(
            building, label=label, start_point=(x_pos, y_extent[0]), end_point=(x_pos, y_extent[1])
        )
        grids.append(grid)

    # Create horizontal grid lines (parallel to X axis)
    for label, y_pos in zip(y_grid_labels, y_grid_positions):
        grid = GridLine(
            building, label=label, start_point=(x_extent[0], y_pos), end_point=(x_extent[1], y_pos)
        )
        grids.append(grid)

    return grids
