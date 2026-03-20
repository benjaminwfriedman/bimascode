"""
Core BIM classes and base element definitions.
"""

from .element import Element
from .type_instance import ElementType, ElementInstance, copy_parameters

__all__ = ["Element", "ElementType", "ElementInstance", "copy_parameters"]
