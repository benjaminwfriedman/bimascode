"""
Wall joins module for BIM as Code.

This module handles the detection and processing of wall joins (corners,
T-junctions, and crossings). Wall joins are detected based on centerline
intersections and processed to adjust wall geometry for clean connections.

HIGH RISK: Wall join processing is complex and may have edge cases.
"""

from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass
import math

if TYPE_CHECKING:
    from bimascode.architecture.wall import Wall


class JoinType(Enum):
    """Type of wall join."""
    L_JUNCTION = "L"      # Corner - both walls end at intersection
    T_JUNCTION = "T"      # T-intersection - one wall ends at another's side
    CROSS = "X"           # Cross - walls pass through each other


class EndCapType(Enum):
    """How wall ends are trimmed at joins."""
    FLUSH = "flush"           # Cut at centerline intersection
    EXTERIOR = "exterior"     # Extend to outer face of joining wall
    INTERIOR = "interior"     # Cut at inner face of joining wall


@dataclass
class WallJoin:
    """Represents a join between two walls."""
    wall_a: 'Wall'
    wall_b: 'Wall'
    join_type: JoinType
    intersection_point: Tuple[float, float]
    # Which end of each wall is at the join (0=start, 1=end, -1=mid)
    wall_a_end: int  # 0=start, 1=end, -1=neither (passes through)
    wall_b_end: int  # 0=start, 1=end, -1=neither (passes through)


def line_intersection(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float]
) -> Optional[Tuple[float, float]]:
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

    return (
        p1[0] + t * (p2[0] - p1[0]),
        p1[1] + t * (p2[1] - p1[1])
    )


def point_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate distance between two points."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def point_on_segment(
    point: Tuple[float, float],
    seg_start: Tuple[float, float],
    seg_end: Tuple[float, float],
    tolerance: float = 1.0  # 1mm tolerance
) -> bool:
    """Check if a point lies on a line segment (within tolerance)."""
    # Calculate distances
    d_start = point_distance(point, seg_start)
    d_end = point_distance(point, seg_end)
    seg_length = point_distance(seg_start, seg_end)

    # Point is on segment if sum of distances equals segment length
    return abs(d_start + d_end - seg_length) < tolerance


def get_wall_centerline(wall: 'Wall') -> Tuple[Tuple[float, float], Tuple[float, float]]:
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

    def __init__(self, walls: List['Wall'], tolerance: float = 50.0):
        """
        Initialize detector.

        Args:
            walls: List of walls to analyze
            tolerance: Distance tolerance for endpoint matching (mm)
        """
        self.walls = walls
        self.tolerance = tolerance

    def detect_joins(self) -> List[WallJoin]:
        """
        Detect all wall joins.

        Returns:
            List of WallJoin objects
        """
        joins = []

        # Compare each pair of walls
        for i, wall_a in enumerate(self.walls):
            for wall_b in self.walls[i + 1:]:
                # Skip if walls are on different levels
                if wall_a.level != wall_b.level:
                    continue

                join = self._detect_join(wall_a, wall_b)
                if join:
                    joins.append(join)

        return joins

    def _detect_join(self, wall_a: 'Wall', wall_b: 'Wall') -> Optional[WallJoin]:
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
            wall_b_end=wall_b_end
        )


class WallJoinProcessor:
    """Processes wall joins to calculate trim adjustments."""

    def __init__(self, joins: List[WallJoin], end_cap_type: EndCapType = EndCapType.FLUSH):
        """
        Initialize processor.

        Args:
            joins: List of wall joins to process
            end_cap_type: How to trim wall ends
        """
        self.joins = joins
        self.end_cap_type = end_cap_type

    def process_joins(self) -> Dict['Wall', Dict]:
        """
        Process all joins and calculate trim adjustments.

        Returns:
            Dict mapping walls to their trim adjustments
        """
        adjustments: Dict['Wall', Dict] = {}

        for join in self.joins:
            self._process_join(join, adjustments)

        return adjustments

    def _process_join(self, join: WallJoin, adjustments: Dict['Wall', Dict]) -> None:
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
            adjustments[wall_a] = {'start_offset': 0.0, 'end_offset': 0.0}
        if wall_b not in adjustments:
            adjustments[wall_b] = {'start_offset': 0.0, 'end_offset': 0.0}

        # Determine priority: structural > non-structural, thicker > thinner
        a_priority = self._get_wall_priority(wall_a)
        b_priority = self._get_wall_priority(wall_b)

        if join.join_type == JoinType.L_JUNCTION:
            self._process_l_junction(join, adjustments, a_priority, b_priority)
        elif join.join_type == JoinType.T_JUNCTION:
            self._process_t_junction(join, adjustments, a_priority, b_priority)
        elif join.join_type == JoinType.CROSS:
            self._process_cross(join, adjustments, a_priority, b_priority)

    def _get_wall_priority(self, wall: 'Wall') -> int:
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
        self,
        join: WallJoin,
        adjustments: Dict['Wall', Dict],
        a_priority: int,
        b_priority: int
    ) -> None:
        """Process an L-junction (corner)."""
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

    def _process_t_junction(
        self,
        join: WallJoin,
        adjustments: Dict['Wall', Dict],
        a_priority: int,
        b_priority: int
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
        self,
        join: WallJoin,
        adjustments: Dict['Wall', Dict],
        a_priority: int,
        b_priority: int
    ) -> None:
        """Process a cross intersection."""
        # For crosses, lower priority wall is typically "cut" by higher priority
        # This is a complex case that may need visual review
        # For now, we don't apply any adjustments (walls pass through each other)
        pass

    def _apply_extension(
        self,
        adj: Dict,
        end: int,
        amount: float
    ) -> None:
        """
        Apply extension/trim to a wall's adjustments.

        Args:
            adj: Adjustment dict for the wall
            end: Which end (0=start, 1=end)
            amount: Positive = extend, negative = trim
        """
        if end == 0:
            # Extending start means moving it back (negative direction)
            adj['start_offset'] = min(adj['start_offset'], -amount)
        elif end == 1:
            # Extending end means moving it forward (positive direction)
            adj['end_offset'] = max(adj['end_offset'], amount)


def detect_and_process_wall_joins(
    walls: List['Wall'],
    end_cap_type: EndCapType = EndCapType.FLUSH,
    tolerance: float = 50.0
) -> Dict['Wall', Dict]:
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
