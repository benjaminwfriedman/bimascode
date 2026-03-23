"""Tests for scale-dependent behavior.

Comprehensive test suite for the enhanced view scale system,
including DetailLevel, ScaleBehaviorConfig, and AI agent helpers.
"""

import pytest

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.line_styles import LineStyle, LineWeight
from bimascode.drawing.scale_helpers import (
    ScaleConfigurator,
    create_multi_scale_template_set,
)
from bimascode.drawing.view_base import (
    DetailLevel,
    ScaleBehaviorConfig,
    ViewScale,
)
from bimascode.drawing.view_templates import ViewTemplate


class TestDetailLevel:
    """Test DetailLevel enum and scale mapping."""

    def test_from_scale_very_high(self):
        """Test VERY_HIGH detail level detection."""
        assert DetailLevel.from_scale(ViewScale.SCALE_1_1) == DetailLevel.VERY_HIGH
        assert DetailLevel.from_scale(ViewScale.SCALE_1_10) == DetailLevel.VERY_HIGH

    def test_from_scale_high(self):
        """Test HIGH detail level detection."""
        assert DetailLevel.from_scale(ViewScale.SCALE_1_20) == DetailLevel.VERY_HIGH
        assert DetailLevel.from_scale(ViewScale.SCALE_1_50) == DetailLevel.HIGH

    def test_from_scale_medium(self):
        """Test MEDIUM detail level detection."""
        assert DetailLevel.from_scale(ViewScale.SCALE_1_100) == DetailLevel.MEDIUM

    def test_from_scale_low(self):
        """Test LOW detail level detection."""
        assert DetailLevel.from_scale(ViewScale.SCALE_1_200) == DetailLevel.LOW

    def test_from_scale_very_low(self):
        """Test VERY_LOW detail level detection."""
        assert DetailLevel.from_scale(ViewScale.SCALE_1_500) == DetailLevel.VERY_LOW

    def test_detail_level_values(self):
        """Test enum values."""
        assert DetailLevel.VERY_HIGH.value == "very_high"
        assert DetailLevel.HIGH.value == "high"
        assert DetailLevel.MEDIUM.value == "medium"
        assert DetailLevel.LOW.value == "low"
        assert DetailLevel.VERY_LOW.value == "very_low"


class TestScaleBehaviorConfig:
    """Test ScaleBehaviorConfig dataclass."""

    def test_for_detail_level_very_high(self):
        """Test VERY_HIGH configuration."""
        config = ScaleBehaviorConfig.for_detail_level(DetailLevel.VERY_HIGH)

        assert config.detail_level == DetailLevel.VERY_HIGH
        assert config.min_element_size == 0.0
        assert config.min_line_length == 0.0
        assert config.line_weight_factor == 1.0
        assert config.show_small_details is True
        assert config.simplify_geometry is False

    def test_for_detail_level_high(self):
        """Test HIGH configuration."""
        config = ScaleBehaviorConfig.for_detail_level(DetailLevel.HIGH)

        assert config.detail_level == DetailLevel.HIGH
        assert config.min_element_size == 10.0
        assert config.min_line_length == 5.0
        assert config.line_weight_factor == 1.0
        assert config.show_small_details is True

    def test_for_detail_level_medium(self):
        """Test MEDIUM configuration."""
        config = ScaleBehaviorConfig.for_detail_level(DetailLevel.MEDIUM)

        assert config.detail_level == DetailLevel.MEDIUM
        assert config.min_element_size == 50.0
        assert config.min_line_length == 20.0
        assert config.line_weight_factor == 0.9
        assert config.show_small_details is True

    def test_for_detail_level_low(self):
        """Test LOW configuration."""
        config = ScaleBehaviorConfig.for_detail_level(DetailLevel.LOW)

        assert config.detail_level == DetailLevel.LOW
        assert config.min_element_size == 100.0
        assert config.min_line_length == 50.0
        assert config.line_weight_factor == 0.8
        assert config.show_small_details is False

    def test_for_detail_level_very_low(self):
        """Test VERY_LOW configuration."""
        config = ScaleBehaviorConfig.for_detail_level(DetailLevel.VERY_LOW)

        assert config.detail_level == DetailLevel.VERY_LOW
        assert config.min_element_size == 200.0
        assert config.min_line_length == 100.0
        assert config.line_weight_factor == 0.7
        assert config.show_small_details is False
        assert config.simplify_geometry is True

    def test_threshold_progression(self):
        """Test that thresholds increase with lower detail levels."""
        config_high = ScaleBehaviorConfig.for_detail_level(DetailLevel.HIGH)
        config_medium = ScaleBehaviorConfig.for_detail_level(DetailLevel.MEDIUM)
        config_low = ScaleBehaviorConfig.for_detail_level(DetailLevel.LOW)

        assert config_high.min_element_size < config_medium.min_element_size
        assert config_medium.min_element_size < config_low.min_element_size

        assert config_high.line_weight_factor > config_low.line_weight_factor

    def test_custom_config_creation(self):
        """Test creating custom configuration."""
        config = ScaleBehaviorConfig(
            detail_level=DetailLevel.MEDIUM,
            min_element_size=75.0,
            min_line_length=30.0,
            line_weight_factor=0.85,
            show_small_details=True,
        )

        assert config.detail_level == DetailLevel.MEDIUM
        assert config.min_element_size == 75.0
        assert config.line_weight_factor == 0.85


