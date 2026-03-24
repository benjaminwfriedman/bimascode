"""
Unit tests for view base classes.
"""

from bimascode.drawing.line_styles import LineStyle
from bimascode.drawing.primitives import Line2D, Point2D
from bimascode.drawing.view_base import (
    ViewCropRegion,
    ViewRange,
    ViewScale,
)


class TestViewRange:
    """Tests for ViewRange class."""

    def test_view_range_defaults(self):
        """Test default view range values."""
        vr = ViewRange()
        assert vr.cut_height == 1200.0
        assert vr.top == 2400.0
        assert vr.bottom == 0.0
        assert vr.view_depth == 0.0

        # Test backward compatibility properties
        assert vr.top_clip == vr.top
        assert vr.bottom_clip == vr.bottom

    def test_view_range_custom(self):
        """Test custom view range values."""
        vr = ViewRange(
            cut_height=1000,
            top=3000,
            bottom=-100,
            view_depth=-500,
        )
        assert vr.cut_height == 1000
        assert vr.top == 3000
        assert vr.bottom == -100
        assert vr.view_depth == -500

    def test_is_cut_by_plane(self):
        """Test is_cut_by_plane check."""
        vr = ViewRange(cut_height=1200)
        level_elev = 0

        # Element spanning cut plane
        assert vr.is_cut_by_plane(0, 2500, level_elev) is True

        # Element below cut plane
        assert vr.is_cut_by_plane(0, 1000, level_elev) is False

        # Element above cut plane
        assert vr.is_cut_by_plane(1500, 2500, level_elev) is False

    def test_is_above_cut(self):
        """Test is_above_cut check."""
        vr = ViewRange(cut_height=1200)
        level_elev = 0

        assert vr.is_above_cut(1500, level_elev) is True
        assert vr.is_above_cut(1000, level_elev) is False

    def test_is_below_cut(self):
        """Test is_below_cut check."""
        vr = ViewRange(cut_height=1200)
        level_elev = 0

        assert vr.is_below_cut(1000, level_elev) is True
        assert vr.is_below_cut(1500, level_elev) is False

    def test_is_visible(self):
        """Test is_visible check with new top/bottom/view_depth model."""
        vr = ViewRange(bottom=0, top=2700, view_depth=0)
        level_elev = 0

        # Inside range [view_depth=0, top=2700]
        assert vr.is_visible(500, 2000, level_elev) is True

        # Spanning range (partially visible)
        assert vr.is_visible(-100, 500, level_elev) is True

        # Above top plane
        assert vr.is_visible(3000, 4000, level_elev) is False

        # Below view_depth plane
        assert vr.is_visible(-500, -100, level_elev) is False

        # Test extended view depth
        vr_extended = ViewRange(bottom=0, top=2700, view_depth=-1000)
        # Element from -500 to -100 should now be visible
        assert vr_extended.is_visible(-500, -100, level_elev) is True

    def test_absolute_cut_height(self):
        """Test absolute cut height calculation."""
        vr = ViewRange(cut_height=1200)
        level_elev = 3000
        assert vr.get_absolute_cut_height(level_elev) == 4200

    def test_absolute_coordinates(self):
        """Test all absolute coordinate methods."""
        vr = ViewRange(cut_height=1200, top=2400, bottom=0, view_depth=-500)
        level_elev = 1000

        assert vr.get_absolute_cut_height(level_elev) == 2200
        assert vr.get_absolute_top(level_elev) == 3400
        assert vr.get_absolute_bottom(level_elev) == 1000
        assert vr.get_absolute_view_depth(level_elev) == 500

    def test_is_above_top(self):
        """Test is_above_top check."""
        vr = ViewRange(top=2400)
        level_elev = 0

        assert vr.is_above_top(2500, level_elev) is True
        assert vr.is_above_top(2000, level_elev) is False

    def test_is_below_view_depth(self):
        """Test is_below_view_depth check."""
        vr = ViewRange(view_depth=-500)
        level_elev = 0

        assert vr.is_below_view_depth(-600, level_elev) is True
        assert vr.is_below_view_depth(-400, level_elev) is False

    def test_get_display_region(self):
        """Test display region classification (Revit-style)."""
        vr = ViewRange(cut_height=1200, top=2400, bottom=0, view_depth=-500)
        level_elev = 0

        # Element cut by plane (z_min < cut < z_max)
        assert vr.get_display_region(1000, 1500, level_elev) == "cut"

        # Element entirely above cut plane
        assert vr.get_display_region(1300, 2000, level_elev) == "above_cut"

        # Element between bottom and cut
        assert vr.get_display_region(100, 800, level_elev) == "below_cut"

        # Element between view_depth and bottom (extended visibility)
        assert vr.get_display_region(-400, -100, level_elev) == "beyond_bottom"

        # Element above top plane (hidden)
        assert vr.get_display_region(2500, 3000, level_elev) == "hidden"

        # Element below view_depth (hidden)
        assert vr.get_display_region(-800, -600, level_elev) == "hidden"


