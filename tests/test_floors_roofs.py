"""
Unit tests for Floor, Roof, and FloorType classes.
"""

import pytest
from bimascode.architecture import (
    FloorType, Floor, Roof,
    LayerFunction,
    create_basic_floor_type,
    create_concrete_floor_type
)
from bimascode.utils.materials import MaterialLibrary
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level


class TestFloorType:
    """Tests for FloorType class."""

    def test_floor_type_creation(self):
        """Test creating a floor type."""
        floor_type = FloorType("Test Floor")
        assert floor_type.name == "Test Floor"
        assert floor_type.layer_count == 0
        assert floor_type.total_thickness_mm == 0.0

    def test_add_layer(self):
        """Test adding layers to floor type."""
        floor_type = FloorType("Test Floor")
        concrete = MaterialLibrary.concrete()

        layer = floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        assert floor_type.layer_count == 1
        assert floor_type.total_thickness_mm == 200.0
        assert layer in floor_type.layers

    def test_multiple_layers(self):
        """Test floor type with multiple layers."""
        floor_type = FloorType("Composite Floor")
        concrete = MaterialLibrary.concrete()
        insulation = MaterialLibrary.insulation_mineral_wool()

        floor_type.add_layer(concrete, 150, LayerFunction.STRUCTURE, structural=True)
        floor_type.add_layer(insulation, 50, LayerFunction.THERMAL_INSULATION)
        floor_type.add_layer(concrete, 50, LayerFunction.FINISH_INTERIOR)  # Screed

        assert floor_type.layer_count == 3
        assert floor_type.total_thickness_mm == 250.0

    def test_create_basic_floor_type(self):
        """Test the basic floor type constructor."""
        concrete = MaterialLibrary.concrete()
        floor_type = create_basic_floor_type("Simple Slab", 200, concrete)

        assert floor_type.name == "Simple Slab"
        assert floor_type.layer_count == 1
        assert floor_type.total_thickness_mm == 200.0

    def test_create_concrete_floor_type(self):
        """Test the concrete floor type constructor."""
        floor_type = create_concrete_floor_type(
            "Concrete Floor",
            slab_thickness=200,
            topping_thickness=50,
            topping_material=MaterialLibrary.concrete()
        )

        assert floor_type.name == "Concrete Floor"
        assert floor_type.layer_count == 2
        assert floor_type.total_thickness_mm == 250.0


class TestFloor:
    """Tests for Floor class."""

    def test_floor_creation(self):
        """Test creating a floor."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        floor = Floor(floor_type, boundary, level)

        assert floor.name == "Test Floor_1"
        assert floor.type == floor_type
        assert floor.level == level
        assert floor.boundary == boundary

    def test_floor_area_calculation(self):
        """Test floor area calculation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        # Rectangular floor (10m x 8m = 80m²)
        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        floor = Floor(floor_type, boundary, level)

        assert floor.area == 80_000_000.0  # mm²
        assert abs(floor.area_m2 - 80.0) < 0.01

    def test_floor_centroid(self):
        """Test floor centroid calculation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 10000), (0, 10000)]
        floor = Floor(floor_type, boundary, level)

        centroid = floor.get_centroid()
        assert centroid == (5000.0, 5000.0)

    def test_floor_center_3d(self):
        """Test 3D center calculation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=1000)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 10000), (0, 10000)]
        floor = Floor(floor_type, boundary, level)

        center = floor.get_center_3d()
        assert center == (5000.0, 5000.0, 1000.0 + 100.0)  # level + thickness/2

    def test_floor_thickness_from_type(self):
        """Test that floor inherits thickness from floor type."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 250, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        floor = Floor(floor_type, boundary, level)

        assert floor.thickness == 250.0

    def test_floor_slope(self):
        """Test floor slope parameter."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        floor = Floor(floor_type, boundary, level, slope=2.0)

        assert floor.slope == 2.0

        floor.set_slope(1.5)
        assert floor.slope == 1.5

    def test_floor_set_boundary(self):
        """Test changing floor boundary."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        boundary1 = [(0, 0), (5000, 0), (5000, 5000), (0, 5000)]
        floor = Floor(floor_type, boundary1, level)
        assert floor.area_m2 == 25.0

        boundary2 = [(0, 0), (10000, 0), (10000, 10000), (0, 10000)]
        floor.set_boundary(boundary2)
        assert floor.area_m2 == 100.0

    def test_floor_on_level(self):
        """Test that floor registers with level."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        floor = Floor(floor_type, boundary, level)

        assert floor in level.elements
        assert len(level.elements) == 1

    def test_floor_type_propagation(self):
        """Test that changing floor type updates all floor instances."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = FloorType("Test Floor")
        concrete = MaterialLibrary.concrete()
        floor_type.add_layer(concrete, 200)

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        floor1 = Floor(floor_type, boundary, level)
        floor2 = Floor(floor_type, [(0, 0), (5000, 0), (5000, 5000), (0, 5000)], level)

        assert floor1.thickness == 200.0
        assert floor2.thickness == 200.0

        # Add another layer to the type
        floor_type.add_layer(concrete, 50)

        assert floor1.thickness == 250.0
        assert floor2.thickness == 250.0

    def test_l_shaped_floor(self):
        """Test L-shaped floor area calculation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        # L-shaped boundary
        boundary = [
            (0, 0),
            (10000, 0),
            (10000, 5000),
            (5000, 5000),
            (5000, 10000),
            (0, 10000)
        ]
        floor = Floor(floor_type, boundary, level)

        # Area should be 75m² (100m² - 25m²)
        assert abs(floor.area_m2 - 75.0) < 0.01


