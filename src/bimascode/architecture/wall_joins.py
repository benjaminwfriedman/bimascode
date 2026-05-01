"""
Wall joins module for BIM as Code.

This module handles the detection and processing of wall joins (corners,
T-junctions, and crossings). Wall joins are detected based on centerline
intersections and processed to adjust wall geometry for clean connections.

HIGH RISK: Wall join processing is complex and may have edge cases.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bimascode.architecture.wall import Wall


class JoinType(Enum):
    """Type of wall join topology."""

    L_JUNCTION = "L"  # Corner - both walls end at intersection
    T_JUNCTION = "T"  # T-intersection - one wall ends at another's side
    CROSS = "X"  # Cross - walls pass through each other


class WallJoinStyle(Enum):
    """
    Style of how wall ends are cut at joins.

    Controls the geometric treatment at wall intersections:
    - BUTT: One wall stops at the face of another (default)
    - MITER: Both walls are cut at bisecting angle

    TODO: Add SQUARE_OFF join style. SQUARE_OFF is a hybrid of butt and miter:
    one wall gets a miter cut on its outside corner while the other wall
    extends (butt) so its end face aligns exactly with that miter's outside
    corner. This creates a clean corner where the miter diagonal meets the
    butt face flush. Useful for non-90° wall joins.
    """

    BUTT = "butt"  # One wall stops at face of another
    MITER = "miter"  # Both walls cut at bisecting angle


class EndCapType(Enum):
    """How wall ends are trimmed at joins."""

    FLUSH = "flush"  # Cut at centerline intersection
    EXTERIOR = "exterior"  # Extend to outer face of joining wall
    INTERIOR = "interior"  # Cut at inner face of joining wall


@dataclass
class WallJoin:
    """Represents a join between two walls."""

    wall_a: "Wall"
    wall_b: "Wall"
    join_type: JoinType
    intersection_point: tuple[float, float]
    # Which end of each wall is at the join (0=start, 1=end, -1=mid)
    wall_a_end: int  # 0=start, 1=end, -1=neither (passes through)
    wall_b_end: int  # 0=start, 1=end, -1=neither (passes through)


def line_intersection(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> tuple[float, float] | None:
    """
    Find the intersection point of two lines.

    Lines are defined by points (p1, p2) and (p3, p4).
    Uses parametric line intersection.

    Args:
        p1, p2: Points defining first line
        p3, p4: Points defining second line

    Returns:
        (x, y) intersection point, or None if lines are parallel
    """
    denom = (p1[0] - p2[0]) * (p3[1] - p4[1]) - (p1[1] - p2[1]) * (p3[0] - p4[0])

    if abs(denom) < 1e-10:
        return None  # Lines are parallel

    t = ((p1[0] - p3[0]) * (p3[1] - p4[1]) - (p1[1] - p3[1]) * (p3[0] - p4[0])) / denom

    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))


def point_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Calculate distance between two points."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def point_on_segment(
    point: tuple[float, float],
    seg_start: tuple[float, float],
    seg_end: tuple[float, float],
    tolerance: float = 1.0,  # 1mm tolerance
) -> bool:
    """Check if a point lies on a line segment (within tolerance)."""
    # Calculate distances
    d_start = point_distance(point, seg_start)
    d_end = point_distance(point, seg_end)
    seg_length = point_distance(seg_start, seg_end)

    # Point is on segment if sum of distances equals segment length
    return abs(d_start + d_end - seg_length) < tolerance


def get_wall_centerline(wall: "Wall") -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Get the centerline of a wall (offset by half width perpendicular to wall).

    For simplicity, we use the wall's defined start/end points as the centerline.
    In a more complete implementation, this would offset by half the wall width.

    Args:
        wall: Wall instance

    Returns:
        (start_point, end_point) of centerline
    """
    return (wall.start_point, wall.end_point)


