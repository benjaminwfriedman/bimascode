"""Protocols for 2D representation generation.

Defines the Drawable2D protocol that elements must implement
to support automatic 2D view generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Union, runtime_checkable

from bimascode.drawing.primitives import Arc2D, Hatch2D, Line2D, Polyline2D

if TYPE_CHECKING:
    from bimascode.drawing.view_base import ViewRange


# Type alias for 2D geometry primitives that elements can return
Linework2D = Union[Line2D, Arc2D, Polyline2D, Hatch2D]


@runtime_checkable
class Drawable2D(Protocol):
    """Protocol for elements that can generate 2D representations.

    Elements implementing this protocol can be automatically rendered
    in floor plans, sections, and elevations without needing OCCT
    section cutting (which is slower).

    The protocol defines methods for generating plan and section
    representations. Elements should return a list of 2D primitives
    (Line2D, Arc2D, Polyline2D, Hatch2D) with appropriate styles.
    """

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: ViewRange,
    ) -> list[Linework2D]:
        """Generate floor plan linework.

        Called when the element is intersected by a horizontal
        section plane (floor plan).

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters

        Returns:
            List of 2D geometry primitives
        """
        ...

    def get_section_representation(
        self,
        section_plane: tuple[tuple[float, float, float], tuple[float, float, float]],
        view_direction: tuple[float, float, float],
    ) -> list[Linework2D]:
        """Generate section/elevation linework.

        Called when the element is intersected by a vertical
        section plane.

        Args:
            section_plane: Tuple of (point, normal) defining the section plane
            view_direction: Direction vector the viewer is looking

        Returns:
            List of 2D geometry primitives
        """
        ...


@runtime_checkable
class HasBoundingBox(Protocol):
    """Protocol for elements that have a bounding box.

    Used for spatial queries and view filtering.
    """

    def get_bounding_box(self):
        """Get the element's bounding box.

        Returns:
            BoundingBox instance or None
        """
        ...


@runtime_checkable
class HasGeometry(Protocol):
    """Protocol for elements that have 3D geometry.

    Used for OCCT-based section cutting when Drawable2D
    is not implemented.
    """

    def get_geometry(self):
        """Get the element's 3D geometry.

        Returns:
            build123d geometry or None
        """
        ...
