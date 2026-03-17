"""
Base classes for all BIM elements.
"""

import uuid
from typing import Optional, Dict, Any


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
