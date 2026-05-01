# BIM as Code v1.0 — Implementation Plan

**Repository:** benjaminwfriedman/bimascode
**Target Release:** v1.0
**Planning Date:** March 2026

## Executive Summary

This implementation plan outlines the development roadmap for BIM as Code v1.0, a Python library for programmatic BIM authoring and drawing set production. The plan is structured around 10 sprints delivering 47 P0 (critical) features organized into functional groups.

## Core Principles

### Development Philosophy
- **Code-first design**: Everything is expressed as Python code, stored in version control
- **IFC-native**: All geometry and metadata exported to IFC4 standard
- **Drawing automation**: Automated generation of construction document sets (DXF/PDF)
- **No standalone GUI**: Headless library with in-IDE visualization for rapid feedback
- **Type/instance model**: Revit-style parametric architecture with type and instance parameters

### Technical Stack
- **Geometry**: build123d (OCCT wrapper) + shapely (2D operations)
- **BIM export**: IfcOpenShell
- **Drawing export**: ezdxf (DXF) + matplotlib (PDF)
- **In-IDE visualization**:
  - build123d show() for 3D geometry preview (OCP CAD Viewer)
  - matplotlib for 2D drawing preview
  - VS Code extension integration for live model updates
- **Collaboration**: specklepy integration
- **Data**: pandas for schedules and queries

## Success Criteria

v1.0 is considered complete when a user can:

1. **Model a building** with walls, floors, roofs, doors, windows, stairs, rooms
2. **Define structure** with columns, beams, structural walls, and slabs
3. **Visualize in real-time** within their IDE/notebook without leaving the development environment
4. **Generate drawings** including floor plans, sections, elevations with annotations
5. **Produce sheets** with title blocks, viewports, and sheet sets
6. **Export deliverables** as DXF, PDF, IFC4, and STEP formats
7. **Create schedules** for doors, windows, rooms, and materials

## Risk Management

### High-Risk Features
1. **Wall-to-wall joins** — T and L junction cleanup (Sprint 3)
2. **Stair geometry** — Complex tread/riser/landing logic (Sprint 10)
3. **Floor plan section cuts** — Performance on large models (Sprint 6)
4. **Hidden line removal** — OCCT HLR for sections/elevations (Sprint 6)

### Mitigation Strategies
- Prototype complex geometry algorithms early (proof-of-concept in Sprint 1)
- Implement performance infrastructure before drawing generation (Sprint 5)
- Create comprehensive test models for wall joins and stairs
- Maintain performance benchmarks throughout development

### Dependencies
- **External libraries**: build123d, IfcOpenShell, ezdxf must remain stable
- **IFC standard**: Targeting IFC4; monitor IFC4.3 adoption
- **OCCT**: Dependency chain via build123d; must handle OCCT API changes

## Development Sequence

The 10-sprint sequence is designed to:
- Establish infrastructure early (Sprints 1-2)
- Build incrementally testable features (Sprints 3-4)
- Optimize before complex operations (Sprint 5)
- Deliver drawing capability mid-way (Sprints 6-7)
- Complete deliverable pipeline (Sprint 8)
- Finalize with schedules and export (Sprint 9)
- Add most complex feature last (Sprint 10)

### Sprint Duration
- Each sprint represents 2-3 weeks of development effort
- Total timeline: 20-30 weeks for v1.0 completion
- Sprints 1-5: Foundation (10-15 weeks)
- Sprints 6-10: Drawing production (10-15 weeks)

## Post-v1.0 Roadmap

### v1.1 Features (P1 Priority)
- MEP disciplines (HVAC, plumbing, electrical)
- Ramp, railing, curtain wall
- Reflected ceiling plans
- Detail views and callouts
- Additional annotation types
- VS Code extension for enhanced in-editor visualization
- Speckle bidirectional sync

### v2.0 Features (P2 Priority)
- Advanced structural (trusses, rebar, connections)
- Site/topography
- Massing and panelization
- Point cloud integration
- Energy analysis export (gbXML)
- Clash detection

## Quality Assurance

### Testing Strategy
- **Unit tests**: Each geometric primitive and IFC entity
- **Integration tests**: End-to-end building model → drawing set workflow
- **Regression tests**: Reference models that must export correctly
- **Performance tests**: Large model benchmarks (1000+ walls, 100+ rooms)

