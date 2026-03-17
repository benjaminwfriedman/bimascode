# BIM as Code
## Research Brief: Landscape Analysis & Library Opportunity

*Prepared by Benny Friedman | March 2026*

---

## Executive Summary

The AEC software ecosystem has a critical missing layer: a high-level, LLM-friendly Python library for declarative building authoring that exports valid IFC files. This gap is the product opportunity. The four populated layers of the ecosystem — geometry kernels, BIM semantic tools, data pipelines, and GUI authoring environments — each solve adjacent problems but leave the programmatic authoring surface unaddressed.

The proposed library, working title **BIM as Code**, would sit between IfcOpenShell (IFC schema machinery) and build123d (BRep geometry) to provide a clean, composable Python DSL: `Wall()`, `Room()`, `Floor()` → IFC. The timing is right: IfcOpenShell v0.8.x recently stabilized its high-level API, build123d v0.10 shipped November 2025, and LLM adoption pressure on AEC firms is accelerating.

---

## The Core Gap

No existing open-source library allows a developer or language model to write semantically meaningful building code at a high level of abstraction. The closest approximation — IfcOpenShell's Python API — requires dozens of lines of schema boilerplate before describing anything architecturally meaningful.

A practitioner attempting to generate a simple wall programmatically must instantiate: `IfcProject`, `IfcSite`, `IfcBuilding`, `IfcBuildingStorey`, `IfcExtrudedAreaSolid`, `IfcRectangleProfileDef`, `IfcDirection`, `IfcAxis2Placement3D`, `IfcLocalPlacement`, and `IfcShapeRepresentation` — before adding properties or materials. This verbosity makes LLM-assisted BIM generation fragile, token-inefficient, and difficult to validate.

The target API for the missing library looks like this:

```python
from bimcode import Building, Floor, Room, Wall, Door

b = Building(name="Office Block", units="mm")
f = Floor(level=0, height=3600)
r = Room(name="Lobby", boundary=[(0,0),(12000,0),(12000,8000),(0,8000)])
r.add(Wall(start=(0,0), end=(12000,0), thickness=200, material="concrete"))
r.add(Door(position=(5000,0), width=900, height=2100))
f.add(r)
b.add(f)
b.export_ifc("building.ifc")
```

This is the **Terraform of buildings**: declare the intent, let the library handle the IFC schema machinery underneath.