class WallJoinDetector:
    """Detects wall joins based on centerline intersections."""

    def __init__(self, walls: list["Wall"], tolerance: float = 50.0):
        """
        Initialize detector.

        Args:
            walls: List of walls to analyze
            tolerance: Distance tolerance for endpoint matching (mm)
        """
        self.walls = walls
        self.tolerance = tolerance

    def detect_joins(self) -> list[WallJoin]:
        """
        Detect all wall joins.

        Returns:
            List of WallJoin objects
        """
        joins = []

        # Compare each pair of walls
        for i, wall_a in enumerate(self.walls):
            for wall_b in self.walls[i + 1 :]:
                # Skip if walls are on different levels
                if wall_a.level != wall_b.level:
                    continue

                join = self._detect_join(wall_a, wall_b)
                if join:
                    joins.append(join)

        return joins

    def _detect_join(self, wall_a: "Wall", wall_b: "Wall") -> WallJoin | None:
        """
        Detect if two walls join.

        Args:
            wall_a, wall_b: Walls to check

        Returns:
            WallJoin if walls join, None otherwise
        """
        # Get centerlines
        a_start, a_end = get_wall_centerline(wall_a)
        b_start, b_end = get_wall_centerline(wall_b)

        # Find line intersection
        intersection = line_intersection(a_start, a_end, b_start, b_end)

        if intersection is None:
            return None  # Walls are parallel

        # Check if intersection is near endpoints or mid-segment
        tol = self.tolerance

        # Check wall A
        a_at_start = point_distance(intersection, a_start) < tol
        a_at_end = point_distance(intersection, a_end) < tol
        a_on_segment = point_on_segment(intersection, a_start, a_end, tol)

        # Check wall B
        b_at_start = point_distance(intersection, b_start) < tol
        b_at_end = point_distance(intersection, b_end) < tol
        b_on_segment = point_on_segment(intersection, b_start, b_end, tol)

        # Determine wall end indicators
        if a_at_start:
            wall_a_end = 0
        elif a_at_end:
            wall_a_end = 1
        elif a_on_segment:
            wall_a_end = -1
        else:
            return None  # Intersection not on wall A

        if b_at_start:
            wall_b_end = 0
        elif b_at_end:
            wall_b_end = 1
        elif b_on_segment:
            wall_b_end = -1
        else:
            return None  # Intersection not on wall B

        # Classify join type
        if wall_a_end >= 0 and wall_b_end >= 0:
            # Both walls end at intersection -> L junction (corner)
            join_type = JoinType.L_JUNCTION
        elif wall_a_end == -1 and wall_b_end == -1:
            # Both walls pass through -> Cross
            join_type = JoinType.CROSS
        else:
            # One ends, one passes through -> T junction
            join_type = JoinType.T_JUNCTION

        return WallJoin(
            wall_a=wall_a,
            wall_b=wall_b,
            join_type=join_type,
            intersection_point=intersection,
            wall_a_end=wall_a_end,
            wall_b_end=wall_b_end,
        )


