"""
Tests for curtain wall system.
"""

import pytest
import math

from bimascode.architecture.curtain_wall.mullion_profile import (
    MullionProfile,
    create_rectangular_mullion_profile,
    create_i_section_mullion_profile,
)
from bimascode.architecture.curtain_wall.mullion import (
    MullionType,
    Mullion,
    create_rectangular_mullion_type,
)
from bimascode.architecture.curtain_wall.panel import (
    CurtainPanelType,
    GlazedPanelType,
    OpaquePanelType,
    EmptyPanelType,
    CurtainPanel,
    create_double_glazed_panel_type,
    create_triple_glazed_panel_type,
)
from bimascode.architecture.curtain_wall.curtain_grid import (
    GridLayout,
    GridJustification,
    CurtainGridLine,
    GridSegment,
    CurtainCell,
    CurtainGrid,
)


class TestMullionProfile:
    """Tests for MullionProfile class."""

    def test_rectangular_profile_creation(self):
        """Test creating a rectangular mullion profile."""
        profile = MullionProfile(width=50, depth=100)

        assert profile.width == 50
        assert profile.depth == 100
        assert profile.profile_type == "rectangular"
        assert profile.web_thickness is None
        assert profile.flange_thickness is None
        assert not profile.has_thermal_break

    def test_rectangular_profile_area(self):
        """Test rectangular profile area calculation."""
        profile = MullionProfile(width=50, depth=100)
        assert profile.area == 5000  # 50 * 100

    def test_i_section_profile_creation(self):
        """Test creating an I-section mullion profile."""
        profile = MullionProfile(
            width=50,
            depth=100,
            web_thickness=10,
            flange_thickness=15,
        )

        assert profile.width == 50
        assert profile.depth == 100
        assert profile.profile_type == "i_section"
        assert profile.web_thickness == 10
        assert profile.flange_thickness == 15

    def test_i_section_profile_area(self):
        """Test I-section profile area calculation."""
        profile = MullionProfile(
            width=50,
            depth=100,
            web_thickness=10,
            flange_thickness=15,
        )
        # Two flanges: 2 * 50 * 15 = 1500
        # Web: 10 * (100 - 30) = 700
        # Total: 2200
        assert profile.area == 2200

    def test_profile_with_thermal_break(self):
        """Test profile with thermal break."""
        profile = MullionProfile(width=50, depth=100, thermal_break_gap=20)

        assert profile.has_thermal_break
        assert profile.thermal_break_gap == 20

    def test_rectangular_profile_to_build123d(self):
        """Test converting rectangular profile to build123d."""
        profile = MullionProfile(width=50, depth=100)
        face = profile.to_build123d()

        # Should return a Face-like object (Rectangle is a Face subclass)
        assert face is not None
        # Check it has area (indicating valid face)
        assert hasattr(face, "area")

    def test_i_section_profile_to_build123d(self):
        """Test converting I-section profile to build123d."""
        profile = MullionProfile(
            width=50,
            depth=100,
            web_thickness=10,
            flange_thickness=15,
        )
        face = profile.to_build123d()

        # Should return a Face (fused compound)
        # Note: fuse returns a Shape, which we treat as Face-like
        assert face is not None

    def test_factory_rectangular(self):
        """Test rectangular profile factory function."""
        profile = create_rectangular_mullion_profile(60, 120, name="Test Profile")

        assert profile.width == 60
        assert profile.depth == 120
        assert profile.name == "Test Profile"
        assert profile.profile_type == "rectangular"

    def test_factory_i_section(self):
        """Test I-section profile factory function."""
        profile = create_i_section_mullion_profile(
            width=50,
            depth=100,
            web_thickness=8,
            flange_thickness=12,
            thermal_break_gap=15,
        )

        assert profile.width == 50
        assert profile.depth == 100
        assert profile.web_thickness == 8
        assert profile.flange_thickness == 12
        assert profile.thermal_break_gap == 15

    def test_profile_equality(self):
        """Test profile equality comparison."""
        p1 = MullionProfile(width=50, depth=100)
        p2 = MullionProfile(width=50, depth=100)
        p3 = MullionProfile(width=60, depth=100)

        assert p1 == p2
        assert p1 != p3