class TestViewScaleEnhancements:
    """Test ViewScale new methods."""

    def test_get_default_detail_level(self):
        """Test automatic detail level determination."""
        assert (
            ViewScale.SCALE_1_50.get_default_detail_level() == DetailLevel.HIGH
        )
        assert (
            ViewScale.SCALE_1_100.get_default_detail_level()
            == DetailLevel.MEDIUM
        )
        assert (
            ViewScale.SCALE_1_500.get_default_detail_level()
            == DetailLevel.VERY_LOW
        )

    def test_get_behavior_config(self):
        """Test behavior config retrieval."""
        config = ViewScale.SCALE_1_100.get_behavior_config()

        assert config.detail_level == DetailLevel.MEDIUM
        assert config.min_element_size == 50.0

    def test_get_behavior_config_with_override(self):
        """Test behavior config with override level."""
        config = ViewScale.SCALE_1_100.get_behavior_config(
            override_level=DetailLevel.LOW
        )

        assert config.detail_level == DetailLevel.LOW
        assert config.min_element_size == 100.0

    def test_recommend_for_view_type(self):
        """Test scale recommendations."""
        assert (
            ViewScale.recommend_for_view_type("floor_plan")
            == ViewScale.SCALE_1_100
        )
        assert (
            ViewScale.recommend_for_view_type("section") == ViewScale.SCALE_1_50
        )
        assert (
            ViewScale.recommend_for_view_type("elevation")
            == ViewScale.SCALE_1_100
        )
        assert (
            ViewScale.recommend_for_view_type("detail") == ViewScale.SCALE_1_20
        )
        assert ViewScale.recommend_for_view_type("site") == ViewScale.SCALE_1_500


