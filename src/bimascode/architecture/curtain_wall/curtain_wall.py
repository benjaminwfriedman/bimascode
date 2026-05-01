"""
Freestanding curtain wall element.

CurtainWall is placed like a regular wall using start/end points,
and generates mullions and panels based on its type settings.
"""

from __future__ import annotations

import copy
import math
from typing import TYPE_CHECKING, Any

from build123d import Compound, Location, Pos, Rotation

from bimascode.architecture.curtain_wall.curtain_grid import (
    CurtainGrid,
    CurtainGridLine,
    GridSegment,
)
from bimascode.architecture.curtain_wall.panel import CurtainPanelType, CurtainPanel
from bimascode.core.type_instance import ElementInstance
from bimascode.core.world_geometry import FreestandingElementMixin

if TYPE_CHECKING:
    from bimascode.architecture.curtain_wall.curtain_wall_type import CurtainWallType
    from bimascode.spatial.level import Level


class CurtainWall(ElementInstance, FreestandingElementMixin):
    """
    Freestanding curtain wall element.

    Placed using start and end points like a regular wall, but generates
    a mullion/panel grid based on its type settings.
    """

    def __init__(
        self,
        curtain_wall_type: "CurtainWallType",
        start_point: tuple[float, float],
        end_point: tuple[float, float],
        level: "Level",
        height: float | None = None,
        base_offset: float = 0.0,
        name: str | None = None,
    ):
        """
        Create a freestanding curtain wall.

        Args:
            curtain_wall_type: The curtain wall type
            start_point: Start point (x, y) in mm
            end_point: End point (x, y) in mm
            level: The level this wall is on
            height: Wall height in mm (defaults to level height)
            base_offset: Offset from level elevation in mm
            name: Optional instance name
        """
        super().__init__(curtain_wall_type, name)

        self._start_point = start_point
        self._end_point = end_point
        self._level = level
        self._height = height if height is not None else 3000.0  # Default 3m
        self._base_offset = base_offset

        # Grid and overrides (generated on demand)
        self._grid: CurtainGrid | None = None
        self._panel_overrides: dict[tuple[int, int], CurtainPanelType] = {}
        self._mullion_overrides: dict[GridSegment, Any] = {}

        # Register with level
        if hasattr(level, "add_element"):
            level.add_element(self)

    @property
    def start_point(self) -> tuple[float, float]:
        """Get start point (x, y)."""
        return self._start_point

    @property
    def end_point(self) -> tuple[float, float]:
        """Get end point (x, y)."""
        return self._end_point

    @property
    def level(self) -> "Level":
        """Get the level this wall is on."""
        return self._level

    @property
    def height(self) -> float:
        """Get wall height in mm."""
        return self._height

    @height.setter
    def height(self, value: float) -> None:
        """Set wall height and invalidate geometry."""
        if value != self._height:
            self._height = value
            self.invalidate_geometry()
            self._grid = None

    @property
    def base_offset(self) -> float:
        """Get base offset from level elevation in mm."""
        return self._base_offset

    @property
    def width(self) -> float:
        """Get wall width (length along base) in mm."""
        dx = self._end_point[0] - self._start_point[0]
        dy = self._end_point[1] - self._start_point[1]
        return math.sqrt(dx * dx + dy * dy)

    @property
    def angle(self) -> float:
        """Get wall angle in degrees (from positive X axis)."""
        dx = self._end_point[0] - self._start_point[0]
        dy = self._end_point[1] - self._start_point[1]
        return math.degrees(math.atan2(dy, dx))

    @property
    def grid(self) -> CurtainGrid:
        """Get the curtain grid, generating if needed."""
        if self._grid is None:
            self._grid = self.type.generate_grid(self.width, self.height)
        return self._grid

    # FreestandingElementMixin implementation

    def _get_world_position(self) -> tuple[float, float, float]:
        """Get world position (start point + level elevation)."""
        return (
            self._start_point[0],
            self._start_point[1],
            self._level.elevation_mm + self._base_offset,
        )

    def _get_world_rotation(self) -> float:
        """Get rotation angle in degrees."""
        return self.angle

    def get_world_geometry(self) -> Compound:
        """
        Get geometry positioned in world coordinates.

        Returns:
            Compound with all mullions and panels in world position
        """
        # Get local geometry
        local_geom = self.get_geometry()

        if local_geom is None:
            return Compound(children=[])

        # Copy before transforming
        geom_copy = copy.copy(local_geom)

        # Create world transform
        pos = self._get_world_position()
        rotation = self._get_world_rotation()

        transform = Location(
            Pos(pos[0], pos[1], pos[2]),
            Rotation(0, 0, rotation),
        )

        geom_copy = geom_copy.locate(transform)
        return geom_copy

    # Grid manipulation methods (Revit-style)

    def add_grid_line(self, direction: str, position: float) -> CurtainGridLine | None:
        """
        Add a new grid line at the specified position.

        Args:
            direction: 'U' (vertical) or 'V' (horizontal)
            position: Position in mm (along wall width for U, along height for V)

        Returns:
            The new CurtainGridLine, or None if invalid
        """
        grid = self.grid  # Ensure grid exists
        result = grid.add_grid_line(direction, position)
        if result:
            self.invalidate_geometry()
        return result

    def remove_grid_segment(self, segment: GridSegment) -> bool:
        """
        Remove a grid segment, merging adjacent panels.

        Args:
            segment: The segment to remove

        Returns:
            True if segment was removed
        """
        grid = self.grid
        for line in grid.u_lines + grid.v_lines:
            if segment in line.segments:
                result = grid.remove_segment(line, segment)
                if result:
                    self.invalidate_geometry()
                return result
        return False

    def set_panel_type(
        self, u_index: int, v_index: int, panel_type: CurtainPanelType
    ) -> None:
        """
        Override the panel type for a specific cell.

        Args:
            u_index: Column index
            v_index: Row index
            panel_type: Panel type to use for this cell
        """
        self._panel_overrides[(u_index, v_index)] = panel_type
        self.invalidate_geometry()

    def get_panel_type(self, u_index: int, v_index: int) -> CurtainPanelType | None:
        """
        Get the panel type for a specific cell.

        Returns override if set, otherwise None (use default).

        Args:
            u_index: Column index
            v_index: Row index

        Returns:
            Panel type override, or None to use default
        """
        return self._panel_overrides.get((u_index, v_index))

    def clear_panel_override(self, u_index: int, v_index: int) -> None:
        """
        Clear the panel type override for a cell.

        Args:
            u_index: Column index
            v_index: Row index
        """
        if (u_index, v_index) in self._panel_overrides:
            del self._panel_overrides[(u_index, v_index)]
            self.invalidate_geometry()

    # 2D representation

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: Any = None,
        symbology: Any = None,
    ) -> list:
        """
        Generate 2D floor plan representation.

        Args:
            cut_height: Height of cut plane in mm (relative to level)
            view_range: ViewRange object (optional)
            symbology: ElementSymbology (optional)

        Returns:
            List of 2D primitives (Line2D, Polyline2D, etc.)
        """
        from bimascode.drawing.primitives import Line2D, Polyline2D, Point2D
        from bimascode.drawing.line_styles import LineStyle, LineWeight

        result = []

        # Get world position
        x1, y1 = self._start_point
        x2, y2 = self._end_point

        # Calculate direction and perpendicular
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-6:
            return result

        # Normalized direction
        dir_x = dx / length
        dir_y = dy / length

        # Perpendicular (90 degrees counter-clockwise)
        perp_x = -dir_y
        perp_y = dir_x

        # Curtain wall depth (from mullion type)
        depth = self._get_total_depth()
        half_depth = depth / 2

        # Create line style
        style = LineStyle(weight=LineWeight.MEDIUM)

        # Outer line (exterior face)
        outer_start = Point2D(x1 + perp_x * half_depth, y1 + perp_y * half_depth)
        outer_end = Point2D(x2 + perp_x * half_depth, y2 + perp_y * half_depth)
        result.append(Line2D(start=outer_start, end=outer_end, style=style))

        # Inner line (interior face)
        inner_start = Point2D(x1 - perp_x * half_depth, y1 - perp_y * half_depth)
        inner_end = Point2D(x2 - perp_x * half_depth, y2 - perp_y * half_depth)
        result.append(Line2D(start=inner_start, end=inner_end, style=style))

        # End caps
        result.append(Line2D(start=outer_start, end=inner_start, style=style))
        result.append(Line2D(start=outer_end, end=inner_end, style=style))

        # Mullion tick marks at each vertical grid line
        grid = self.grid
        mullion_style = LineStyle(weight=LineWeight.FINE)

        for u_line in grid.u_lines:
            if u_line.is_border:
                continue  # Skip borders, already have end caps

            # Position along wall
            t = u_line.position / length
            mx = x1 + t * dx
            my = y1 + t * dy

            # Draw tick across wall depth
            tick_start = Point2D(mx + perp_x * half_depth, my + perp_y * half_depth)
            tick_end = Point2D(mx - perp_x * half_depth, my - perp_y * half_depth)
            result.append(Line2D(start=tick_start, end=tick_end, style=mullion_style))

        return result

    def _get_total_depth(self) -> float:
        """Get total curtain wall depth from mullion types."""
        # Get maximum mullion depth
        depths = []
        curtain_type = self.type

        for mullion_type in [
            curtain_type._vertical_interior_mullion_type,
            curtain_type._vertical_border_1_mullion_type,
            curtain_type._vertical_border_2_mullion_type,
            curtain_type._horizontal_interior_mullion_type,
            curtain_type._horizontal_border_1_mullion_type,
            curtain_type._horizontal_border_2_mullion_type,
        ]:
            if mullion_type is not None:
                depths.append(mullion_type.depth)

        if not depths:
            # Default depth if no mullions defined
            return 100.0

        return max(depths)

    # IFC export

    def to_ifc(self, ifc_file: Any, ifc_storey: Any) -> Any:
        """
        Export curtain wall to IFC.

        Creates IfcCurtainWall with aggregated mullions and panels.

        Args:
            ifc_file: IFC file object
            ifc_storey: IfcBuildingStorey to contain this wall

        Returns:
            IfcCurtainWall entity
        """
        # Create IfcCurtainWall
        ifc_curtain_wall = ifc_file.create_entity(
            "IfcCurtainWall",
            GlobalId=self.guid,
            Name=self.name,
            Description=f"{self.type.name} curtain wall",
            PredefinedType="PARTITIONING",
        )

        # Set placement
        self._set_ifc_placement(ifc_file, ifc_curtain_wall, ifc_storey)

        # Create representation
        geom = self.get_geometry()
        if geom is not None:
            self._set_ifc_representation(ifc_file, ifc_curtain_wall, geom)

        return ifc_curtain_wall

    def _set_ifc_placement(self, ifc_file, ifc_element, ifc_storey) -> None:
        """Set IFC local placement for the element."""
        # Get position relative to storey
        pos = self._get_world_position()

        # Create placement
        location = ifc_file.createIfcCartesianPoint((pos[0], pos[1], pos[2]))

        # Rotation around Z axis
        angle_rad = math.radians(self.angle)
        ref_direction = ifc_file.createIfcDirection(
            (math.cos(angle_rad), math.sin(angle_rad), 0.0)
        )

        axis_placement = ifc_file.createIfcAxis2Placement3D(
            location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ref_direction,
        )

        ifc_element.ObjectPlacement = ifc_file.createIfcLocalPlacement(
            ifc_storey.ObjectPlacement, axis_placement
        )

    def _set_ifc_representation(self, ifc_file, ifc_element, geom) -> None:
        """Set IFC shape representation for the element."""
        # This would convert build123d geometry to IFC
        # For now, simplified implementation
        pass

    def __repr__(self) -> str:
        return (
            f"CurtainWall(name='{self.name}', "
            f"type='{self.type.name}', "
            f"size={self.width:.0f}x{self.height:.0f}mm)"
        )