class TestMullionType:
    """Tests for MullionType class."""

    @pytest.fixture
    def basic_profile(self):
        """Create a basic rectangular profile."""
        return MullionProfile(width=50, depth=100)

    def test_mullion_type_creation(self, basic_profile):
        """Test creating a mullion type."""
        mullion_type = MullionType(
            name="Standard Mullion",
            profile=basic_profile,
            finish="anodized",
        )

        assert mullion_type.name == "Standard Mullion"
        assert mullion_type.profile == basic_profile
        assert mullion_type.finish == "anodized"
        assert mullion_type.thermal_break is False
        assert mullion_type.width == 50
        assert mullion_type.depth == 100

    def test_mullion_type_with_thermal_break(self, basic_profile):
        """Test mullion type with thermal break."""
        mullion_type = MullionType(
            name="Thermal Break Mullion",
            profile=basic_profile,
            thermal_break=True,
        )

        assert mullion_type.thermal_break is True

    def test_mullion_type_with_color(self, basic_profile):
        """Test mullion type with painted finish."""
        mullion_type = MullionType(
            name="Painted Mullion",
            profile=basic_profile,
            finish="painted",
            color=(100, 100, 100),
        )

        assert mullion_type.finish == "painted"
        assert mullion_type.color == (100, 100, 100)

    def test_factory_rectangular_mullion_type(self):
        """Test rectangular mullion type factory."""
        mullion_type = create_rectangular_mullion_type(
            name="Test Mullion",
            width=50,
            depth=100,
            finish="mill",
        )

        assert mullion_type.name == "Test Mullion"
        assert mullion_type.width == 50
        assert mullion_type.depth == 100


class TestMullion:
    """Tests for Mullion class."""

    @pytest.fixture
    def mullion_type(self):
        """Create a basic mullion type."""
        profile = MullionProfile(width=50, depth=100)
        return MullionType(name="Test Mullion", profile=profile)

    def test_mullion_creation(self, mullion_type):
        """Test creating a mullion instance."""
        mullion = Mullion(
            mullion_type=mullion_type,
            start_point=(0, 0, 0),
            end_point=(0, 0, 3000),
        )

        assert mullion.start_point == (0, 0, 0)
        assert mullion.end_point == (0, 0, 3000)
        assert mullion.length == 3000
        assert mullion.direction == "vertical"

    def test_horizontal_mullion(self, mullion_type):
        """Test horizontal mullion direction detection."""
        mullion = Mullion(
            mullion_type=mullion_type,
            start_point=(0, 0, 1500),
            end_point=(5000, 0, 1500),
        )

        assert mullion.length == 5000
        assert mullion.direction == "horizontal"

    def test_mullion_geometry(self, mullion_type):
        """Test mullion geometry generation."""
        mullion = Mullion(
            mullion_type=mullion_type,
            start_point=(0, 0, 0),
            end_point=(0, 0, 3000),
        )

        geometry = mullion.get_geometry()
        assert geometry is not None

        from build123d import Compound

        assert isinstance(geometry, Compound)


class TestPanelTypes:
    """Tests for panel type classes."""

    def test_glazed_panel_single(self):
        """Test single glazed panel type."""
        panel = GlazedPanelType(
            name="Single Glazed",
            glazing_type="single",
            glass_thickness=8.0,
        )

        assert panel.glazing_type == "single"
        assert panel.glass_thickness == 8.0
        assert panel.num_lites == 1
        assert panel.thickness == 8.0

    def test_glazed_panel_double(self):
        """Test double glazed panel type."""
        panel = GlazedPanelType(
            name="Double Glazed",
            glazing_type="double",
            glass_thickness=6.0,
            air_gap=12.0,
        )

        assert panel.glazing_type == "double"
        assert panel.num_lites == 2
        assert panel.thickness == 24.0  # 6 + 12 + 6

    def test_glazed_panel_triple(self):
        """Test triple glazed panel type."""
        panel = GlazedPanelType(
            name="Triple Glazed",
            glazing_type="triple",
            glass_thickness=6.0,
            air_gap=12.0,
        )

        assert panel.glazing_type == "triple"
        assert panel.num_lites == 3
        assert panel.thickness == 42.0  # 6 + 12 + 6 + 12 + 6

    def test_glazed_panel_with_low_e(self):
        """Test glazed panel with low-E coating."""
        panel = GlazedPanelType(
            name="Low-E Double",
            glazing_type="double",
            low_e=True,
            tint="gray",
        )

        assert panel.low_e is True
        assert panel.tint == "gray"

    def test_opaque_panel(self):
        """Test opaque panel type."""
        from bimascode.utils.materials import MaterialLibrary

        # Use steel as face material (aluminum not in library)
        material = MaterialLibrary.steel()
        panel = OpaquePanelType(
            name="Spandrel Panel",
            material=material,
            insulation_thickness=50.0,
            face_thickness=6.0,
            backing_thickness=12.0,
        )

        assert panel.material == material
        assert panel.insulation_thickness == 50.0
        assert panel.thickness == 68.0  # 6 + 50 + 12

    def test_empty_panel(self):
        """Test empty panel type."""
        panel = EmptyPanelType()

        assert panel.name == "Empty"
        assert panel.thickness == 0.0

    def test_factory_double_glazed(self):
        """Test double glazed panel factory."""
        panel = create_double_glazed_panel_type(low_e=True)

        assert panel.glazing_type == "double"
        assert panel.low_e is True

    def test_factory_triple_glazed(self):
        """Test triple glazed panel factory."""
        panel = create_triple_glazed_panel_type()

        assert panel.glazing_type == "triple"
        assert panel.low_e is True  # Default for triple


