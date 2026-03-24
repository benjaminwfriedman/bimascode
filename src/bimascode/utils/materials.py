"""
Material definition and management for BIM elements.
"""

from enum import Enum
from typing import Any


class MaterialCategory(Enum):
    """Standard material categories."""

    CONCRETE = "Concrete"
    STEEL = "Steel"
    WOOD = "Wood"
    MASONRY = "Masonry"
    GLASS = "Glass"
    INSULATION = "Insulation"
    GYPSUM = "Gypsum"
    METAL = "Metal"
    PLASTIC = "Plastic"
    MEMBRANE = "Membrane"
    FINISH = "Finish"
    OTHER = "Other"


class Material:
    """
    Represents a building material with physical and visual properties.

    Materials can be assigned to BIM elements (walls, floors, etc.) and
    exported to IFC as IfcMaterial with associated properties.
    """

    def __init__(
        self,
        name: str,
        category: MaterialCategory | None = None,
        description: str | None = None,
        # Physical properties
        density: float | None = None,  # kg/m³
        thermal_conductivity: float | None = None,  # W/(m·K)
        specific_heat: float | None = None,  # J/(kg·K)
        # Acoustic properties
        sound_transmission_class: int | None = None,  # STC rating
        # Visual properties
        color: tuple[int, int, int] | None = None,  # RGB (0-255)
        transparency: float = 0.0,  # 0.0 = opaque, 1.0 = transparent
        # Cost and sustainability
        cost_per_unit: float | None = None,  # currency per m³
        embodied_carbon: float | None = None,  # kgCO2e per kg
        recyclable: bool = False,
    ):
        """
        Create a material definition.

        Args:
            name: Material name
            category: Material category
            description: Optional description
            density: Material density in kg/m³
            thermal_conductivity: Thermal conductivity in W/(m·K)
            specific_heat: Specific heat capacity in J/(kg·K)
            sound_transmission_class: STC rating for acoustic performance
            color: RGB color tuple (0-255)
            transparency: Transparency level (0.0-1.0)
            cost_per_unit: Cost per cubic meter
            embodied_carbon: Embodied carbon in kgCO2e per kg
            recyclable: Whether material is recyclable
        """
        self.name = name
        self.category = category if isinstance(category, MaterialCategory) else None
        self.description = description

        # Physical properties
        self.density = density
        self.thermal_conductivity = thermal_conductivity
        self.specific_heat = specific_heat

        # Acoustic properties
        self.sound_transmission_class = sound_transmission_class

        # Visual properties
        self.color = color
        self.transparency = max(0.0, min(1.0, transparency))  # Clamp to 0-1

        # Cost and sustainability
        self.cost_per_unit = cost_per_unit
        self.embodied_carbon = embodied_carbon
        self.recyclable = recyclable

        # Custom properties dictionary
        self._custom_properties: dict[str, Any] = {}

    def set_property(self, name: str, value: Any) -> None:
        """
        Set a custom property on the material.

        Args:
            name: Property name
            value: Property value
        """
        self._custom_properties[name] = value

    def get_property(self, name: str, default: Any = None) -> Any:
        """
        Get a custom property value.

        Args:
            name: Property name
            default: Default value if property not found

        Returns:
            Property value or default
        """
        return self._custom_properties.get(name, default)

    @property
    def properties(self) -> dict[str, Any]:
        """Get all custom properties."""
        return self._custom_properties.copy()

    def to_ifc(self, ifc_file):
        """
        Export this material to IFC as IfcMaterial with properties.

        Args:
            ifc_file: IfcOpenShell file object

        Returns:
            IfcMaterial instance
        """
        # Create the base material
        ifc_material = ifc_file.createIfcMaterial(
            self.name, self.description, self.category.value if self.category else None
        )

        # Create property set for physical properties if any are defined
        properties = []

        if self.density is not None:
            properties.append(
                ifc_file.createIfcPropertySingleValue(
                    "Density",
                    "Material density",
                    ifc_file.createIfcMassDensityMeasure(self.density),
                    None,
                )
            )

        if self.thermal_conductivity is not None:
            properties.append(
                ifc_file.createIfcPropertySingleValue(
                    "ThermalConductivity",
                    "Thermal conductivity",
                    ifc_file.createIfcThermalConductivityMeasure(self.thermal_conductivity),
                    None,
                )
            )

        if self.specific_heat is not None:
            properties.append(
                ifc_file.createIfcPropertySingleValue(
                    "SpecificHeat",
                    "Specific heat capacity",
                    ifc_file.createIfcSpecificHeatCapacityMeasure(self.specific_heat),
                    None,
                )
            )

        if self.sound_transmission_class is not None:
            properties.append(
                ifc_file.createIfcPropertySingleValue(
                    "SoundTransmissionClass",
                    "STC rating",
                    ifc_file.createIfcInteger(self.sound_transmission_class),
                    None,
                )
            )

        if self.cost_per_unit is not None:
            properties.append(
                ifc_file.createIfcPropertySingleValue(
                    "CostPerUnit",
                    "Cost per cubic meter",
                    ifc_file.createIfcReal(self.cost_per_unit),
                    None,
                )
            )

        if self.embodied_carbon is not None:
            properties.append(
                ifc_file.createIfcPropertySingleValue(
                    "EmbodiedCarbon",
                    "Embodied carbon kgCO2e per kg",
                    ifc_file.createIfcReal(self.embodied_carbon),
                    None,
                )
            )

        properties.append(
            ifc_file.createIfcPropertySingleValue(
                "Recyclable",
                "Whether material is recyclable",
                ifc_file.createIfcBoolean(self.recyclable),
                None,
            )
        )

        # Add custom properties
        for key, value in self._custom_properties.items():
            if isinstance(value, bool):
                ifc_value = ifc_file.createIfcBoolean(value)
            elif isinstance(value, int):
                ifc_value = ifc_file.createIfcInteger(value)
            elif isinstance(value, float):
                ifc_value = ifc_file.createIfcReal(value)
            elif isinstance(value, str):
                ifc_value = ifc_file.createIfcLabel(value)
            else:
                ifc_value = ifc_file.createIfcLabel(str(value))

            properties.append(
                ifc_file.createIfcPropertySingleValue(
                    key, f"Custom property: {key}", ifc_value, None
                )
            )

        # Create property set if we have properties
        if properties:
            ifc_file.createIfcMaterialProperties(
                self.name + "_Properties", self.description, properties, ifc_material
            )

        return ifc_material

    def __repr__(self) -> str:
        props = []
        if self.category:
            props.append(f"category={self.category.value}")
        if self.density:
            props.append(f"density={self.density}kg/m³")
        if self.thermal_conductivity:
            props.append(f"k={self.thermal_conductivity}W/(m·K)")

        props_str = ", ".join(props) if props else "no properties"
        return f"Material('{self.name}', {props_str})"