class WallJoinProcessor:
    """Processes wall joins to calculate trim adjustments."""

    def __init__(self, joins: list[WallJoin], end_cap_type: EndCapType = EndCapType.FLUSH):
        """
        Initialize processor.

        Args:
            joins: List of wall joins to process
            end_cap_type: How to trim wall ends
        """
        self.joins = joins
        self.end_cap_type = end_cap_type

    def process_joins(self) -> dict["Wall", dict]:
        """
        Process all joins and calculate trim adjustments.

        Returns:
            Dict mapping walls to their trim adjustments
        """
        adjustments: dict[Wall, dict] = {}

        for join in self.joins:
            self._process_join(join, adjustments)

        return adjustments

    def _process_join(self, join: WallJoin, adjustments: dict["Wall", dict]) -> None:
        """
        Process a single join.

        Args:
            join: WallJoin to process
            adjustments: Dict to update with adjustments
        """
        wall_a = join.wall_a
        wall_b = join.wall_b

        # Initialize adjustments if not present
        if wall_a not in adjustments:
            adjustments[wall_a] = {"start_offset": 0.0, "end_offset": 0.0}
        if wall_b not in adjustments:
            adjustments[wall_b] = {"start_offset": 0.0, "end_offset": 0.0}

        # Determine priority: structural > non-structural, thicker > thinner
        a_priority = self._get_wall_priority(wall_a)
        b_priority = self._get_wall_priority(wall_b)

        if join.join_type == JoinType.L_JUNCTION:
            self._process_l_junction(join, adjustments, a_priority, b_priority)
        elif join.join_type == JoinType.T_JUNCTION:
            self._process_t_junction(join, adjustments, a_priority, b_priority)
        elif join.join_type == JoinType.CROSS:
            self._process_cross(join, adjustments, a_priority, b_priority)

    def _get_wall_priority(self, wall: "Wall") -> int:
        """
        Calculate wall priority for join processing.

        Higher priority walls "win" at joins.

        Args:
            wall: Wall to evaluate

        Returns:
            Priority score (higher = wins at joins)
        """
        priority = 0

        # Structural walls have higher priority
        if wall.is_structural:
            priority += 1000

        # Thicker walls have higher priority
        priority += wall.width

        return priority

    def _process_l_junction(
        self, join: WallJoin, adjustments: dict["Wall", dict], a_priority: int, b_priority: int
    ) -> None:
        """Process an L-junction (corner)."""
        wall_a = join.wall_a
        wall_b = join.wall_b

        # Get join styles for each wall at the joining endpoint
        style_a = wall_a.get_join_style(join.wall_a_end)
        style_b = wall_b.get_join_style(join.wall_b_end)

        # Calculate wall angles
        angle_a = wall_a.angle
        angle_b = wall_b.angle

        # Handle based on join styles
        if style_a == WallJoinStyle.MITER and style_b == WallJoinStyle.MITER:
            # Both walls get miter cut at bisecting angle
            self._apply_miter_cut(join, adjustments, angle_a, angle_b)
        else:
            # Default BUTT join or mixed: use end cap type
            self._apply_butt_join(join, adjustments, a_priority, b_priority)

    def _apply_butt_join(
        self, join: WallJoin, adjustments: dict["Wall", dict], a_priority: int, b_priority: int
    ) -> None:
        """Apply butt join (one wall extends to face of other)."""
        wall_a = join.wall_a
        wall_b = join.wall_b

        # Calculate extension/trim based on end cap type
        if self.end_cap_type == EndCapType.FLUSH:
            # Both walls meet at centerline - no extension needed
            pass

        elif self.end_cap_type == EndCapType.EXTERIOR:
            # Higher priority wall extends to outer face of other
            if a_priority >= b_priority:
                # Wall A extends, Wall B is trimmed
                extension = wall_b.width / 2
                self._apply_extension(adjustments[wall_a], join.wall_a_end, extension)
            else:
                # Wall B extends, Wall A is trimmed
                extension = wall_a.width / 2
                self._apply_extension(adjustments[wall_b], join.wall_b_end, extension)

        elif self.end_cap_type == EndCapType.INTERIOR:
            # Higher priority wall stops at inner face of other
            if a_priority >= b_priority:
                # Wall A is trimmed
                trim = wall_b.width / 2
                self._apply_extension(adjustments[wall_a], join.wall_a_end, -trim)
            else:
                # Wall B is trimmed
                trim = wall_a.width / 2
                self._apply_extension(adjustments[wall_b], join.wall_b_end, -trim)

    def _apply_miter_cut(
        self,
        join: WallJoin,
        adjustments: dict["Wall", dict],
        angle_a: float,
        angle_b: float,
    ) -> None:
        """
        Apply miter cut to both walls at the intersection.

        Both walls are cut at the bisecting angle so they meet cleanly.
        """
        wall_a = join.wall_a
        wall_b = join.wall_b

        # Calculate the angle between walls
        angle_diff = abs(angle_b - angle_a)

        # Normalize to 0-180 range
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff

        # For a miter, each wall extends by: (half_width / tan(half_angle))
        # where half_angle is half the angle between the walls
        half_angle = angle_diff / 2

        # Prevent division by zero for near-parallel walls
        if abs(math.sin(half_angle)) < 0.01:
            return

        # Extension for wall A (based on wall A's width)
        ext_a = (wall_a.width / 2) / math.tan(half_angle)
        # Extension for wall B (based on wall B's width)
        ext_b = (wall_b.width / 2) / math.tan(half_angle)

        # Apply extensions
        self._apply_extension(adjustments[wall_a], join.wall_a_end, ext_a)
        self._apply_extension(adjustments[wall_b], join.wall_b_end, ext_b)

    def _process_t_junction(
        self, join: WallJoin, adjustments: dict["Wall", dict], a_priority: int, b_priority: int
    ) -> None:
        """Process a T-junction."""
        # The wall that ends (not passing through) gets trimmed/extended
        if join.wall_a_end >= 0:
            # Wall A ends at wall B's side
            ending_wall = join.wall_a
            continuous_wall = join.wall_b
            ending_end = join.wall_a_end
            adj = adjustments[ending_wall]
        else:
            # Wall B ends at wall A's side
            ending_wall = join.wall_b
            continuous_wall = join.wall_a
            ending_end = join.wall_b_end
            adj = adjustments[ending_wall]

        # Get join style for the ending wall
        style = ending_wall.get_join_style(ending_end)

        if style == WallJoinStyle.MITER:
            # Miter doesn't apply to T-junctions, treat as BUTT
            self._apply_t_butt_join(adj, ending_end, continuous_wall)
        else:
            # Default BUTT behavior
            self._apply_t_butt_join(adj, ending_end, continuous_wall)

    def _apply_t_butt_join(self, adj: dict, ending_end: int, continuous_wall: "Wall") -> None:
        """Apply butt join for T-junction ending wall."""
        if self.end_cap_type == EndCapType.FLUSH:
            # End at centerline
            pass
        elif self.end_cap_type == EndCapType.EXTERIOR:
            # Extend to outer face
            extension = continuous_wall.width / 2
            self._apply_extension(adj, ending_end, extension)
        elif self.end_cap_type == EndCapType.INTERIOR:
            # Trim to inner face
            trim = continuous_wall.width / 2
            self._apply_extension(adj, ending_end, -trim)

    def _process_cross(
        self, join: WallJoin, adjustments: dict["Wall", dict], a_priority: int, b_priority: int
    ) -> None:
        """Process a cross intersection."""
        # For crosses, lower priority wall is typically "cut" by higher priority
        # This is a complex case that may need visual review
        # For now, we don't apply any adjustments (walls pass through each other)
        pass

    def _apply_extension(self, adj: dict, end: int, amount: float) -> None:
        """
        Apply extension/trim to a wall's adjustments.

        Args:
            adj: Adjustment dict for the wall
            end: Which end (0=start, 1=end)
            amount: Positive = extend, negative = trim
        """
        if end == 0:
            # Extending start means moving it back (negative direction)
            adj["start_offset"] = min(adj["start_offset"], -amount)
        elif end == 1:
            # Extending end means moving it forward (positive direction)
            adj["end_offset"] = max(adj["end_offset"], amount)


