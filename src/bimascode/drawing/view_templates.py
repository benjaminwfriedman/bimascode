"""View templates for controlling visibility and graphics overrides.

Provides ViewTemplate and related classes for managing element
visibility and graphic representation in views.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from bimascode.drawing.line_styles import LineStyle, LineWeight
from bimascode.drawing.view_base import DetailLevel, ScaleBehaviorConfig

if TYPE_CHECKING:
    from bimascode.drawing.view_base import ViewScale


class CategoryVisibility(Enum):
    """Visibility states for element categories."""

    VISIBLE = "visible"  # Normal visibility
    HIDDEN = "hidden"  # Not displayed
    HALFTONE = "halftone"  # Displayed with reduced intensity


@dataclass
class GraphicOverride:
    """Override graphics for a category.

    Allows customizing how elements of a category appear in a view,
    including visibility, line weight, and color.

    Attributes:
        visibility: Whether category is visible, hidden, or halftone
        line_weight: Override line weight (None = use default)
        line_color: Override line color as RGB (None = use default)
        halftone: Apply halftone effect (50% transparency)
        cut_line_weight: Override for cut lines specifically
        projection_line_weight: Override for projection lines
    """

    visibility: CategoryVisibility = CategoryVisibility.VISIBLE
    line_weight: Optional[LineWeight] = None
    line_color: Optional[Tuple[int, int, int]] = None
    halftone: bool = False
    cut_line_weight: Optional[LineWeight] = None
    projection_line_weight: Optional[LineWeight] = None

    def apply_to_style(self, style: LineStyle) -> LineStyle:
        """Apply this override to a line style.

        Args:
            style: Original line style

        Returns:
            Modified line style
        """
        if self.visibility == CategoryVisibility.HIDDEN:
            return style  # Will be filtered out

        new_weight = style.weight
        if self.line_weight is not None:
            new_weight = self.line_weight
        elif style.is_cut and self.cut_line_weight is not None:
            new_weight = self.cut_line_weight
        elif not style.is_cut and self.projection_line_weight is not None:
            new_weight = self.projection_line_weight

        new_color = self.line_color if self.line_color is not None else style.color

        # Apply halftone as a gray color
        if self.halftone and new_color is None:
            new_color = (128, 128, 128)  # 50% gray

        return LineStyle(
            weight=new_weight,
            type=style.type,
            color=new_color,
            is_cut=style.is_cut,
        )


@dataclass
class ViewVisibilitySettings:
    """Settings for element visibility in a view.

    Controls which categories of elements are visible by default.
    """

    # Architecture
    walls: bool = True
    doors: bool = True
    windows: bool = True
    floors: bool = True
    ceilings: bool = False  # Hidden by default in floor plan
    roofs: bool = False
    stairs: bool = True
    furniture: bool = False

    # Structure
    columns: bool = True
    beams: bool = True
    foundations: bool = False

    # Annotations
    dimensions: bool = True
    text: bool = True
    symbols: bool = True
    grids: bool = True

    # Other
    rooms: bool = True
    show_hidden_lines: bool = False

    def is_category_visible(self, category: str) -> bool:
        """Check if a category is visible.

        Args:
            category: Category name (e.g., "Wall", "Door")

        Returns:
            True if category should be visible
        """
        category_map = {
            "Wall": self.walls,
            "Door": self.doors,
            "Window": self.windows,
            "Floor": self.floors,
            "Ceiling": self.ceilings,
            "Roof": self.roofs,
            "Stair": self.stairs,
            "Furniture": self.furniture,
            "StructuralColumn": self.columns,
            "Column": self.columns,
            "Beam": self.beams,
            "Foundation": self.foundations,
            "Room": self.rooms,
        }

        return category_map.get(category, True)


class ViewTemplate:
    """Reusable view settings template.

    ViewTemplates define a set of visibility and graphics settings
    that can be applied to multiple views. This ensures consistency
    across a drawing set.

    Example:
        >>> template = ViewTemplate.floor_plan_default()
        >>> view.template = template
    """

    def __init__(
        self,
        name: str,
        visibility: Optional[ViewVisibilitySettings] = None,
    ):
        """Create a view template.

        Args:
            name: Template name
            visibility: Default visibility settings
        """
        self.name = name
        self.visibility = visibility or ViewVisibilitySettings()
        self.category_overrides: Dict[str, GraphicOverride] = {}
        self.view_scale: Optional["ViewScale"] = None
        # Scale behavior configuration
        self.scale_behaviors: Dict["ViewScale", "ScaleBehaviorConfig"] = {}
        self._active_scale: Optional["ViewScale"] = None

    def set_category_override(
        self,
        category: str,
        override: GraphicOverride,
    ) -> None:
        """Set graphics override for a category.

        Args:
            category: Category name (e.g., "Wall", "Door")
            override: Graphics override to apply
        """
        self.category_overrides[category] = override

    def get_category_override(self, category: str) -> Optional[GraphicOverride]:
        """Get graphics override for a category.

        Args:
            category: Category name

        Returns:
            GraphicOverride if set, None otherwise
        """
        return self.category_overrides.get(category)

    def filter_visible(self, elements: List) -> List:
        """Filter elements by visibility settings.

        Args:
            elements: List of elements to filter

        Returns:
            List of visible elements
        """
        result = []

        for element in elements:
            category = type(element).__name__

            # Check category override first
            override = self.category_overrides.get(category)
            if override is not None:
                if override.visibility == CategoryVisibility.HIDDEN:
                    continue

            # Check default visibility
            if not self.visibility.is_category_visible(category):
                continue

            result.append(element)

        return result

    def apply_style(self, element, style: LineStyle) -> LineStyle:
        """Apply template overrides to a line style.

        Args:
            element: The element this style is for
            style: Original line style

        Returns:
            Modified line style
        """
        category = type(element).__name__
        override = self.category_overrides.get(category)

        if override is not None:
            return override.apply_to_style(style)

        return style

    def set_scale_behavior(
        self,
        scale: "ViewScale",
        detail_level: DetailLevel,
        custom_config: Optional[ScaleBehaviorConfig] = None,
    ) -> None:
        """Configure behavior for a specific scale.

        Primary API for controlling scale-dependent rendering.

        Args:
            scale: ViewScale to configure
            detail_level: Target detail level
            custom_config: Optional custom configuration (overrides detail_level defaults)

        Example:
            >>> template.set_scale_behavior(
            ...     ViewScale.SCALE_1_500,
            ...     DetailLevel.LOW
            ... )
        """
        if custom_config is not None:
            self.scale_behaviors[scale] = custom_config
        else:
            self.scale_behaviors[scale] = ScaleBehaviorConfig.for_detail_level(
                detail_level
            )

    def get_scale_behavior(self, scale: "ViewScale") -> ScaleBehaviorConfig:
        """Get behavior configuration for a scale.

        Args:
            scale: ViewScale to query

        Returns:
            ScaleBehaviorConfig for the scale
        """
        if scale in self.scale_behaviors:
            return self.scale_behaviors[scale]
        return scale.get_behavior_config()

    def set_active_scale(self, scale: "ViewScale") -> None:
        """Set currently active scale.

        Used by views during generation to activate scale-dependent behavior.

        Args:
            scale: ViewScale that is currently active
        """
        self._active_scale = scale

    def should_show_element(
        self, element, size_hint: Optional[float] = None
    ) -> bool:
        """Check if element should be visible at current scale.

        Args:
            element: Element to check
            size_hint: Optional size hint (width, diameter, etc.) in mm

        Returns:
            True if element should be shown, False otherwise
        """
        if self._active_scale is None:
            return True

        config = self.get_scale_behavior(self._active_scale)

        # Check minimum element size
        if size_hint is not None and config.min_element_size > 0:
            if size_hint < config.min_element_size:
                return False

        # Check small details flag
        if not config.show_small_details:
            element_type = type(element).__name__
            small_detail_types = {
                "DoorHardware",
                "WindowHardware",
                "Trim",
                "Molding",
            }
            if element_type in small_detail_types:
                return False

        return True

    def apply_scale_adjusted_style(
        self, element, style: LineStyle
    ) -> LineStyle:
        """Apply both category overrides and scale adjustments.

        Args:
            element: Element the style is for
            style: Original line style

        Returns:
            Style with category and scale adjustments applied
        """
        # First apply category overrides
        style = self.apply_style(element, style)

        # Then apply scale adjustments
        if self._active_scale is not None:
            config = self.get_scale_behavior(self._active_scale)

            if config.line_weight_factor != 1.0:
                adjusted_weight = self._adjust_line_weight(
                    style.weight, config.line_weight_factor
                )
                style = style.with_weight(adjusted_weight)

        return style

    def _adjust_line_weight(
        self, weight: LineWeight, factor: float
    ) -> LineWeight:
        """Adjust line weight by factor, clamping to valid range.

        Args:
            weight: Original line weight
            factor: Multiplier (0.7 = 30% reduction)

        Returns:
            Adjusted line weight (closest valid weight)
        """
        current_value = weight.value
        target_value = current_value * factor

        all_weights = [
            LineWeight.EXTRA_FINE,
            LineWeight.FINE,
            LineWeight.NARROW,
            LineWeight.MEDIUM,
            LineWeight.WIDE,
            LineWeight.HEAVY,
        ]

        closest = min(all_weights, key=lambda w: abs(w.value - target_value))
        return closest

    @classmethod
    def floor_plan_default(cls) -> ViewTemplate:
        """Create default floor plan template.

        Standard architectural floor plan with:
        - All walls, doors, windows visible
        - Structure in halftone
        - Ceilings hidden
        """
        template = cls("Floor Plan Default")

        # Default visibility
        template.visibility.ceilings = False
        template.visibility.roofs = False
        template.visibility.furniture = False

        # Structure in halftone
        template.category_overrides["StructuralColumn"] = GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            halftone=True,
        )
        template.category_overrides["Beam"] = GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            halftone=True,
        )

        return template

    @classmethod
    def reflected_ceiling_plan(cls) -> ViewTemplate:
        """Create reflected ceiling plan template.

        Shows ceilings, hides most architecture.
        """
        template = cls("Reflected Ceiling Plan")

        # Hide most elements
        template.visibility.walls = False
        template.visibility.doors = False
        template.visibility.windows = False
        template.visibility.floors = False
        template.visibility.furniture = False

        # Show ceilings
        template.visibility.ceilings = True

        # Show beams in halftone
        template.category_overrides["Beam"] = GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            halftone=True,
        )

        return template

    @classmethod
    def structural_plan(cls) -> ViewTemplate:
        """Create structural plan template.

        Emphasizes structure, shows architecture in halftone.
        """
        template = cls("Structural Plan")

        # Full visibility for structure
        template.visibility.columns = True
        template.visibility.beams = True
        template.visibility.foundations = True

        # Architecture in halftone
        template.category_overrides["Wall"] = GraphicOverride(
            visibility=CategoryVisibility.VISIBLE,
            halftone=True,
        )
        template.category_overrides["Door"] = GraphicOverride(
            visibility=CategoryVisibility.HALFTONE,
            halftone=True,
        )
        template.category_overrides["Window"] = GraphicOverride(
            visibility=CategoryVisibility.HALFTONE,
            halftone=True,
        )

        return template

    @classmethod
    def section_default(cls) -> ViewTemplate:
        """Create default section template.

        Shows all elements with hidden lines.
        """
        template = cls("Section Default")

        # Show everything
        template.visibility.ceilings = True
        template.visibility.roofs = True
        template.visibility.show_hidden_lines = True

        return template

    @classmethod
    def elevation_default(cls) -> ViewTemplate:
        """Create default elevation template.

        Shows exterior elements, hides hidden lines.
        """
        template = cls("Elevation Default")

        # Standard visibility
        template.visibility.show_hidden_lines = False

        return template

    @classmethod
    def floor_plan_scaled(cls, scale: "ViewScale") -> ViewTemplate:
        """Create floor plan template optimized for a specific scale.

        Automatically configures detail level and visibility based on scale.

        Args:
            scale: ViewScale to optimize for

        Returns:
            ViewTemplate configured for the scale

        Example:
            >>> template = ViewTemplate.floor_plan_scaled(ViewScale.SCALE_1_500)
        """
        from bimascode.drawing.view_base import ViewScale

        template = cls.floor_plan_default()
        detail_level = scale.get_default_detail_level()
        template.set_scale_behavior(scale, detail_level)

        # Adjust visibility for small scales
        if detail_level in (DetailLevel.LOW, DetailLevel.VERY_LOW):
            template.visibility.furniture = False
            template.category_overrides["StructuralColumn"] = GraphicOverride(
                visibility=CategoryVisibility.HALFTONE,
                line_weight=LineWeight.FINE,
                halftone=True,
            )

        return template

    @classmethod
    def section_scaled(cls, scale: "ViewScale") -> ViewTemplate:
        """Create section template optimized for a specific scale.

        Automatically configures detail level and visibility based on scale.

        Args:
            scale: ViewScale to optimize for

        Returns:
            ViewTemplate configured for the scale

        Example:
            >>> template = ViewTemplate.section_scaled(ViewScale.SCALE_1_200)
        """
        template = cls.section_default()
        detail_level = scale.get_default_detail_level()
        template.set_scale_behavior(scale, detail_level)

        # Hide hidden lines at very small scales
        if detail_level == DetailLevel.VERY_LOW:
            template.visibility.show_hidden_lines = False

        return template

    def __repr__(self) -> str:
        return f"ViewTemplate(name='{self.name}')"
