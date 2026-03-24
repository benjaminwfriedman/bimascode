"""
Core BIM classes and base element definitions.
"""

from .element import Element
from .type_instance import ElementInstance, ElementType, copy_parameters

__all__ = ["Element", "ElementType", "ElementInstance", "copy_parameters"]