class TestCurtainPanel:
    """Tests for CurtainPanel class."""

    @pytest.fixture
    def panel_type(self):
        """Create a basic panel type."""
        return create_double_glazed_panel_type()

    def test_panel_creation(self, panel_type):
        """Test creating a panel instance."""
        panel = CurtainPanel(
            panel_type=panel_type,
            width=1200,
            height=1500,
        )

        assert panel.width == 1200
        assert panel.height == 1500
        assert panel.area == 1800000
        assert panel.area_m2 == 1.8

    def test_panel_geometry(self, panel_type):
        """Test panel geometry generation."""
        panel = CurtainPanel(
            panel_type=panel_type,
            width=1200,
            height=1500,
        )

        geometry = panel.get_geometry()
        assert geometry is not None

        from build123d import Compound

        assert isinstance(geometry, Compound)

    def test_empty_panel_geometry(self):
        """Test empty panel has no geometry."""
        panel_type = EmptyPanelType()
        panel = CurtainPanel(
            panel_type=panel_type,
            width=1200,
            height=1500,
        )

        geometry = panel.get_geometry()
        assert geometry is None


class TestCurtainGrid:
    """Tests for CurtainGrid class."""

    def test_grid_creation(self):
        """Test creating an empty grid."""
        grid = CurtainGrid(width=6000, height=3000)

        assert grid.width == 6000
        assert grid.height == 3000
        assert grid.u_count == 0
        assert grid.v_count == 0

    def test_fixed_distance_grid(self):
        """Test fixed distance grid generation."""
        grid = CurtainGrid(width=6000, height=3000)
        grid.generate_fixed_distance(u_spacing=1200, v_spacing=1500)

        # 6000 / 1200 = 5 panels horizontally
        # 3000 / 1500 = 2 panels vertically
        assert grid.u_count == 5
        assert grid.v_count == 2
        assert grid.cell_count == 10

    def test_fixed_distance_with_remainder(self):
        """Test fixed distance with remainder panel."""
        grid = CurtainGrid(width=5000, height=3000)
        grid.generate_fixed_distance(
            u_spacing=1200,
            v_spacing=1500,
            u_justification=GridJustification.BEGINNING,
        )

        # 5000 / 1200 = 4 full panels + 200mm remainder
        # Should have 5 panels total (4 @ 1200mm + 1 @ 200mm)
        assert grid.u_count == 5
        assert grid.v_count == 2

        # First 4 cells should be 1200mm wide
        cell_0 = grid.get_cell(0, 0)
        assert cell_0.width == 1200

        # Last cell should be 200mm wide (remainder)
        cell_4 = grid.get_cell(4, 0)
        assert abs(cell_4.width - 200) < 1e-6

    def test_fixed_number_grid(self):
        """Test fixed number grid generation."""
        grid = CurtainGrid(width=6000, height=3000)
        grid.generate_fixed_number(u_divisions=4, v_divisions=3)

        assert grid.u_count == 4
        assert grid.v_count == 3
        assert grid.cell_count == 12

        # All cells should be equally sized
        cell_0 = grid.get_cell(0, 0)
        assert cell_0.width == 1500  # 6000 / 4
        assert cell_0.height == 1000  # 3000 / 3

    def test_maximum_spacing_grid(self):
        """Test maximum spacing grid generation."""
        grid = CurtainGrid(width=5500, height=3000)
        grid.generate_maximum_spacing(u_max_spacing=1200, v_max_spacing=1500)

        # Should create enough divisions to stay under max
        # 5500 / 1200 = 4.58, so need 5 divisions
        assert grid.u_count == 5

        # All panels should be <= max spacing
        for u in range(grid.u_count):
            cell = grid.get_cell(u, 0)
            assert cell.width <= 1200 + 1e-6

    def test_grid_cell_access(self):
        """Test accessing grid cells."""
        grid = CurtainGrid(width=6000, height=3000)
        grid.generate_fixed_number(u_divisions=3, v_divisions=2)

        # Valid cell access
        cell = grid.get_cell(1, 1)
        assert cell is not None
        assert cell.u_index == 1
        assert cell.v_index == 1

        # Out of range returns None
        assert grid.get_cell(10, 0) is None
        assert grid.get_cell(0, 10) is None

    def test_grid_positions(self):
        """Test getting grid line positions."""
        grid = CurtainGrid(width=6000, height=3000)
        grid.generate_fixed_number(u_divisions=3, v_divisions=2)

        # U line positions (vertical lines)
        assert grid.get_u_position(0) == 0
        assert grid.get_u_position(1) == 2000
        assert grid.get_u_position(2) == 4000
        assert grid.get_u_position(3) == 6000

        # V line positions (horizontal lines)
        assert grid.get_v_position(0) == 0
        assert grid.get_v_position(1) == 1500
        assert grid.get_v_position(2) == 3000

    def test_grid_segments(self):
        """Test grid segments generation."""
        grid = CurtainGrid(width=6000, height=3000)
        grid.generate_fixed_number(u_divisions=2, v_divisions=2)

        # Check U lines have V segments
        for u_line in grid.u_lines:
            assert len(u_line.segments) == 2  # Two vertical segments

        # Check V lines have U segments
        for v_line in grid.v_lines:
            assert len(v_line.segments) == 2  # Two horizontal segments

    def test_add_grid_line(self):
        """Test adding a grid line."""
        grid = CurtainGrid(width=6000, height=3000)
        grid.generate_fixed_number(u_divisions=2, v_divisions=1)

        initial_u_count = grid.u_count
        initial_cell_count = grid.cell_count

        # Add a new vertical line
        new_line = grid.add_grid_line("U", 4500)

        assert new_line is not None
        assert grid.u_count == initial_u_count + 1
        assert grid.cell_count > initial_cell_count

    def test_add_invalid_grid_line(self):
        """Test adding invalid grid line."""
        grid = CurtainGrid(width=6000, height=3000)
        grid.generate_fixed_number(u_divisions=2, v_divisions=1)

        # Outside range
        assert grid.add_grid_line("U", 7000) is None
        assert grid.add_grid_line("U", -100) is None

        # On border
        assert grid.add_grid_line("U", 0) is None
        assert grid.add_grid_line("U", 6000) is None

    def test_border_lines(self):
        """Test border line identification."""
        grid = CurtainGrid(width=6000, height=3000)
        grid.generate_fixed_number(u_divisions=2, v_divisions=2)

        # First and last U lines are borders
        assert grid.u_lines[0].is_border
        assert grid.u_lines[0].border_type == 1
        assert grid.u_lines[-1].is_border
        assert grid.u_lines[-1].border_type == 2

        # Middle lines are not borders
        assert not grid.u_lines[1].is_border
        assert grid.u_lines[1].border_type == 0


