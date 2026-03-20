"""
Base classes for all BIM elements.
"""

import time
import uuid
from typing import Optional, Dict, Any

from bimascode.performance.bounding_box import BoundingBox


class Element:
    """
    Base class for all BIM elements.

    Provides:
    - Unique GUID generation
    - Property storage
    - Common attributes (name, description)
    """

    def __init__(self, name: str, description: Optional[str] = None):
        """
        Initialize a BIM element.

        Args:
            name: Element name
            description: Optional element description
        """
        self.name = name
        self.description = description
        self._guid = self._generate_guid()
        self._properties: Dict[str, Any] = {}
        self._modified_timestamp: float = time.time()
        self._cached_2d: Any = None
        self._cache_timestamp: float = 0.0

    @staticmethod
    def _generate_guid() -> str:
        """
        Generate a valid IFC GUID.

        IFC GUIDs are base64-encoded UUIDs with a specific character set.
        For now, we use standard UUIDs and will convert during IFC export.
        """
        return str(uuid.uuid4())

    @property
    def guid(self) -> str:
        """Get the element's globally unique identifier."""
        return self._guid

    def set_property(self, name: str, value: Any) -> None:
        """
        Set a custom property on the element.

        Args:
            name: Property name
            value: Property value
        """
        self._properties[name] = value

    def get_property(self, name: str, default: Any = None) -> Any:
        """
        Get a custom property value.

        Args:
            name: Property name
            default: Default value if property not found

        Returns:
            Property value or default
        """
        return self._properties.get(name, default)

    @property
    def properties(self) -> Dict[str, Any]:
        """Get all custom properties."""
        return self._properties.copy()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', guid='{self._guid}')"

    def _invalidate_cache(self) -> None:
        """Invalidate cached representations when geometry changes.

        Call this method from property setters that modify element geometry.
        """
        self._modified_timestamp = time.time()
        self._cached_2d = None

    @property
    def modified_timestamp(self) -> float:
        """Get the timestamp of the last geometry modification."""
        return self._modified_timestamp

    def get_bounding_box(self) -> Optional[BoundingBox]:
        """Get the axis-aligned bounding box of this element.

        Subclasses should override this method to provide accurate bounds.

        Returns:
            BoundingBox for the element, or None if not applicable
        """
        return None