def detect_and_process_wall_joins(
    walls: list["Wall"], end_cap_type: EndCapType = EndCapType.FLUSH, tolerance: float = 50.0
) -> dict["Wall", dict]:
    """
    Convenience function to detect and process wall joins.

    Args:
        walls: List of walls to process
        end_cap_type: How to trim wall ends
        tolerance: Distance tolerance for join detection (mm)

    Returns:
        Dict mapping walls to their trim adjustments
    """
    detector = WallJoinDetector(walls, tolerance)
    joins = detector.detect_joins()

    processor = WallJoinProcessor(joins, end_cap_type)
    return processor.process_joins()


def clean_wall_joins(
    walls: list["Wall"],
    end_cap_type: EndCapType = EndCapType.EXTERIOR,
    tolerance: float = 50.0,
) -> None:
    """
    Recalculate all wall joins and apply trim adjustments.

    This function clears existing trim adjustments, re-detects joins,
    and applies new adjustments based on current wall positions and
    join styles.

    Args:
        walls: List of walls to process
        end_cap_type: How to trim wall ends at joins
        tolerance: Distance tolerance for join detection (mm)
    """
    # Clear existing trim adjustments
    for wall in walls:
        wall._trim_adjustments = {}

    # Detect and process joins
    adjustments = detect_and_process_wall_joins(walls, end_cap_type, tolerance)

    # Apply adjustments to walls
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj
        wall.invalidate_geometry()


