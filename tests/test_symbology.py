"""Tests for the symbology configuration system."""

import pytest

from bimascode.architecture.door import Door
from bimascode.architecture.wall import Wall
from bimascode.architecture.window import Window
from bimascode.drawing.line_styles import LineStyle, LineWeight
from bimascode.drawing.symbology import (
    ElementSymbology,
    FillMode,
    SymbologySettings,
    get_default_symbology,
)
from bimascode.structure.column import StructuralColumn


class TestFillMode:
    """Tests for FillMode enum."""

    def test_fill_mode_values(self):
        """Test FillMode enum has expected values."""
        assert FillMode.MATERIAL.value == "material"
        assert FillMode.SOLID.value == "solid"
        assert FillMode.EMPTY.value == "empty"
        assert FillMode.PATTERN.value == "pattern"


class TestElementSymbology:
    """Tests for ElementSymbology dataclass."""

    def test_default_values(self):
        """Test ElementSymbology has reasonable defaults."""
        symbology = ElementSymbology()

        # Line styles default to None (use element defaults)
        assert symbology.cut_style is None
        assert symbology.visible_style is None
        assert symbology.above_style is None

        # Fill defaults
        assert symbology.fill_mode == FillMode.MATERIAL
        assert symbology.fill_pattern is None
        assert symbology.fill_color is None

        # Element-specific flags default to True
        assert symbology.show_swing is True
        assert symbology.show_panel is True
        assert symbology.show_x_pattern is True
        assert symbology.outline_only is False
        assert symbology.show_hatching is True
        assert symbology.show_jambs is True

    def test_custom_values(self):
        """Test ElementSymbology with custom values."""
        custom_style = LineStyle.cut_wide()
        symbology = ElementSymbology(
            cut_style=custom_style,
            fill_mode=FillMode.EMPTY,
            show_swing=False,
            outline_only=True,
        )

        assert symbology.cut_style == custom_style
        assert symbology.fill_mode == FillMode.EMPTY
        assert symbology.show_swing is False
        assert symbology.outline_only is True

    def test_immutable(self):
        """Test ElementSymbology is frozen."""
        symbology = ElementSymbology()
        with pytest.raises(AttributeError):
            symbology.fill_mode = FillMode.SOLID


class TestGetDefaultSymbology:
    """Tests for get_default_symbology function."""

    def test_wall_defaults(self):
        """Test Wall default symbology."""
        symbology = get_default_symbology("Wall")

        assert symbology.cut_style == LineStyle.cut_heavy()
        assert symbology.visible_style == LineStyle.visible()
        assert symbology.fill_mode == FillMode.MATERIAL
        assert symbology.show_hatching is True

    def test_door_defaults(self):
        """Test Door default symbology."""
        symbology = get_default_symbology("Door")

        assert symbology.cut_style == LineStyle.cut_wide()
        assert symbology.fill_mode == FillMode.EMPTY
        assert symbology.show_swing is True
        assert symbology.show_panel is True
        assert symbology.show_jambs is True

    def test_window_defaults(self):
        """Test Window default symbology."""
        symbology = get_default_symbology("Window")

        assert symbology.cut_style == LineStyle.cut_wide()
        assert symbology.fill_mode == FillMode.EMPTY
        assert symbology.outline_only is False
        assert symbology.show_jambs is True

    def test_column_defaults(self):
        """Test StructuralColumn default symbology."""
        symbology = get_default_symbology("StructuralColumn")

        assert symbology.cut_style == LineStyle.cut_heavy()
        assert symbology.visible_style == LineStyle.visible()
        assert symbology.fill_mode == FillMode.EMPTY
        assert symbology.show_x_pattern is True

    def test_unknown_element(self):
        """Test unknown element type gets default symbology."""
        symbology = get_default_symbology("UnknownElement")

        # Should get default fallback symbology
        assert symbology.cut_style == LineStyle.cut_medium()
        assert symbology.visible_style == LineStyle.visible()
        assert symbology.fill_mode == FillMode.EMPTY