class TestRoof:
    """Tests for Roof class."""

    def test_roof_creation(self):
        """Test creating a roof."""
        building = Building("Test Building")
        level = Level(building, "Roof Level", elevation=9000)
        roof_type = create_basic_floor_type("Test Roof", 250, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        roof = Roof(roof_type, boundary, level)

        assert roof.name == "Test Roof_1"
        assert roof.type == roof_type
        assert roof.level == level
        assert roof.boundary == boundary

    def test_roof_with_drainage_slope(self):
        """Test roof with drainage slope."""
        building = Building("Test Building")
        level = Level(building, "Roof Level", elevation=9000)
        roof_type = create_basic_floor_type("Test Roof", 250, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        roof = Roof(roof_type, boundary, level, slope=2.0)  # 2% slope

        assert roof.slope == 2.0

    def test_roof_area_calculation(self):
        """Test roof area calculation."""
        building = Building("Test Building")
        level = Level(building, "Roof Level", elevation=9000)
        roof_type = create_basic_floor_type("Test Roof", 250, MaterialLibrary.concrete())

        # Rectangular roof (10m x 8m = 80m²)
        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        roof = Roof(roof_type, boundary, level)

        assert roof.area == 80_000_000.0  # mm²
        assert abs(roof.area_m2 - 80.0) < 0.01

    def test_roof_centroid(self):
        """Test roof centroid calculation."""
        building = Building("Test Building")
        level = Level(building, "Roof Level", elevation=9000)
        roof_type = create_basic_floor_type("Test Roof", 250, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 10000), (0, 10000)]
        roof = Roof(roof_type, boundary, level)

        centroid = roof.get_centroid()
        assert centroid == (5000.0, 5000.0)

    def test_roof_on_level(self):
        """Test that roof registers with level."""
        building = Building("Test Building")
        level = Level(building, "Roof Level", elevation=9000)
        roof_type = create_basic_floor_type("Test Roof", 250, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        roof = Roof(roof_type, boundary, level)

        assert roof in level.elements
        assert len(level.elements) == 1

    def test_roof_set_slope(self):
        """Test changing roof slope."""
        building = Building("Test Building")
        level = Level(building, "Roof Level", elevation=9000)
        roof_type = create_basic_floor_type("Test Roof", 250, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        roof = Roof(roof_type, boundary, level, slope=1.0)

        assert roof.slope == 1.0

        roof.set_slope(2.5)
        assert roof.slope == 2.5

    def test_roof_thickness_from_type(self):
        """Test that roof inherits thickness from roof type."""
        building = Building("Test Building")
        level = Level(building, "Roof Level", elevation=9000)
        roof_type = create_basic_floor_type("Test Roof", 300, MaterialLibrary.concrete())

        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        roof = Roof(roof_type, boundary, level)

        assert roof.thickness == 300.0


class TestIntegration:
    """Integration tests for walls, floors, and roofs together."""

    def test_complete_building(self):
        """Test a complete building with walls, floors, and roof."""
        building = Building("Test Building")
        ground = Level(building, "Ground Floor", elevation=0)
        first = Level(building, "First Floor", elevation=3000)
        roof_level = Level(building, "Roof", elevation=6000)

        # Create floor types
        concrete = MaterialLibrary.concrete()
        floor_type = create_basic_floor_type("Concrete Slab", 200, concrete)
        wall_type = FloorType("Wall Type")
        wall_type.add_layer(concrete, 200)

        # Create floors
        boundary = [(0, 0), (10000, 0), (10000, 8000), (0, 8000)]
        ground_floor = Floor(floor_type, boundary, ground)
        first_floor = Floor(floor_type, boundary, first)
        roof = Roof(floor_type, boundary, roof_level, slope=2.0)

        # Verify structure
        assert len(building.levels) == 3
        assert len(ground.elements) == 1
        assert len(first.elements) == 1
        assert len(roof_level.elements) == 1

        # Verify areas
        assert ground_floor.area_m2 == 80.0
        assert first_floor.area_m2 == 80.0
        assert roof.area_m2 == 80.0

    def test_multiple_floors_on_level(self):
        """Test multiple floor segments on same level."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        floor_type = create_basic_floor_type("Test Floor", 200, MaterialLibrary.concrete())

        floor1 = Floor(floor_type, [(0, 0), (5000, 0), (5000, 5000), (0, 5000)], level)
        floor2 = Floor(floor_type, [(5000, 0), (10000, 0), (10000, 5000), (5000, 5000)], level)

        assert len(level.elements) == 2
        assert floor1.area_m2 == 25.0
        assert floor2.area_m2 == 25.0