class TestCurtainWallType:
    """Tests for CurtainWallType class."""

    @pytest.fixture
    def mullion_type(self):
        """Create a basic mullion type."""
        from bimascode.architecture.curtain_wall.mullion import create_rectangular_mullion_type

        return create_rectangular_mullion_type(
            name="Test Mullion",
            width=50,
            depth=100,
        )

    @pytest.fixture
    def panel_type(self):
        """Create a basic panel type."""
        return create_double_glazed_panel_type()

    def test_curtain_wall_type_creation(self, mullion_type, panel_type):
        """Test creating a curtain wall type."""
        from bimascode.architecture.curtain_wall.curtain_wall_type import CurtainWallType

        cw_type = CurtainWallType(
            name="Test Curtain Wall",
            vertical_grid_spacing=1200,
            horizontal_grid_spacing=1500,
            vertical_interior_mullion_type=mullion_type,
            horizontal_interior_mullion_type=mullion_type,
            default_panel_type=panel_type,
        )

        assert cw_type.name == "Test Curtain Wall"
        assert cw_type.vertical_grid_spacing == 1200
        assert cw_type.horizontal_grid_spacing == 1500
        assert cw_type.default_panel_type == panel_type

    def test_curtain_wall_type_grid_generation(self, mullion_type, panel_type):
        """Test grid generation from type."""
        from bimascode.architecture.curtain_wall.curtain_wall_type import CurtainWallType

        cw_type = CurtainWallType(
            name="Test",
            vertical_grid_spacing=1200,
            horizontal_grid_spacing=1500,
        )

        grid = cw_type.generate_grid(width=6000, height=3000)

        assert grid.u_count == 5  # 6000 / 1200
        assert grid.v_count == 2  # 3000 / 1500

    def test_curtain_wall_type_fixed_number(self):
        """Test fixed number grid generation."""
        from bimascode.architecture.curtain_wall.curtain_wall_type import CurtainWallType

        cw_type = CurtainWallType(
            name="Test",
            vertical_grid_layout=GridLayout.FIXED_NUMBER,
            vertical_grid_number=4,
            horizontal_grid_layout=GridLayout.FIXED_NUMBER,
            horizontal_grid_number=3,
        )

        grid = cw_type.generate_grid(width=6000, height=3000)

        assert grid.u_count == 4
        assert grid.v_count == 3

    def test_get_mullion_type_by_border(self, mullion_type):
        """Test getting mullion type by border type."""
        from bimascode.architecture.curtain_wall.curtain_wall_type import CurtainWallType
        from bimascode.architecture.curtain_wall.mullion import create_rectangular_mullion_type

        border_mullion = create_rectangular_mullion_type("Border", 60, 120)

        cw_type = CurtainWallType(
            name="Test",
            vertical_interior_mullion_type=mullion_type,
            vertical_border_1_mullion_type=border_mullion,
        )

        assert cw_type.get_vertical_mullion_type(0) == mullion_type
        assert cw_type.get_vertical_mullion_type(1) == border_mullion
        assert cw_type.get_vertical_mullion_type(2) is None


