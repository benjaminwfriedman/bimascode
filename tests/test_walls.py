"""
Unit tests for Wall and WallType classes.
"""

import math

from bimascode.architecture import (
    Layer,
    LayerFunction,
    Wall,
    WallFunction,
    WallType,
    create_basic_wall_type,
    create_stud_wall_type,
)
from bimascode.architecture.wall_joins import WallJoinStyle
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.materials import MaterialLibrary


class TestLayer:
    """Tests for Layer class."""

    def test_layer_creation(self):
        """Test creating a material layer."""
        material = MaterialLibrary.concrete()
        layer = Layer(material, 200, LayerFunction.STRUCTURE, structural=True)

        assert layer.material == material
        assert layer.thickness_mm == 200.0
        assert layer.function == LayerFunction.STRUCTURE
        assert layer.structural is True

    def test_layer_with_length_unit(self):
        """Test layer with Length object."""
        from bimascode.utils.units import Length

        material = MaterialLibrary.concrete()
        thickness = Length(0.2, "m")
        layer = Layer(material, thickness, LayerFunction.STRUCTURE)

        assert layer.thickness_mm == 200.0


class TestWallType:
    """Tests for WallType class."""

    def test_wall_type_creation(self):
        """Test creating a wall type."""
        wall_type = WallType("Test Wall")
        assert wall_type.name == "Test Wall"
        assert wall_type.layer_count == 0
        assert wall_type.total_width_mm == 0.0

    def test_add_layer(self):
        """Test adding layers to wall type."""
        wall_type = WallType("Test Wall")
        concrete = MaterialLibrary.concrete()

        layer = wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

        assert wall_type.layer_count == 1
        assert wall_type.total_width_mm == 200.0
        assert layer in wall_type.layers

    def test_multiple_layers(self):
        """Test wall type with multiple layers."""
        wall_type = WallType("Exterior Wall")
        brick = MaterialLibrary.brick()
        insulation = MaterialLibrary.insulation_mineral_wool()
        gypsum = MaterialLibrary.gypsum_board()

        wall_type.add_layer(brick, 100, LayerFunction.FINISH_EXTERIOR)
        wall_type.add_layer(insulation, 90, LayerFunction.THERMAL_INSULATION)
        wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)

        assert wall_type.layer_count == 3
        assert wall_type.total_width_mm == 202.5

    def test_remove_layer(self):
        """Test removing a layer."""
        wall_type = WallType("Test Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200)
        wall_type.add_layer(concrete, 100)

        assert wall_type.layer_count == 2
        wall_type.remove_layer(0)
        assert wall_type.layer_count == 1
        assert wall_type.total_width_mm == 100.0

    def test_get_layer(self):
        """Test getting a layer by index."""
        wall_type = WallType("Test Wall")
        concrete = MaterialLibrary.concrete()
        brick = MaterialLibrary.brick()

        wall_type.add_layer(concrete, 200)
        wall_type.add_layer(brick, 100)

        layer0 = wall_type.get_layer(0)
        assert layer0.material == concrete
        layer1 = wall_type.get_layer(1)
        assert layer1.material == brick

    def test_get_structural_layers(self):
        """Test getting structural layers."""
        wall_type = WallType("Test Wall")
        concrete = MaterialLibrary.concrete()
        gypsum = MaterialLibrary.gypsum_board()

        wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_EXTERIOR, structural=False)
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
        wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR, structural=False)

        structural = wall_type.get_structural_layers()
        assert len(structural) == 1
        assert structural[0].material == concrete

    def test_get_layers_by_function(self):
        """Test filtering layers by function."""
        wall_type = WallType("Test Wall")
        gypsum = MaterialLibrary.gypsum_board()

        wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_EXTERIOR)
        wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_INTERIOR)
        wall_type.add_layer(gypsum, 12.5, LayerFunction.FINISH_EXTERIOR)

        exterior_layers = wall_type.get_layers_by_function(LayerFunction.FINISH_EXTERIOR)
        assert len(exterior_layers) == 2

    def test_create_basic_wall_type(self):
        """Test the basic wall type constructor."""
        concrete = MaterialLibrary.concrete()
        wall_type = create_basic_wall_type("Simple Wall", 200, concrete)

        assert wall_type.name == "Simple Wall"
        assert wall_type.layer_count == 1
        assert wall_type.total_width_mm == 200.0
        assert wall_type.get_structural_layers()[0].material == concrete

    def test_create_stud_wall_type(self):
        """Test the stud wall type constructor."""
        timber = MaterialLibrary.timber()
        gypsum = MaterialLibrary.gypsum_board()

        wall_type = create_stud_wall_type(
            "Stud Wall",
            stud_material=timber,
            stud_depth=90,
            interior_finish=gypsum,
            interior_finish_thickness=12.5,
            exterior_finish=gypsum,
            exterior_finish_thickness=12.5,
        )

        assert wall_type.name == "Stud Wall"
        assert wall_type.layer_count == 3
        assert wall_type.total_width_mm == 115.0