# Pre-defined material library
class MaterialLibrary:
    """Common building materials with typical properties."""

    @staticmethod
    def concrete(strength: str = "C30/37") -> Material:
        """
        Standard structural concrete.

        Args:
            strength: Concrete strength grade (e.g., "C30/37")
        """
        return Material(
            name=f"Concrete {strength}",
            category=MaterialCategory.CONCRETE,
            description=f"Structural concrete, strength class {strength}",
            density=2400,  # kg/m³
            thermal_conductivity=1.4,  # W/(m·K)
            specific_heat=880,  # J/(kg·K)
            color=(192, 192, 192),  # Gray
            embodied_carbon=0.15,  # kgCO2e/kg (typical for concrete)
            recyclable=True,
        )

    @staticmethod
    def steel(grade: str = "S355") -> Material:
        """
        Structural steel.

        Args:
            grade: Steel grade (e.g., "S355", "A36")
        """
        return Material(
            name=f"Steel {grade}",
            category=MaterialCategory.STEEL,
            description=f"Structural steel, grade {grade}",
            density=7850,  # kg/m³
            thermal_conductivity=50,  # W/(m·K)
            specific_heat=490,  # J/(kg·K)
            color=(128, 128, 128),  # Dark gray
            embodied_carbon=2.5,  # kgCO2e/kg (typical for steel)
            recyclable=True,
        )

    @staticmethod
    def timber(species: str = "Spruce") -> Material:
        """
        Structural timber.

        Args:
            species: Wood species
        """
        return Material(
            name=f"{species} Timber",
            category=MaterialCategory.WOOD,
            description=f"Structural timber - {species}",
            density=450,  # kg/m³ (typical for softwood)
            thermal_conductivity=0.13,  # W/(m·K)
            specific_heat=1600,  # J/(kg·K)
            color=(210, 180, 140),  # Tan
            embodied_carbon=-0.5,  # Negative carbon (carbon storage)
            recyclable=True,
        )

    @staticmethod
    def brick() -> Material:
        """Standard clay brick."""
        return Material(
            name="Clay Brick",
            category=MaterialCategory.MASONRY,
            description="Standard clay brick for masonry construction",
            density=1920,  # kg/m³
            thermal_conductivity=0.77,  # W/(m·K)
            specific_heat=840,  # J/(kg·K)
            color=(178, 34, 34),  # Firebrick red
            embodied_carbon=0.24,  # kgCO2e/kg
            recyclable=True,
        )

    @staticmethod
    def glass(glass_type: str = "standard") -> Material:
        """
        Architectural glass.

        Args:
            glass_type: Type of glass ("standard", "low-e", "laminated")
        """
        return Material(
            name=f"Glass - {glass_type}",
            category=MaterialCategory.GLASS,
            description=f"Architectural glass - {glass_type}",
            density=2500,  # kg/m³
            thermal_conductivity=1.0,  # W/(m·K)
            specific_heat=840,  # J/(kg·K)
            color=(200, 230, 255),  # Light blue
            transparency=0.7,
            embodied_carbon=0.85,  # kgCO2e/kg
            recyclable=True,
        )

    @staticmethod
    def insulation_mineral_wool() -> Material:
        """Mineral wool insulation."""
        return Material(
            name="Mineral Wool Insulation",
            category=MaterialCategory.INSULATION,
            description="Mineral wool batt insulation",
            density=30,  # kg/m³
            thermal_conductivity=0.035,  # W/(m·K) - excellent insulator
            specific_heat=840,  # J/(kg·K)
            color=(255, 255, 200),  # Light yellow
            embodied_carbon=1.2,  # kgCO2e/kg
            recyclable=True,
        )

    @staticmethod
    def gypsum_board() -> Material:
        """Standard gypsum wallboard."""
        return Material(
            name="Gypsum Board",
            category=MaterialCategory.GYPSUM,
            description="Standard gypsum wallboard (drywall)",
            density=800,  # kg/m³
            thermal_conductivity=0.25,  # W/(m·K)
            specific_heat=1090,  # J/(kg·K)
            color=(255, 255, 255),  # White
            embodied_carbon=0.39,  # kgCO2e/kg
            recyclable=True,
        )