class TestSymbologySettings:
    """Tests for SymbologySettings class."""

    def test_initial_state(self):
        """Test SymbologySettings initial state."""
        settings = SymbologySettings()

        assert settings.version == 0
        # Should return defaults for any element type
        wall_symbology = settings.get(Wall)
        assert wall_symbology.cut_style == LineStyle.cut_heavy()

    def test_set_increments_version(self):
        """Test set() increments version."""
        settings = SymbologySettings()
        assert settings.version == 0

        settings.set(Wall, ElementSymbology(fill_mode=FillMode.EMPTY))
        assert settings.version == 1

        settings.set(Door, ElementSymbology(show_swing=False))
        assert settings.version == 2

    def test_get_returns_override(self):
        """Test get() returns override when set."""
        settings = SymbologySettings()

        custom = ElementSymbology(
            cut_style=LineStyle.cut_wide(),
            fill_mode=FillMode.EMPTY,
        )
        settings.set(Wall, custom)

        result = settings.get(Wall)
        assert result == custom
        assert result.cut_style == LineStyle.cut_wide()

    def test_get_returns_default_when_no_override(self):
        """Test get() returns default when no override."""
        settings = SymbologySettings()

        # Set override for Wall but not Door
        settings.set(Wall, ElementSymbology(fill_mode=FillMode.EMPTY))

        # Door should still return defaults
        door_symbology = settings.get(Door)
        assert door_symbology.show_swing is True
        assert door_symbology.fill_mode == FillMode.EMPTY  # Door default

    def test_get_for_element(self):
        """Test get_for_element() works with instances."""
        settings = SymbologySettings()

        custom = ElementSymbology(show_x_pattern=False)
        settings.set(StructuralColumn, custom)

        # We can't create a real StructuralColumn without a ColumnType,
        # so we test via get() instead
        result = settings.get(StructuralColumn)
        assert result.show_x_pattern is False

    def test_reset_single_type(self):
        """Test reset() for single element type."""
        settings = SymbologySettings()

        settings.set(Wall, ElementSymbology(fill_mode=FillMode.EMPTY))
        settings.set(Door, ElementSymbology(show_swing=False))
        assert settings.version == 2

        settings.reset(Wall)
        assert settings.version == 3

        # Wall should be back to default
        wall_symbology = settings.get(Wall)
        assert wall_symbology.fill_mode == FillMode.MATERIAL

        # Door should still be overridden
        door_symbology = settings.get(Door)
        assert door_symbology.show_swing is False

    def test_reset_all(self):
        """Test reset() for all types."""
        settings = SymbologySettings()

        settings.set(Wall, ElementSymbology(fill_mode=FillMode.EMPTY))
        settings.set(Door, ElementSymbology(show_swing=False))

        settings.reset()  # Reset all

        # Both should be back to defaults
        wall_symbology = settings.get(Wall)
        assert wall_symbology.fill_mode == FillMode.MATERIAL

        door_symbology = settings.get(Door)
        assert door_symbology.show_swing is True

    def test_reset_nonexistent_no_version_change(self):
        """Test reset() on non-overridden type doesn't change version."""
        settings = SymbologySettings()
        assert settings.version == 0

        settings.reset(Wall)  # Was never set
        assert settings.version == 0  # No change

    def test_aia_defaults_factory(self):
        """Test aia_defaults() class method."""
        settings = SymbologySettings.aia_defaults()

        assert settings.version == 0
        # Should return AIA defaults
        wall_symbology = settings.get(Wall)
        assert wall_symbology.cut_style == LineStyle.cut_heavy()

    def test_simplified_factory(self):
        """Test simplified() class method."""
        settings = SymbologySettings.simplified()

        # Version should be incremented for each set()
        assert settings.version > 0

        # Wall should have hatching disabled
        wall_symbology = settings.get(Wall)
        assert wall_symbology.show_hatching is False
        assert wall_symbology.fill_mode == FillMode.EMPTY

        # Door should have swing disabled
        door_symbology = settings.get(Door)
        assert door_symbology.show_swing is False

        # Column should have X pattern disabled
        column_symbology = settings.get(StructuralColumn)
        assert column_symbology.show_x_pattern is False


class TestSymbologyWithLineStyles:
    """Tests for symbology integration with LineStyle."""

    def test_custom_line_weight(self):
        """Test using custom line weight in symbology."""
        custom_style = LineStyle(weight=LineWeight.EXTRA_FINE)
        symbology = ElementSymbology(cut_style=custom_style)

        assert symbology.cut_style.weight == LineWeight.EXTRA_FINE

    def test_with_color(self):
        """Test symbology with custom fill color."""
        symbology = ElementSymbology(
            fill_mode=FillMode.SOLID,
            fill_color=(255, 0, 0),  # Red
        )

        assert symbology.fill_mode == FillMode.SOLID
        assert symbology.fill_color == (255, 0, 0)

    def test_custom_pattern(self):
        """Test symbology with custom pattern."""
        symbology = ElementSymbology(
            fill_mode=FillMode.PATTERN,
            fill_pattern="ANSI31",
        )

        assert symbology.fill_mode == FillMode.PATTERN
        assert symbology.fill_pattern == "ANSI31"
