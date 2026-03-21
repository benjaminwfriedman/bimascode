"""
Sprint 4 Demo: Spatial + Structural

This example demonstrates all Sprint 4 features:
- Rooms with area/volume calculations
- Room schedule generation
- Ceilings
- Structural columns on grid
- Beams between columns
- Structural walls and floors

The model creates a small office building with:
- Multiple named rooms
- Structural grid with columns
- Beams spanning between columns
- Ceiling elements
- Room schedule output
"""

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.spatial.room import Room
from bimascode.architecture import (
    # Wall components
    WallType,
    Wall,
    LayerFunction,
    # Floor components
    FloorType,
    Floor,
    create_concrete_floor_type,
    # Ceiling components (Sprint 4)
    CeilingType,
    Ceiling,
    create_gypsum_ceiling_type,
)
from bimascode.structure import (
    # Profile
    RectangularProfile,
    # Column components (Sprint 4)
    ColumnType,
    StructuralColumn,
    create_square_column_type,
    # Beam components (Sprint 4)
    BeamType,
    Beam,
    create_rectangular_beam_type,
)
from bimascode.utils.materials import MaterialLibrary


def main():
    """Create a building demonstrating Sprint 4 features."""

    print("=" * 60)
    print("Sprint 4 Demo: Spatial + Structural")
    print("=" * 60)

    # =========================================================================
    # 1. Create Building and Levels
    # =========================================================================

    print("\n1. Creating building and levels...")
    building = Building("Sprint 4 Office Building")
    ground_floor = Level(building, "Ground Floor", elevation=0)
    first_floor = Level(building, "First Floor", elevation=4000)

    print(f"   Building: {building.name}")
    print(f"   Ground Floor: {ground_floor.elevation_mm}mm")
    print(f"   First Floor: {first_floor.elevation_mm}mm")

    # =========================================================================
    # 2. Define Grid and Structure
    # =========================================================================

    print("\n2. Defining structural grid...")

    # Grid spacing: 6m x 6m bays
    grid_spacing_x = 6000  # mm
    grid_spacing_y = 6000  # mm
    num_bays_x = 3  # 3 bays in X direction
    num_bays_y = 2  # 2 bays in Y direction

    # Grid positions
    grid_x = [i * grid_spacing_x for i in range(num_bays_x + 1)]
    grid_y = [j * grid_spacing_y for j in range(num_bays_y + 1)]

    print(f"   Grid X positions: {grid_x}")
    print(f"   Grid Y positions: {grid_y}")

    # =========================================================================
    # 3. Create Structural Elements
    # =========================================================================

    print("\n3. Creating structural elements...")

    # Column type (400x400mm concrete)
    concrete = MaterialLibrary.concrete()
    column_type = create_square_column_type("Concrete Column", size=400, material=concrete)

    # Beam type (300x600mm concrete)
    beam_type = create_rectangular_beam_type("Concrete Beam", width=300, height=600, material=concrete)

    print(f"   Column type: {column_type.name} ({column_type.width}x{column_type.depth}mm)")
    print(f"   Beam type: {beam_type.name} ({beam_type.width}x{beam_type.height}mm)")

    # =========================================================================
    # 4. Create Columns at Grid Intersections
    # =========================================================================

    print("\n4. Creating columns at grid intersections...")

    columns = []
    column_height = first_floor.elevation_mm - ground_floor.elevation_mm

    for i, x in enumerate(grid_x):
        for j, y in enumerate(grid_y):
            column = StructuralColumn(
                column_type,
                ground_floor,
                position=(x, y),
                height=column_height,
                name=f"Col_{chr(65+i)}{j+1}"  # A1, A2, B1, B2, etc.
            )
            columns.append(column)

    print(f"   Created {len(columns)} columns")
    for col in columns[:4]:  # Show first 4
        print(f"     {col.name} at ({col.position[0]}, {col.position[1]})")
    print(f"     ... and {len(columns) - 4} more")

    # =========================================================================
    # 5. Create Beams Between Columns
    # =========================================================================

    print("\n5. Creating beams between columns...")

    beams = []
    beam_z = column_height - beam_type.height / 2  # Top of beam at column top

    # Beams in X direction
    for j, y in enumerate(grid_y):
        for i in range(len(grid_x) - 1):
            beam = Beam(
                beam_type,
                ground_floor,
                start_point=(grid_x[i], y, beam_z),
                end_point=(grid_x[i+1], y, beam_z),
                name=f"Beam_X{j+1}_{chr(65+i)}"
            )
            beams.append(beam)

    # Beams in Y direction
    for i, x in enumerate(grid_x):
        for j in range(len(grid_y) - 1):
            beam = Beam(
                beam_type,
                ground_floor,
                start_point=(x, grid_y[j], beam_z),
                end_point=(x, grid_y[j+1], beam_z),
                name=f"Beam_Y{i+1}_{j+1}"
            )
            beams.append(beam)

    print(f"   Created {len(beams)} beams")
    print(f"     X-direction beams: {len(grid_y) * (len(grid_x) - 1)}")
    print(f"     Y-direction beams: {len(grid_x) * (len(grid_y) - 1)}")

    # =========================================================================
    # 6. Create Structural Floor Slab
    # =========================================================================

    print("\n6. Creating structural floor slab...")

    floor_type = create_concrete_floor_type("Structural Slab", slab_thickness=200)

    # Floor covers entire building footprint
    floor_boundary = [
        (0, 0),
        (grid_x[-1], 0),
        (grid_x[-1], grid_y[-1]),
        (0, grid_y[-1]),
    ]

    structural_slab = Floor(
        floor_type,
        floor_boundary,
        ground_floor,
        structural=True,  # Sprint 4: Structural flag
        name="Ground Slab"
    )

    print(f"   {structural_slab.name}: {structural_slab.area_m2:.2f}m²")
    print(f"   Structural: {structural_slab.structural}")

    # =========================================================================
    # 7. Create Walls (including structural shear walls)
    # =========================================================================

    print("\n7. Creating walls...")

    wall_type = WallType("Exterior Wall")
    wall_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)
    wall_type.add_layer(MaterialLibrary.gypsum_board(), 12.5, LayerFunction.FINISH_INTERIOR)

    interior_wall_type = WallType("Interior Partition")
    interior_wall_type.add_layer(MaterialLibrary.gypsum_board(), 12.5, LayerFunction.FINISH_INTERIOR)
    interior_wall_type.add_layer(MaterialLibrary.insulation_mineral_wool(), 90, LayerFunction.THERMAL_INSULATION)
    interior_wall_type.add_layer(MaterialLibrary.gypsum_board(), 12.5, LayerFunction.FINISH_INTERIOR)

    wall_height = 3600  # mm

    # Exterior walls (structural shear walls on corners)
    walls = []

    # South wall - structural shear wall
    wall_south = Wall(
        wall_type,
        (0, 0), (grid_x[-1], 0),
        ground_floor,
        height=wall_height,
        structural=True,  # Sprint 4: Structural flag
        name="South Wall (Shear)"
    )
    walls.append(wall_south)

    # North wall - structural shear wall
    wall_north = Wall(
        wall_type,
        (grid_x[-1], grid_y[-1]), (0, grid_y[-1]),
        ground_floor,
        height=wall_height,
        structural=True,
        name="North Wall (Shear)"
    )
    walls.append(wall_north)

    # East and west walls
    wall_east = Wall(wall_type, (grid_x[-1], 0), (grid_x[-1], grid_y[-1]), ground_floor, height=wall_height, name="East Wall")
    wall_west = Wall(wall_type, (0, grid_y[-1]), (0, 0), ground_floor, height=wall_height, name="West Wall")
    walls.extend([wall_east, wall_west])

    # Interior partition walls
    interior_wall_1 = Wall(interior_wall_type, (grid_x[1], 0), (grid_x[1], grid_y[-1]), ground_floor, height=wall_height, name="Interior Wall 1")
    interior_wall_2 = Wall(interior_wall_type, (grid_x[2], 0), (grid_x[2], grid_y[1]), ground_floor, height=wall_height, name="Interior Wall 2")
    walls.extend([interior_wall_1, interior_wall_2])

    print(f"   Created {len(walls)} walls")
    for wall in walls:
        struct_label = " (STRUCTURAL)" if wall.structural else ""
        print(f"     {wall.name}: {wall.length:.0f}mm{struct_label}")

    # =========================================================================
    # 8. Create Rooms
    # =========================================================================

    print("\n8. Creating rooms...")

    # Room 101: Reception (first bay)
    room_reception = Room(
        name="Reception",
        number="101",
        boundary=[
            (0, 0),
            (grid_x[1], 0),
            (grid_x[1], grid_y[-1]),
            (0, grid_y[-1]),
        ],
        level=ground_floor,
        floor_to_ceiling_height=2700,
        floor_finish="Porcelain Tile",
        wall_finish="Paint - White",
        ceiling_finish="Acoustic Tile"
    )

    # Room 102: Open Office (middle bay)
    room_office = Room(
        name="Open Office",
        number="102",
        boundary=[
            (grid_x[1], 0),
            (grid_x[2], 0),
            (grid_x[2], grid_y[-1]),
            (grid_x[1], grid_y[-1]),
        ],
        level=ground_floor,
        floor_to_ceiling_height=2700,
        floor_finish="Carpet",
        wall_finish="Paint - Gray",
        ceiling_finish="Acoustic Tile"
    )

    # Room 103: Conference Room
    room_conference = Room(
        name="Conference Room",
        number="103",
        boundary=[
            (grid_x[2], 0),
            (grid_x[3], 0),
            (grid_x[3], grid_y[1]),
            (grid_x[2], grid_y[1]),
        ],
        level=ground_floor,
        floor_to_ceiling_height=2700,
        floor_finish="Carpet",
        wall_finish="Paint - Blue",
        ceiling_finish="Gypsum Board"
    )

    # Room 104: Break Room
    room_break = Room(
        name="Break Room",
        number="104",
        boundary=[
            (grid_x[2], grid_y[1]),
            (grid_x[3], grid_y[1]),
            (grid_x[3], grid_y[2]),
            (grid_x[2], grid_y[2]),
        ],
        level=ground_floor,
        floor_to_ceiling_height=2700,
        floor_finish="Vinyl",
        wall_finish="Paint - Yellow",
        ceiling_finish="Gypsum Board"
    )

    rooms = [room_reception, room_office, room_conference, room_break]

    print(f"   Created {len(rooms)} rooms")
    for room in rooms:
        print(f"     {room.number} - {room.name}: {room.area_m2:.2f}m², {room.volume_m3:.2f}m³")

    # =========================================================================
    # 9. Create Ceilings
    # =========================================================================

    print("\n9. Creating ceilings...")

    ceiling_type = create_gypsum_ceiling_type("Standard Ceiling", thickness=15)
    suspended_type = CeilingType("Acoustic Ceiling", thickness=20)

    ceilings = []
    for room in rooms:
        ceiling_t = suspended_type if room.ceiling_finish == "Acoustic Tile" else ceiling_type
        ceiling = Ceiling(
            ceiling_t,
            boundary=room.boundary,
            level=ground_floor,
            height=room.floor_to_ceiling_height,
            name=f"{room.name} Ceiling"
        )
        ceilings.append(ceiling)

    print(f"   Created {len(ceilings)} ceilings")
    for ceiling in ceilings:
        print(f"     {ceiling.name}: {ceiling.area_m2:.2f}m² at {ceiling.height}mm")

    # =========================================================================
    # 10. Generate Room Schedule
    # =========================================================================

    print("\n10. Generating room schedule...")

    schedule = building.room_schedule()
    print(f"\n{schedule.to_string(index=False)}")

    # Calculate totals
    total_area = schedule["area_m2"].sum()
    total_volume = schedule["volume_m3"].sum()

    print(f"\n   TOTALS:")
    print(f"   Total Area: {total_area:.2f} m²")
    print(f"   Total Volume: {total_volume:.2f} m³")

    # =========================================================================
    # 11. Export to IFC
    # =========================================================================

    print("\n11. Exporting to IFC...")

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"output/sprint4_demo_{timestamp}.ifc"
    building.export_ifc(output_path)

    print(f"   Exported to: {output_path}")

    # =========================================================================
    # Summary
    # =========================================================================

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    print(f"\nBuilding: {building.name}")
    print(f"Levels: {len(building.levels)}")

    print(f"\nStructural Grid:")
    print(f"  - Bays: {num_bays_x} x {num_bays_y}")
    print(f"  - Spacing: {grid_spacing_x/1000}m x {grid_spacing_y/1000}m")

    print(f"\nGround Floor Elements:")
    print(f"  - Columns: {len(columns)}")
    print(f"  - Beams: {len(beams)}")
    print(f"  - Walls: {len(walls)} ({sum(1 for w in walls if w.structural)} structural)")
    print(f"  - Rooms: {len(rooms)}")
    print(f"  - Ceilings: {len(ceilings)}")

    print(f"\nStructural Elements:")
    column_vol = sum(c.volume_m3 for c in columns)
    beam_vol = sum(b.volume_m3 for b in beams)
    print(f"  - Column volume: {column_vol:.2f} m³")
    print(f"  - Beam volume: {beam_vol:.2f} m³")
    print(f"  - Slab area: {structural_slab.area_m2:.2f} m²")

    print("\n" + "=" * 60)
    print("Sprint 4 Demo Complete!")
    print("=" * 60)
    print("\nOpen output/sprint4_demo.ifc in Bonsai or Autodesk Viewer to verify:")
    print("  - IfcColumn elements at grid intersections")
    print("  - IfcBeam elements spanning between columns")
    print("  - IfcWall elements with SHEAR type for structural walls")
    print("  - IfcSlab with BASESLAB type for structural slab")
    print("  - IfcSpace elements for rooms with properties")
    print("  - IfcCovering elements for ceilings")


if __name__ == "__main__":
    main()
