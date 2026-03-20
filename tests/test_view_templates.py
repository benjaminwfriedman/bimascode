"""
Unit tests for view templates.
"""

import pytest
from bimascode.drawing.view_templates import (
    CategoryVisibility,
    GraphicOverride,
    ViewVisibilitySettings,
    ViewTemplate,
)
from bimascode.drawing.line_styles import LineStyle, LineWeight
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import Wall, create_basic_wall_type
from bimascode.architecture.ceiling import Ceiling
from bimascode.architecture.ceiling_type import CeilingType
from bimascode.utils.materials import MaterialLibrary


class TestCategoryVisibility:
    """Tests for CategoryVisibility enum."""

    def test_visibility_values(self):
        """Test visibility enum values."""
        assert CategoryVisibility.VISIBLE.value == "visible"
        assert CategoryVisibility.HIDDEN.value == "hidden"
        assert CategoryVisibility.HALFTONE.value == "halftone"


class TestGraphicOverride:
    """Tests for GraphicOverride class."""

    def test_default_override(self):
        """Test default graphic override."""
        override = GraphicOverride()
        assert override.visibility == CategoryVisibility.VISIBLE
        assert override.line_weight is None
        assert override.line_color is None
        assert override.halftone is False

    def test_override_with_settings(self):
        """Test graphic override with custom settings."""
        override = GraphicOverride(
            visibility=CategoryVisibility.HALFTONE,
            line_weight=LineWeight.FINE,
            line_color=(128, 128, 128),
            halftone=True,
        )
        assert override.visibility == CategoryVisibility.HALFTONE
        assert override.line_weight == LineWeight.FINE
        assert override.line_color == (128, 128, 128)
        assert override.halftone is True

    def test_apply_to_style_weight(self):
        """Test applying override to line style - weight."""
        override = GraphicOverride(line_weight=LineWeight.EXTRA_FINE)
        style = LineStyle.cut_heavy()
        modified = override.apply_to_style(style)
        assert modified.weight == LineWeight.EXTRA_FINE

    def test_apply_to_style_color(self):
        """Test applying override to line style - color."""
        override = GraphicOverride(line_color=(255, 0, 0))
        style = LineStyle.default()
        modified = override.apply_to_style(style)
        assert modified.color == (255, 0, 0)

    def test_apply_to_style_halftone(self):
        """Test applying halftone override."""
        override = GraphicOverride(halftone=True)
        style = LineStyle.default()
        modified = override.apply_to_style(style)
        assert modified.color == (128, 128, 128)


class TestViewVisibilitySettings:
    """Tests for ViewVisibilitySettings class."""

    def test_default_visibility(self):
        """Test default visibility settings."""
        settings = ViewVisibilitySettings()
        assert settings.walls is True
        assert settings.doors is True
        assert settings.windows is True
        assert settings.ceilings is False  # Hidden by default
        assert settings.furniture is False

    def test_is_category_visible(self):
        """Test category visibility lookup."""
        settings = ViewVisibilitySettings()
        assert settings.is_category_visible("Wall") is True
        assert settings.is_category_visible("Ceiling") is False
        assert settings.is_category_visible("Unknown") is True  # Default

    def test_custom_visibility(self):
        """Test custom visibility settings."""
        settings = ViewVisibilitySettings(
            walls=False,
            ceilings=True,
        )
        assert settings.walls is False
        assert settings.ceilings is True


class TestViewTemplate:
    """Tests for ViewTemplate class."""

    def test_template_creation(self):
        """Test creating a view template."""
        template = ViewTemplate("Test Template")
        assert template.name == "Test Template"
        assert template.visibility is not None

    def test_set_category_override(self):
        """Test setting category override."""
        template = ViewTemplate("Test")
        override = GraphicOverride(halftone=True)
        template.set_category_override("Wall", override)

        result = template.get_category_override("Wall")
        assert result is not None
        assert result.halftone is True

    def test_get_missing_override(self):
        """Test getting non-existent override."""
        template = ViewTemplate("Test")
        result = template.get_category_override("Missing")
        assert result is None

    def test_floor_plan_default(self):
        """Test floor plan default template."""
        template = ViewTemplate.floor_plan_default()
        assert template.name == "Floor Plan Default"
        assert template.visibility.ceilings is False

        # Structure should be halftone
        col_override = template.get_category_override("StructuralColumn")
        assert col_override is not None
        assert col_override.halftone is True

    def test_reflected_ceiling_plan(self):
        """Test reflected ceiling plan template."""
        template = ViewTemplate.reflected_ceiling_plan()
        assert template.name == "Reflected Ceiling Plan"
        assert template.visibility.ceilings is True
        assert template.visibility.walls is False

    def test_structural_plan(self):
        """Test structural plan template."""
        template = ViewTemplate.structural_plan()
        assert template.name == "Structural Plan"

        # Walls should be halftone
        wall_override = template.get_category_override("Wall")
        assert wall_override is not None
        assert wall_override.halftone is True

    def test_filter_visible_basic(self):
        """Test filtering elements by visibility using real element types."""
        template = ViewTemplate("Test")
        template.visibility.walls = True
        template.visibility.ceilings = False

        # Create real building elements
        building = Building("Test Building")
        level = Level(building, "Ground", 0)
        wall_type = create_basic_wall_type("200mm Concrete", 200, MaterialLibrary.concrete())
        ceiling_type = CeilingType("Gypsum Ceiling", thickness=15)

        wall1 = Wall(wall_type, (0, 0), (5000, 0), level)
        wall2 = Wall(wall_type, (5000, 0), (5000, 4000), level)
        ceiling = Ceiling(
            ceiling_type,
            [(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level,
        )

        elements = [wall1, ceiling, wall2]
        filtered = template.filter_visible(elements)

        # Should only include walls (ceilings hidden)
        assert len(filtered) == 2
        assert all(isinstance(e, Wall) for e in filtered)

    def test_filter_visible_with_override(self):
        """Test filtering with category override using real elements."""
        template = ViewTemplate("Test")
        template.visibility.walls = True  # Normally visible
        template.set_category_override(
            "Wall",
            GraphicOverride(visibility=CategoryVisibility.HIDDEN),
        )

        # Create a real wall
        building = Building("Test Building")
        level = Level(building, "Ground", 0)
        wall_type = create_basic_wall_type("200mm Concrete", 200, MaterialLibrary.concrete())
        wall = Wall(wall_type, (0, 0), (5000, 0), level)

        elements = [wall]
        filtered = template.filter_visible(elements)

        # Override should hide it
        assert len(filtered) == 0

    def test_repr(self):
        """Test template string representation."""
        template = ViewTemplate("My Template")
        assert "My Template" in repr(template)
