import ifcopenshell

# Load the newly generated IFC file
import sys
ifc_path = sys.argv[1] if len(sys.argv) > 1 else '/Users/benjaminfriedman/repos/bimcode/output/sprint3_demo.ifc'
new_file = ifcopenshell.open(ifc_path)

print("=" * 80)
print("VERIFICATION OF NEW IFC SETUP")
print("=" * 80)

# Header information
print("\n### HEADER INFORMATION ###")
header = new_file.header
print(f"✓ File Description: {header.file_description.description}")
print(f"✓ Implementation Level: {header.file_description.implementation_level}")
print(f"✓ Authorization: {header.file_name.authorization}")
print(f"✓ Originating System: {header.file_name.originating_system}")
print(f"✓ Schema: {header.file_schema.schema_identifiers}")

# Units
print("\n### UNITS ###")
project = new_file.by_type('IfcProject')[0]
units = project.UnitsInContext.Units
print(f"Total units: {len(units)}")
for unit in units:
    unit_type = unit.UnitType if hasattr(unit, 'UnitType') else 'N/A'
    if unit.is_a('IfcConversionBasedUnit'):
        print(f"✓ {unit.is_a()}: {unit_type} - {unit.Name}")
    else:
        print(f"✓ {unit.is_a()}: {unit_type} - {unit.Name if hasattr(unit, 'Name') else unit.Prefix if hasattr(unit, 'Prefix') else 'SI'}")

# Representation contexts
print("\n### REPRESENTATION CONTEXTS ###")
print(f"Total main contexts: {len(project.RepresentationContexts)}")

for ctx in project.RepresentationContexts:
    print(f"\n✓ {ctx.ContextType} Context (Dimension: {ctx.CoordinateSpaceDimension}D)")
    print(f"  Precision: {ctx.Precision}")

    if hasattr(ctx, 'HasSubContexts') and ctx.HasSubContexts:
        print(f"  SubContexts: {len(ctx.HasSubContexts)}")
        for subctx in ctx.HasSubContexts:
            print(f"    ✓ {subctx.ContextIdentifier} - {subctx.TargetView}")
    else:
        print(f"  SubContexts: 0")

# Summary
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

# Check all requirements
checks = {
    "File Description (ViewDefinition)": header.file_description.description == ('ViewDefinition[DesignTransferView]',),
    "Implementation Level (2;1)": header.file_description.implementation_level == '2;1',
    "Authorization (Nobody)": header.file_name.authorization == 'Nobody',
    "Has degree unit": any(hasattr(u, 'Name') and u.Name == 'degree' for u in units),
    "Has Model context (3D)": any(ctx.ContextType == 'Model' and ctx.CoordinateSpaceDimension == 3 for ctx in project.RepresentationContexts),
    "Has Plan context (2D)": any(ctx.ContextType == 'Plan' and ctx.CoordinateSpaceDimension == 2 for ctx in project.RepresentationContexts),
}

# Count subcontexts
model_ctx = next((ctx for ctx in project.RepresentationContexts if ctx.ContextType == 'Model'), None)
plan_ctx = next((ctx for ctx in project.RepresentationContexts if ctx.ContextType == 'Plan'), None)

model_subctx_count = len(model_ctx.HasSubContexts) if model_ctx and hasattr(model_ctx, 'HasSubContexts') and model_ctx.HasSubContexts else 0
plan_subctx_count = len(plan_ctx.HasSubContexts) if plan_ctx and hasattr(plan_ctx, 'HasSubContexts') and plan_ctx.HasSubContexts else 0

checks["Model has subcontexts (8)"] = model_subctx_count == 8
checks["Plan has subcontexts (4)"] = plan_subctx_count == 4

print("\nRequirement Checklist:")
for requirement, passed in checks.items():
    status = "✓" if passed else "✗"
    print(f"  {status} {requirement}")

all_passed = all(checks.values())
print("\n" + "=" * 80)
if all_passed:
    print("✓✓✓ ALL CHECKS PASSED! IFC setup matches Bonsai standards! ✓✓✓")
else:
    print("✗ Some checks failed - review output above")
print("=" * 80)
