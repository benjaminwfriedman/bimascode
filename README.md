<p align="center">
  <img src="assets/bimascode-logo.svg" alt="BIM as Code" width="400">
</p>

<p align="center">
  <strong>Programmatic Building Information Modeling in Python</strong>
</p>

---

**BIM as Code** is a Python library for programmatic Building Information Modeling. Write Python code to create buildings, generate documentation drawings, and export to industry-standard formats like IFC and DXF.

## Quick Example

```python
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import Wall, create_basic_wall_type, Door, DoorType, Window, WindowType
from bimascode.utils.materials import MaterialLibrary

# Create building and level
building = Building("My Building")
ground = Level(building, "Ground Floor", elevation=0)

# Define types
concrete = MaterialLibrary.concrete()
wall_type = create_basic_wall_type("Exterior Wall", 300, concrete)
door_type = DoorType(name="Entry Door", width=900, height=2100)
window_type = WindowType(name="Standard Window", width=1200, height=1500, default_sill_height=900)

# Create walls (10m x 8m building)
wall_south = Wall(wall_type, (0, 0), (10000, 0), ground)
wall_east = Wall(wall_type, (10000, 0), (10000, 8000), ground)
wall_north = Wall(wall_type, (10000, 8000), (0, 8000), ground)
wall_west = Wall(wall_type, (0, 8000), (0, 0), ground)

# Add door and window
door = Door(door_type, wall_south, offset=2000)
window = Window(window_type, wall_east, offset=3000)

# Export to IFC
building.export_ifc("my_building.ifc")
```

## Features

### Spatial Organization
- **Buildings** - Root container with unit system (metric/imperial)
- **Levels** - Building storeys with elevation tracking
- **Grids** - Architectural layout axes
- **Rooms** - Spatial elements with area/volume calculations

### Architectural Elements
- **Walls** - Straight walls with compound layer stacks
- **Wall Joins** - Automatic corner, T-junction, and cross detection
- **Doors** - Hosted in walls with configurable types
- **Windows** - Hosted in walls with sill height control
- **Floors/Slabs** - Horizontal elements with layer stacks
- **Roofs** - Flat roofs with drainage slope
- **Ceilings** - Suspended ceiling elements
- **Openings** - Voids in floors/roofs (stairs, shafts, skylights)

### Structural Elements
- **Columns** - Vertical structural members with section profiles
- **Beams** - Horizontal/sloped members spanning between points

### Drawing Generation
- **Floor Plans** - Horizontal section cuts with configurable cut height
- **Elevations** - Exterior projections with hidden line removal
- **Sections** - Vertical section cuts with depth control
- **View Templates** - Visibility and graphic overrides per element category
- **Line Weights** - AIA/NCS standard line weights (0.13mm to 0.70mm)
- **DXF Export** - Professional CAD output with proper layers

### Performance
- **Spatial Indexing** - R-tree for fast element queries
- **Representation Caching** - Cached 2D linework with automatic invalidation

### Export Formats
- **IFC4/IFC2x3** - Full project hierarchy, properties, and materials
- **DXF** - AIA-compliant layers and line weights

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

- Python 3.10+
- [build123d](https://github.com/gumyr/build123d) - Geometry engine
- [IfcOpenShell](https://ifcopenshell.org/) - IFC support
- [ezdxf](https://ezdxf.mozman.at/) - DXF export

## Examples

See the [examples/](./examples) directory:

| Example | Description |
|---------|-------------|
| `sprint6_demo.py` | Simple house with walls, doors, windows → IFC + DXF |
| `school_floor_plan.py` | School with 16 classrooms, lobby, corridors |
| `office_world_geometry_demo.py` | Office with exposed structural grid, view templates |

## Documentation

See the [docs/](./docs) directory for detailed documentation.

## Project Structure

```
bimascode/
├── src/bimascode/
│   ├── core/           # Base Element class, type/instance pattern
│   ├── spatial/        # Building, Level, Grid, Room
│   ├── architecture/   # Wall, Floor, Roof, Door, Window, Ceiling
│   ├── structure/      # Column, Beam, Profile
│   ├── drawing/        # Floor plans, elevations, sections, DXF export
│   ├── performance/    # Spatial index, representation cache
│   ├── export/         # IFC exporter/importer
│   └── utils/          # Units, Materials
├── examples/
├── tests/
└── docs/
```

## License

MIT

## Credits

Built with:
- [build123d](https://github.com/gumyr/build123d) - Pythonic CAD library
- [IfcOpenShell](https://ifcopenshell.org/) - IFC toolkit
- [ezdxf](https://ezdxf.mozman.at/) - DXF library
- [OCP CAD Viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer) - 3D visualization
