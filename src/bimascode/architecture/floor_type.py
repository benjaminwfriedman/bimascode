"""
Floor/Slab types with compound layer stacks.

Similar to WallType, FloorType defines horizontal assemblies
with multiple material layers (structural slab, insulation, finish, etc.).
"""

from typing import List, Optional
from bimascode.core.type_instance import ElementType
from bimascode.architecture.wall_type import Layer, LayerFunction
from bimascode.utils.materials import Material
from bimascode.utils.units import Length, normalize_length
from build123d import Box, Location, Compound, extrude, Polygon, Plane


class FloorType(ElementType):
    """
    Floor type defining a compound layer stack.

    Similar to walls, floors consist of multiple layers stacked
    from bottom to top. Total thickness is the sum of all layer thicknesses.
    """

    def __init__(
        self,
        name: str,
        layers: Optional[List[Layer]] = None,
        description: Optional[str] = None
    ):
        """
        Create a floor type.

        Args:
            name: Name for this floor type
            layers: List of layers from bottom to top
            description: Optional description
        """
        super().__init__(name)
        self.layers = layers or []
        self.description = description

        # Store total thickness as a parameter
        self._update_thickness()

    def add_layer(
        self,
        material: Material,
        thickness: Length | float,
        function: LayerFunction = LayerFunction.OTHER,
        structural: bool = False,
        position: Optional[int] = None
    ) -> Layer:
        """
        Add a material layer to the floor assembly.

        Args:
            material: Material for this layer
            thickness: Layer thickness
            function: Functional role of this layer
            structural: Whether layer is load-bearing
            position: Position to insert layer (0=bottom, None=top)

        Returns:
            The created Layer object
        """
        layer = Layer(material, thickness, function, structural)

        if position is None:
            self.layers.append(layer)
        else:
            self.layers.insert(position, layer)

        self._update_thickness()
        return layer

    def remove_layer(self, index: int) -> None:
        """
        Remove a layer by index.

        Args:
            index: Layer index (0 = bottom)
        """
        if 0 <= index < len(self.layers):
            self.layers.pop(index)
            self._update_thickness()

    def get_layer(self, index: int) -> Layer:
        """
        Get a layer by index.

        Args:
            index: Layer index (0 = bottom)

        Returns:
            Layer at the specified index
        """
        return self.layers[index]

    @property
    def layer_count(self) -> int:
        """Get the number of layers."""
        return len(self.layers)

    @property
    def total_thickness(self) -> Length:
        """Get the total floor thickness (sum of all layers)."""
        return Length(sum(layer.thickness_mm for layer in self.layers), "mm")

    @property
    def total_thickness_mm(self) -> float:
        """Get total floor thickness in millimeters."""
        return self.total_thickness.mm

    def _update_thickness(self) -> None:
        """Update the thickness parameter based on layer thicknesses."""
        self.set_parameter("thickness", self.total_thickness_mm)

    def get_structural_layers(self) -> List[Layer]:
        """Get all structural layers."""
        return [layer for layer in self.layers if layer.structural]

    def get_layers_by_function(self, function: LayerFunction) -> List[Layer]:
        """
        Get all layers with a specific function.

        Args:
            function: Layer function to filter by

        Returns:
            List of layers with the specified function
        """
        return [layer for layer in self.layers if layer.function == function]

    def create_geometry(self, instance: 'Floor') -> Compound:
        """
        Create 3D geometry for a floor instance.

        The floor is created as a compound of extruded polygons,
        one for each layer. Layers are stacked from bottom to top.

        Args:
            instance: Floor instance to create geometry for

        Returns:
            build123d Compound representing the floor
        """
        from bimascode.architecture.floor import Floor  # Avoid circular import

        # Get floor parameters
        boundary = instance.get_parameter("boundary")
        slope = instance.get_parameter("slope", 0.0)  # degrees

        if boundary is None:
            raise ValueError("Floor must have a boundary polygon")

        # Create layer geometries
        layer_solids = []
        current_z = 0.0

        for layer in self.layers:
            # Extrude the boundary polygon for this layer
            # For now, simple extrusion (slope support can be added later)
            poly = Polygon(*boundary)
            layer_solid = extrude(poly, amount=layer.thickness_mm)

            # Position the layer vertically
            layer_solid = layer_solid.locate(Location((0, 0, current_z)))
            layer_solids.append(layer_solid)

            current_z += layer.thickness_mm

        # Create floor compound
        floor_compound = Compound(children=layer_solids)

        # Apply boolean subtraction for openings
        if hasattr(instance, 'openings') and instance.openings:
            for opening in instance.openings:
                try:
                    opening_geom = opening.get_opening_geometry()
                    floor_compound = floor_compound - opening_geom
                except Exception:
                    # Boolean operation failed - skip this opening
                    pass

        return floor_compound

    def to_ifc(self, ifc_file):
        """
        Export floor type to IFC as IfcMaterialLayerSet.

        Args:
            ifc_file: IFC file object

        Returns:
            IfcMaterialLayerSet
        """
        # Create IFC material layers
        ifc_layers = []
        for i, layer in enumerate(self.layers):
            # Create IFC material for layer
            ifc_material = layer.material.to_ifc(ifc_file)

            # Create material layer
            ifc_layer = ifc_file.create_entity(
                "IfcMaterialLayer",
                Material=ifc_material,
                LayerThickness=layer.thickness_mm,
                IsVentilated=False,
                Name=layer.description,
                Category=layer.function.value,
                Priority=i + 1
            )
            ifc_layers.append(ifc_layer)

        # Create material layer set
        ifc_layer_set = ifc_file.create_entity(
            "IfcMaterialLayerSet",
            MaterialLayers=ifc_layers,
            LayerSetName=self.name,
            Description=self.description
        )

        return ifc_layer_set

    def __repr__(self) -> str:
        return f"FloorType(name='{self.name}', layers={self.layer_count}, thickness={self.total_thickness_mm:.1f}mm)"


# Common floor type constructors
def create_basic_floor_type(
    name: str,
    thickness: Length | float,
    material: Material
) -> FloorType:
    """
    Create a simple single-layer floor type.

    Args:
        name: Floor type name
        thickness: Floor thickness
        material: Floor material

    Returns:
        FloorType with single layer
    """
    floor_type = FloorType(name)
    floor_type.add_layer(
        material=material,
        thickness=thickness,
        function=LayerFunction.STRUCTURE,
        structural=True
    )
    return floor_type


def create_concrete_floor_type(
    name: str,
    slab_thickness: Length | float = 200.0,
    concrete_material: Optional[Material] = None,
    topping_thickness: Length | float = 50.0,
    topping_material: Optional[Material] = None
) -> FloorType:
    """
    Create a typical concrete floor with structural slab and topping.

    Args:
        name: Floor type name
        slab_thickness: Structural slab thickness (default 200mm)
        concrete_material: Concrete material for slab
        topping_thickness: Screed/topping thickness (default 50mm)
        topping_material: Topping material

    Returns:
        FloorType with concrete slab and topping
    """
    from bimascode.utils.materials import MaterialLibrary

    floor_type = FloorType(name, description=f"{name} - Concrete Floor")

    # Structural slab
    if concrete_material is None:
        concrete_material = MaterialLibrary.concrete()

    floor_type.add_layer(
        material=concrete_material,
        thickness=slab_thickness,
        function=LayerFunction.STRUCTURE,
        structural=True
    )

    # Topping/screed
    if topping_material:
        floor_type.add_layer(
            material=topping_material,
            thickness=topping_thickness,
            function=LayerFunction.FINISH_INTERIOR
        )

    return floor_type
