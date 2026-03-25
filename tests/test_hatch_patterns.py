"""Tests for hatch pattern functionality."""

import pytest

from bimascode.architecture.wall_type import Layer, LayerFunction
from bimascode.drawing.hatch_patterns import (
    DEFAULT_HATCH_PATTERN,
    MATERIAL_HATCH_PATTERNS,
    HatchPattern,
    get_hatch_pattern_for_layer,
    get_hatch_pattern_for_material,
)
from bimascode.utils.materials import Material, MaterialCategory, MaterialLibrary


class TestHatchPattern:
    """Tests for HatchPattern dataclass."""

    def test_default_values(self):
        """Test HatchPattern with default values."""
        pattern = HatchPattern("SOLID")
        assert pattern.name == "SOLID"
        assert pattern.scale == 1.0
        assert pattern.rotation == 0.0
        assert pattern.color is None

    def test_custom_values(self):
        """Test HatchPattern with custom values."""
        pattern = HatchPattern("AR-CONC", scale=0.02, rotation=45.0, color=(128, 128, 128))
        assert pattern.name == "AR-CONC"
        assert pattern.scale == 0.02
        assert pattern.rotation == 45.0
        assert pattern.color == (128, 128, 128)

    def test_frozen(self):
        """Test that HatchPattern is immutable."""
        from dataclasses import FrozenInstanceError

        pattern = HatchPattern("SOLID")
        with pytest.raises(FrozenInstanceError):
            pattern.name = "CHANGED"


class TestMaterialHatchMapping:
    """Tests for material-to-hatch mapping."""

    def test_all_categories_have_patterns(self):
        """Test that all MaterialCategory values have a pattern mapping."""
        for category in MaterialCategory:
            assert category in MATERIAL_HATCH_PATTERNS

    def test_concrete_pattern(self):
        """Test concrete material returns AR-CONC pattern."""
        material = MaterialLibrary.concrete()
        pattern = get_hatch_pattern_for_material(material)
        assert pattern.name == "AR-CONC"
        assert pattern.scale == 0.02

    def test_steel_pattern(self):
        """Test steel material returns ANSI31 pattern."""
        material = MaterialLibrary.steel()
        pattern = get_hatch_pattern_for_material(material)
        assert pattern.name == "ANSI31"

    def test_wood_pattern(self):
        """Test wood material returns AR-PARQ1 pattern."""
        material = MaterialLibrary.timber()
        pattern = get_hatch_pattern_for_material(material)
        assert pattern.name == "AR-PARQ1"

    def test_masonry_pattern(self):
        """Test masonry material returns AR-BRSTD pattern."""
        material = MaterialLibrary.brick()
        pattern = get_hatch_pattern_for_material(material)
        assert pattern.name == "AR-BRSTD"

    def test_glass_pattern(self):
        """Test glass material returns SOLID with color."""
        material = MaterialLibrary.glass()
        pattern = get_hatch_pattern_for_material(material)
        assert pattern.name == "SOLID"
        assert pattern.color == (200, 230, 255)

    def test_insulation_pattern(self):
        """Test insulation material returns INSUL pattern."""
        material = MaterialLibrary.insulation_mineral_wool()
        pattern = get_hatch_pattern_for_material(material)
        assert pattern.name == "INSUL"

    def test_gypsum_pattern(self):
        """Test gypsum material returns SOLID with color."""
        material = MaterialLibrary.gypsum_board()
        pattern = get_hatch_pattern_for_material(material)
        assert pattern.name == "SOLID"
        assert pattern.color == (240, 240, 240)

    def test_none_material_fallback(self):
        """Test that None material returns default SOLID pattern."""
        pattern = get_hatch_pattern_for_material(None)
        assert pattern == DEFAULT_HATCH_PATTERN
        assert pattern.name == "SOLID"

    def test_none_category_fallback(self):
        """Test that material with None category returns default pattern."""
        material = Material("Unknown", category=None)
        pattern = get_hatch_pattern_for_material(material)
        assert pattern == DEFAULT_HATCH_PATTERN


class TestLayerHatching:
    """Tests for layer hatch pattern retrieval."""

    def test_concrete_layer_pattern(self):
        """Test layer with concrete material gets concrete pattern."""
        concrete = MaterialLibrary.concrete()
        layer = Layer(concrete, 200, LayerFunction.STRUCTURE)
        pattern = get_hatch_pattern_for_layer(layer)
        assert pattern.name == "AR-CONC"

    def test_insulation_layer_pattern(self):
        """Test layer with insulation material gets insulation pattern."""
        insulation = MaterialLibrary.insulation_mineral_wool()
        layer = Layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
        pattern = get_hatch_pattern_for_layer(layer)
        assert pattern.name == "INSUL"

    def test_gypsum_layer_pattern(self):
        """Test layer with gypsum material gets gypsum pattern."""
        gypsum = MaterialLibrary.gypsum_board()
        layer = Layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)
        pattern = get_hatch_pattern_for_layer(layer)
        assert pattern.name == "SOLID"
        assert pattern.color == (240, 240, 240)


class TestPatternProperties:
    """Tests for pattern property values."""

    def test_pattern_scales_are_positive(self):
        """Test that all pattern scales are positive."""
        for pattern in MATERIAL_HATCH_PATTERNS.values():
            assert pattern.scale > 0

    def test_pattern_rotations_are_valid(self):
        """Test that all pattern rotations are valid degrees."""
        for pattern in MATERIAL_HATCH_PATTERNS.values():
            assert 0 <= pattern.rotation < 360

    def test_pattern_colors_are_valid_rgb(self):
        """Test that all pattern colors are valid RGB tuples."""
        for pattern in MATERIAL_HATCH_PATTERNS.values():
            if pattern.color is not None:
                r, g, b = pattern.color
                assert 0 <= r <= 255
                assert 0 <= g <= 255
                assert 0 <= b <= 255