class TestCurtainWall:
    """Tests for CurtainWall class."""

    @pytest.fixture
    def level(self):
        """Create a mock level."""

        class MockLevel:
            elevation_mm = 0.0

            def add_element(self, element):
                pass

        return MockLevel()

    @pytest.fixture
    def curtain_wall_type(self):
        """Create a basic curtain wall type."""
        from bimascode.architecture.curtain_wall.curtain_wall_type import CurtainWallType
        from bimascode.architecture.curtain_wall.mullion import create_rectangular_mullion_type

        mullion_type = create_rectangular_mullion_type("Test", 50, 100)

        return CurtainWallType(
            name="Test Curtain Wall",
            vertical_grid_spacing=1200,
            horizontal_grid_spacing=1500,
            vertical_interior_mullion_type=mullion_type,
            horizontal_interior_mullion_type=mullion_type,
        )

    def test_curtain_wall_creation(self, curtain_wall_type, level):
        """Test creating a curtain wall."""
        from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall

        cw = CurtainWall(
            curtain_wall_type=curtain_wall_type,
            start_point=(0, 0),
            end_point=(6000, 0),
            level=level,
            height=3000,
        )

        assert cw.start_point == (0, 0)
        assert cw.end_point == (6000, 0)
        assert cw.width == 6000
        assert cw.height == 3000
        assert cw.angle == 0.0

    def test_curtain_wall_angled(self, curtain_wall_type, level):
        """Test angled curtain wall."""
        from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall

        cw = CurtainWall(
            curtain_wall_type=curtain_wall_type,
            start_point=(0, 0),
            end_point=(3000, 3000),
            level=level,
        )

        assert abs(cw.angle - 45.0) < 1e-6
        assert abs(cw.width - 4242.64) < 1  # sqrt(3000^2 + 3000^2)

    def test_curtain_wall_grid_access(self, curtain_wall_type, level):
        """Test accessing curtain wall grid."""
        from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall

        cw = CurtainWall(
            curtain_wall_type=curtain_wall_type,
            start_point=(0, 0),
            end_point=(6000, 0),
            level=level,
            height=3000,
        )

        grid = cw.grid
        assert grid is not None
        assert grid.u_count == 5
        assert grid.v_count == 2

    def test_curtain_wall_panel_override(self, curtain_wall_type, level):
        """Test panel type override."""
        from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall

        cw = CurtainWall(
            curtain_wall_type=curtain_wall_type,
            start_point=(0, 0),
            end_point=(6000, 0),
            level=level,
        )

        # Initially no override
        assert cw.get_panel_type(0, 0) is None

        # Set override
        opaque = OpaquePanelType(
            name="Spandrel",
            material=None,
            insulation_thickness=50,
        )
        cw.set_panel_type(0, 0, opaque)

        assert cw.get_panel_type(0, 0) == opaque

        # Clear override
        cw.clear_panel_override(0, 0)
        assert cw.get_panel_type(0, 0) is None

    def test_curtain_wall_geometry(self, curtain_wall_type, level):
        """Test curtain wall geometry generation."""
        from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall

        cw = CurtainWall(
            curtain_wall_type=curtain_wall_type,
            start_point=(0, 0),
            end_point=(6000, 0),
            level=level,
            height=3000,
        )

        geometry = cw.get_geometry()
        assert geometry is not None

        from build123d import Compound

        assert isinstance(geometry, Compound)

    def test_curtain_wall_plan_representation(self, curtain_wall_type, level):
        """Test 2D plan representation."""
        from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall

        cw = CurtainWall(
            curtain_wall_type=curtain_wall_type,
            start_point=(0, 0),
            end_point=(6000, 0),
            level=level,
            height=3000,
        )

        primitives = cw.get_plan_representation(cut_height=1200)

        # Should have outer line, inner line, end caps, and mullion ticks
        assert len(primitives) > 4

        from bimascode.drawing.primitives import Line2D

        for p in primitives:
            assert isinstance(p, Line2D)

    def test_curtain_wall_world_position(self, curtain_wall_type, level):
        """Test world position calculation."""
        from bimascode.architecture.curtain_wall.curtain_wall import CurtainWall

        level.elevation_mm = 3000.0

        cw = CurtainWall(
            curtain_wall_type=curtain_wall_type,
            start_point=(1000, 2000),
            end_point=(6000, 2000),
            level=level,
            base_offset=100,
        )

        pos = cw._get_world_position()
        assert pos == (1000, 2000, 3100)  # level + base_offset


