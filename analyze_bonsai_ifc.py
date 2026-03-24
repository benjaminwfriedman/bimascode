import ifcopenshell

# Load the Bonsai-created IFC file
bonsai_file = ifcopenshell.open('/Users/benjaminfriedman/repos/bimcode/examples/Untitled.ifc')

# Load one of your IFC files for comparison
your_file = ifcopenshell.open('/Users/benjaminfriedman/repos/bimcode/output/sprint3_demo.ifc')

print("=" * 80)
print("BONSAI IFC FILE ANALYSIS")
print("=" * 80)

# Header information
print("\n### HEADER INFORMATION ###")
header = bonsai_file.header
print(f"File Description: {header.file_description.description}")
print(f"Implementation Level: {header.file_description.implementation_level}")
print(f"File Name: {header.file_name.name}")
print(f"Time Stamp: {header.file_name.time_stamp}")
print(f"Author: {header.file_name.author}")
print(f"Organization: {header.file_name.organization}")
print(f"Preprocessor Version: {header.file_name.preprocessor_version}")
print(f"Originating System: {header.file_name.originating_system}")
print(f"Authorization: {header.file_name.authorization}")
print(f"Schema Identifiers: {header.file_schema.schema_identifiers}")

# Project information
print("\n### PROJECT SETUP ###")
project = bonsai_file.by_type('IfcProject')[0] if bonsai_file.by_type('IfcProject') else None
if project:
    print(f"Project Name: {project.Name}")
    print(f"Project Description: {project.Description}")
    print(f"Project Long Name: {project.LongName if hasattr(project, 'LongName') else 'N/A'}")
    print(f"Project Phase: {project.Phase if hasattr(project, 'Phase') else 'N/A'}")

# Unit assignment
print("\n### UNITS ###")
if project and project.UnitsInContext:
    units = project.UnitsInContext.Units
    for unit in units:
        print(f"  - {unit.is_a()}: {unit}")

# Representation contexts
print("\n### REPRESENTATION CONTEXTS ###")
if project and project.RepresentationContexts:
    for ctx in project.RepresentationContexts:
        print(f"  - {ctx.is_a()}")
        print(f"    ContextType: {ctx.ContextType}")
        print(f"    ContextIdentifier: {ctx.ContextIdentifier}")
        print(f"    CoordinateSpaceDimension: {ctx.CoordinateSpaceDimension}")
        print(f"    Precision: {ctx.Precision}")
        print(f"    WorldCoordinateSystem: {ctx.WorldCoordinateSystem}")
        print(f"    TrueNorth: {ctx.TrueNorth}")
        if hasattr(ctx, 'HasSubContexts') and ctx.HasSubContexts:
            for subctx in ctx.HasSubContexts:
                print(f"      SubContext: {subctx.ContextType}/{subctx.ContextIdentifier} - {subctx.TargetView}")

# Site, Building, Storey hierarchy
print("\n### SPATIAL HIERARCHY ###")
sites = bonsai_file.by_type('IfcSite')
print(f"Sites: {len(sites)}")
for site in sites:
    print(f"  - Site Name: {site.Name}")
    print(f"    CompositionType: {site.CompositionType}")
    print(f"    RefLatitude: {site.RefLatitude}")
    print(f"    RefLongitude: {site.RefLongitude}")
    print(f"    RefElevation: {site.RefElevation}")

buildings = bonsai_file.by_type('IfcBuilding')
print(f"Buildings: {len(buildings)}")
for building in buildings:
    print(f"  - Building Name: {building.Name}")
    print(f"    CompositionType: {building.CompositionType}")
    print(f"    ElevationOfRefHeight: {building.ElevationOfRefHeight}")
    print(f"    ElevationOfTerrain: {building.ElevationOfTerrain}")

storeys = bonsai_file.by_type('IfcBuildingStorey')
print(f"Storeys: {len(storeys)}")
for storey in storeys:
    print(f"  - Storey Name: {storey.Name}")
    print(f"    CompositionType: {storey.CompositionType}")
    print(f"    Elevation: {storey.Elevation}")

# Owner history
print("\n### OWNER HISTORY ###")
owner_histories = bonsai_file.by_type('IfcOwnerHistory')
if owner_histories:
    oh = owner_histories[0]
    print(f"OwningUser: {oh.OwningUser}")
    print(f"OwningApplication: {oh.OwningApplication}")
    print(f"State: {oh.State}")
    print(f"ChangeAction: {oh.ChangeAction}")
    print(f"CreationDate: {oh.CreationDate}")

# Person and Organization
print("\n### PERSON AND ORGANIZATION ###")
persons = bonsai_file.by_type('IfcPerson')
for person in persons:
    print(f"Person: {person.GivenName} {person.FamilyName}")

orgs = bonsai_file.by_type('IfcOrganization')
for org in orgs:
    print(f"Organization: {org.Name}")

applications = bonsai_file.by_type('IfcApplication')
for app in applications:
    print(f"Application: {app.ApplicationFullName} v{app.Version}")

print("\n" + "=" * 80)
print("YOUR IFC FILE ANALYSIS (for comparison)")
print("=" * 80)

# Compare with your file
print("\n### HEADER INFORMATION ###")
your_header = your_file.header
print(f"Originating System: {your_header.file_name.originating_system}")
print(f"Schema Identifiers: {your_header.file_schema.schema_identifiers}")

print("\n### PROJECT SETUP ###")
your_project = your_file.by_type('IfcProject')[0] if your_file.by_type('IfcProject') else None
if your_project:
    print(f"Project Name: {your_project.Name}")
    if your_project.RepresentationContexts:
        print(f"Representation Contexts: {len(your_project.RepresentationContexts)}")
        for ctx in your_project.RepresentationContexts:
            print(f"  - {ctx.ContextType}/{ctx.ContextIdentifier}")

print("\n### SPATIAL HIERARCHY ###")
your_sites = your_file.by_type('IfcSite')
print(f"Sites: {len(your_sites)}")
your_buildings = your_file.by_type('IfcBuilding')
print(f"Buildings: {len(your_buildings)}")
your_storeys = your_file.by_type('IfcBuildingStorey')
print(f"Storeys: {len(your_storeys)}")
