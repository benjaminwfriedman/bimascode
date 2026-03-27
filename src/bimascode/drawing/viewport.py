"""Sheet viewport for placing views on sheets.

Defines SheetViewport dataclass for positioning views in paperspace.
This is a stub implementation for Issue #39 - full viewport features
will be implemented separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bimascode.drawing.primitives import Point2D, ViewResult
from bimascode.drawing.view_base import ViewScale

if TYPE_CHECKING:
    pass


@dataclass
class SheetViewport:
    """Viewport placing a view on a sheet.

    A viewport is a window into modelspace displayed at a specific
    location and scale on a sheet (paperspace).

    NOTE: This is a placeholder for Issue #39. Full implementation
    will include clipping boundaries, frozen layers, and rotation.

    Attributes:
        view_result: The generated view content to display
        position: Center point of viewport on sheet (mm from sheet origin)
        scale: Display scale (e.g., ViewScale.SCALE_1_100)
        width: Viewport width on sheet in mm (auto-calculated if None)
        height: Viewport height on sheet in mm (auto-calculated if None)
        name: Optional viewport name/label

    Example:
        >>> from bimascode.drawing import ViewResult, ViewScale
        >>> viewport = SheetViewport(
        ...     view_result=floor_plan_result,
        ...     position=Point2D(300, 200),
        ...     scale=ViewScale.SCALE_1_100,
        ... )
    """

    view_result: ViewResult
    position: Point2D
    scale: ViewScale
    width: float | None = None
    height: float | None = None
    name: str = ""

    # Placeholder fields for future #39 features
    clip_boundary: list[Point2D] | None = None
    frozen_layers: list[str] = field(default_factory=list)
    rotation: float = 0.0  # degrees

    @property
    def bounds_on_sheet(self) -> tuple[float, float, float, float]:
        """Get viewport bounds on sheet (min_x, min_y, max_x, max_y).

        Returns:
            Tuple of (min_x, min_y, max_x, max_y) in sheet coordinates (mm)
        """
        w = self.width if self.width is not None else self._auto_width()
        h = self.height if self.height is not None else self._auto_height()
        half_w, half_h = w / 2, h / 2
        return (
            self.position.x - half_w,
            self.position.y - half_h,
            self.position.x + half_w,
            self.position.y + half_h,
        )

    @property
    def effective_width(self) -> float:
        """Get effective viewport width (explicit or auto-calculated)."""
        return self.width if self.width is not None else self._auto_width()

    @property
    def effective_height(self) -> float:
        """Get effective viewport height (explicit or auto-calculated)."""
        return self.height if self.height is not None else self._auto_height()

    def _auto_width(self) -> float:
        """Calculate width from view content bounds and scale."""
        bounds = self.view_result.get_bounds()
        if bounds:
            model_width = bounds[2] - bounds[0]
            return model_width * self.scale.ratio
        return 100.0  # Default fallback

    def _auto_height(self) -> float:
        """Calculate height from view content bounds and scale."""
        bounds = self.view_result.get_bounds()
        if bounds:
            model_height = bounds[3] - bounds[1]
            return model_height * self.scale.ratio
        return 100.0  # Default fallback

    @property
    def model_bounds(self) -> tuple[float, float, float, float] | None:
        """Get the bounds of the view content in model coordinates.

        Returns:
            Tuple of (min_x, min_y, max_x, max_y) or None if empty
        """
        return self.view_result.get_bounds()

    @property
    def model_center(self) -> tuple[float, float] | None:
        """Get the center of the view content in model coordinates.

        Returns:
            Tuple of (center_x, center_y) or None if empty
        """
        bounds = self.view_result.get_bounds()
        if bounds:
            return (
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2,
            )
        return None

    @property
    def view_height_in_model(self) -> float:
        """Get the viewport height in model space units.

        This is used for DXF viewport configuration.

        Returns:
            Height in model units (mm)
        """
        return self.effective_height / self.scale.ratio
