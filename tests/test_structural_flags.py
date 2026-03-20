"""
Tests for structural flags on walls and floors.
"""

import pytest
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture.wall_type import WallType, LayerFunction
from bimascode.architecture.wall import Wall
from bimascode.architecture.floor_type import FloorType
from bimascode.architecture.floor import Floor
from bimascode.utils.materials import MaterialLibrary


class TestStructuralWall:
    """Tests for structural wall flag."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with level for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        return building, level

    @pytest.fixture
    def setup_wall_type(self):
        """Create a wall type for testing."""
        wall_type = WallType("Concrete Wall")
        concrete = MaterialLibrary.concrete()
        wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
        return wall_type

    def test_wall_default_non_structural(self, setup_building, setup_wall_type):
        """Test that walls are non-structural by default."""
        building, level = setup_building
        wall_type = setup_wall_type

        wall = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)

        assert wall.structural is False

    def test_wall_structural_flag(self, setup_building, setup_wall_type):
        """Test setting structural flag on wall."""
        building, level = setup_building
        wall_type = setup_wall_type

        wall = Wall(
            wall_type,
            (0, 0), (5000, 0),
            level,
            height=3000,
            structural=True
        )

        assert wall.structural is True

    def test_wall_structural_setter(self, setup_building, setup_wall_type):
        """Test structural flag setter."""
        building, level = setup_building
        wall_type = setup_wall_type

        wall = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        assert wall.structural is False

        wall.structural = True
        assert wall.structural is True

    def test_wall_is_structural_combined(self, setup_building, setup_wall_type):
        """Test is_structural checks both flag and layers."""
        building, level = setup_building
        wall_type = setup_wall_type

        # Wall with structural layers but no flag
        wall1 = Wall(wall_type, (0, 0), (5000, 0), level, height=3000)
        assert wall1.is_structural is True  # Has structural layers

        # Non-structural wall type with structural flag
        non_struct_type = WallType("Partition")
        gypsum = MaterialLibrary.gypsum_board()
        non_struct_type.add_layer(gypsum, 15, LayerFunction.OTHER)

        wall2 = Wall(
            non_struct_type,
            (0, 0), (5000, 0),
            level,
            height=3000,
            structural=True
        )
        assert wall2.is_structural is True  # Flag is set

    def test_structural_wall_ifc_export(self, setup_building, setup_wall_type, tmp_path):
        """Test structural wall exports with SHEAR predefined type."""
        building, level = setup_building
        wall_type = setup_wall_type

        wall = Wall(
            wall_type,
            (0, 0), (5000, 0),
            level,
            height=3000,
            structural=True
        )

        output_file = tmp_path / "test_structural_wall.ifc"
        building.export_ifc(str(output_file))

        assert output_file.exists()

        # Verify IFC content
        import ifcopenshell
        ifc = ifcopenshell.open(str(output_file))
        walls = ifc.by_type("IfcWall")
        assert len(walls) == 1
        assert walls[0].PredefinedType == "SHEAR"


class TestStructuralFloor:
    """Tests for structural floor flag."""

    @pytest.fixture
    def setup_building(self):
        """Create a building with level for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground Floor", elevation=0)
        return building, level

    @pytest.fixture
    def setup_floor_type(self):
        """Create a floor type for testing."""
        floor_type = FloorType("Concrete Floor")
        concrete = MaterialLibrary.concrete()
        floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE)
        return floor_type

    def test_floor_default_non_structural(self, setup_building, setup_floor_type):
        """Test that floors are non-structural by default."""
        building, level = setup_building
        floor_type = setup_floor_type

        floor = Floor(
            floor_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level
        )

        assert floor.structural is False

    def test_floor_structural_flag(self, setup_building, setup_floor_type):
        """Test setting structural flag on floor."""
        building, level = setup_building
        floor_type = setup_floor_type

        floor = Floor(
            floor_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            structural=True
        )

        assert floor.structural is True

    def test_floor_structural_setter(self, setup_building, setup_floor_type):
        """Test structural flag setter."""
        building, level = setup_building
        floor_type = setup_floor_type

        floor = Floor(
            floor_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level
        )
        assert floor.structural is False

        floor.structural = True
        assert floor.structural is True

    def test_structural_floor_ifc_export(self, setup_building, setup_floor_type, tmp_path):
        """Test structural floor exports with BASESLAB predefined type."""
        building, level = setup_building
        floor_type = setup_floor_type

        floor = Floor(
            floor_type,
            boundary=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
            level=level,
            structural=True
        )

        output_file = tmp_path / "test_structural_floor.ifc"
        building.export_ifc(str(output_file))

        assert output_file.exists()

        # Verify IFC content
        import ifcopenshell
        ifc = ifcopenshell.open(str(output_file))
        slabs = ifc.by_type("IfcSlab")
        assert len(slabs) == 1
        assert slabs[0].PredefinedType == "BASESLAB"