def reset_wall_joins(walls: list["Wall"]) -> None:
    """
    Reset all wall join adjustments to defaults.

    Clears all trim adjustments and resets join styles to BUTT.

    Args:
        walls: List of walls to reset
    """
    for wall in walls:
        wall._trim_adjustments = {}
        wall._join_style_start = WallJoinStyle.BUTT
        wall._join_style_end = WallJoinStyle.BUTT
        wall.invalidate_geometry()


def _find_common_intersection(
    walls: tuple["Wall", ...], tolerance: float = 50.0
) -> tuple[float, float] | None:
    """
    Find a common intersection point where all walls meet.

    Args:
        walls: Walls to check
        tolerance: Distance tolerance for endpoint matching (mm)

    Returns:
        (x, y) intersection point, or None if walls don't meet at a common point
    """
    if len(walls) < 2:
        return None

    # Collect all endpoints from all walls
    endpoints: list[tuple[float, float]] = []
    for wall in walls:
        endpoints.append(wall.start_point)
        endpoints.append(wall.end_point)

    # Find a point that is near at least one endpoint from each wall
    # Try each endpoint as a potential common point
    for candidate in endpoints:
        walls_at_point = 0
        for wall in walls:
            start = wall.start_point
            end = wall.end_point
            # Check if wall has an endpoint near candidate OR passes through it
            if point_distance(candidate, start) < tolerance:
                walls_at_point += 1
            elif point_distance(candidate, end) < tolerance:
                walls_at_point += 1
            elif point_on_segment(candidate, start, end, tolerance):
                walls_at_point += 1

        if walls_at_point == len(walls):
            return candidate

    return None


def _detect_join_at_point(
    wall_a: "Wall", wall_b: "Wall", intersection: tuple[float, float], tolerance: float = 50.0
) -> WallJoin | None:
    """
    Detect the join type between two walls at a specific intersection point.

    Args:
        wall_a, wall_b: Walls to check
        intersection: The known intersection point
        tolerance: Distance tolerance for endpoint matching (mm)

    Returns:
        WallJoin if walls join at the point, None otherwise
    """
    # Check wall A
    a_start, a_end = get_wall_centerline(wall_a)
    a_at_start = point_distance(intersection, a_start) < tolerance
    a_at_end = point_distance(intersection, a_end) < tolerance
    a_on_segment = point_on_segment(intersection, a_start, a_end, tolerance)

    # Check wall B
    b_start, b_end = get_wall_centerline(wall_b)
    b_at_start = point_distance(intersection, b_start) < tolerance
    b_at_end = point_distance(intersection, b_end) < tolerance
    b_on_segment = point_on_segment(intersection, b_start, b_end, tolerance)

    # Determine wall end indicators
    if a_at_start:
        wall_a_end = 0
    elif a_at_end:
        wall_a_end = 1
    elif a_on_segment:
        wall_a_end = -1
    else:
        return None  # Wall A not at intersection

    if b_at_start:
        wall_b_end = 0
    elif b_at_end:
        wall_b_end = 1
    elif b_on_segment:
        wall_b_end = -1
    else:
        return None  # Wall B not at intersection

    # Classify join type
    if wall_a_end >= 0 and wall_b_end >= 0:
        join_type = JoinType.L_JUNCTION
    elif wall_a_end == -1 and wall_b_end == -1:
        join_type = JoinType.CROSS
    else:
        join_type = JoinType.T_JUNCTION

    return WallJoin(
        wall_a=wall_a,
        wall_b=wall_b,
        join_type=join_type,
        intersection_point=intersection,
        wall_a_end=wall_a_end,
        wall_b_end=wall_b_end,
    )


