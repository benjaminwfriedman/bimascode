"""
IFC export functionality for BIM as Code models.
"""

import time
from typing import TYPE_CHECKING, Optional
from pathlib import Path

if TYPE_CHECKING:
    from ..spatial.building import Building


class IFCExporter:
    """
    Handles export of BIM as Code models to IFC format.

    This class encapsulates all IFC-specific export logic, creating
    proper IFC project hierarchies and entity relationships.
    """

    def __init__(self, schema: str = "IFC4"):
        """
        Initialize the IFC exporter.

        Args:
            schema: IFC schema version (default: IFC4)
        """
        self.schema = schema
        self._ifc_file = None

    def export(self, building: "Building", filepath: str) -> None:
        """
        Export a building model to IFC file.

        Args:
            building: Building instance to export
            filepath: Output file path

        Raises:
            ImportError: If ifcopenshell is not installed
        """
        try:
            import ifcopenshell
        except ImportError:
            raise ImportError(
                "ifcopenshell is required for IFC export. "
                "Install it with: pip install ifcopenshell"
            )

        # Create IFC file
        self._ifc_file = ifcopenshell.file(schema=self.schema)

        # Create project hierarchy
        self._create_project_hierarchy(building)

        # Export all building components
        self._export_levels(building)
        self._export_grids(building)
        self._export_elements(building)  # Sprint 2: Walls, Floors, Roofs

        # Write file
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._ifc_file.write(str(filepath))

    def _create_project_hierarchy(self, building: "Building") -> None:
        """
        Create the IFC project hierarchy scaffolding.

        IfcProject → IfcSite → IfcBuilding → (levels/grids added separately)

        Args:
            building: Building instance
        """
        ifc = self._ifc_file

        # Create application and organization
        create_time = int(time.time())
        application = ifc.createIfcApplication(
            ifc.createIfcOrganization(None, "BIM as Code", None, None, None),
            "1.0",
            "BIM as Code",
            "bimascode"
        )

        person = ifc.createIfcPerson(None, None, "User", None, None, None, None, None)
        organization = ifc.createIfcOrganization(None, "BIM as Code", None, None, None)
        person_org = ifc.createIfcPersonAndOrganization(person, organization, None)

        owner_history = ifc.createIfcOwnerHistory(
            person_org,
            application,
            None,  # State
            None,  # ChangeAction
            create_time,
            person_org,
            application,
            create_time
        )

        # Store for later use
        building._ifc_owner_history = owner_history

        # Create units based on unit system
        units = self._create_units(building)

        # Create project
        ifc_project = ifc.createIfcProject(
            building.guid,
            owner_history,
            building.name,
            building.description,
            None,  # ObjectType
            None,  # LongName
            None,  # Phase
            None,  # RepresentationContexts
            units
        )

        # Create default geometric representation context
        context = ifc.createIfcGeometricRepresentationContext(
            None,  # ContextIdentifier
            "Model",  # ContextType
            3,  # CoordinateSpaceDimension
            1.0e-5,  # Precision
            ifc.createIfcAxis2Placement3D(
                ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                ifc.createIfcDirection((0.0, 0.0, 1.0)),
                ifc.createIfcDirection((1.0, 0.0, 0.0))
            ),
            None  # TrueNorth
        )

        # Update project with context
        ifc_project.RepresentationContexts = [context]

        # Create site
        site_placement = ifc.createIfcLocalPlacement(
            None,
            ifc.createIfcAxis2Placement3D(
                ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                ifc.createIfcDirection((0.0, 0.0, 1.0)),
                ifc.createIfcDirection((1.0, 0.0, 0.0))
            )
        )

        ifc_site = ifc.createIfcSite(
            building._generate_guid(),
            owner_history,
            "Default Site",
            None,
            None,
            site_placement,
            None,
            None,
            "ELEMENT",
            None,
            None,
            None,
            None,
            None
        )

        # Create building
        building_placement = ifc.createIfcLocalPlacement(
            site_placement,
            ifc.createIfcAxis2Placement3D(
                ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                ifc.createIfcDirection((0.0, 0.0, 1.0)),
                ifc.createIfcDirection((1.0, 0.0, 0.0))
            )
        )

        # Create postal address if provided
        postal_address = None
        if building.address:
            postal_address = ifc.createIfcPostalAddress(
                None,  # Purpose
                None,  # Description
                None,  # UserDefinedPurpose
                None,  # InternalLocation
                [building.address],  # AddressLines
                None,  # PostalBox
                None,  # Town
                None,  # Region
                None,  # PostalCode
                None  # Country
            )

        ifc_building = ifc.createIfcBuilding(
            building.guid,
            owner_history,
            building.name,
            building.description,
            None,
            building_placement,
            None,
            None,
            "ELEMENT",
            None,
            None,
            postal_address
        )

        # Store for later use
        building._ifc_project = ifc_project
        building._ifc_site = ifc_site
        building._ifc_building = ifc_building
        building._ifc_file = self._ifc_file

        # Create spatial hierarchy relationships
        ifc.createIfcRelAggregates(
            building._generate_guid(),
            owner_history,
            "ProjectContainer",
            None,
            ifc_project,
            [ifc_site]
        )

        ifc.createIfcRelAggregates(
            building._generate_guid(),
            owner_history,
            "SiteContainer",
            None,
            ifc_site,
            [ifc_building]
        )

    def _create_units(self, building: "Building"):
        """
        Create IFC unit assignment based on building's unit system.

        Args:
            building: Building instance

        Returns:
            IfcUnitAssignment instance
        """
        ifc = self._ifc_file
        from ..utils.units import UnitSystem

        if building.unit_system == UnitSystem.METRIC:
            length_unit = ifc.createIfcSIUnit(None, "LENGTHUNIT", None, "METRE")
            area_unit = ifc.createIfcSIUnit(None, "AREAUNIT", None, "SQUARE_METRE")
            volume_unit = ifc.createIfcSIUnit(None, "VOLUMEUNIT", None, "CUBIC_METRE")
        else:
            # Imperial units
            length_unit = ifc.createIfcConversionBasedUnit(
                ifc.createIfcDimensionalExponents(1, 0, 0, 0, 0, 0, 0),
                "LENGTHUNIT",
                "FOOT",
                ifc.createIfcMeasureWithUnit(
                    ifc.createIfcLengthMeasure(0.3048),
                    ifc.createIfcSIUnit(None, "LENGTHUNIT", None, "METRE")
                )
            )
            area_unit = ifc.createIfcSIUnit(None, "AREAUNIT", None, "SQUARE_METRE")
            volume_unit = ifc.createIfcSIUnit(None, "VOLUMEUNIT", None, "CUBIC_METRE")

        angle_unit = ifc.createIfcSIUnit(None, "PLANEANGLEUNIT", None, "RADIAN")

        return ifc.createIfcUnitAssignment([length_unit, area_unit, volume_unit, angle_unit])

    def _export_levels(self, building: "Building") -> None:
        """
        Export all levels (building storeys) to IFC.

        Args:
            building: Building instance
        """
        for level in building.levels:
            level.to_ifc(self._ifc_file)

    def _export_grids(self, building: "Building") -> None:
        """
        Export grid lines to IFC as IfcGrid.

        Args:
            building: Building instance
        """
        if not building.grids:
            return

        ifc = self._ifc_file

        # Separate grids into U (vertical) and V (horizontal) axes
        u_axes = []
        v_axes = []

        for grid in building.grids:
            grid_axis = grid.to_ifc(ifc)
            if grid.is_vertical():
                u_axes.append(grid_axis)
            elif grid.is_horizontal():
                v_axes.append(grid_axis)
            else:
                # For angled grids, default to U axes
                u_axes.append(grid_axis)

        # Create grid placement
        grid_placement = ifc.createIfcLocalPlacement(
            building._ifc_building.ObjectPlacement,
            ifc.createIfcAxis2Placement3D(
                ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                ifc.createIfcDirection((0.0, 0.0, 1.0)),
                ifc.createIfcDirection((1.0, 0.0, 0.0))
            )
        )

        # Create IfcGrid
        ifc_grid = ifc.createIfcGrid(
            building._generate_guid(),
            building._ifc_owner_history,
            "Building Grid",
            "Architectural grid lines",
            None,  # ObjectType
            grid_placement,
            None,  # Representation
            u_axes if u_axes else None,
            v_axes if v_axes else None,
            None   # WAxes (for 3D grids)
        )

        # Relate grid to building
        ifc.createIfcRelContainedInSpatialStructure(
            building._generate_guid(),
            building._ifc_owner_history,
            "BuildingGridContainer",
            None,
            [ifc_grid],
            building._ifc_building
        )

    def validate_export(self, filepath: str) -> dict:
        """
        Validate an exported IFC file.

        Args:
            filepath: Path to IFC file

        Returns:
            Dictionary with validation results
        """
        try:
            import ifcopenshell
        except ImportError:
            return {"valid": False, "error": "ifcopenshell not installed"}

        try:
            ifc_file = ifcopenshell.open(filepath)

            # Check for required entities
            projects = ifc_file.by_type("IfcProject")
            sites = ifc_file.by_type("IfcSite")
            buildings = ifc_file.by_type("IfcBuilding")
            storeys = ifc_file.by_type("IfcBuildingStorey")

            return {
                "valid": True,
                "schema": ifc_file.schema,
                "entities": {
                    "projects": len(projects),
                    "sites": len(sites),
                    "buildings": len(buildings),
                    "storeys": len(storeys),
                    "grids": len(ifc_file.by_type("IfcGrid")),
                    "materials": len(ifc_file.by_type("IfcMaterial"))
                }
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _export_elements(self, building: "Building") -> None:
        """
        Export all building elements to IFC.

        Handles:
        - Architectural: Wall, Floor, Roof, Door, Window, Ceiling
        - Structural: StructuralColumn, Beam
        - Spatial: Room

        Args:
            building: Building instance
        """
        from ..architecture import Wall, Floor, Roof, Door, Window, Ceiling
        from ..structure import StructuralColumn, Beam
        from ..spatial import Room

        # Store IFC storeys for element placement
        ifc_storeys = {}

        # Get IFC storeys that were already created
        for level in building.levels:
            # Find the IFC storey for this level
            for ifc_storey in self._ifc_file.by_type("IfcBuildingStorey"):
                if ifc_storey.GlobalId == level.guid:
                    ifc_storeys[level] = ifc_storey
                    break

        # Export elements from each level
        for level in building.levels:
            ifc_storey = ifc_storeys.get(level)
            if not ifc_storey or not level.elements:
                continue

            for element in level.elements:
                if isinstance(element, Wall):
                    ifc_wall = element.to_ifc(self._ifc_file, ifc_storey)
                    # Export hosted elements (doors, windows)
                    for hosted in element.hosted_elements:
                        if isinstance(hosted, Door):
                            hosted.to_ifc(self._ifc_file, ifc_storey, ifc_wall)
                        elif isinstance(hosted, Window):
                            hosted.to_ifc(self._ifc_file, ifc_storey, ifc_wall)
                elif isinstance(element, (Floor, Roof)):
                    element.to_ifc(self._ifc_file, ifc_storey)
                elif isinstance(element, StructuralColumn):
                    element.to_ifc(self._ifc_file, ifc_storey)
                elif isinstance(element, Beam):
                    element.to_ifc(self._ifc_file, ifc_storey)
                elif isinstance(element, Ceiling):
                    element.to_ifc(self._ifc_file, ifc_storey)
                elif isinstance(element, Room):
                    element.to_ifc(self._ifc_file, ifc_storey)
