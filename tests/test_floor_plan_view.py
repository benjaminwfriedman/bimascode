"""
Unit tests for floor plan view generation.
"""

import pytest
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import WallType, Wall, create_basic_wall_type
from bimascode.utils.materials import MaterialLibrary
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.performance.representation_cache import RepresentationCache


class TestFloorPlanView:
    """Tests for FloorPlanView class."""

    @pytest.fixture
    def simple_building(self):
        """Create a simple building with walls for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground", 0)

        # Create a basic wall type
        wall_type = create_basic_wall_type("200mm Concrete", 200, MaterialLibrary.concrete())

        # Create walls forming a simple room
        wall1 = Wall(wall_type, (0, 0), (5000, 0), level)
        wall2 = Wall(wall_type, (5000, 0), (5000, 4000), level)
        wall3 = Wall(wall_type, (5000, 4000), (0, 4000), level)
        wall4 = Wall(wall_type, (0, 4000), (0, 0), level)

        return building, level, [wall1, wall2, wall3, wall4]

    @pytest.fixture
    def spatial_index_with_walls(self, simple_building):
        """Create a spatial index populated with walls."""
        building, level, walls = simple_building
        index = SpatialIndex()
        for wall in walls:
            index.insert(wall)
        return index, level, walls

    def test_floor_plan_view_creation(self, simple_building):
        """Test creating a floor plan view."""
        _, level, _ = simple_building
        view = FloorPlanView("Ground Floor Plan", level)

        assert view.name == "Ground Floor Plan"
        assert view.level == level
        assert view.view_range is not None
        assert view.scale == ViewScale.SCALE_1_100

    def test_floor_plan_view_custom_range(self, simple_building):
        """Test floor plan view with custom view range."""
        _, level, _ = simple_building
        view_range = ViewRange(cut_height=1000, top_clip=3000)
        view = FloorPlanView("Custom Plan", level, view_range=view_range)

        assert view.view_range.cut_height == 1000
        assert view.view_range.top_clip == 3000

    def test_floor_plan_view_cut_height(self, simple_building):
        """Test cut height calculation."""
        _, level, _ = simple_building
        view = FloorPlanView("Plan", level)

        # Cut height should be level elevation + view range cut height
        expected = level.elevation_mm + view.view_range.cut_height
        assert view.cut_height == expected

    def test_floor_plan_generate_basic(self, spatial_index_with_walls):
        """Test basic floor plan generation."""
        index, level, walls = spatial_index_with_walls
        cache = RepresentationCache()

        view = FloorPlanView("Ground Floor Plan", level)
        result = view.generate(index, cache)

        # Should have generated some geometry
        assert result.element_count == 4  # 4 walls
        assert result.total_geometry_count > 0
        assert result.generation_time > 0

    def test_floor_plan_uses_cache(self, spatial_index_with_walls):
        """Test that floor plan generation uses cache."""
        index, level, walls = spatial_index_with_walls
        cache = RepresentationCache()

        view = FloorPlanView("Plan", level)

        # First generation
        result1 = view.generate(index, cache)
        assert cache.size > 0

        # Second generation should have cache hits
        result2 = view.generate(index, cache)
        assert result2.cache_hits > 0

    def test_floor_plan_with_crop_region(self, spatial_index_with_walls):
        """Test floor plan with crop region."""
        from bimascode.drawing.view_base import ViewCropRegion

        index, level, walls = spatial_index_with_walls
        cache = RepresentationCache()

        # Create a crop region that covers only part of the model
        crop = ViewCropRegion(
            min_x=0,
            min_y=0,
            max_x=2500,  # Half the room
            max_y=4000,
        )

        view = FloorPlanView("Cropped Plan", level, crop_region=crop)
        result = view.generate(index, cache)

        # Result should have some geometry, but clipped
        assert result.total_geometry_count > 0


class TestWallPlanRepresentation:
    """Tests for Wall.get_plan_representation()."""

    @pytest.fixture
    def wall_with_level(self):
        """Create a wall for testing."""
        building = Building("Test")
        level = Level(building, "Ground", 0)
        wall_type = create_basic_wall_type("200mm Concrete", 200, MaterialLibrary.concrete())
        wall = Wall(wall_type, (0, 0), (5000, 0), level)
        return wall, level

    def test_wall_plan_representation(self, wall_with_level):
        """Test wall plan representation generation."""
        wall, level = wall_with_level
        view_range = ViewRange()
        cut_height = level.elevation_mm + view_range.cut_height

        linework = wall.get_plan_representation(cut_height, view_range)

        # Should return at least one polyline for the outline
        assert len(linework) > 0

    def test_wall_cut_style(self, wall_with_level):
        """Test that cut walls use heavy line style."""
        from bimascode.drawing.primitives import Polyline2D
        from bimascode.drawing.line_styles import LineWeight

        wall, level = wall_with_level
        view_range = ViewRange()
        cut_height = level.elevation_mm + view_range.cut_height

        linework = wall.get_plan_representation(cut_height, view_range)

        # Find the polyline (wall outline)
        polylines = [item for item in linework if isinstance(item, Polyline2D)]
        assert len(polylines) > 0

        # Check that cut lines use heavy weight
        outline = polylines[0]
        assert outline.style.weight == LineWeight.HEAVY
        assert outline.style.is_cut is True

    def test_wall_not_cut_style(self, wall_with_level):
        """Test that walls not cut use lighter style."""
        from bimascode.drawing.primitives import Polyline2D
        from bimascode.drawing.line_styles import LineWeight

        wall, level = wall_with_level
        view_range = ViewRange()
        # Cut height above the wall (wall is 3000mm high from level 0)
        cut_height = level.elevation_mm + 3500

        linework = wall.get_plan_representation(cut_height, view_range)

        # Check that non-cut lines use narrower weight
        polylines = [item for item in linework if isinstance(item, Polyline2D)]
        if polylines:
            outline = polylines[0]
            assert outline.style.weight != LineWeight.HEAVY
            assert outline.style.is_cut is False
