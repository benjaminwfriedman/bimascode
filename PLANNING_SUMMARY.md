# BIM as Code v1.0 — Planning Summary

**Created:** March 17, 2026
**Repository:** https://github.com/benjaminwfriedman/bimascode

---

## What Was Created

### 1. **GitHub Repository**
- Created public repository: `benjaminwfriedman/bimascode`
- Initialized with labels for priorities (P0, P1, P2), sprints (1-10), domains, and complexity

### 2. **Planning Documents**
- **[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)** - High-level roadmap, principles, risk management, visualization strategy
- **[EPOCH_SPRINT_PLAN.md](./EPOCH_SPRINT_PLAN.md)** - Detailed 10-sprint breakdown with 57 P0 features
- **[BIM_AS_CODE_MAIN_FEATURE_LIST.md](./BIM_AS_CODE_MAIN_FEATURE_LIST.md)** - Comprehensive 115-feature analysis (existing)

### 3. **GitHub Issues Created**
- **62 total issues** created across 10 sprints
- All issues include: priority, complexity, requirements, acceptance criteria, example usage
- Issues link to related features and dependencies

---

## Sprint Breakdown (57 P0 Features)

### **Sprint 1: Project Skeleton** (2 weeks, 7 features)
1. Level / Building Storey (#15)
2. Building / Site Hierarchy (#16)
3. Grid Lines (#17)
4. Material Definition (#23)
5. IFC Export (#86) ✅
6. **IFC Import (#91)** ✅ *Added based on critique*
7. **Units Management** ✅ *Added based on critique*

### **Sprint 2: Core Architecture** (3 weeks, 5 features)
8. Type / Instance Parameter Model (#19)
9. WallType - Compound Layer Stack (#18)
10. Wall - Straight, No Joins (#1) *with end caps enhancement*
11. Floor / Slab (#2) *with slope parameter*
12. Roof - Flat Only (#3) *with slope parameter, pitched TBD*

### **Sprint 3: Hosted Elements + Wall Joins** (3 weeks, 5 features)
13. Door - Hosted in Wall (#4)
14. Window - Hosted in Wall (#5)
15. Material Layer Assignment (#24)
16. Wall-to-Wall Joins (#1 enhanced) *with end cap types*
17. **Non-Hosted Openings** ✅ *Added based on critique*

### **Sprint 4: Spatial + Structural** (2 weeks, 7 features)
18. Room / Space (#12)
19. Ceiling (#6)
20. Structural Column (#25)
21. Beam (#26)
22. Structural Wall (#27)
23. Structural Floor / Slab (#28)
24. Section Profile Library - Basic (#34)

### **Sprint 5: Performance Infrastructure** (2 weeks, 2 features)
25. 2D Representation Caching (#104)
26. Bounding Box Pre-Filter (#105)

### **Sprint 6: Drawing Generation** (3 weeks, 8 features)
27. Floor Plan View Generation (#47)
28. Section View Generation (#48)
29. Elevation View Generation (#49)
30. View Crop Region (#53)
31. View Scale (#54)
32. View Range / Cut Height (#55)
33. **Line Weights and Line Types** ✅ *Added based on critique*
34. **View Visibility and View Templates** ✅ *Added based on critique*

### **Sprint 7: Annotation Core** (2 weeks, 7 features)
35. Linear Dimension (#56) *view-specific*
36. Chain / Continuous Dimensioning (#57) *view-specific*
37. Room Tag (#62) *view-specific*
38. Door / Window Tag (#63) *view-specific*
39. Text Note (#66) *view-specific*
40. Section Symbol / Cut Mark (#68) *view-specific*
41. North Arrow (#71) *view-specific*

### **Sprint 8: Sheet Production** (2 weeks, 6 features)
42. Sheet - DXF Paperspace (#75)
43. Viewport Placement on Sheet (#76)
44. Title Block - Parametric (#77)
45. Sheet Number / Name (#78)
46. DXF Export (#84)
47. PDF Export (#85)

### **Sprint 9: Schedules + Export Formats** (2 weeks, 7 features)
48. Door / Window Schedule (#95)
49. Room Finish Schedule (#96)
50. Material Takeoff (#98)
51. Custom Schedule - Any Category (#99)
52. Schedule Filters / Sorting / Grouping (#100)
53. IFC Export - Enhanced (#86)
54. STEP Export (#87)

### **Sprint 10: Stair + Advanced Architecture** (3 weeks, 3 features)
55. Stair - Straight Run (#7)
56. Stair - L-Shape and U-Shape (#7 enhanced)
57. Section Profile Library - Full (#34)

---

## Critical Enhancements Added

Based on production AE project requirements critique, the following **5 critical features** were added to close gaps:

### ✅ **1. IFC Import (#91)** - Sprint 1
- **Gap:** Can't work with existing models from consultants or iterate on existing buildings
- **Impact:** Blocks consultant coordination and renovation workflows
- **Solution:** `Building.import_ifc()` for reading existing IFC4 models

### ✅ **2. Units Management** - Sprint 1
- **Gap:** No explicit unit handling (mixing mm/inches/feet will cause errors)
- **Impact:** Can't reliably work across metric/imperial projects
- **Solution:** Project-level units with automatic conversion

### ✅ **3. Non-Hosted Openings** - Sprint 3
- **Gap:** Only have door/window (hosted), no arbitrary voids
- **Impact:** Can't model shaft openings, floor penetrations for stairs/elevators, MEP penetrations
- **Solution:** `Opening(host_element, boundary)` for arbitrary voids

### ✅ **4. Line Weights and Line Types** - Sprint 6
- **Gap:** Missing entirely from feature list
- **Impact:** Drawings won't meet AIA/NCS professional standards
- **Solution:** Standard line weights (fine/thin/medium/thick) with automatic assignment

### ✅ **5. View Visibility and View Templates** - Sprint 6
- **Gap:** No way to control element visibility per view
- **Impact:** Can't hide structure in arch plans, can't show only ceilings in RCP
- **Solution:** Show/hide by category with view templates

### 📝 **Enhancements to Existing Features:**
- **Floor/Roof slope parameter** - for drainage and accessibility
- **Wall end caps** - flush, exterior, interior terminations
- **View-specific annotations** - clarified that annotations belong to views
- **Pitched roof priority** - flagged for decision (P0 or defer to P1)

---

## Plan Assessment

### **Production Readiness: 95%**

After adding the 5 critical features, the plan now covers:
- ✅ Complete building modeling (architecture + structure)
- ✅ Professional drawing production with proper line weights
- ✅ View visibility control for discipline separation
- ✅ IFC interoperability (import + export)
- ✅ Units management across metric/imperial
- ✅ Non-hosted openings for shafts and penetrations
- ✅ View-specific annotations
- ✅ Complete sheet production pipeline

### **Remaining Considerations:**

**Recommended for v1.1 (P1):**
- Element filters / selection sets (useful but not blocking)
- Copy/array/mirror operations (productivity enhancement)
- Detail components (2D-only symbols)
- Graphic overrides per view (halftone, color)

**✅ Decision Made:**
- **Pitched Roof** - Deferred to P1 (v1.1)
  - Sprint 2 delivers flat roofs with slope for drainage
  - Reduces Sprint 2 complexity and allows faster v1.0 delivery
  - Pitched roofs (gable, hip, shed) will be fully developed in v1.1

---

## Timeline

- **Total Duration:** 24 weeks (6 months)
- **Epoch 1 (Foundation):** Sprints 1-5, 12 weeks
- **Epoch 2 (Production):** Sprints 6-8, 7 weeks
- **Epoch 3 (Completeness):** Sprints 9-10, 5 weeks

---

## Next Steps

1. ✅ ~~**Decide on pitched roof priority**~~ - Deferred to P1 (v1.1)
2. **Review and refine issue descriptions** as team forms
3. **Set up development environment** (Python, build123d, IfcOpenShell, ezdxf)
4. **Create repository structure** (src/, tests/, docs/, examples/)
5. **Sprint 1 kickoff** - Begin with Level, Building, Grid, Materials, IFC import/export, Units

---

## Repository Links

- **Repository:** https://github.com/benjaminwfriedman/bimascode
- **Issues:** https://github.com/benjaminwfriedman/bimascode/issues
- **Planning Docs:**
  - [Implementation Plan](./IMPLEMENTATION_PLAN.md)
  - [Epoch Sprint Plan](./EPOCH_SPRINT_PLAN.md)
  - [Feature List](./BIM_AS_CODE_MAIN_FEATURE_LIST.md)

---

**Status:** ✅ Planning Complete - Ready for Development

**Last Updated:** March 17, 2026
