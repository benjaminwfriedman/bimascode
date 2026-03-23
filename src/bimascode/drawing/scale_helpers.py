"""Helper functions for configuring scale behavior.

Provides high-level utilities for configuring scale-dependent
rendering without needing low-level details.
"""

from typing import Dict, Optional

from bimascode.drawing.view_base import (
    DetailLevel,
    ScaleBehaviorConfig,
    ViewScale,
)
from bimascode.drawing.view_templates import ViewTemplate


class ScaleConfigurator:
    """Helper class for configuring scale behavior.

    Provides convenient methods for creating view templates
    with appropriate scale-dependent behavior.

    Example:
        >>> config = ScaleConfigurator()
        >>> template = config.create_template_for_scale(
        ...     ViewScale.SCALE_1_500,
        ...     view_type="floor_plan",
        ...     hide_small_details=True
        ... )
    """

    @staticmethod
    def create_template_for_scale(
        scale: ViewScale,
        view_type: str = "floor_plan",
        hide_small_details: Optional[bool] = None,
        reduce_line_weights: Optional[bool] = None,
        custom_detail_level: Optional[DetailLevel] = None,
    ) -> ViewTemplate:
        """Create view template optimized for a scale.

        Creates appropriately configured template based on scale
        and preferences.

        Args:
            scale: ViewScale to optimize for
            view_type: Type of view (floor_plan, section, elevation)
            hide_small_details: Override small details visibility
            reduce_line_weights: Override line weight reduction
            custom_detail_level: Override automatic detail level

        Returns:
            ViewTemplate configured for the scale

        Example:
            >>> template = ScaleConfigurator.create_template_for_scale(
            ...     ViewScale.SCALE_1_500,
            ...     view_type="floor_plan",
            ...     hide_small_details=True,
            ...     reduce_line_weights=True
            ... )
        """
        # Start with appropriate scaled template
        if view_type == "floor_plan":
            template = ViewTemplate.floor_plan_scaled(scale)
        elif view_type == "section":
            template = ViewTemplate.section_scaled(scale)
        else:
            template = ViewTemplate(f"{view_type.title()} @ {scale.name}")

        # Get or create behavior config
        detail_level = custom_detail_level or scale.get_default_detail_level()
        config = ScaleBehaviorConfig.for_detail_level(detail_level)

        # Apply overrides
        if hide_small_details is not None:
            config.show_small_details = not hide_small_details

        if reduce_line_weights is not None:
            config.line_weight_factor = 0.7 if reduce_line_weights else 1.0

        # Set the customized config
        template.set_scale_behavior(scale, detail_level, custom_config=config)
        return template

    @staticmethod
    def recommend_scale(
        view_type: str,
        content_size: Optional[float] = None,
        target_paper_size: str = "A3",
    ) -> ViewScale:
        """Recommend appropriate scale.

        Intelligently recommends a scale based on content size
        and target paper format.

        Args:
            view_type: Type of view (floor_plan, section, elevation, detail, site)
            content_size: Optional content dimension in mm
            target_paper_size: Paper format (A4, A3, A2, A1, A0)

        Returns:
            Recommended ViewScale

        Example:
            >>> scale = ScaleConfigurator.recommend_scale(
            ...     "floor_plan",
            ...     content_size=50000,  # 50m building
            ...     target_paper_size="A3"
            ... )
        """
        paper_sizes = {
            "A4": 297,
            "A3": 420,
            "A2": 594,
            "A1": 841,
            "A0": 1189,
        }

        # If content size provided, calculate required scale
        if content_size is not None:
            paper_width = paper_sizes.get(target_paper_size, 420)
            usable_width = paper_width - 100  # Account for margins
            required_ratio = usable_width / content_size

            # Find smallest scale that fits
            standard_scales = [
                ViewScale.SCALE_1_1,
                ViewScale.SCALE_1_10,
                ViewScale.SCALE_1_20,
                ViewScale.SCALE_1_50,
                ViewScale.SCALE_1_100,
                ViewScale.SCALE_1_200,
                ViewScale.SCALE_1_500,
            ]

            for scale in reversed(standard_scales):
                if scale.ratio >= required_ratio:
                    return scale

            # If nothing fits, return smallest
            return ViewScale.SCALE_1_500

        # Use view type recommendation
        return ViewScale.recommend_for_view_type(view_type)

    @staticmethod
    def get_visibility_thresholds(scale: ViewScale) -> Dict[str, float]:
        """Get minimum size thresholds for element types.

        Returns recommended minimum sizes for different element
        types at the given scale.

        Args:
            scale: ViewScale to analyze

        Returns:
            Dict mapping element type to minimum size (mm)

        Example:
            >>> thresholds = ScaleConfigurator.get_visibility_thresholds(
            ...     ViewScale.SCALE_1_200
            ... )
            >>> print(thresholds["Furniture"])  # 200.0
        """
        config = scale.get_behavior_config()
        base_threshold = config.min_element_size

        return {
            "Wall": 0.0,  # Always show structure
            "Column": 0.0,
            "Beam": 0.0,
            "Floor": 0.0,
            "Door": base_threshold,
            "Window": base_threshold,
            "Furniture": base_threshold * 2,  # Higher threshold
            "Fixture": base_threshold * 1.5,
            "Trim": base_threshold * 3,  # Highest threshold
        }


def create_multi_scale_template_set(
    view_type: str = "floor_plan",
) -> Dict[ViewScale, ViewTemplate]:
    """Create templates for all standard scales.

    Useful for preparing multiple scale options at once.

    Args:
        view_type: Type of view to create templates for

    Returns:
        Dict mapping ViewScale to configured ViewTemplate

    Example:
        >>> templates = create_multi_scale_template_set("floor_plan")
        >>> plan_view.template = templates[ViewScale.SCALE_1_100]
    """
    configurator = ScaleConfigurator()

    standard_scales = [
        ViewScale.SCALE_1_20,
        ViewScale.SCALE_1_50,
        ViewScale.SCALE_1_100,
        ViewScale.SCALE_1_200,
        ViewScale.SCALE_1_500,
    ]

    return {
        scale: configurator.create_template_for_scale(scale, view_type)
        for scale in standard_scales
    }
