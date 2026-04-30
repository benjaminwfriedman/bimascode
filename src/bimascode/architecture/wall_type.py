"""
Wall types with compound layer stacks.

This module implements the WallType class which defines wall assemblies
with multiple material layers. Each layer has a material, thickness,
and functional role (structural, insulation, finish, etc.).
"""

from enum import Enum
from typing import TYPE_CHECKING

from build123d import Box, Compound, Location

from bimascode.core.type_instance import ElementType
from bimascode.utils.materials import Material
from bimascode.utils.units import Length, normalize_length

if TYPE_CHECKING:
    from bimascode.architecture.wall import Wall


class WallFunction(Enum):
    """
    Classification of wall function/purpose.

    Aligns with Revit's wall function system for proper filtering
    in views and schedules.
    """

    EXTERIOR = "Exterior"  # External envelope walls
    INTERIOR = "Interior"  # Internal partition walls
    FOUNDATION = "Foundation"  # Below-grade foundation walls
    RETAINING = "Retaining"  # Earth-retaining walls
    SOFFIT = "Soffit"  # Horizontal wall elements (undersides of overhangs)
    CORE_SHAFT = "Core-Shaft"  # Elevator/stair shaft enclosure walls


class LayerFunction(Enum):
    """
    Functional role of a material layer in a wall assembly.
    """

    STRUCTURE = "Structure"  # Load-bearing layer
    SUBSTRATE = "Substrate"  # Backing/sheathing
    THERMAL_INSULATION = "Thermal Insulation"
    AIR_BARRIER = "Air Barrier"
    VAPOR_BARRIER = "Vapor Barrier"
    FINISH_EXTERIOR = "Finish - Exterior"
    FINISH_INTERIOR = "Finish - Interior"
    MEMBRANE = "Membrane"  # Waterproofing, etc.
    OTHER = "Other"


class Layer:
    """
    A single material layer in a wall assembly.

    Each layer has a material, thickness, and functional role.
    Layers are stacked from exterior to interior.
    """

    def __init__(
        self,
        material: Material,
        thickness: Length | float,
        function: LayerFunction = LayerFunction.OTHER,
        structural: bool = False,
        description: str | None = None,
    ):
        """
        Create a material layer.

        Args:
            material: Material for this layer
            thickness: Layer thickness (in mm or Length)
            function: Functional role of this layer
            structural: Whether this layer is load-bearing
            description: Optional description
        """
        self.material = material
        self.thickness = normalize_length(thickness)
        self.function = function
        self.structural = structural
        self.description = description or f"{material.name} - {function.value}"

    @property
    def thickness_mm(self) -> float:
        """Get thickness in millimeters."""
        return self.thickness.mm

    def __repr__(self) -> str:
        return f"Layer({self.material.name}, {self.thickness_mm}mm, {self.function.value})"