class TestWall:
    """Tests for Wall class."""

    def test_wall_creation(self):
        """Test creating a wall."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level)

        assert wall.name == "Test Wall_1"
        assert wall.type == wall_type
        assert wall.level == level
        assert wall.start_point == (0, 0)
        assert wall.end_point == (5000, 0)

    def test_wall_length(self):
        """Test wall length calculation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level)
        assert wall.length == 5000.0

        # Diagonal wall
        wall2 = Wall(wall_type, (0, 0), (3000, 4000), level)
        assert wall2.length == 5000.0  # 3-4-5 triangle

    def test_wall_angle(self):
        """Test wall angle calculation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        # Horizontal wall (0 degrees)
        wall1 = Wall(wall_type, (0, 0), (5000, 0), level)
        assert abs(wall1.angle) < 0.001

        # Vertical wall (90 degrees)
        wall2 = Wall(wall_type, (0, 0), (0, 5000), level)
        assert abs(wall2.angle - math.pi / 2) < 0.001

        # 45 degree wall
        wall3 = Wall(wall_type, (0, 0), (5000, 5000), level)
        assert abs(wall3.angle - math.pi / 4) < 0.001

    def test_wall_midpoint(self):
        """Test wall midpoint calculation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (10000, 0), level)
        mid = wall.get_midpoint()
        assert mid == (5000.0, 0.0)

    def test_wall_center_3d(self):
        """Test 3D center calculation."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=1000)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (10000, 0), level, height=3000)
        center = wall.get_center_3d()
        assert center == (5000.0, 0.0, 1000.0 + 1500.0)  # level + height/2

    def test_wall_reverse(self):
        """Test reversing wall direction."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level)
        wall.reverse()

        assert wall.start_point == (5000, 0)
        assert wall.end_point == (0, 0)

    def test_wall_set_points(self):
        """Test setting wall endpoints."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level)
        wall.set_start_point((1000, 0))
        wall.set_end_point((6000, 0))

        assert wall.start_point == (1000, 0)
        assert wall.end_point == (6000, 0)
        assert wall.length == 5000.0

    def test_wall_height(self):
        """Test wall height."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level, height=4000)
        assert wall.height == 4000.0

        wall.set_height(3500)
        assert wall.height == 3500.0

    def test_wall_width_from_type(self):
        """Test that wall inherits width from wall type."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 250, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level)
        assert wall.width == 250.0

    def test_wall_type_propagation(self):
        """Test that changing wall type updates all wall instances."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = WallType("Test Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200)

        wall1 = Wall(wall_type, (0, 0), (5000, 0), level)
        wall2 = Wall(wall_type, (0, 0), (0, 5000), level)

        assert wall1.width == 200.0
        assert wall2.width == 200.0

        # Add another layer to the type
        wall_type.add_layer(concrete, 100)

        assert wall1.width == 300.0
        assert wall2.width == 300.0

    def test_wall_instance_override(self):
        """Test that wall can override type width."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall1 = Wall(wall_type, (0, 0), (5000, 0), level)
        wall2 = Wall(wall_type, (0, 0), (0, 5000), level)

        # Override wall1's width
        wall1.set_parameter("width", 300, override=True)

        assert wall1.width == 300.0
        assert wall2.width == 200.0

    def test_multiple_walls_on_level(self):
        """Test multiple walls on same level."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall1 = Wall(wall_type, (0, 0), (5000, 0), level)
        wall2 = Wall(wall_type, (5000, 0), (5000, 4000), level)
        wall3 = Wall(wall_type, (5000, 4000), (0, 4000), level)
        wall4 = Wall(wall_type, (0, 4000), (0, 0), level)

        assert len(level.elements) == 4
        assert wall1 in level.elements
        assert wall2 in level.elements
        assert wall3 in level.elements
        assert wall4 in level.elements

    def test_wall_join_styles_default(self):
        """Test that wall join styles default to BUTT."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level)

        assert wall.join_style_start == WallJoinStyle.BUTT
        assert wall.join_style_end == WallJoinStyle.BUTT

    def test_wall_set_join_style(self):
        """Test setting join styles on wall endpoints."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level)

        wall.join_style_start = WallJoinStyle.MITER
        wall.join_style_end = WallJoinStyle.SQUARE_OFF

        assert wall.join_style_start == WallJoinStyle.MITER
        assert wall.join_style_end == WallJoinStyle.SQUARE_OFF
        assert wall.get_join_style(0) == WallJoinStyle.MITER
        assert wall.get_join_style(1) == WallJoinStyle.SQUARE_OFF

    def test_wall_set_join_style_method(self):
        """Test set_join_style method."""
        building = Building("Test Building")
        level = Level(building, "Level 1", elevation=0)
        wall_type = create_basic_wall_type("Test Wall", 200, MaterialLibrary.concrete())

        wall = Wall(wall_type, (0, 0), (5000, 0), level)

        wall.set_join_style(0, WallJoinStyle.MITER)
        wall.set_join_style(1, WallJoinStyle.SQUARE_OFF)

        assert wall.join_style_start == WallJoinStyle.MITER
        assert wall.join_style_end == WallJoinStyle.SQUARE_OFF