def _validate_style_for_topology(style: WallJoinStyle, join_type: JoinType) -> None:
    """
    Validate that the requested style is valid for the detected topology.

    Args:
        style: Requested join style
        join_type: Detected topology

    Raises:
        ValueError: If style is invalid for topology
    """
    if style == WallJoinStyle.MITER:
        if join_type != JoinType.L_JUNCTION:
            raise ValueError(
                f"MITER join style requires L-junction (corner), "
                f"but detected {join_type.value}-junction. "
                f"Use BUTT for T-junctions."
            )
    elif style == WallJoinStyle.BUTT:
        if join_type == JoinType.CROSS:
            raise ValueError(
                f"BUTT join style requires at least one wall to terminate, "
                f"but detected CROSS-junction where both walls pass through."
            )


def _get_wall_priority(wall: "Wall") -> int:
    """
    Calculate wall priority for join processing.

    Higher priority walls "win" at joins.

    Args:
        wall: Wall to evaluate

    Returns:
        Priority score (higher = wins at joins)
    """
    priority = 0

    # Structural walls have higher priority
    if wall.is_structural:
        priority += 1000

    # Thicker walls have higher priority
    priority += wall.width

    return priority


def _ensure_trim_adjustments(wall: "Wall") -> None:
    """Ensure wall has a _trim_adjustments dict initialized."""
    if not hasattr(wall, "_trim_adjustments") or wall._trim_adjustments is None:
        wall._trim_adjustments = {}
    if "start_offset" not in wall._trim_adjustments:
        wall._trim_adjustments["start_offset"] = 0.0
    if "end_offset" not in wall._trim_adjustments:
        wall._trim_adjustments["end_offset"] = 0.0


def _apply_adjustment(
    wall: "Wall",
    end: int,
    offset: float,
    miter_angle: float | None = None,
    miter_inside_sign: int | None = None,
) -> None:
    """
    Apply offset and optional miter angle to a wall endpoint.

    Args:
        wall: Wall to adjust
        end: Which end (0=start, 1=end)
        offset: Extension amount (positive = extend, negative = trim)
        miter_angle: Optional miter cut angle in radians
        miter_inside_sign: Optional sign indicating which side is inside of L-corner
                          +1 means inside is on +perp side (left when walking along wall)
                          -1 means inside is on -perp side (right when walking along wall)
    """
    _ensure_trim_adjustments(wall)

    if end == 0:
        # Extending start means moving it back (negative direction)
        current = wall._trim_adjustments.get("start_offset", 0.0)
        wall._trim_adjustments["start_offset"] = min(current, -offset)
        if miter_angle is not None:
            wall._trim_adjustments["start_miter_angle"] = miter_angle
        if miter_inside_sign is not None:
            wall._trim_adjustments["start_miter_inside_sign"] = miter_inside_sign
    elif end == 1:
        # Extending end means moving it forward (positive direction)
        current = wall._trim_adjustments.get("end_offset", 0.0)
        wall._trim_adjustments["end_offset"] = max(current, offset)
        if miter_angle is not None:
            wall._trim_adjustments["end_miter_angle"] = miter_angle
        if miter_inside_sign is not None:
            wall._trim_adjustments["end_miter_inside_sign"] = miter_inside_sign

    wall.invalidate_geometry()


