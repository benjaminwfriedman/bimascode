"""
Unit tests for the Type/Instance parameter model.
"""

import pytest
from bimascode.core.type_instance import ElementType, ElementInstance, copy_parameters


# Test implementations of abstract classes
class MockType(ElementType):
    """Mock element type for testing."""

    def __init__(self, name: str, width: float = 200.0):
        super().__init__(name)
        self.set_parameter("width", width)
        self.set_parameter("material", "Concrete")

    def create_geometry(self, instance):
        """Mock geometry creation."""
        return f"Geometry for {instance.name}"


class MockInstance(ElementInstance):
    """Mock element instance for testing."""
    pass


class TestElementType:
    """Tests for ElementType base class."""

    def test_type_creation(self):
        """Test creating an element type."""
        type1 = MockType("Test Type")
        assert type1.name == "Test Type"
        assert type1.guid is not None
        assert len(type1.guid) == 36  # UUID format
        assert type1.instance_count == 0

    def test_type_parameters(self):
        """Test setting and getting type parameters."""
        type1 = MockType("Type A")
        assert type1.get_parameter("width") == 200.0
        assert type1.get_parameter("material") == "Concrete"

        type1.set_parameter("width", 300.0)
        assert type1.get_parameter("width") == 300.0

    def test_type_parameter_default(self):
        """Test getting non-existent parameter with default."""
        type1 = MockType("Type A")
        assert type1.get_parameter("nonexistent") is None
        assert type1.get_parameter("nonexistent", "default") == "default"

    def test_instance_registration(self):
        """Test that instances are registered with their type."""
        type1 = MockType("Type A")
        assert type1.instance_count == 0

        inst1 = MockInstance(type1)
        assert type1.instance_count == 1
        assert inst1 in type1.instances

        inst2 = MockInstance(type1)
        assert type1.instance_count == 2
        assert inst2 in type1.instances


class TestElementInstance:
    """Tests for ElementInstance base class."""

    def test_instance_creation(self):
        """Test creating an element instance."""
        type1 = MockType("Type A")
        inst1 = MockInstance(type1, name="Instance 1")

        assert inst1.name == "Instance 1"
        assert inst1.type == type1
        assert inst1.guid is not None
        assert len(inst1.guid) == 36

    def test_instance_auto_naming(self):
        """Test automatic instance naming."""
        type1 = MockType("Wall Type")
        inst1 = MockInstance(type1)
        inst2 = MockInstance(type1)

        assert inst1.name == "Wall Type_1"
        assert inst2.name == "Wall Type_2"

    def test_instance_inherits_type_parameters(self):
        """Test that instance inherits parameters from type."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)

        assert inst1.get_parameter("width") == 250.0
        assert inst1.get_parameter("material") == "Concrete"

    def test_instance_parameter_override(self):
        """Test that instance can override type parameters."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)

        # Override the width parameter
        inst1.set_parameter("width", 300.0, override=True)
        assert inst1.get_parameter("width") == 300.0
        assert inst1.is_parameter_overridden("width")

        # Type parameter should remain unchanged
        assert type1.get_parameter("width") == 250.0

    def test_instance_parameter_no_override(self):
        """Test setting instance parameter without override."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)

        # Set instance-specific parameter (not overriding type)
        inst1.set_parameter("custom_prop", "value", override=False)
        assert inst1.get_parameter("custom_prop") == "value"
        assert not inst1.is_parameter_overridden("custom_prop")

    def test_parameter_reset(self):
        """Test resetting parameter to type value."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)

        # Override parameter
        inst1.set_parameter("width", 300.0, override=True)
        assert inst1.get_parameter("width") == 300.0

        # Reset to type value
        inst1.reset_parameter("width")
        assert inst1.get_parameter("width") == 250.0
        assert not inst1.is_parameter_overridden("width")