class TestViewScale:
    """Tests for ViewScale class."""

    def test_view_scale_creation(self):
        """Test creating a view scale."""
        scale = ViewScale(ratio=0.01, name="1:100")
        assert scale.ratio == 0.01
        assert scale.name == "1:100"

    def test_from_string(self):
        """Test creating scale from string."""
        scale = ViewScale.from_string("1:100")
        assert scale.ratio == 0.01
        assert scale.name == "1:100"

    def test_from_string_slash(self):
        """Test creating scale from slash format."""
        scale = ViewScale.from_string("1/50")
        assert scale.ratio == 0.02

    def test_to_paper(self):
        """Test model to paper conversion."""
        scale = ViewScale(ratio=0.01)  # 1:100
        assert scale.to_paper(1000) == 10  # 1000mm -> 10mm

    def test_to_model(self):
        """Test paper to model conversion."""
        scale = ViewScale(ratio=0.01)  # 1:100
        assert scale.to_model(10) == 1000  # 10mm -> 1000mm

    def test_standard_scales(self):
        """Test standard scale constants."""
        assert ViewScale.SCALE_1_1.ratio == 1.0
        assert ViewScale.SCALE_1_50.ratio == 0.02
        assert ViewScale.SCALE_1_100.ratio == 0.01
        assert ViewScale.SCALE_1_200.ratio == 0.005


class TestViewCropRegion:
    """Tests for ViewCropRegion class."""

    def test_crop_region_creation(self):
        """Test creating a crop region."""
        crop = ViewCropRegion(
            min_x=0,
            min_y=0,
            max_x=1000,
            max_y=1000,
        )
        assert crop.width == 1000
        assert crop.height == 1000

    def test_crop_region_center(self):
        """Test crop region center."""
        crop = ViewCropRegion(
            min_x=0,
            min_y=0,
            max_x=1000,
            max_y=2000,
        )
        center = crop.center
        assert center.x == 500
        assert center.y == 1000

    def test_contains_point(self):
        """Test point containment."""
        crop = ViewCropRegion(min_x=0, min_y=0, max_x=1000, max_y=1000)

        assert crop.contains_point(Point2D(500, 500)) is True
        assert crop.contains_point(Point2D(0, 0)) is True  # Edge
        assert crop.contains_point(Point2D(1500, 500)) is False
        assert crop.contains_point(Point2D(-100, 500)) is False

    def test_clip_line_inside(self):
        """Test clipping a line fully inside."""
        crop = ViewCropRegion(min_x=0, min_y=0, max_x=1000, max_y=1000)
        line = Line2D(
            start=Point2D(100, 100),
            end=Point2D(500, 500),
            style=LineStyle.default(),
        )
        clipped = crop.clip_line(line)
        assert clipped is not None
        assert clipped.start.x == 100
        assert clipped.end.x == 500

    def test_clip_line_outside(self):
        """Test clipping a line fully outside."""
        crop = ViewCropRegion(min_x=0, min_y=0, max_x=1000, max_y=1000)
        line = Line2D(
            start=Point2D(1500, 100),
            end=Point2D(2000, 500),
            style=LineStyle.default(),
        )
        clipped = crop.clip_line(line)
        assert clipped is None

    def test_clip_line_crossing(self):
        """Test clipping a line crossing the boundary."""
        crop = ViewCropRegion(min_x=0, min_y=0, max_x=1000, max_y=1000)
        line = Line2D(
            start=Point2D(-500, 500),
            end=Point2D(500, 500),
            style=LineStyle.default(),
        )
        clipped = crop.clip_line(line)
        assert clipped is not None
        assert clipped.start.x == 0  # Clipped to left edge
        assert clipped.end.x == 500

    def test_clip_disabled(self):
        """Test that disabled crop region passes through."""
        crop = ViewCropRegion(min_x=0, min_y=0, max_x=100, max_y=100, enabled=False)
        line = Line2D(
            start=Point2D(500, 500),
            end=Point2D(1000, 1000),
            style=LineStyle.default(),
        )
        clipped = crop.clip_line(line)
        assert clipped is not None
        assert clipped.start.x == 500  # Not clipped

    def test_from_bounds(self):
        """Test creating crop region from bounds tuple."""
        crop = ViewCropRegion.from_bounds((100, 200, 500, 600), margin=50)
        assert crop.min_x == 50
        assert crop.min_y == 150
        assert crop.max_x == 550
        assert crop.max_y == 650