def _apply_miter_join(wall_a: "Wall", wall_b: "Wall", join: WallJoin) -> None:
    """
    Apply miter cut to both walls at L-junction.

    Both walls are cut at the bisecting angle so they meet cleanly.
    The miter cut is on the INSIDE of the L-corner (interior corner gets cut,
    exterior corners meet at a point).

    Args:
        wall_a, wall_b: Walls to join
        join: WallJoin describing the junction
    """
    angle_a = wall_a.angle
    angle_b = wall_b.angle

    # Calculate the angle between walls
    angle_diff = abs(angle_b - angle_a)

    # Normalize to 0-180 range
    if angle_diff > math.pi:
        angle_diff = 2 * math.pi - angle_diff

    # For a miter, each wall extends by: (half_width / tan(half_angle))
    half_angle = angle_diff / 2

    # Prevent division by zero for near-parallel walls
    if abs(math.sin(half_angle)) < 0.01:
        return

    # Determine which side of each wall is the "inside" of the L-corner.
    # The inside is where the two walls enclose space (the corner pocket).
    #
    # We use the cross product of direction vectors pointing AWAY from the junction.
    # This tells us how the walls "fan out" from the corner:
    #   cross_z < 0: walls fan out clockwise -> inside is on left (+perp)
    #   cross_z > 0: walls fan out counterclockwise -> inside is on right (-perp)

    # Get direction vectors pointing AWAY from the junction
    # Wall direction is start->end. If wall ends at junction, flip to point away.
    away_a_x = math.cos(angle_a)
    away_a_y = math.sin(angle_a)
    if join.wall_a_end == 1:
        away_a_x = -away_a_x
        away_a_y = -away_a_y

    away_b_x = math.cos(angle_b)
    away_b_y = math.sin(angle_b)
    if join.wall_b_end == 1:
        away_b_x = -away_b_x
        away_b_y = -away_b_y

    # Cross product z-component determines turning direction
    cross_z = away_a_x * away_b_y - away_a_y * away_b_x

    # miter_inside_sign indicates which side of the wall is inside the L-corner:
    #   +1 = inside is on +perp side (left when walking start->end)
    #   -1 = inside is on -perp side (right when walking start->end)
    if cross_z < 0:
        inside_sign = 1   # Inside on left (+perp)
    else:
        inside_sign = -1  # Inside on right (-perp)

    # Apply miter angle and inside sign to both walls.
    # Offset is 0 because the corner geometry handles the diagonal cut in wall.py.
    _apply_adjustment(wall_a, join.wall_a_end, 0.0, half_angle, inside_sign)
    _apply_adjustment(wall_b, join.wall_b_end, 0.0, half_angle, inside_sign)