class TestTypeInstancePropagation:
    """Tests for parameter propagation from type to instances."""

    def test_type_change_propagates_to_instances(self):
        """Test that changing type parameter affects non-overridden instances."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)
        inst2 = MockInstance(type1)

        # Both instances should have type width
        assert inst1.get_parameter("width") == 250.0
        assert inst2.get_parameter("width") == 250.0

        # Change type parameter
        type1.set_parameter("width", 300.0)

        # Both instances should reflect the change
        assert inst1.get_parameter("width") == 300.0
        assert inst2.get_parameter("width") == 300.0

    def test_type_change_does_not_affect_overridden_instances(self):
        """Test that type changes don't affect instances with overrides."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)
        inst2 = MockInstance(type1)

        # Override inst1's width
        inst1.set_parameter("width", 400.0, override=True)

        # Change type parameter
        type1.set_parameter("width", 300.0)

        # inst1 should keep its override
        assert inst1.get_parameter("width") == 400.0
        # inst2 should reflect type change
        assert inst2.get_parameter("width") == 300.0

    def test_geometry_invalidation_on_type_change(self):
        """Test that geometry is invalidated when type changes."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)

        # Build geometry
        geom1 = inst1.get_geometry()
        assert inst1._geometry_valid

        # Change type parameter
        type1.set_parameter("width", 300.0)

        # Geometry should be invalidated
        assert not inst1._geometry_valid

    def test_geometry_invalidation_on_instance_change(self):
        """Test that geometry is invalidated when instance parameter changes."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)

        # Build geometry
        geom1 = inst1.get_geometry()
        assert inst1._geometry_valid

        # Change instance parameter
        inst1.set_parameter("width", 300.0, override=True)

        # Geometry should be invalidated
        assert not inst1._geometry_valid


class TestGeometryManagement:
    """Tests for geometry caching and regeneration."""

    def test_geometry_caching(self):
        """Test that geometry is cached."""
        type1 = MockType("Type A")
        inst1 = MockInstance(type1)

        geom1 = inst1.get_geometry()
        geom2 = inst1.get_geometry()

        # Should return same cached geometry
        assert geom1 == geom2
        assert inst1._geometry_valid

    def test_geometry_force_rebuild(self):
        """Test forcing geometry rebuild."""
        type1 = MockType("Type A")
        inst1 = MockInstance(type1)

        geom1 = inst1.get_geometry()
        geom2 = inst1.get_geometry(force_rebuild=True)

        # Geometry should be rebuilt (different object in real scenario)
        assert inst1._geometry_valid

    def test_geometry_rebuild_after_invalidation(self):
        """Test that geometry is rebuilt after invalidation."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)

        geom1 = inst1.get_geometry()
        assert inst1._geometry_valid

        # Change parameter
        inst1.set_parameter("width", 300.0, override=True)
        assert not inst1._geometry_valid

        # Get geometry again - should rebuild
        geom2 = inst1.get_geometry()
        assert inst1._geometry_valid


class TestCopyParameters:
    """Tests for copy_parameters utility function."""

    def test_copy_all_type_parameters(self):
        """Test copying all parameters from one type to another."""
        type1 = MockType("Type A", width=250.0)
        type1.set_parameter("height", 3000.0)

        type2 = MockType("Type B", width=100.0)

        copy_parameters(type1, type2)

        assert type2.get_parameter("width") == 250.0
        assert type2.get_parameter("height") == 3000.0
        assert type2.get_parameter("material") == "Concrete"

    def test_copy_specific_parameters(self):
        """Test copying specific parameters."""
        type1 = MockType("Type A", width=250.0)
        type1.set_parameter("height", 3000.0)

        type2 = MockType("Type B", width=100.0)

        copy_parameters(type1, type2, param_names=["width"])

        assert type2.get_parameter("width") == 250.0
        assert type2.get_parameter("height") is None  # Not copied

    def test_copy_instance_to_instance(self):
        """Test copying parameters between instances."""
        type1 = MockType("Type A", width=250.0)
        inst1 = MockInstance(type1)
        inst1.set_parameter("custom", "value1")

        inst2 = MockInstance(type1)
        copy_parameters(inst1, inst2, param_names=["custom"])

        assert inst2.get_parameter("custom") == "value1"


class TestMultipleTypes:
    """Tests for multiple types and instances."""

    def test_multiple_independent_types(self):
        """Test that multiple types are independent."""
        type1 = MockType("Type A", width=250.0)
        type2 = MockType("Type B", width=300.0)

        assert type1.get_parameter("width") == 250.0
        assert type2.get_parameter("width") == 300.0

        type1.set_parameter("width", 400.0)

        assert type1.get_parameter("width") == 400.0
        assert type2.get_parameter("width") == 300.0  # Unchanged

    def test_instances_across_types(self):
        """Test instances belonging to different types."""
        type1 = MockType("Type A", width=250.0)
        type2 = MockType("Type B", width=300.0)

        inst1 = MockInstance(type1)
        inst2 = MockInstance(type2)

        assert inst1.get_parameter("width") == 250.0
        assert inst2.get_parameter("width") == 300.0

        assert type1.instance_count == 1
        assert type2.instance_count == 1