class TestWallFunction:
    """Tests for WallFunction enum and wall type function parameter."""

    def test_wall_function_enum_values(self):
        """Test that WallFunction enum has all expected values."""
        assert WallFunction.EXTERIOR.value == "Exterior"
        assert WallFunction.INTERIOR.value == "Interior"
        assert WallFunction.FOUNDATION.value == "Foundation"
        assert WallFunction.RETAINING.value == "Retaining"
        assert WallFunction.SOFFIT.value == "Soffit"
        assert WallFunction.CORE_SHAFT.value == "Core-Shaft"

    def test_wall_type_default_function(self):
        """Test that wall type defaults to INTERIOR function."""
        wall_type = WallType("Test Wall")
        assert wall_type.function == WallFunction.INTERIOR

    def test_wall_type_with_function(self):
        """Test creating wall type with specific function."""
        wall_type = WallType("Exterior Wall", function=WallFunction.EXTERIOR)
        assert wall_type.function == WallFunction.EXTERIOR

    def test_wall_type_function_setter(self):
        """Test changing wall type function."""
        wall_type = WallType("Test Wall")
        wall_type.function = WallFunction.FOUNDATION
        assert wall_type.function == WallFunction.FOUNDATION

    def test_create_basic_wall_type_with_function(self):
        """Test create_basic_wall_type with function parameter."""
        concrete = MaterialLibrary.concrete()
        wall_type = create_basic_wall_type(
            "Exterior Concrete", 300, concrete, function=WallFunction.EXTERIOR
        )
        assert wall_type.function == WallFunction.EXTERIOR

    def test_create_stud_wall_type_with_function(self):
        """Test create_stud_wall_type with function parameter."""
        timber = MaterialLibrary.timber()
        gypsum = MaterialLibrary.gypsum_board()

        wall_type = create_stud_wall_type(
            "Interior Stud Wall",
            stud_material=timber,
            interior_finish=gypsum,
            function=WallFunction.INTERIOR,
        )
        assert wall_type.function == WallFunction.INTERIOR

    def test_ifc_predefined_type_mapping(self):
        """Test IFC predefined type mapping for wall functions."""
        exterior = WallType("Exterior", function=WallFunction.EXTERIOR)
        interior = WallType("Interior", function=WallFunction.INTERIOR)
        foundation = WallType("Foundation", function=WallFunction.FOUNDATION)
        retaining = WallType("Retaining", function=WallFunction.RETAINING)
        soffit = WallType("Soffit", function=WallFunction.SOFFIT)
        core_shaft = WallType("Core-Shaft", function=WallFunction.CORE_SHAFT)

        assert exterior.get_ifc_predefined_type() == "PARTITIONING"
        assert interior.get_ifc_predefined_type() == "PARTITIONING"
        assert foundation.get_ifc_predefined_type() == "SOLIDWALL"
        assert retaining.get_ifc_predefined_type() == "SOLIDWALL"
        assert soffit.get_ifc_predefined_type() == "PARTITIONING"
        assert core_shaft.get_ifc_predefined_type() == "SHEAR"
