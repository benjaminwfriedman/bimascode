"""
World geometry transformation base classes.

This module provides two mixin classes for transforming local geometry to world coordinates:

- FreestandingElementMixin: For elements positioned directly in world coordinates (Wall, Floor, Column, Beam)
- HostedElementMixin: For elements positioned relative to a host element (Door, Window)

These mixins centralize the error-prone logic around build123d's locate() behavior:
1. locate() modifies geometry IN PLACE - we must copy before transforming
2. locate() REPLACES transforms, doesn't chain them - we must compose transforms with multiplication

Usage:
    class Wall(ElementInstance, FreestandingElementMixin):
        def _get_world_position(self):
            return (self.start_point[0], self.start_point[1], self.level.elevation_mm)

        def _get_world_rotation(self):
            return self.angle_degrees

    class Door(ElementInstance, HostedElementMixin):
        def _get_host_transform(self):
            # Return wall's world transform
            ...

        def _get_local_transform(self):
            # Return door's position within wall
            ...
"""

import copy
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from build123d import Location


class FreestandingElementMixin:
    """Mixin for elements positioned directly in world coordinates.

    Freestanding elements have their own level reference and are positioned
    using world X, Y coordinates plus level elevation for Z.

    Examples: Wall, Floor, Ceiling, Column, Beam

    Subclasses must implement:
        - _get_world_position() -> (x, y, z) tuple
        - _get_world_rotation() -> angle in degrees (rotation around Z axis)

    Optionally override:
        - _get_local_transform() -> Location for internal centering (Column, Beam)
    """

    def get_world_geometry(self) -> Any | None:
        """Get geometry transformed to world coordinates.

        Returns:
            build123d geometry in world coordinates, or None if no local geometry
        """
        # Import here to avoid circular imports and allow testing without build123d
        from build123d import Location

        # Get local geometry (from ElementInstance.get_geometry())
        local_geom = self.get_geometry()
        if local_geom is None:
            return None

        # CRITICAL: Copy geometry before transforming!
        # locate() modifies in place, which would corrupt the cached local geometry
        geom_copy = copy.copy(local_geom)

        # Get world position and rotation from subclass
        position = self._get_world_position()
        rotation = self._get_world_rotation()

        # Check if there's an internal centering transform to compose
        local_transform = self._get_local_transform()

        # Create world transform
        world_transform = Location(position, (0, 0, 1), rotation)

        if local_transform is not None:
            # CRITICAL: locate() REPLACES transforms, doesn't chain them!
            # We must compose transforms using multiplication
            combined = world_transform * local_transform
            return geom_copy.locate(combined)
        else:
            return geom_copy.locate(world_transform)

    @abstractmethod
    def _get_world_position(self) -> tuple[float, float, float]:
        """Get the world position (x, y, z) for this element.

        Z should include level elevation.

        Returns:
            (x, y, z) tuple in world coordinates
        """
        raise NotImplementedError

    @abstractmethod
    def _get_world_rotation(self) -> float:
        """Get the rotation angle in degrees around the Z axis.

        Returns:
            Rotation angle in degrees
        """
        raise NotImplementedError

    def _get_local_transform(self) -> Optional["Location"]:
        """Get optional local transform for internal centering.

        Override this for elements that have internal transforms applied
        in create_geometry() (e.g., Column centering, Beam start-point shift).

        Returns:
            Location transform or None if no local transform needed
        """
        return None


class HostedElementMixin:
    """Mixin for elements positioned relative to a host element.

    Hosted elements (like doors and windows) are positioned within a host
    element (like a wall). Their world position is computed by composing:
        host_transform * local_transform

    Examples: Door, Window

    Subclasses must implement:
        - _get_host_transform() -> Location (host's world transform)
        - _get_local_transform() -> Location (position within host)
    """

    def get_world_geometry(self) -> Any | None:
        """Get geometry transformed to world coordinates.

        Returns:
            build123d geometry in world coordinates, or None if no local geometry
        """

        local_geom = self.get_geometry()
        if local_geom is None:
            return None

        # CRITICAL: Copy geometry before transforming!
        geom_copy = copy.copy(local_geom)

        # Get transforms from subclass
        host_transform = self._get_host_transform()
        local_transform = self._get_local_transform()

        # CRITICAL: Compose transforms using multiplication
        # This applies local_transform first (position within host),
        # then host_transform (rotate and translate to host's world position)
        combined = host_transform * local_transform

        return geom_copy.locate(combined)

    @abstractmethod
    def _get_host_transform(self) -> "Location":
        """Get the host element's world transform.

        Returns:
            Location representing host's position and rotation in world coordinates
        """
        raise NotImplementedError

    @abstractmethod
    def _get_local_transform(self) -> "Location":
        """Get this element's transform within the host.

        Returns:
            Location representing position within host (e.g., offset along wall)
        """
        raise NotImplementedError
