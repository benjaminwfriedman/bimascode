"""
Building / Site Hierarchy implementation.
"""

from typing import Optional, List, Union

from ..core.element import Element
from ..utils.units import UnitSystem, LengthUnit


class Building(Element):
    """
    Represents the root building object and IFC project hierarchy.

    Creates the full IFC scaffolding:
    IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey (levels)
    """

    def __init__(
        self,
        name: str,
        address: Optional[str] = None,
        description: Optional[str] = None,
        unit_system: Union[str, UnitSystem] = UnitSystem.METRIC
    ):
        """
        Create a new building.

        Args:
            name: Building name
            address: Building address
            description: Optional description
            unit_system: Unit system to use ('metric' or 'imperial')
        """
        super().__init__(name=name, description=description)

        self.address = address

        # Unit system
        if isinstance(unit_system, str):
            unit_system = UnitSystem(unit_system)
        self._unit_system = unit_system

        # Set default length unit based on system
        if unit_system == UnitSystem.METRIC:
            self._length_unit = LengthUnit.MILLIMETER
        else:
            self._length_unit = LengthUnit.INCH

        # Collections
        self._levels: List["Level"] = []  # noqa: F821
        self._grids: List = []
        self._elements: List = []

        # IFC entities (populated during export)
        self._ifc_file = None
        self._ifc_project = None
        self._ifc_site = None
        self._ifc_building = None
        self._ifc_owner_history = None

    @property
    def unit_system(self) -> UnitSystem:
        """Get the building's unit system."""
        return self._unit_system

    @property
    def length_unit(self) -> LengthUnit:
        """Get the default length unit for this building."""
        return self._length_unit

    @property
    def levels(self) -> List["Level"]:  # noqa: F821
        """Get all levels in the building."""
        return self._levels.copy()

    @property
    def grids(self) -> List:
        """Get all grid lines in the building."""
        return self._grids.copy()

    def _add_level(self, level: "Level") -> None:  # noqa: F821
        """
        Internal method to register a level with the building.

        Args:
            level: Level to add
        """
        if level not in self._levels:
            self._levels.append(level)

    def get_level(self, name: str) -> Optional["Level"]:  # noqa: F821
        """
        Get a level by name.

        Args:
            name: Level name

        Returns:
            Level if found, None otherwise
        """
        for level in self._levels:
            if level.name == name:
                return level
        return None

    @classmethod
    def from_ifc(cls, filepath: str) -> "Building":
        """
        Create a Building instance by importing from an IFC file.

        Args:
            filepath: Path to IFC file

        Returns:
            Building instance with imported elements

        Raises:
            ImportError: If ifcopenshell is not installed
            FileNotFoundError: If IFC file doesn't exist
            ValueError: If IFC file has invalid structure
        """
        from ..export.ifc_importer import IFCImporter

        importer = IFCImporter()
        return importer.import_building(filepath)

    def export_ifc(self, filepath: str, schema: str = "IFC4") -> None:
        """
        Export the building to an IFC file.

        Args:
            filepath: Output file path
            schema: IFC schema version (default: IFC4)
        """
        from ..export.ifc_exporter import IFCExporter

        exporter = IFCExporter(schema=schema)
        exporter.export(self, filepath)

    def get_rooms(self) -> List:
        """
        Get all rooms in the building across all levels.

        Returns:
            List of Room objects
        """
        from ..spatial.room import Room

        rooms = []
        for level in self._levels:
            for element in level.elements:
                if isinstance(element, Room):
                    rooms.append(element)
        return rooms

    def room_schedule(self):
        """
        Generate a room schedule as a pandas DataFrame.

        Returns a DataFrame with columns:
        - number: Room number
        - name: Room name
        - level: Level name
        - area_m2: Area in square meters
        - area_sqft: Area in square feet
        - volume_m3: Volume in cubic meters
        - height_m: Floor-to-ceiling height in meters
        - perimeter_m: Perimeter in meters
        - floor_finish: Floor finish description
        - wall_finish: Wall finish description
        - ceiling_finish: Ceiling finish description

        Returns:
            pandas DataFrame with room schedule

        Raises:
            ImportError: If pandas is not installed
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for room_schedule(). Install with: pip install pandas")

        rooms = self.get_rooms()

        if not rooms:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=[
                "number", "name", "level", "area_m2", "area_sqft",
                "volume_m3", "height_m", "perimeter_m",
                "floor_finish", "wall_finish", "ceiling_finish"
            ])

        # Convert rooms to dictionaries
        data = [room.to_dict() for room in rooms]

        # Create DataFrame
        df = pd.DataFrame(data)

        # Sort by level and room number
        df = df.sort_values(by=["level", "number"])

        return df

    def __repr__(self) -> str:
        return f"Building(name='{self.name}', levels={len(self._levels)})"
