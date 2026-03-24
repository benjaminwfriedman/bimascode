"""
Unit tests for Material system.
"""

import pytest

from bimascode.utils.materials import Material, MaterialCategory, MaterialLibrary


class TestMaterial:
    """Test Material class."""

    def test_creation_basic(self):
        """Test creating a basic material."""
        mat = Material("Concrete")
        assert mat.name == "Concrete"
        assert mat.category is None

    def test_creation_with_properties(self):
        """Test creating material with properties."""
        mat = Material(
            "Concrete C30/37",
            category=MaterialCategory.CONCRETE,
            density=2400,
            thermal_conductivity=1.4,
        )

        assert mat.name == "Concrete C30/37"
        assert mat.category == MaterialCategory.CONCRETE
        assert mat.density == 2400
        assert mat.thermal_conductivity == 1.4

    def test_custom_properties(self):
        """Test setting custom properties."""
        mat = Material("Steel")
        mat.set_property("grade", "S355")
        mat.set_property("certified", True)

        assert mat.get_property("grade") == "S355"
        assert mat.get_property("certified") is True
        assert mat.get_property("nonexistent") is None
        assert mat.get_property("nonexistent", "default") == "default"

    def test_color(self):
        """Test material color."""
        mat = Material("Red Paint", color=(255, 0, 0))
        assert mat.color == (255, 0, 0)

    def test_transparency(self):
        """Test transparency values."""
        opaque = Material("Concrete", transparency=0.0)
        transparent = Material("Glass", transparency=0.7)
        fully_transparent = Material("Air", transparency=1.0)

        assert opaque.transparency == 0.0
        assert transparent.transparency == 0.7
        assert fully_transparent.transparency == 1.0

    def test_transparency_clamping(self):
        """Test that transparency is clamped to 0-1."""
        mat1 = Material("Test", transparency=-0.5)
        mat2 = Material("Test", transparency=1.5)

        assert mat1.transparency == 0.0
        assert mat2.transparency == 1.0

    def test_recyclable(self):
        """Test recyclable property."""
        recyclable = Material("Steel", recyclable=True)
        not_recyclable = Material("Composite", recyclable=False)

        assert recyclable.recyclable is True
        assert not_recyclable.recyclable is False


class TestMaterialCategory:
    """Test MaterialCategory enum."""

    def test_categories_exist(self):
        """Test that expected categories exist."""
        assert MaterialCategory.CONCRETE
        assert MaterialCategory.STEEL
        assert MaterialCategory.WOOD
        assert MaterialCategory.GLASS
        assert MaterialCategory.INSULATION

    def test_category_values(self):
        """Test category string values."""
        assert MaterialCategory.CONCRETE.value == "Concrete"
        assert MaterialCategory.STEEL.value == "Steel"
        assert MaterialCategory.WOOD.value == "Wood"


class TestMaterialLibrary:
    """Test MaterialLibrary with pre-defined materials."""

    def test_concrete(self):
        """Test concrete material."""
        concrete = MaterialLibrary.concrete()

        assert "Concrete" in concrete.name
        assert concrete.category == MaterialCategory.CONCRETE
        assert concrete.density == 2400
        assert concrete.thermal_conductivity == 1.4
        assert concrete.recyclable is True

    def test_concrete_with_grade(self):
        """Test concrete with specific grade."""
        concrete = MaterialLibrary.concrete("C50/60")

        assert "C50/60" in concrete.name

    def test_steel(self):
        """Test steel material."""
        steel = MaterialLibrary.steel()

        assert "Steel" in steel.name
        assert steel.category == MaterialCategory.STEEL
        assert steel.density == 7850
        assert steel.thermal_conductivity == 50
        assert steel.recyclable is True

    def test_timber(self):
        """Test timber material."""
        timber = MaterialLibrary.timber("Pine")

        assert "Pine" in timber.name
        assert timber.category == MaterialCategory.WOOD
        assert timber.density == 450
        assert timber.recyclable is True
        # Timber stores carbon (negative embodied carbon)
        assert timber.embodied_carbon < 0

    def test_brick(self):
        """Test brick material."""
        brick = MaterialLibrary.brick()

        assert "Brick" in brick.name
        assert brick.category == MaterialCategory.MASONRY
        assert brick.recyclable is True

    def test_glass(self):
        """Test glass material."""
        glass = MaterialLibrary.glass()

        assert "Glass" in glass.name
        assert glass.category == MaterialCategory.GLASS
        assert glass.transparency > 0
        assert glass.recyclable is True

    def test_insulation(self):
        """Test insulation material."""
        insulation = MaterialLibrary.insulation_mineral_wool()

        assert "Insulation" in insulation.name
        assert insulation.category == MaterialCategory.INSULATION
        # Insulation should have low thermal conductivity
        assert insulation.thermal_conductivity < 0.1
        assert insulation.recyclable is True

    def test_gypsum(self):
        """Test gypsum board material."""
        gypsum = MaterialLibrary.gypsum_board()

        assert "Gypsum" in gypsum.name
        assert gypsum.category == MaterialCategory.GYPSUM
        assert gypsum.recyclable is True


class TestMaterialThermalProperties:
    """Test thermal property comparisons."""

    def test_insulator_vs_conductor(self):
        """Test that insulators have lower k than conductors."""
        insulation = MaterialLibrary.insulation_mineral_wool()
        steel = MaterialLibrary.steel()

        # Insulation should be much better insulator (lower k)
        assert insulation.thermal_conductivity < steel.thermal_conductivity

    def test_wood_vs_concrete(self):
        """Test thermal properties of wood vs concrete."""
        wood = MaterialLibrary.timber()
        concrete = MaterialLibrary.concrete()

        # Wood is a better insulator than concrete
        assert wood.thermal_conductivity < concrete.thermal_conductivity


class TestMaterialIFCExport:
    """Test material IFC export."""

    def test_material_to_ifc(self):
        """Test exporting material to IFC."""

        try:
            import ifcopenshell

            mat = Material(
                "Test Concrete",
                category=MaterialCategory.CONCRETE,
                density=2400,
                thermal_conductivity=1.4,
                recyclable=True,
            )

            # Create minimal IFC file
            ifc_file = ifcopenshell.file(schema="IFC4")

            # Export material
            ifc_mat = mat.to_ifc(ifc_file)

            assert ifc_mat.Name == "Test Concrete"
            assert ifc_mat.Category == "Concrete"

        except ImportError:
            pytest.skip("ifcopenshell not available")

    def test_material_properties_export(self):
        """Test that material properties are exported."""

        try:
            import ifcopenshell

            mat = Material(
                "Test Material", density=2400, thermal_conductivity=1.4, specific_heat=880
            )
            mat.set_property("custom_prop", "test_value")

            ifc_file = ifcopenshell.file(schema="IFC4")
            mat.to_ifc(ifc_file)

            # Check that material properties were created
            mat_props = ifc_file.by_type("IfcMaterialProperties")
            assert len(mat_props) > 0

        except ImportError:
            pytest.skip("ifcopenshell not available")
