"""
Curtain wall type definition.

CurtainWallType defines the shared parameters for curtain wall instances,
including grid layout, mullion types, and default panel type.

This matches Revit's Curtain Wall Type with automatic grid generation.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from build123d import Compound

from bimascode.architecture.curtain_wall.curtain_grid import (
    CurtainGrid,
    GridLayout,
    GridJustification,
)
from bimascode.architecture.curtain_wall.mullion import MullionType, Mullion
from bimascode.architecture.curtain_wall.panel import (
    CurtainPanelType,
    GlazedPanelType,
    CurtainPanel,
)
from bimascode.core.type_instance import ElementType

if TYPE_CHECKING:
    from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall


class CurtainWallType(ElementType):
    """
    Type definition for curtain walls.

    Defines grid layout, mullion assignments, and default panel type.
    Matches Revit's Curtain Wall Type behavior with automatic grid generation.
    """

    def __init__(
        self,
        name: str,
        # Vertical Grid (U direction - along width)
        vertical_grid_layout: GridLayout = GridLayout.FIXED_DISTANCE,
        vertical_grid_spacing: float = 1200.0,
        vertical_grid_number: int = 0,
        vertical_justification: GridJustification = GridJustification.BEGINNING,
        adjust_for_mullion_size_vertical: bool = True,
        # Horizontal Grid (V direction - along height)
        horizontal_grid_layout: GridLayout = GridLayout.FIXED_DISTANCE,
        horizontal_grid_spacing: float = 1500.0,
        horizontal_grid_number: int = 0,
        horizontal_justification: GridJustification = GridJustification.BEGINNING,
        adjust_for_mullion_size_horizontal: bool = True,
        # Vertical Mullions (on U lines)
        vertical_interior_mullion_type: MullionType | None = None,
        vertical_border_1_mullion_type: MullionType | None = None,
        vertical_border_2_mullion_type: MullionType | None = None,
        # Horizontal Mullions (on V lines)
        horizontal_interior_mullion_type: MullionType | None = None,
        horizontal_border_1_mullion_type: MullionType | None = None,
        horizontal_border_2_mullion_type: MullionType | None = None,
        # Default Panel
        default_panel_type: CurtainPanelType | None = None,
    ):
        """
        Create a curtain wall type.

        Args:
            name: Type name

            # Vertical Grid (U direction)
            vertical_grid_layout: Layout mode for vertical grid lines
            vertical_grid_spacing: Spacing for FIXED_DISTANCE or MAXIMUM_SPACING (mm)
            vertical_grid_number: Number of divisions for FIXED_NUMBER
            vertical_justification: Where to place remainder panels
            adjust_for_mullion_size_vertical: Shrink panels to account for mullion width

            # Horizontal Grid (V direction)
            horizontal_grid_layout: Layout mode for horizontal grid lines
            horizontal_grid_spacing: Spacing for FIXED_DISTANCE or MAXIMUM_SPACING (mm)
            horizontal_grid_number: Number of divisions for FIXED_NUMBER
            horizontal_justification: Where to place remainder panels
            adjust_for_mullion_size_horizontal: Shrink panels to account for mullion width

            # Vertical Mullions
            vertical_interior_mullion_type: Mullion type for interior vertical lines
            vertical_border_1_mullion_type: Mullion type for left edge
            vertical_border_2_mullion_type: Mullion type for right edge

            # Horizontal Mullions
            horizontal_interior_mullion_type: Mullion type for interior horizontal lines
            horizontal_border_1_mullion_type: Mullion type for bottom edge
            horizontal_border_2_mullion_type: Mullion type for top edge

            # Panel
            default_panel_type: Default panel type for all cells
        """
        super().__init__(name)

        # Vertical grid settings
        self._vertical_grid_layout = vertical_grid_layout
        self._vertical_grid_spacing = vertical_grid_spacing
        self._vertical_grid_number = vertical_grid_number
        self._vertical_justification = vertical_justification
        self._adjust_for_mullion_size_vertical = adjust_for_mullion_size_vertical

        # Horizontal grid settings
        self._horizontal_grid_layout = horizontal_grid_layout
        self._horizontal_grid_spacing = horizontal_grid_spacing
        self._horizontal_grid_number = horizontal_grid_number
        self._horizontal_justification = horizontal_justification
        self._adjust_for_mullion_size_horizontal = adjust_for_mullion_size_horizontal

        # Vertical mullion types
        self._vertical_interior_mullion_type = vertical_interior_mullion_type
        self._vertical_border_1_mullion_type = vertical_border_1_mullion_type
        self._vertical_border_2_mullion_type = vertical_border_2_mullion_type

        # Horizontal mullion types
        self._horizontal_interior_mullion_type = horizontal_interior_mullion_type
        self._horizontal_border_1_mullion_type = horizontal_border_1_mullion_type
        self._horizontal_border_2_mullion_type = horizontal_border_2_mullion_type

        # Default panel type
        self._default_panel_type = default_panel_type or GlazedPanelType(
            name="Default Double Glazed",
            glazing_type="double",
        )

        # Store all in type parameters
        self._store_parameters()

    def _store_parameters(self) -> None:
        """Store all settings in type parameters."""
        self.set_parameter("vertical_grid_layout", self._vertical_grid_layout)
        self.set_parameter("vertical_grid_spacing", self._vertical_grid_spacing)
        self.set_parameter("vertical_grid_number", self._vertical_grid_number)
        self.set_parameter("vertical_justification", self._vertical_justification)
        self.set_parameter(
            "adjust_for_mullion_size_vertical", self._adjust_for_mullion_size_vertical
        )

        self.set_parameter("horizontal_grid_layout", self._horizontal_grid_layout)
        self.set_parameter("horizontal_grid_spacing", self._horizontal_grid_spacing)
        self.set_parameter("horizontal_grid_number", self._horizontal_grid_number)
        self.set_parameter("horizontal_justification", self._horizontal_justification)
        self.set_parameter(
            "adjust_for_mullion_size_horizontal",
            self._adjust_for_mullion_size_horizontal,
        )

        self.set_parameter(
            "vertical_interior_mullion_type", self._vertical_interior_mullion_type
        )
        self.set_parameter(
            "vertical_border_1_mullion_type", self._vertical_border_1_mullion_type
        )
        self.set_parameter(
            "vertical_border_2_mullion_type", self._vertical_border_2_mullion_type
        )

        self.set_parameter(
            "horizontal_interior_mullion_type", self._horizontal_interior_mullion_type
        )
        self.set_parameter(
            "horizontal_border_1_mullion_type", self._horizontal_border_1_mullion_type
        )
        self.set_parameter(
            "horizontal_border_2_mullion_type", self._horizontal_border_2_mullion_type
        )

        self.set_parameter("default_panel_type", self._default_panel_type)

    # Property accessors
    @property
    def vertical_grid_layout(self) -> GridLayout:
        """Get vertical grid layout mode."""
        return self._vertical_grid_layout

    @property
    def vertical_grid_spacing(self) -> float:
        """Get vertical grid spacing in mm."""
        return self._vertical_grid_spacing

    @property
    def horizontal_grid_layout(self) -> GridLayout:
        """Get horizontal grid layout mode."""
        return self._horizontal_grid_layout

    @property
    def horizontal_grid_spacing(self) -> float:
        """Get horizontal grid spacing in mm."""
        return self._horizontal_grid_spacing

    @property
    def default_panel_type(self) -> CurtainPanelType:
        """Get default panel type."""
        return self._default_panel_type

    def get_vertical_mullion_type(self, border_type: int) -> MullionType | None:
        """
        Get mullion type for vertical lines based on border type.

        Args:
            border_type: 0=interior, 1=border_1 (left), 2=border_2 (right)

        Returns:
            MullionType or None
        """
        if border_type == 1:
            return self._vertical_border_1_mullion_type
        elif border_type == 2:
            return self._vertical_border_2_mullion_type
        else:
            return self._vertical_interior_mullion_type

    def get_horizontal_mullion_type(self, border_type: int) -> MullionType | None:
        """
        Get mullion type for horizontal lines based on border type.

        Args:
            border_type: 0=interior, 1=border_1 (bottom), 2=border_2 (top)

        Returns:
            MullionType or None
        """
        if border_type == 1:
            return self._horizontal_border_1_mullion_type
        elif border_type == 2:
            return self._horizontal_border_2_mullion_type
        else:
            return self._horizontal_interior_mullion_type

    def generate_grid(self, width: float, height: float) -> CurtainGrid:
        """
        Generate a curtain grid based on type settings.

        Args:
            width: Total curtain wall width (mm)
            height: Total curtain wall height (mm)

        Returns:
            CurtainGrid configured according to type parameters
        """
        grid = CurtainGrid(width=width, height=height)

        # Generate based on layout mode
        if (
            self._vertical_grid_layout == GridLayout.FIXED_DISTANCE
            and self._horizontal_grid_layout == GridLayout.FIXED_DISTANCE
        ):
            grid.generate_fixed_distance(
                u_spacing=self._vertical_grid_spacing,
                v_spacing=self._horizontal_grid_spacing,
                u_justification=self._vertical_justification,
                v_justification=self._horizontal_justification,
            )
        elif (
            self._vertical_grid_layout == GridLayout.FIXED_NUMBER
            and self._horizontal_grid_layout == GridLayout.FIXED_NUMBER
        ):
            grid.generate_fixed_number(
                u_divisions=self._vertical_grid_number,
                v_divisions=self._horizontal_grid_number,
            )
        elif (
            self._vertical_grid_layout == GridLayout.MAXIMUM_SPACING
            and self._horizontal_grid_layout == GridLayout.MAXIMUM_SPACING
        ):
            grid.generate_maximum_spacing(
                u_max_spacing=self._vertical_grid_spacing,
                v_max_spacing=self._horizontal_grid_spacing,
            )
        else:
            # Mixed modes - handle each direction separately
            # For now, default to fixed distance
            grid.generate_fixed_distance(
                u_spacing=self._vertical_grid_spacing,
                v_spacing=self._horizontal_grid_spacing,
                u_justification=self._vertical_justification,
                v_justification=self._horizontal_justification,
            )

        return grid

    def create_geometry(self, instance: "CurtainWall") -> Compound:
        """
        Create 3D geometry for a curtain wall instance.

        Generates mullions and panels based on the instance's grid.

        Args:
            instance: The curtain wall instance

        Returns:
            Compound containing all mullion and panel geometry
        """
        parts = []

        # Get instance dimensions
        width = instance.width
        height = instance.height

        # Generate or get grid
        grid = instance._grid
        if grid is None:
            grid = self.generate_grid(width, height)
            instance._grid = grid

        # Generate mullions
        mullion_parts = self._create_mullion_geometry(instance, grid)
        parts.extend(mullion_parts)

        # Generate panels
        panel_parts = self._create_panel_geometry(instance, grid)
        parts.extend(panel_parts)

        if not parts:
            # Return empty compound if no parts
            from build123d import Box

            return Compound(children=[])

        return Compound(children=parts)

    def _create_mullion_geometry(
        self, instance: "CurtainWall", grid: CurtainGrid
    ) -> list:
        """Create mullion geometry for all grid segments."""
        parts = []

        # Vertical mullions (U lines)
        for u_line in grid.u_lines:
            mullion_type = self.get_vertical_mullion_type(u_line.border_type)
            if mullion_type is None:
                continue

            for segment in u_line.segments:
                if segment.removed:
                    continue

                # Create mullion from segment
                start_point = (u_line.position, 0, segment.start_position)
                end_point = (u_line.position, 0, segment.end_position)

                mullion = Mullion(
                    mullion_type=mullion_type,
                    start_point=start_point,
                    end_point=end_point,
                    segment=segment,
                )
                segment.mullion = mullion

                # Get positioned geometry
                mullion_geom = mullion.get_local_geometry()
                if mullion_geom is not None:
                    parts.append(mullion_geom)

        # Horizontal mullions (V lines)
        for v_line in grid.v_lines:
            mullion_type = self.get_horizontal_mullion_type(v_line.border_type)
            if mullion_type is None:
                continue

            for segment in v_line.segments:
                if segment.removed:
                    continue

                # Create mullion from segment
                start_point = (segment.start_position, 0, v_line.position)
                end_point = (segment.end_position, 0, v_line.position)

                mullion = Mullion(
                    mullion_type=mullion_type,
                    start_point=start_point,
                    end_point=end_point,
                    segment=segment,
                )
                segment.mullion = mullion

                # Get positioned geometry
                mullion_geom = mullion.get_local_geometry()
                if mullion_geom is not None:
                    parts.append(mullion_geom)

        return parts

    def _create_panel_geometry(
        self, instance: "CurtainWall", grid: CurtainGrid
    ) -> list:
        """Create panel geometry for all grid cells."""
        parts = []

        for u_index in range(grid.u_count):
            for v_index in range(grid.v_count):
                cell = grid.get_cell(u_index, v_index)
                if cell is None or cell.is_merged:
                    continue

                # Get panel type (check for override)
                panel_type = instance.get_panel_type(u_index, v_index)
                if panel_type is None:
                    panel_type = self._default_panel_type

                # Calculate panel dimensions
                panel_width = cell.width
                panel_height = cell.height

                # Adjust for mullion size if enabled
                if self._adjust_for_mullion_size_vertical:
                    mullion_width = self._get_average_mullion_width("vertical")
                    panel_width -= mullion_width

                if self._adjust_for_mullion_size_horizontal:
                    mullion_width = self._get_average_mullion_width("horizontal")
                    panel_height -= mullion_width

                # Ensure positive dimensions
                panel_width = max(1, panel_width)
                panel_height = max(1, panel_height)

                # Create panel instance
                panel = CurtainPanel(
                    panel_type=panel_type,
                    width=panel_width,
                    height=panel_height,
                    cell=cell,
                )
                cell.panel = panel

                # Get positioned geometry
                origin = (
                    cell.x_start + (cell.width - panel_width) / 2,
                    0,
                    cell.y_start + (cell.height - panel_height) / 2,
                )
                panel_geom = panel.get_local_geometry(origin)
                if panel_geom is not None:
                    parts.append(panel_geom)

        return parts

    def _get_average_mullion_width(self, direction: str) -> float:
        """Get average mullion width for dimension adjustment."""
        if direction == "vertical":
            mullion_types = [
                self._vertical_interior_mullion_type,
                self._vertical_border_1_mullion_type,
                self._vertical_border_2_mullion_type,
            ]
        else:
            mullion_types = [
                self._horizontal_interior_mullion_type,
                self._horizontal_border_1_mullion_type,
                self._horizontal_border_2_mullion_type,
            ]

        widths = [mt.width for mt in mullion_types if mt is not None]
        if not widths:
            return 0
        return sum(widths) / len(widths)

    def __repr__(self) -> str:
        return (
            f"CurtainWallType(name='{self.name}', "
            f"vertical_spacing={self._vertical_grid_spacing:.0f}mm, "
            f"horizontal_spacing={self._horizontal_grid_spacing:.0f}mm)"
        )
