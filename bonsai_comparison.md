# Bonsai IFC Setup Comparison

## Analysis of Bonsai-created IFC vs BIM as Code IFC

### Key Differences Found

## 1. HEADER INFORMATION

### Bonsai IFC Header:
```
File Description: ('ViewDefinition[DesignTransferView]',)
Implementation Level: 2;1
Preprocessor Version: IfcOpenShell 0.8.4
Originating System: Bonsai 0.8.4
Authorization: Nobody
Schema: IFC4
```

### Your IFC Header:
```
Originating System: IfcOpenShell 0.8.4-e8eb5e4
Schema: IFC4
```

**Missing in your IFC:**
- ❌ File Description with `ViewDefinition[DesignTransferView]`
- ❌ `Implementation Level` specification
- ❌ `Authorization` field

---

## 2. REPRESENTATION CONTEXTS

### Bonsai Setup (COMPREHENSIVE):

#### Model Context (3D):
- **Main Context:** Model (3D, Precision: 1e-05)
- **SubContexts:**
  - `Model/Body` - MODEL_VIEW
  - `Model/Axis` - GRAPH_VIEW
  - `Model/Box` - MODEL_VIEW
  - `Model/Annotation` - SECTION_VIEW
  - `Model/Annotation` - ELEVATION_VIEW
  - `Model/Annotation` - MODEL_VIEW
  - `Model/Annotation` - PLAN_VIEW
  - `Model/Profile` - ELEVATION_VIEW

#### Plan Context (2D):
- **Main Context:** Plan (2D, Precision: 1e-05)
- **SubContexts:**
  - `Plan/Axis` - GRAPH_VIEW
  - `Plan/Body` - PLAN_VIEW
  - `Plan/Annotation` - PLAN_VIEW
  - `Plan/Annotation` - REFLECTED_PLAN_VIEW

### Your Setup (MINIMAL):
- **Single Context:** Model (no identifier)
- **No SubContexts**
- **No Plan Context**

**Missing in your IFC:**
- ❌ **Plan context** (2D representations)
- ❌ **SubContexts** for different views (Body, Axis, Box, Annotation, Profile)
- ❌ **Target views** (MODEL_VIEW, GRAPH_VIEW, SECTION_VIEW, ELEVATION_VIEW, PLAN_VIEW, REFLECTED_PLAN_VIEW)
- ❌ **Context identifiers** (Body, Axis, Box, Annotation, Profile)

---

## 3. UNITS

### Bonsai Units:
```
- IfcSIUnit: LENGTHUNIT - METRE
- IfcSIUnit: AREAUNIT - SQUARE_METRE
- IfcSIUnit: VOLUMEUNIT - CUBIC_METRE
- IfcConversionBasedUnit: PLANEANGLEUNIT - degree
```

### Your Units:
Likely similar, but need to verify you have all four unit types including the **degree** unit for angles.

**Verify:**
- ✓ Length (METRE)
- ✓ Area (SQUARE_METRE)
- ✓ Volume (CUBIC_METRE)
- ❓ Plane Angle (degree) - **needs verification**

---

## 4. SPATIAL HIERARCHY

### Both have similar structure:
- IfcProject
- IfcSite
- IfcBuilding
- IfcBuildingStorey

### Bonsai specifics:
- Site: CompositionType = None (not specified)
- Building: CompositionType = None
- Storey: CompositionType = None

**Note:** Your implementation appears similar, but verify that optional fields like `RefLatitude`, `RefLongitude`, `RefElevation`, `ElevationOfRefHeight`, `ElevationOfTerrain` are properly set to `None` when not used.

---

## 5. OWNER HISTORY

### Bonsai:
The analysis showed no IfcOwnerHistory entities were created. However, this is unusual - Bonsai typically creates owner history.

### Your Setup:
You DO create IfcOwnerHistory with:
- Person
- Organization ("BIM as Code")
- Application
- Timestamps

**Status:** ✓ Your setup is actually MORE complete here

---

## CRITICAL MISSING ITEMS

### 1. Multiple Representation Contexts ⚠️

You need to create:

1. **Model Context (3D)** with subcontexts:
   - Body (for 3D solid geometry)
   - Axis (for centerlines/axes)
   - Box (for bounding boxes)
   - Annotation (for annotations in different views)
   - Profile (for cross-sections)

2. **Plan Context (2D)** with subcontexts:
   - Body (for 2D plan representations)
   - Axis (for 2D axes)
   - Annotation (for plan annotations)

### 2. File Description

Your header should include:
```python
file_description = ('ViewDefinition[DesignTransferView]',)
```

### 3. Implementation Level

Set to `'2;1'` in header.

---

## IMPLEMENTATION RECOMMENDATIONS

### Priority 1: Representation Contexts

Update `ifc_exporter.py` to create proper representation contexts:

```python
# Create Model context (3D)
model_context = ifc.createIfcGeometricRepresentationContext(
    None,  # ContextIdentifier
    "Model",  # ContextType
    3,  # CoordinateSpaceDimension
    1.0e-5,  # Precision
    ifc.createIfcAxis2Placement3D(...),
    None  # TrueNorth
)

# Create subcontexts for Model
body_context = ifc.createIfcGeometricRepresentationSubContext(
    "Body",  # ContextIdentifier
    "Model",  # ContextType
    None,  # ParentContext - will be set
    None,  # TargetScale
    "MODEL_VIEW",  # TargetView
    None  # UserDefinedTargetView
)
body_context.ParentContext = model_context

# ... create other subcontexts (Axis, Box, Annotation, Profile)

# Create Plan context (2D)
plan_context = ifc.createIfcGeometricRepresentationContext(
    None,  # ContextIdentifier
    "Plan",  # ContextType
    2,  # CoordinateSpaceDimension
    1.0e-5,  # Precision
    ifc.createIfcAxis2Placement2D(...),
    None  # TrueNorth
)

# Create subcontexts for Plan
# ... (similar to Model subcontexts but 2D)

# Update project
ifc_project.RepresentationContexts = [model_context, plan_context]
```

### Priority 2: Header Information

Update file creation to set proper header:

```python
ifc_file = ifcopenshell.file(schema="IFC4")

# Set file description
ifc_file.wrapped_data.header.file_description.description = ('ViewDefinition[DesignTransferView]',)
ifc_file.wrapped_data.header.file_description.implementation_level = '2;1'
ifc_file.wrapped_data.header.file_name.authorization = 'Nobody'
```

### Priority 3: Unit Verification

Ensure you have the plane angle unit:

```python
# Create degree unit for angles
conversion = ifc.createIfcMeasureWithUnit(
    ifc.createIfcPlaneAngleMeasure(0.017453292519943295),  # 1 degree in radians
    ifc.createIfcSIUnit(None, "PLANEANGLEUNIT", None, "RADIAN")
)
degree_unit = ifc.createIfcConversionBasedUnit(
    ifc.createIfcDimensionalExponents(0, 0, 0, 0, 0, 0, 0),
    "PLANEANGLEUNIT",
    "degree",
    conversion
)
```

---

## CURRENT STATUS

### What you have ✓
- Basic project hierarchy
- Owner history
- Single Model context
- Core units (length, area, volume)
- Proper BREP geometry generation

### What's missing ❌
- Multiple representation contexts (Model + Plan)
- SubContexts for different views
- Proper file description header
- Implementation level specification
- Plane angle unit (degree)

---

## NEXT STEPS

1. Update `_create_project_hierarchy()` in `ifc_exporter.py` to create all contexts
2. Update file header settings
3. Add plane angle unit to `_create_units()`
4. Test with Bonsai to ensure compatibility