class TestViewTemplateScaleBehavior:
    """Test ViewTemplate scale behavior integration."""

    def test_init_includes_scale_fields(self):
        """Test template initialization includes scale fields."""
        template = ViewTemplate("Test")

        assert hasattr(template, "scale_behaviors")
        assert hasattr(template, "_active_scale")
        assert template.scale_behaviors == {}
        assert template._active_scale is None

    def test_set_scale_behavior(self):
        """Test setting scale behavior."""
        template = ViewTemplate("Test")
        template.set_scale_behavior(ViewScale.SCALE_1_500, DetailLevel.LOW)

        config = template.get_scale_behavior(ViewScale.SCALE_1_500)
        assert config.detail_level == DetailLevel.LOW
        assert config.min_element_size == 100.0

    def test_set_scale_behavior_with_custom_config(self):
        """Test setting custom scale behavior."""
        template = ViewTemplate("Test")
        custom_config = ScaleBehaviorConfig(
            detail_level=DetailLevel.MEDIUM,
            min_element_size=75.0,
            line_weight_factor=0.85,
        )

        template.set_scale_behavior(
            ViewScale.SCALE_1_100, DetailLevel.MEDIUM, custom_config
        )

        config = template.get_scale_behavior(ViewScale.SCALE_1_100)
        assert config.min_element_size == 75.0
        assert config.line_weight_factor == 0.85

    def test_get_scale_behavior_default(self):
        """Test getting scale behavior without explicit config."""
        template = ViewTemplate("Test")

        # Should fall back to scale's default
        config = template.get_scale_behavior(ViewScale.SCALE_1_200)
        assert config.detail_level == DetailLevel.LOW

    def test_set_active_scale(self):
        """Test setting active scale."""
        template = ViewTemplate("Test")
        template.set_active_scale(ViewScale.SCALE_1_100)

        assert template._active_scale == ViewScale.SCALE_1_100

    def test_should_show_element_no_active_scale(self):
        """Test element visibility without active scale."""
        template = ViewTemplate("Test")

        # Should show everything when no active scale
        assert template.should_show_element(None, size_hint=1.0) is True

    def test_should_show_element_by_size(self):
        """Test size-based element filtering."""
        template = ViewTemplate("Test")
        template.set_scale_behavior(ViewScale.SCALE_1_200, DetailLevel.LOW)
        template.set_active_scale(ViewScale.SCALE_1_200)

        # LOW detail has min_element_size=100.0
        assert template.should_show_element(None, size_hint=50.0) is False
        assert template.should_show_element(None, size_hint=150.0) is True

    def test_should_show_element_no_size_hint(self):
        """Test element filtering without size hint."""
        template = ViewTemplate("Test")
        template.set_scale_behavior(ViewScale.SCALE_1_200, DetailLevel.LOW)
        template.set_active_scale(ViewScale.SCALE_1_200)

        # Should show when no size hint
        assert template.should_show_element(None) is True

    def test_line_weight_adjustment(self):
        """Test automatic line weight adjustment."""
        template = ViewTemplate("Test")
        template.set_scale_behavior(
            ViewScale.SCALE_1_500, DetailLevel.VERY_LOW
        )
        template.set_active_scale(ViewScale.SCALE_1_500)

        style = LineStyle.default()
        adjusted = template.apply_scale_adjusted_style(None, style)

        # VERY_LOW has line_weight_factor=0.7, should reduce weight
        assert adjusted.weight.value <= style.weight.value

    def test_adjust_line_weight(self):
        """Test line weight adjustment logic."""
        template = ViewTemplate("Test")

        # Test reduction
        adjusted = template._adjust_line_weight(LineWeight.HEAVY, 0.7)
        assert adjusted.value < LineWeight.HEAVY.value

        # Test no change
        adjusted = template._adjust_line_weight(LineWeight.MEDIUM, 1.0)
        assert adjusted == LineWeight.MEDIUM

    def test_floor_plan_scaled_factory(self):
        """Test floor_plan_scaled factory method."""
        template = ViewTemplate.floor_plan_scaled(ViewScale.SCALE_1_500)

        assert template.name == "Floor Plan Default"
        config = template.get_scale_behavior(ViewScale.SCALE_1_500)
        assert config.detail_level == DetailLevel.VERY_LOW

        # Should hide furniture at small scale
        assert template.visibility.furniture is False

    def test_section_scaled_factory(self):
        """Test section_scaled factory method."""
        template = ViewTemplate.section_scaled(ViewScale.SCALE_1_500)

        assert template.name == "Section Default"
        config = template.get_scale_behavior(ViewScale.SCALE_1_500)
        assert config.detail_level == DetailLevel.VERY_LOW

        # Should hide hidden lines at very small scale
        assert template.visibility.show_hidden_lines is False