> **Key quote from the OSArch community** (re: IfcOpenShell's programmatic authoring surface): *"There is still room for thinking about approaches to reducing the amount of code involved to generate a simple building."* — This is essentially the product spec.

---

## Existing Tooling Landscape

Research surfaced four distinct tooling layers. None provides the missing authoring surface, but each contributes building blocks.

| Tool | Language | Geometry Type | IFC Export | LLM-Friendly API |
|---|---|---|---|---|
| **IfcOpenShell** | Python / C++ | BRep (OCCT) | Native read/write | No — schema-bound API |
| **build123d** | Python | BRep (OCCT) | None | Yes — clean context managers |
| **COMPAS** (ETH Zurich) | Python | Mesh + BRep | Partial | Partial — research-oriented |
| **Speckle** | Python / .NET | Object graph | Via connectors | No — data pipeline tool |
| **pyRevit** | Python (IronPython) | Revit native | Via Revit | No — Revit-dependent |
| **Xbim** | C# / .NET | BRep (OCCT) | Full | No — .NET only |
| **opencascade-rs** | Rust | BRep (OCCT) | None | No — hobby project |

### IfcOpenShell

The most important existing piece. The C++ codebase uses OpenCASCADE as its geometry engine and exposes a Python API with a high-level authoring layer. It handles IFC read/write, geometry conversion, clash detection, quantity takeoff, and BCF/IDS compliance checking. It is the de facto standard for open-source IFC work.

The critical limitation: its API mirrors the IFC schema rather than human intent. Generating a building programmatically requires intimate knowledge of the EXPRESS schema — entity types, relationship patterns, geometric representations. An LLM can technically generate IfcOpenShell code but the token cost and error surface are prohibitive for general use.

- **Status:** Active, v0.8.4.post1, LGPL
- **Website:** [ifcopenshell.org](https://ifcopenshell.org)

### build123d

The most ergonomic code-first geometry library in the Python ecosystem as of 2025. Built on OpenCASCADE via the OCP Python bindings, it provides a context-manager-based API that is genuinely readable and composable. v0.10.0 shipped November 2025.

- **Strength:** Pythonic, LLM-friendly, active development, algebraic modeling operators (`obj += sub_obj`)
- **Gap:** Entirely focused on mechanical CAD (3D printing, CNC). No IFC entity types, no building systems, no architectural semantics.

build123d is the recommended geometry engine to depend on rather than reimplement.

- **Status:** Active, v0.10.0, Apache 2.0
- **Website:** [build123d.readthedocs.io](https://build123d.readthedocs.io)

### COMPAS (ETH Zurich / Block Research Group)

A mature open-source Python framework for computational research in AEC, developed over six years at ETH Zurich's NCCR Digital Fabrication. Provides CAD-agnostic geometry processing, data structures, and integration with Rhino/Grasshopper/Blender. Includes `compas_occ` for OCCT-based BRep work outside of Rhino.

- **Strength:** Academic rigor, broad geometry toolkit, active research community, partial IFC support via extensions
- **Gap:** Research-oriented API design, not optimized for LLM generation. No BIM semantic layer (no `Wall`, `Room`, `Floor` abstractions).

- **Status:** Active, MIT
- **Website:** [compas.dev](https://compas.dev)

### Speckle

An open-source BIM data platform providing connectivity and automation across AEC tools. Speckle Automate provides CI/CD-style automation triggered by model changes — clash detection, compliance checking, report generation. Strong Python SDK (`specklepy`) and connector ecosystem covering Revit, Rhino, Grasshopper, Blender, and more.

- **Role in the stack:** Ideal as an export target and integration layer, not a geometry authoring tool. A BIM as Code library should include a Speckle export adapter.

- **Status:** Active, open-source server + SDKs
- **Website:** [speckle.systems](https://speckle.systems)

---

## Geometry Kernel Analysis

The choice of geometry kernel is the most consequential technical decision.

### OpenCASCADE (OCCT) — the only viable open-source BRep option

OCCT is the kernel underlying IfcOpenShell, build123d, CadQuery, FreeCAD, and COMPAS's OCC extension. It is the de facto standard for open-source boundary representation geometry, despite a notoriously complex C++ codebase. The Python bindings (OCP) are maintained by the CadQuery/build123d community and actively developed. This is the recommended kernel — battle-tested for IFC geometry generation and already integrated with IfcOpenShell.

### Rust alternatives — promising but premature

Several Rust BRep kernel projects exist: Fornjot, Truck (by RICOS in Japan), CADmium's custom kernel, and `opencascade-rs` (Rust bindings to OCCT). The appeal is memory safety, WASM compilation, and modern tooling. The reality: all are early-stage and none is production-ready for AEC-scale boolean operations.

- **Fornjot:** Explicitly focused on mechanical CAD; architectural use is out of scope.
- **Truck:** Noted as a modern Rust-native kernel — promising, but boolean operations and advanced surfaces are incomplete.
- **opencascade-rs:** Hobby project; not production-ready.

**Recommendation:** Build on OCCT/OCP now via build123d. Monitor the Rust kernel space — a PyO3-wrapped Rust geometry layer for the hot path is a viable v2 architecture if Truck matures.

### Language architecture recommendation

The library should be pure Python at the API surface, with C++ OCCT handling the geometry kernel via existing bindings. This mirrors the stack used by both IfcOpenShell and build123d — the two libraries the project would depend on.

| Layer | Technology |
|---|---|
| Developer API | Python 3.10+, context managers, dataclasses, type hints |
| Geometry engine | build123d → OCP → OpenCASCADE (C++) |
| IFC serialization | IfcOpenShell high-level API |
| Export adapters | specklepy, STEP via build123d, GLB via IfcConvert |

---

## Proposed Library Architecture

Three layers, stacked cleanly:

### Layer 1 — Geometry engine (use existing, don't build)

build123d handles all BRep operations: wall extrusion, opening boolean subtraction, roof lofts, column placement. No custom geometry code required at this layer.

### Layer 2 — BIM semantic layer (the library itself)

Python classes for the architectural domain: `Wall`, `Room`, `Floor`, `Building`, `Column`, `Beam`, `Slab`, `Door`, `Window`, `Space`, `MEPSystem`. Each class encapsulates:

- IFC entity type mapping
- Geometry recipe (delegated to build123d)
- Default property sets (`Pset_WallCommon`, `Pset_SpaceCommon`, etc.)
- Relationship rules (a `Door` lives in a `Wall`, a `Wall` belongs to a `Storey`)
- Validation constraints (wall thickness > 0, door width < wall length)

### Layer 3 — Export adapters (build on existing tools)

- `export_ifc()` — via IfcOpenShell high-level API
- `export_speckle()` — via specklepy SDK
- `export_step()` — via build123d native STEP export
- `export_glb()` — via IfcConvert CLI

---

## LLM-First API Design Principles

The primary differentiator from IfcOpenShell is designing the API surface for LLM generation rather than for BIM schema experts:

- **Named constructors with sensible defaults:** `Wall(start=..., end=...)` works without specifying material, fire rating, or property sets
- **No project setup boilerplate:** `Building()` creates a valid IFC project context automatically
- **Implicit unit handling:** The library accepts mm, m, or ft — no IfcUnit declarations required
- **Actionable error messages:** `"Door width (1200mm) exceeds wall length (800mm)"` not `"IfcRelVoidsElement validation failed"`
- **Parametric composability:** Every element is a first-class Python object — transform, clone, parameterize, iterate
- **Token efficiency:** A complete single-story office floor plate should be expressible in fewer than 50 lines of library code

---

## Open Source Strategy & Positioning

The conceptual framing maps directly onto the AEC/AI gap thesis: the industry has ~64% theoretical AI coverage but ~4% observed adoption. The missing piece is not models or data — it is a programmatic surface that AI can reliably write and validate.

- **Package name:** `bimcode` or `bim-as-code` (PyPI + GitHub org)
- **License:** MIT or Apache 2.0 — maximize adoption; commercial layer can be hosted validation/compliance checking
- **Primary audience:** AEC developers, computational designers, BIM automation engineers, AI application builders in AEC
- **Secondary audience:** LLM tool-use agents that need to generate or modify building models
- **Moat:** The semantic layer and LLM-optimized API design; the protocol/format is open, the ergonomics are the product

**Closest competitors to monitor:** Trunk Tools (BIM AI platform, not open-source), Speckle Automate (pipeline tool, not authoring), and any future IfcOpenShell high-level DSL work from the BlenderBIM/Bonsai community.

---

## Sources

| Source | Description | URL |
|---|---|---|
| IfcOpenShell | Official site: open-source IFC toolkit and geometry engine (LGPL), Python + C++ API, v0.8.4 | https://ifcopenshell.org |
| IfcOpenShell PyPI | Latest release (v0.8.4.post1), cross-platform wheels for Python 3.10–3.14 | https://pypi.org/project/ifcopenshell/ |
| IfcOpenHouse tutorial (OSArch) | Community discussion on programmatic IFC generation — source of the key verbosity quote | https://community.osarch.org/discussion/1471/ |
| build123d GitHub | Python parametric BRep framework on OpenCASCADE, v0.10.0 (Nov 2025), Apache 2.0 | https://github.com/gumyr/build123d |
| build123d docs | Full API reference, introduction, and comparison with CadQuery | https://build123d.readthedocs.io/ |
| COMPAS GitHub | ETH Zurich open-source computational AEC framework — geometry, structures, robotics | https://github.com/compas-dev |
| COMPAS (OSArch) | Community introduction to the COMPAS framework and its role in AEC research | https://osarch.org/2021/03/03/compas-an-open-source-python-framework-for-aec/ |
| Speckle Systems | Open-source BIM data hub: connectivity, collaboration, and Automate (CI/CD) for AEC | https://speckle.systems |
| Speckle GitHub | Speckle open-source repositories: server, connectors, SDKs (MIT/Apache) | https://github.com/specklesystems |
| Speckle Automate (AEC Mag) | AEC Magazine analysis of Speckle's CI/CD automation capabilities (Nov 2023) | https://aecmag.com/collaboration/automatic-for-the-people-2/ |
| opencascade-rs | Rust bindings to OpenCASCADE — hobby project, code-first CAD philosophy in Rust | https://github.com/bschwind/opencascade-rs |
| Fornjot | Early-stage BRep CAD kernel in Rust — focused on mechanical CAD, not architecture | https://www.fornjot.app/ |
| CADmium / Truck | Browser-native CAD using the Truck Rust BRep kernel — frank survey of the open-source kernel landscape | https://mattferraro.dev/posts/cadmium |
| Use AI to manipulate IFC (BIM Corner) | Practical guide to using LLMs with IfcOpenShell for IFC file manipulation | https://bimcorner.com/use-ai-to-manipulate-your-ifc/ |
| Sorted Solution AEC repos | Survey of open-source AEC design repositories including COMPAS, pyRevit, Xbim | https://www.sortedsolution.com/news/open-source-aec-design-repositories-for-architects/ |

---

*BIM as Code Research Brief | Benny Friedman | March 2026 | Not Magic, Just Math*