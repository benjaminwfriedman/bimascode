"""
IFC import functionality for reading existing IFC files into BIM as Code models.
"""

from typing import Optional, List
from pathlib import Path


class IFCImporter:
    """
    Handles import of IFC files into BIM as Code model structures.

    Reads existing IFC files and reconstructs Building, Level, Grid,
    and other BIM elements.
    """

    def __init__(self):
        """Initialize the IFC importer."""
        self._ifc_file = None

    def import_building(self, filepath: str) -> "Building":
        """
        Import a building from an IFC file.

        Args:
            filepath: Path to IFC file

        Returns:
            Building instance with all imported elements

        Raises:
            ImportError: If ifcopenshell is not installed
            FileNotFoundError: If IFC file doesn't exist
            ValueError: If IFC file has invalid structure
        """
        try:
            import ifcopenshell
        except ImportError:
            raise ImportError(
                "ifcopenshell is required for IFC import. "
                "Install it with: pip install ifcopenshell"
            )

        # Check file exists
        if not Path(filepath).exists():
            raise FileNotFoundError(f"IFC file not found: {filepath}")

        # Open IFC file
        self._ifc_file = ifcopenshell.open(filepath)

        # Find the building entity
        ifc_buildings = self._ifc_file.by_type("IfcBuilding")
        if not ifc_buildings:
            raise ValueError("No IfcBuilding found in IFC file")

        # For now, import the first building
        ifc_building = ifc_buildings[0]

        # Create Building instance
        from ..spatial.building import Building
        from ..utils.units import UnitSystem

        # Determine unit system from IFC
        unit_system = self._get_unit_system()

        # Create building
        building = Building(
            name=ifc_building.Name or "Imported Building",
            address=self._get_address(ifc_building),
            description=ifc_building.Description,
            unit_system=unit_system
        )

        # Set GUID to maintain identity
        building._guid = ifc_building.GlobalId

        # Import levels (building storeys)
        self._import_levels(building, ifc_building)

        # Import grids
        self._import_grids(building)

        return building

    def _get_unit_system(self) -> str:
        """
        Determine the unit system from IFC file.

        Returns:
            "metric" or "imperial"
        """
        # Get project
        projects = self._ifc_file.by_type("IfcProject")
        if not projects:
            return "metric"  # Default

        project = projects[0]
        if not hasattr(project, 'UnitsInContext') or not project.UnitsInContext:
            return "metric"

        # Check length units
        for unit in project.UnitsInContext.Units:
            if hasattr(unit, 'UnitType') and unit.UnitType == 'LENGTHUNIT':
                if hasattr(unit, 'Name'):
                    if unit.Name == 'FOOT' or unit.Name == 'INCH':
                        return "imperial"
                    elif unit.Name == 'METRE' or unit.Name == 'MILLIMETRE':
                        return "metric"

        return "metric"  # Default

    def _get_address(self, ifc_building) -> Optional[str]:
        """
        Extract address from IFC building.

        Args:
            ifc_building: IfcBuilding entity

        Returns:
            Address string or None
        """
        if not hasattr(ifc_building, 'BuildingAddress') or not ifc_building.BuildingAddress:
            return None

        address = ifc_building.BuildingAddress

        # Try to build address from components
        address_parts = []

        if hasattr(address, 'AddressLines') and address.AddressLines:
            address_parts.extend(address.AddressLines)

        if hasattr(address, 'Town') and address.Town:
            address_parts.append(address.Town)

        if hasattr(address, 'PostalCode') and address.PostalCode:
            address_parts.append(address.PostalCode)

        if hasattr(address, 'Country') and address.Country:
            address_parts.append(address.Country)

        return ", ".join(address_parts) if address_parts else None

    def _import_levels(self, building: "Building", ifc_building) -> None:
        """
        Import building storeys as Level objects.

        Args:
            building: Building instance to add levels to
            ifc_building: IfcBuilding entity
        """
        from ..spatial.level import Level
        from ..utils.units import Length

        # Find all building storeys contained in this building
        storeys = []

        # Get storeys through spatial decomposition
        if hasattr(ifc_building, 'IsDecomposedBy'):
            for rel in ifc_building.IsDecomposedBy:
                if hasattr(rel, 'RelatedObjects'):
                    for obj in rel.RelatedObjects:
                        if obj.is_a("IfcBuildingStorey"):
                            storeys.append(obj)

        # Create Level objects
        for storey in storeys:
            # Get elevation
            elevation_mm = 0.0
            if hasattr(storey, 'Elevation') and storey.Elevation is not None:
                elevation_mm = float(storey.Elevation)

            # Create level
            level = Level(
                building,
                name=storey.Name or "Unnamed Level",
                elevation=Length(elevation_mm, "mm"),
                description=storey.Description
            )

            # Preserve GUID
            level._guid = storey.GlobalId

    def _import_grids(self, building: "Building") -> None:
        """
        Import grid lines from IFC.

        Args:
            building: Building instance to add grids to
        """
        from ..spatial.grid import GridLine

        # Find all grids in the file
        ifc_grids = self._ifc_file.by_type("IfcGrid")

        for ifc_grid in ifc_grids:
            # Import U axes (vertical grids)
            if hasattr(ifc_grid, 'UAxes') and ifc_grid.UAxes:
                for axis in ifc_grid.UAxes:
                    self._import_grid_axis(building, axis)

            # Import V axes (horizontal grids)
            if hasattr(ifc_grid, 'VAxes') and ifc_grid.VAxes:
                for axis in ifc_grid.VAxes:
                    self._import_grid_axis(building, axis)

            # Import W axes if present
            if hasattr(ifc_grid, 'WAxes') and ifc_grid.WAxes:
                for axis in ifc_grid.WAxes:
                    self._import_grid_axis(building, axis)

    def _import_grid_axis(self, building: "Building", axis) -> None:
        """
        Import a single grid axis.

        Args:
            building: Building instance
            axis: IfcGridAxis entity
        """
        from ..spatial.grid import GridLine

        # Get axis curve
        if not hasattr(axis, 'AxisCurve'):
            return

        curve = axis.AxisCurve

        # Handle polyline (most common for grid axes)
        if curve.is_a("IfcPolyline"):
            if not hasattr(curve, 'Points') or len(curve.Points) < 2:
                return

            # Get start and end points
            start_point = curve.Points[0]
            end_point = curve.Points[-1]

            if not (hasattr(start_point, 'Coordinates') and hasattr(end_point, 'Coordinates')):
                return

            start_coords = start_point.Coordinates
            end_coords = end_point.Coordinates

            # Create grid line (coordinates are in mm from IFC)
            grid_line = GridLine(
                building,
                label=axis.AxisTag or "?",
                start_point=(float(start_coords[0]), float(start_coords[1])),
                end_point=(float(end_coords[0]), float(end_coords[1]))
            )

    def get_info(self, filepath: str) -> dict:
        """
        Get information about an IFC file without full import.

        Args:
            filepath: Path to IFC file

        Returns:
            Dictionary with file information
        """
        try:
            import ifcopenshell
        except ImportError:
            return {"error": "ifcopenshell not installed"}

        if not Path(filepath).exists():
            return {"error": "File not found"}

        try:
            ifc_file = ifcopenshell.open(filepath)

            # Collect information
            projects = ifc_file.by_type("IfcProject")
            buildings = ifc_file.by_type("IfcBuilding")
            storeys = ifc_file.by_type("IfcBuildingStorey")
            grids = ifc_file.by_type("IfcGrid")
            materials = ifc_file.by_type("IfcMaterial")

            info = {
                "schema": ifc_file.schema,
                "projects": len(projects),
                "buildings": len(buildings),
                "storeys": len(storeys),
                "grids": len(grids),
                "materials": len(materials)
            }

            # Add building names
            if buildings:
                info["building_names"] = [b.Name for b in buildings if hasattr(b, 'Name')]

            # Add storey names
            if storeys:
                info["storey_names"] = [s.Name for s in storeys if hasattr(s, 'Name')]

            return info

        except Exception as e:
            return {"error": str(e)}


# Convenience method for Building class
def import_from_ifc(filepath: str) -> "Building":
    """
    Import a building from an IFC file.

    This is a convenience function that can be used as:
        building = import_from_ifc("path/to/file.ifc")

    Args:
        filepath: Path to IFC file

    Returns:
        Building instance

    Raises:
        Various exceptions from IFCImporter
    """
    importer = IFCImporter()
    return importer.import_building(filepath)