class TestScaleConfigurator:
    """Test ScaleConfigurator helper class."""

    def test_create_template_for_scale_floor_plan(self):
        """Test creating floor plan template."""
        template = ScaleConfigurator.create_template_for_scale(
            ViewScale.SCALE_1_200, view_type="floor_plan"
        )

        assert "Floor Plan" in template.name
        config = template.get_scale_behavior(ViewScale.SCALE_1_200)
        assert config.detail_level == DetailLevel.LOW

    def test_create_template_with_hide_small_details(self):
        """Test hiding small details override."""
        template = ScaleConfigurator.create_template_for_scale(
            ViewScale.SCALE_1_200,
            view_type="floor_plan",
            hide_small_details=True,
        )

        config = template.get_scale_behavior(ViewScale.SCALE_1_200)
        assert config.show_small_details is False

    def test_create_template_with_reduce_line_weights(self):
        """Test line weight reduction override."""
        template = ScaleConfigurator.create_template_for_scale(
            ViewScale.SCALE_1_100,
            view_type="floor_plan",
            reduce_line_weights=True,
        )

        config = template.get_scale_behavior(ViewScale.SCALE_1_100)
        assert config.line_weight_factor == 0.7

    def test_create_template_with_custom_detail_level(self):
        """Test custom detail level override."""
        template = ScaleConfigurator.create_template_for_scale(
            ViewScale.SCALE_1_100,
            view_type="floor_plan",
            custom_detail_level=DetailLevel.LOW,
        )

        config = template.get_scale_behavior(ViewScale.SCALE_1_100)
        assert config.detail_level == DetailLevel.LOW

    def test_recommend_scale_without_size(self):
        """Test default scale recommendation."""
        scale = ScaleConfigurator.recommend_scale("floor_plan")
        assert scale == ViewScale.SCALE_1_100

    def test_recommend_scale_with_size(self):
        """Test intelligent scale recommendation."""
        scale = ScaleConfigurator.recommend_scale(
            "floor_plan", content_size=50000, target_paper_size="A3"
        )

        # 50000mm on A3 (420mm usable) requires small scale
        assert scale.ratio <= 0.01

    def test_recommend_scale_large_content(self):
        """Test scale recommendation for very large content."""
        scale = ScaleConfigurator.recommend_scale(
            "floor_plan", content_size=200000, target_paper_size="A3"
        )

        # Should return smallest available scale
        assert scale == ViewScale.SCALE_1_500

    def test_get_visibility_thresholds(self):
        """Test per-category visibility thresholds."""
        thresholds = ScaleConfigurator.get_visibility_thresholds(
            ViewScale.SCALE_1_200
        )

        # Structural elements have no threshold
        assert thresholds["Wall"] == 0.0
        assert thresholds["Column"] == 0.0

        # Small details have higher thresholds
        assert thresholds["Furniture"] > thresholds["Door"]
        assert thresholds["Trim"] > thresholds["Furniture"]


class TestMultiScaleTemplateSet:
    """Test multi-scale template creation."""

    def test_create_multi_scale_template_set(self):
        """Test creating template set for all scales."""
        templates = create_multi_scale_template_set("floor_plan")

        assert ViewScale.SCALE_1_20 in templates
        assert ViewScale.SCALE_1_50 in templates
        assert ViewScale.SCALE_1_100 in templates
        assert ViewScale.SCALE_1_200 in templates
        assert ViewScale.SCALE_1_500 in templates

    def test_multi_scale_templates_configured(self):
        """Test that templates are properly configured."""
        templates = create_multi_scale_template_set("floor_plan")

        # Each should have appropriate detail level
        config_50 = templates[ViewScale.SCALE_1_50].get_scale_behavior(
            ViewScale.SCALE_1_50
        )
        config_500 = templates[ViewScale.SCALE_1_500].get_scale_behavior(
            ViewScale.SCALE_1_500
        )

        assert config_50.detail_level == DetailLevel.HIGH
        assert config_500.detail_level == DetailLevel.VERY_LOW


class TestIntegration:
    """Integration tests with actual view generation."""

    def test_backward_compatibility(self):
        """Test that existing code still works without templates."""
        building = Building("Test Building")
        level = Level(building, "Ground", 0.0)
        view = FloorPlanView("Test Plan", level, scale=ViewScale.SCALE_1_100)

        # Should work without template
        assert view.scale == ViewScale.SCALE_1_100
        assert view._template is None

    def test_view_with_scaled_template(self):
        """Test view with scale-aware template."""
        building = Building("Test Building")
        level = Level(building, "Ground", 0.0)
        template = ViewTemplate.floor_plan_scaled(ViewScale.SCALE_1_500)
        view = FloorPlanView(
            "Test Plan", level, scale=ViewScale.SCALE_1_500, template=template
        )

        assert view.scale == ViewScale.SCALE_1_500
        assert view._template == template

    def test_scale_behavior_persists(self):
        """Test that scale behavior is preserved."""
        template = ViewTemplate("Test")
        template.set_scale_behavior(ViewScale.SCALE_1_100, DetailLevel.LOW)

        # Should retrieve the same config
        config1 = template.get_scale_behavior(ViewScale.SCALE_1_100)
        config2 = template.get_scale_behavior(ViewScale.SCALE_1_100)

        assert config1 == config2
        assert config1.detail_level == DetailLevel.LOW