### Documentation Requirements
- API reference (auto-generated from docstrings)
- User guide with worked examples
- Architecture decision records (ADRs) for key design choices
- Migration guides between versions

### Code Quality Standards
- Type hints throughout (mypy strict mode)
- Docstrings for all public APIs
- Black formatting, flake8 linting
- Minimum 80% test coverage for core modules

## Deployment & Distribution

### Release Channels
- **PyPI**: Primary distribution via `pip install bimascode`
- **Conda-forge**: For scientific/engineering users
- **GitHub releases**: Versioned source archives

### Versioning Strategy
- Semantic versioning (MAJOR.MINOR.PATCH)
- v1.0.0: Initial stable release
- v1.x.x: P1 features, non-breaking additions
- v2.0.0: Breaking API changes, P2 features

### Breaking Change Policy
- Deprecation warnings one minor version before removal
- Migration guide for all breaking changes
- Maintain compatibility shims where feasible

## Team Structure (Recommended)

### Core Development Roles
- **Geometry Lead**: Wall joins, stairs, section cuts (Sprints 2-3, 6, 10)
- **IFC/Standards Lead**: IFC export, parametric model (Sprints 1-4, 9)
- **Drawing Lead**: DXF generation, annotations, sheets (Sprints 6-8)
- **Performance Lead**: Caching, optimization, BVH trees (Sprint 5)

### Support Roles
- **Documentation**: User guides, examples, tutorials
- **Testing**: Test models, regression suite, CI/CD
- **DevOps**: PyPI releases, conda packaging, versioning

## Communication & Tracking

### Development Updates
- Weekly sprint progress reports
- Bi-weekly demo of completed features
- Monthly roadmap review with stakeholders

### Issue Management
- GitHub Issues for all features and bugs
- GitHub Projects for sprint planning
- Labels: `P0`, `P1`, `P2`, `sprint-N`, `domain/architecture`, `domain/structural`, etc.
- Milestones for each sprint

### Community Engagement
- Public Discord/Slack for user support
- GitHub Discussions for feature requests and design discussions
- Quarterly community calls for roadmap input

---

## Visualization Strategy

### In-IDE Development Workflow
Developers need immediate visual feedback without context-switching. BIM as Code supports:

1. **Interactive 3D preview**: `building.show()` or `wall.show()` launches OCP CAD Viewer (build123d's native viewer)
2. **2D drawing preview**: `view.preview()` displays matplotlib figure inline (Jupyter) or in popup window
3. **Live mode (scripts)**: File watcher auto-updates preview when Python source changes in .py files
4. **Notebook mode**: Jupyter notebooks render visualizations inline at time of cell execution (static snapshots per cell)

### Visualization Modes

#### Script Development (Live)
When running a .py file with `building.show(live=True)`:
- Opens OCP CAD Viewer window
- Watches source file for changes
- Auto-refreshes 3D view on save
- Ideal for rapid iteration on geometry

#### Notebook Development (Snapshot)
In Jupyter notebooks:
```python
# Early design iteration
building = Building()
building.add_walls(...)
building.show()  # Output cell 1: static snapshot of walls only

# Add floors
building.add_floors(...)
building.show()  # Output cell 2: static snapshot with walls + floors

# Final with MEP
building.add_hvac(...)
building.show()  # Output cell 3: static snapshot of complete model
```
Each `.show()` creates a static visualization reflecting the model state at that point in execution, preserving the design evolution throughout the notebook.

### Visualization Outputs
- **Development**: OCP CAD Viewer (OpenGL, interactive rotation/pan/zoom)
- **Documentation**: Matplotlib PNG/SVG exports for docs and presentations
- **Collaboration**: Speckle web viewer for team review
- **Validation**: IFC viewers (Bonsai, Solibri) for standards compliance

### VS Code Extension (v1.1)
Post-v1.0, a dedicated VS Code extension will provide:
- Side-panel 3D viewport with auto-refresh on save
- Hover tooltips showing element properties
- Jump-to-definition from 3D view to Python code
- Visual diff for model changes in version control

---

## Appendix: Feature Breakdown by Sprint

See [EPOCH_SPRINT_PLAN.md](./EPOCH_SPRINT_PLAN.md) for detailed sprint-by-sprint feature lists and dependencies.

---

**Prepared by:** Benny Friedman
**Last Updated:** March 2026
**Version:** 1.0
