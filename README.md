<p align="center">
  <img src="assets/bimascode-logo.svg" alt="BIM as Code" width="400">
</p>

<p align="center">
  <strong>Programmatic Building Information Modeling in Python</strong>
</p>

---

**BIM as Code** is a Python library for programmatic Building Information Modeling. Write Python code to create buildings, generate documentation drawings, and export to industry-standard formats like IFC and DXF.

## Status

🚧 **v1.0 Development In Progress** - Sprint 1 of 10

This project is under active development. See [EPOCH_SPRINT_PLAN.md](./EPOCH_SPRINT_PLAN.md) for the full roadmap.

## Vision

Replace GUI-based BIM authoring with a code-first workflow:

```python
from bimascode import Building, Level, Wall, Door

# Create a building
building = Building(name="My Building")

# Add levels
level_1 = Level(building, name="Level 1", elevation=0.0)
level_2 = Level(building, name="Level 2", elevation=4000.0)

# Add walls
wall = Wall(
    level=level_1,
    start=(0, 0),
    end=(10000, 0),
    height=4000,
    thickness=200
)

# Add a door
door = Door(wall, location=5000, width=900, height=2100)

# Export to IFC
building.export_ifc("my_building.ifc")

# Generate floor plan
plan = building.floor_plan(level_1)
plan.export("floor_plan.pdf")
```

## Features (v1.0)

- **Building Modeling**: Walls, floors, roofs, doors, windows, stairs
- **Structure**: Columns, beams, foundations
- **Spatial Organization**: Levels, grids, rooms
- **Documentation**: Floor plans, elevations, sections, schedules
- **Interoperability**: IFC4 import/export, DXF output
- **Visualization**: In-IDE 3D preview with OCP CAD Viewer

## Installation

```bash
pip install bimascode
```

For development:

```bash
git clone https://github.com/benjaminwfriedman/bimascode.git
cd bimascode
pip install -e ".[dev,viz]"
```

## Requirements

- Python 3.10 or higher
- build123d (geometry engine)
- IfcOpenShell (IFC support)
- ezdxf (DXF export)

## Documentation

See the [examples](./examples) directory for usage examples and the [docs](./docs) directory for detailed documentation.

## Project Structure

```
bimascode/
├── src/bimascode/
│   ├── core/          # Building, Level, Element
│   ├── architecture/  # Wall, Floor, Roof, Door, Window
│   ├── structure/     # Column, Beam, Foundation
│   ├── spatial/       # Room, Grid, Level
│   ├── drawing/       # Views, Annotations
│   ├── sheets/        # Sheet, Viewport, TitleBlock
│   ├── export/        # IFC, DXF, PDF, STEP
│   └── utils/         # Units, Materials, Parameters
├── tests/
├── docs/
└── examples/
```

## Development Roadmap

This project follows a 10-sprint development plan:

- **Sprint 1** (Current): IFC import/export, levels, grids, units
- **Sprint 2-3**: Walls, roofs, openings, wall joins
- **Sprint 4**: Rooms, structure (columns, beams)
- **Sprint 5**: Performance optimization
- **Sprint 6**: Drawing generation with professional line weights
- **Sprint 7-8**: Annotations, sheets, title blocks
- **Sprint 9**: Schedules and material takeoffs
- **Sprint 10**: Stairs and v1.0 release

See [EPOCH_SPRINT_PLAN.md](./EPOCH_SPRINT_PLAN.md) for details.

## Contributing

This project is currently in early development. Contributions will be welcomed after v1.0 release.

## License

MIT

## Credits

Built with:
- [build123d](https://github.com/gumyr/build123d) - Pythonic CAD library
- [IfcOpenShell](https://ifcopenshell.org/) - IFC toolkit
- [ezdxf](https://ezdxf.mozman.at/) - DXF library
- [OCP CAD Viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer) - 3D visualization