class WallType(ElementType):
    """
    Wall type defining a compound layer stack.

    A wall type consists of multiple material layers stacked from
    exterior to interior. The total width is the sum of all layer
    thicknesses.
    """

    def __init__(
        self,
        name: str,
        layers: list[Layer] | None = None,
        description: str | None = None,
        function: WallFunction = WallFunction.INTERIOR,
    ):
        """
        Create a wall type.

        Args:
            name: Name for this wall type
            layers: List of layers from exterior to interior
            description: Optional description
            function: Wall function classification (default: INTERIOR)
        """
        super().__init__(name)
        self.layers = layers or []
        self.description = description
        self._function = function

        # Store total width as a parameter
        self._update_width()

    def add_layer(
        self,
        material: Material,
        thickness: Length | float,
        function: LayerFunction = LayerFunction.OTHER,
        structural: bool = False,
        position: int | None = None,
    ) -> Layer:
        """
        Add a material layer to the wall assembly.

        Args:
            material: Material for this layer
            thickness: Layer thickness
            function: Functional role of this layer
            structural: Whether layer is load-bearing
            position: Position to insert layer (0=exterior, None=interior)

        Returns:
            The created Layer object
        """
        layer = Layer(material, thickness, function, structural)

        if position is None:
            self.layers.append(layer)
        else:
            self.layers.insert(position, layer)

        self._update_width()
        return layer

    def remove_layer(self, index: int) -> None:
        """
        Remove a layer by index.

        Args:
            index: Layer index (0 = exterior face)
        """
        if 0 <= index < len(self.layers):
            self.layers.pop(index)
            self._update_width()

    def get_layer(self, index: int) -> Layer:
        """
        Get a layer by index.

        Args:
            index: Layer index (0 = exterior face)

        Returns:
            Layer at the specified index
        """
        return self.layers[index]

    @property
    def layer_count(self) -> int:
        """Get the number of layers."""
        return len(self.layers)

    @property
    def total_width(self) -> Length:
        """Get the total wall width (sum of all layers)."""
        return Length(sum(layer.thickness_mm for layer in self.layers), "mm")

    @property
    def total_width_mm(self) -> float:
        """Get total wall width in millimeters."""
        return self.total_width.mm

    def _update_width(self) -> None:
        """Update the width parameter based on layer thicknesses."""
        self.set_parameter("width", self.total_width_mm)

    def get_structural_layers(self) -> list[Layer]:
        """Get all structural layers."""
        return [layer for layer in self.layers if layer.structural]

    @property
    def function(self) -> WallFunction:
        """Get the wall function classification."""
        return self._function

    @function.setter
    def function(self, value: WallFunction) -> None:
        """Set the wall function classification."""
        self._function = value

    def get_ifc_predefined_type(self) -> str:
        """
        Get the IFC predefined type based on wall function.

        Maps WallFunction to appropriate IfcWall predefined types.

        Returns:
            IFC predefined type string
        """
        mapping = {
            WallFunction.EXTERIOR: "PARTITIONING",
            WallFunction.INTERIOR: "PARTITIONING",
            WallFunction.FOUNDATION: "SOLIDWALL",
            WallFunction.RETAINING: "SOLIDWALL",
            WallFunction.SOFFIT: "PARTITIONING",
            WallFunction.CORE_SHAFT: "SHEAR",
        }
        return mapping.get(self._function, "NOTDEFINED")

    def get_layers_by_function(self, function: LayerFunction) -> list[Layer]:
        """
        Get all layers with a specific function.

        Args:
            function: Layer function to filter by

        Returns:
            List of layers with the specified function
        """
        return [layer for layer in self.layers if layer.function == function]

    def create_geometry(self, instance: "Wall") -> Compound:
        """
        Create 3D geometry for a wall instance.

        The wall is created as a compound of boxes, one for each layer.
        Layers are positioned from exterior to interior.

        IMPORTANT: Geometry is created in LOCAL coordinates:
        - Origin at wall start point
        - X-axis along wall length direction
        - Y-axis perpendicular (toward interior)
        - Z-axis upward

        The IFC placement (in wall.py) handles world positioning.

        Args:
            instance: Wall instance to create geometry for

        Returns:
            build123d Compound representing the wall
        """

        # Get wall parameters
        start_point = instance.get_parameter("start_point")
        end_point = instance.get_parameter("end_point")
        height = instance.get_parameter("height", 3000.0)  # Default 3m

        if start_point is None or end_point is None:
            raise ValueError("Wall must have start_point and end_point")

        # Calculate wall length
        import math

        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        length = math.sqrt(dx * dx + dy * dy)

        # Create layer geometries in LOCAL coordinates
        # X = along wall length (0 to length)
        # Y = perpendicular to wall (layers stack in Y direction)
        # Z = height (0 to height)
        layer_solids = []
        current_offset = 0.0

        for layer in self.layers:
            # Create box for this layer
            layer_box = Box(length, layer.thickness_mm, height)

            # Position the layer in local coordinates:
            # - X: center along wall length (length/2)
            # - Y: centered on wall centerline (Y=0 is centerline)
            #      Wall extends from Y = -total_width/2 to Y = +total_width/2
            # - Z: center at half height
            total_width = sum(lyr.thickness_mm for lyr in self.layers)
            half_total = total_width / 2.0
            layer_y_offset = current_offset + layer.thickness_mm / 2 - half_total

            loc = Location(
                (length / 2, layer_y_offset, height / 2),
                (0, 0, 1),
                0,  # No rotation - geometry is in local coords
            )

            layer_box = layer_box.locate(loc)
            layer_solids.append(layer_box)

            current_offset += layer.thickness_mm

        # Create wall compound
        wall_compound = Compound(children=layer_solids)

        # Apply boolean subtraction for hosted element openings
        if hasattr(instance, "openings") and instance.openings:
            for opening in instance.openings:
                try:
                    wall_compound = wall_compound - opening
                except Exception:
                    # Boolean operation failed - skip this opening
                    # This can happen with edge cases in geometry
                    pass

        return wall_compound

    def to_ifc(self, ifc_file):
        """
        Export wall type to IFC as IfcMaterialLayerSet.

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
                Priority=i + 1,
            )
            ifc_layers.append(ifc_layer)

        # Create material layer set
        ifc_layer_set = ifc_file.create_entity(
            "IfcMaterialLayerSet",
            MaterialLayers=ifc_layers,
            LayerSetName=self.name,
            Description=self.description,
        )

        return ifc_layer_set

    def __repr__(self) -> str:
        return f"WallType(name='{self.name}', layers={self.layer_count}, width={self.total_width_mm:.1f}mm)"


# Common wall type constructors
def create_basic_wall_type(
    name: str,
    thickness: Length | float,
    material: Material,
    function: WallFunction = WallFunction.INTERIOR,
) -> WallType:
    """
    Create a simple single-layer wall type.

    Args:
        name: Wall type name
        thickness: Wall thickness
        material: Wall material
        function: Wall function classification (default: INTERIOR)

    Returns:
        WallType with single layer
    """
    wall_type = WallType(name, function=function)
    wall_type.add_layer(
        material=material, thickness=thickness, function=LayerFunction.STRUCTURE, structural=True
    )
    return wall_type


def create_stud_wall_type(
    name: str,
    stud_material: Material,
    stud_depth: Length | float = 90.0,
    interior_finish: Material | None = None,
    interior_finish_thickness: Length | float = 12.5,
    exterior_finish: Material | None = None,
    exterior_finish_thickness: Length | float = 12.5,
    function: WallFunction = WallFunction.INTERIOR,
) -> WallType:
    """
    Create a typical stud wall type with finishes.

    Args:
        name: Wall type name
        stud_material: Material for structural studs
        stud_depth: Depth of stud cavity (default 90mm)
        interior_finish: Interior finish material (e.g., gypsum board)
        interior_finish_thickness: Interior finish thickness
        exterior_finish: Exterior finish material
        exterior_finish_thickness: Exterior finish thickness
        function: Wall function classification (default: INTERIOR)

    Returns:
        WallType with multiple layers
    """

    wall_type = WallType(name, description=f"{name} - Wood Stud Wall", function=function)

    # Exterior finish
    if exterior_finish:
        wall_type.add_layer(
            material=exterior_finish,
            thickness=exterior_finish_thickness,
            function=LayerFunction.FINISH_EXTERIOR,
        )

    # Structural studs
    wall_type.add_layer(
        material=stud_material,
        thickness=stud_depth,
        function=LayerFunction.STRUCTURE,
        structural=True,
    )

    # Interior finish
    if interior_finish:
        wall_type.add_layer(
            material=interior_finish,
            thickness=interior_finish_thickness,
            function=LayerFunction.FINISH_INTERIOR,
        )

    return wall_type
