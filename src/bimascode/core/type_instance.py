"""
Type/Instance parameter model for BIM as Code.

This module implements the parametric type/instance pattern used throughout BIM systems:
- ElementType: Defines shared parameters for all instances of that type
- Element instances: Can override type parameters with instance-specific values
- Property change notifications propagate from type to instances
"""

from typing import Any, Dict, List, Optional, Set
from abc import ABC, abstractmethod
import time
import uuid


class ElementType(ABC):
    """
    Base class for all element types (WallType, FloorType, etc.).

    Types define shared parameters that propagate to all instances.
    When a type parameter changes, all instances are notified.
    """

    def __init__(self, name: str):
        """
        Initialize an element type.

        Args:
            name: Unique name for this type
        """
        self.name = name
        self.guid = str(uuid.uuid4())
        self._instances: List['ElementInstance'] = []
        self._type_parameters: Dict[str, Any] = {}

    def set_parameter(self, param_name: str, value: Any) -> None:
        """
        Set a type parameter value.

        This will notify all instances that the type parameter has changed.
        Instances without overrides will reflect the new value.

        Args:
            param_name: Name of the parameter
            value: New value for the parameter
        """
        old_value = self._type_parameters.get(param_name)
        self._type_parameters[param_name] = value

        # Notify all instances of the change
        for instance in self._instances:
            instance._on_type_parameter_changed(param_name, value, old_value)

    def get_parameter(self, param_name: str, default: Any = None) -> Any:
        """
        Get a type parameter value.

        Args:
            param_name: Name of the parameter
            default: Default value if parameter doesn't exist

        Returns:
            Parameter value or default
        """
        return self._type_parameters.get(param_name, default)

    def _register_instance(self, instance: 'ElementInstance') -> None:
        """Register an instance with this type."""
        if instance not in self._instances:
            self._instances.append(instance)

    def _unregister_instance(self, instance: 'ElementInstance') -> None:
        """Unregister an instance from this type."""
        if instance in self._instances:
            self._instances.remove(instance)

    @property
    def instances(self) -> List['ElementInstance']:
        """Get all instances of this type."""
        return self._instances.copy()

    @property
    def instance_count(self) -> int:
        """Get the number of instances of this type."""
        return len(self._instances)

    @abstractmethod
    def create_geometry(self, instance: 'ElementInstance') -> Any:
        """
        Create geometry for an instance of this type.

        This method must be implemented by subclasses to define how
        geometry is created based on type and instance parameters.

        Args:
            instance: The instance to create geometry for

        Returns:
            Geometry object (typically build123d solid)
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', instances={self.instance_count})"


class ElementInstance(ABC):
    """
    Base class for all element instances (Wall, Floor, etc.).

    Instances reference a type and can override type parameters with
    instance-specific values.
    """

    def __init__(self, element_type: ElementType, name: Optional[str] = None):
        """
        Initialize an element instance.

        Args:
            element_type: The type this instance belongs to
            name: Optional unique name for this instance
        """
        self.type = element_type
        self.name = name or f"{element_type.name}_{len(element_type.instances) + 1}"
        self.guid = str(uuid.uuid4())

        self._instance_parameters: Dict[str, Any] = {}
        self._overridden_parameters: Set[str] = set()
        self._geometry = None
        self._geometry_valid = False

        # Cache invalidation support (Sprint 5)
        self._modified_timestamp: float = time.time()
        self._cached_2d: Any = None
        self._cache_timestamp: float = 0.0

        # Register with type
        self.type._register_instance(self)

    def set_parameter(self, param_name: str, value: Any, override: bool = True) -> None:
        """
        Set an instance parameter value.

        Args:
            param_name: Name of the parameter
            value: New value for the parameter
            override: If True, this overrides the type parameter
        """
        self._instance_parameters[param_name] = value

        if override:
            self._overridden_parameters.add(param_name)

        # Invalidate geometry when parameters change
        self._geometry_valid = False

    def get_parameter(self, param_name: str, default: Any = None) -> Any:
        """
        Get a parameter value.

        This will first check for instance overrides, then fall back to
        the type parameter.

        Args:
            param_name: Name of the parameter
            default: Default value if parameter doesn't exist

        Returns:
            Parameter value or default
        """
        # Check for instance override first
        if param_name in self._overridden_parameters:
            return self._instance_parameters.get(param_name, default)

        # Fall back to type parameter
        type_value = self.type.get_parameter(param_name)
        if type_value is not None:
            return type_value

        # Finally check instance parameters (non-override)
        return self._instance_parameters.get(param_name, default)

    def reset_parameter(self, param_name: str) -> None:
        """
        Reset a parameter to use the type value.

        This removes any instance override for the parameter.

        Args:
            param_name: Name of the parameter to reset
        """
        if param_name in self._overridden_parameters:
            self._overridden_parameters.remove(param_name)
            self._geometry_valid = False

    def is_parameter_overridden(self, param_name: str) -> bool:
        """
        Check if a parameter is overridden at the instance level.

        Args:
            param_name: Name of the parameter

        Returns:
            True if parameter is overridden
        """
        return param_name in self._overridden_parameters

    @staticmethod
    def _generate_guid() -> str:
        """
        Generate a valid IFC GUID.

        Returns:
            UUID string
        """
        return str(uuid.uuid4())

    def _on_type_parameter_changed(self, param_name: str, new_value: Any, old_value: Any) -> None:
        """
        Called when a type parameter changes.

        This only affects the instance if the parameter is not overridden.

        Args:
            param_name: Name of the changed parameter
            new_value: New parameter value
            old_value: Previous parameter value
        """
        if param_name not in self._overridden_parameters:
            # Parameter is not overridden, so instance is affected
            self._geometry_valid = False

    def invalidate_geometry(self) -> None:
        """Mark geometry as invalid and requiring regeneration.

        Also invalidates the 2D representation cache.
        """
        self._geometry_valid = False
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate cached representations when geometry changes."""
        self._modified_timestamp = time.time()
        self._cached_2d = None

    @property
    def modified_timestamp(self) -> float:
        """Get the timestamp of the last geometry modification."""
        return self._modified_timestamp

    def get_geometry(self, force_rebuild: bool = False) -> Any:
        """
        Get the geometry for this instance.

        Geometry is cached and only regenerated when invalid.

        Args:
            force_rebuild: Force geometry regeneration even if valid

        Returns:
            Geometry object (typically build123d solid)
        """
        if not self._geometry_valid or force_rebuild:
            self._geometry = self.type.create_geometry(self)
            self._geometry_valid = True

        return self._geometry

    @property
    def overridden_parameters(self) -> Set[str]:
        """Get the set of parameters overridden at instance level."""
        return self._overridden_parameters.copy()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', type='{self.type.name}')"


# Convenience function for parameter management
def copy_parameters(source: ElementType | ElementInstance,
                    target: ElementType | ElementInstance,
                    param_names: Optional[List[str]] = None) -> None:
    """
    Copy parameters from one element to another.

    Args:
        source: Source element (type or instance)
        target: Target element (type or instance)
        param_names: Optional list of specific parameters to copy.
                    If None, copies all parameters.
    """
    if param_names is None:
        # Copy all parameters
        if isinstance(source, ElementType):
            param_names = list(source._type_parameters.keys())
        else:
            param_names = list(source._instance_parameters.keys())

    for param_name in param_names:
        value = source.get_parameter(param_name)
        if value is not None:
            target.set_parameter(param_name, value)