def _apply_butt_join(
    wall_a: "Wall",
    wall_b: "Wall",
    join: WallJoin,
    extend_wall: "Wall | None" = None,
) -> None:
    """
    Apply butt join between walls.

    For L-junctions: one wall extends to face of other (based on priority or explicit).
    For T-junctions: terminating wall extends to/stops at continuous wall's face.

    Args:
        wall_a, wall_b: Walls to join
        join: WallJoin describing the junction
        extend_wall: Optional explicit wall that should extend (for L-junctions)
    """
    if join.join_type == JoinType.L_JUNCTION:
        # Determine which wall extends
        if extend_wall is not None:
            if extend_wall is wall_a:
                extending, other = wall_a, wall_b
                extending_end = join.wall_a_end
            else:
                extending, other = wall_b, wall_a
                extending_end = join.wall_b_end
        else:
            # Auto-determine by priority
            a_priority = _get_wall_priority(wall_a)
            b_priority = _get_wall_priority(wall_b)
            if a_priority >= b_priority:
                extending, other = wall_a, wall_b
                extending_end = join.wall_a_end
            else:
                extending, other = wall_b, wall_a
                extending_end = join.wall_b_end

        # Extend to outer face of other wall
        extension = other.width / 2
        _apply_adjustment(extending, extending_end, extension)

        # Trim the other wall back to avoid overlap
        # The other wall needs to stop at the extending wall's outer face
        other_end = join.wall_b_end if extending is wall_a else join.wall_a_end
        # For _apply_adjustment: positive offset extends, we want to trim
        # For start (end==0): offset is negated, so positive trim -> negative start_offset won't work
        # For end (end==1): positive offset extends forward
        # We need to directly set the trim value
        trim_amount = extending.width / 2
        _ensure_trim_adjustments(other)
        if other_end == 0:
            # Trim start: move start forward (positive offset in wall coords)
            current = other._trim_adjustments.get("start_offset", 0.0)
            other._trim_adjustments["start_offset"] = max(current, trim_amount)
        else:
            # Trim end: move end backward (negative offset in wall coords)
            current = other._trim_adjustments.get("end_offset", 0.0)
            other._trim_adjustments["end_offset"] = min(current, -trim_amount)
        other.invalidate_geometry()

    elif join.join_type == JoinType.T_JUNCTION:
        # The wall that ends gets extended to continuous wall's face
        if join.wall_a_end >= 0:
            ending_wall = wall_a
            continuous_wall = wall_b
            ending_end = join.wall_a_end
        else:
            ending_wall = wall_b
            continuous_wall = wall_a
            ending_end = join.wall_b_end

        extension = continuous_wall.width / 2
        _apply_adjustment(ending_wall, ending_end, extension)


def join_walls(
    style: WallJoinStyle,
    *walls: "Wall",
    extend: "Wall | None" = None,
    tolerance: float = 50.0,
) -> None:
    """
    Join multiple walls with specified style.

    This is the primary API for creating wall joins. It detects the topology
    (L-junction, T-junction, or Cross) automatically and validates that the
    requested style is appropriate.

    Args:
        style: How walls should be joined (MITER or BUTT)
        *walls: Two or more walls to join
        extend: For BUTT joins, which wall extends to the other's face.
                If None, auto-determines by priority (structural > thicker).
        tolerance: Distance tolerance for detecting joins (mm)

    Raises:
        ValueError: If fewer than 2 walls provided
        ValueError: If walls don't meet at a common point
        ValueError: If style is invalid for detected topology
        ValueError: If extend specified but wall not in *walls

    Examples:
        # L-junction with miter cut
        join_walls(WallJoinStyle.MITER, wall1, wall2)

        # T-junction with auto priority
        join_walls(WallJoinStyle.BUTT, partition, corridor)

        # T-junction with explicit priority
        join_walls(WallJoinStyle.BUTT, partition, corridor, extend=corridor)

        # 3-way corner
        join_walls(WallJoinStyle.MITER, wall1, wall2, wall3)
    """
    if len(walls) < 2:
        raise ValueError("join_walls requires at least 2 walls")

    if extend is not None and extend not in walls:
        raise ValueError("extend wall must be one of the walls being joined")

    # Find common intersection point
    intersection = _find_common_intersection(walls, tolerance)
    if intersection is None:
        raise ValueError(
            "Walls do not meet at a common point. "
            "Ensure wall endpoints are within tolerance of each other."
        )

    # Process each pair of walls that meet at the intersection
    for i, wall_a in enumerate(walls):
        for wall_b in walls[i + 1 :]:
            join = _detect_join_at_point(wall_a, wall_b, intersection, tolerance)
            if join is None:
                continue

            # Validate style for topology
            _validate_style_for_topology(style, join.join_type)

            # Apply join based on style
            if style == WallJoinStyle.MITER:
                _apply_miter_join(wall_a, wall_b, join)
            elif style == WallJoinStyle.BUTT:
                _apply_butt_join(wall_a, wall_b, join, extend)