class TestGridJustification:
    """Tests for grid justification modes."""

    def test_beginning_justification(self):
        """Test BEGINNING justification puts remainder at end."""
        grid = CurtainGrid(width=5000, height=3000)
        grid.generate_fixed_distance(
            u_spacing=1200,
            v_spacing=3000,
            u_justification=GridJustification.BEGINNING,
        )

        # First cells should be full size
        assert grid.get_cell(0, 0).width == 1200

        # Last cell should be remainder
        last_cell = grid.get_cell(grid.u_count - 1, 0)
        assert last_cell.width < 1200

    def test_end_justification(self):
        """Test END justification puts remainder at beginning."""
        grid = CurtainGrid(width=5000, height=3000)
        grid.generate_fixed_distance(
            u_spacing=1200,
            v_spacing=3000,
            u_justification=GridJustification.END,
        )

        # First cell should be remainder
        first_cell = grid.get_cell(0, 0)
        assert first_cell.width < 1200

        # Last cells should be full size
        last_cell = grid.get_cell(grid.u_count - 1, 0)
        assert last_cell.width == 1200

    def test_center_justification(self):
        """Test CENTER justification splits remainder."""
        grid = CurtainGrid(width=5000, height=3000)
        grid.generate_fixed_distance(
            u_spacing=1200,
            v_spacing=3000,
            u_justification=GridJustification.CENTER,
        )

        # First and last cells should be smaller (remainder split)
        first_cell = grid.get_cell(0, 0)
        last_cell = grid.get_cell(grid.u_count - 1, 0)

        # Both end cells should be approximately half the remainder
        # Total remainder is 200mm, so each end gets ~100mm
        assert first_cell.width < 1200
        assert last_cell.width < 1200
