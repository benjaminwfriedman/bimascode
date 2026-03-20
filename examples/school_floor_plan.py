"""
School Floor Plan Demo

Creates a school with:
- Central lobby/entrance
- Two wings (East and West) extending from the lobby
- Classrooms along both sides of each wing corridor
- Boys and girls bathrooms on each wing
"""

from pathlib import Path

from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.architecture import Wall, create_basic_wall_type, detect_and_process_wall_joins, EndCapType
from bimascode.architecture.door import Door
from bimascode.architecture.door_type import DoorType
from bimascode.architecture.floor import Floor
from bimascode.architecture.floor_type import FloorType, LayerFunction
from bimascode.utils.materials import MaterialLibrary
from bimascode.performance.spatial_index import SpatialIndex
from bimascode.performance.representation_cache import RepresentationCache
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.view_base import ViewRange
from bimascode.drawing.dxf_exporter import DXFExporter


def create_school():
    """Create a school floor plan."""
    print("Creating school building...")

    # Create building and level
    building = Building("Elementary School")
    ground = Level(building, "Ground Floor", elevation=0)

    # Materials
    concrete = MaterialLibrary.concrete()

    # Wall types
    exterior_wall = create_basic_wall_type("Exterior Wall", 300, concrete)
    interior_wall = create_basic_wall_type("Interior Wall", 150, concrete)
    corridor_wall = create_basic_wall_type("Corridor Wall", 200, concrete)

    # Door types
    single_door = DoorType(name="Single Door", width=900, height=2100)
    double_door = DoorType(name="Double Door", width=1800, height=2100)

    # Dimensions (in mm)
    # Central lobby: 12m x 10m
    lobby_width = 12000
    lobby_depth = 10000

    # Corridor: 3m wide
    corridor_width = 3000

    # Classroom: 9m x 7m
    classroom_width = 9000
    classroom_depth = 7000

    # Bathroom: 6m x 5m
    bathroom_width = 6000
    bathroom_depth = 5000

    # Wing length (4 classrooms + 2 bathrooms per side)
    wing_length = 4 * classroom_width + bathroom_width  # 42m per wing

    # Center point of building (lobby center)
    center_x = wing_length + lobby_width / 2
    center_y = lobby_depth / 2 + classroom_depth  # Lobby is centered on corridor

    all_walls = []
    all_doors = []

    # =========================================================================
    # CENTRAL LOBBY
    # =========================================================================
    lobby_left = center_x - lobby_width / 2
    lobby_right = center_x + lobby_width / 2
    lobby_bottom = center_y - lobby_depth / 2
    lobby_top = center_y + lobby_depth / 2

    # Lobby exterior walls (front and back)
    lobby_front = Wall(exterior_wall, (lobby_left, lobby_bottom), (lobby_right, lobby_bottom), ground, name="Lobby Front")
    lobby_back = Wall(exterior_wall, (lobby_right, lobby_top), (lobby_left, lobby_top), ground, name="Lobby Back")
    all_walls.extend([lobby_front, lobby_back])

    # Main entrance doors (center of front wall)
    main_entrance = Door(double_door, lobby_front, offset=lobby_width/2 - 900)
    all_doors.append(main_entrance)

    # =========================================================================
    # CORRIDORS (extending from lobby sides)
    # =========================================================================
    corridor_y_bottom = center_y - corridor_width / 2
    corridor_y_top = center_y + corridor_width / 2

    # West wing corridor walls
    west_corridor_north = Wall(corridor_wall, (0, corridor_y_top), (lobby_left, corridor_y_top), ground, name="West Corridor North")
    west_corridor_south = Wall(corridor_wall, (lobby_left, corridor_y_bottom), (0, corridor_y_bottom), ground, name="West Corridor South")
    all_walls.extend([west_corridor_north, west_corridor_south])

    # East wing corridor walls
    east_corridor_north = Wall(corridor_wall, (lobby_right, corridor_y_top), (center_x * 2, corridor_y_top), ground, name="East Corridor North")
    east_corridor_south = Wall(corridor_wall, (center_x * 2, corridor_y_bottom), (lobby_right, corridor_y_bottom), ground, name="East Corridor South")
    all_walls.extend([east_corridor_north, east_corridor_south])

    # =========================================================================
    # WEST WING - North side classrooms (4) + Girls bathroom
    # =========================================================================
    x_pos = 0

    # Girls bathroom (at end of wing)
    girls_bath_walls = create_room(
        x_pos, corridor_y_top,
        bathroom_width, bathroom_depth,
        exterior_wall, interior_wall,
        ground, "West Girls Bathroom",
        north_exterior=True, west_exterior=True
    )
    all_walls.extend(girls_bath_walls)
    girls_bath_door = Door(single_door, girls_bath_walls[3], offset=bathroom_width/2 - 450)  # South wall
    all_doors.append(girls_bath_door)
    x_pos += bathroom_width

    # 4 classrooms on north side
    for i in range(4):
        room_walls = create_room(
            x_pos, corridor_y_top,
            classroom_width, classroom_depth,
            exterior_wall, interior_wall,
            ground, f"West Classroom N{i+1}",
            north_exterior=True
        )
        all_walls.extend(room_walls)
        classroom_door = Door(single_door, room_walls[3], offset=classroom_width/2 - 450)
        all_doors.append(classroom_door)
        x_pos += classroom_width

    # =========================================================================
    # WEST WING - South side classrooms (4) + Boys bathroom
    # =========================================================================
    x_pos = 0
    south_room_y = corridor_y_bottom - classroom_depth

    # Boys bathroom (at end of wing)
    boys_bath_walls = create_room(
        x_pos, south_room_y,
        bathroom_width, bathroom_depth,
        exterior_wall, interior_wall,
        ground, "West Boys Bathroom",
        south_exterior=True, west_exterior=True
    )
    all_walls.extend(boys_bath_walls)
    boys_bath_door = Door(single_door, boys_bath_walls[0], offset=bathroom_width/2 - 450)  # North wall
    all_doors.append(boys_bath_door)
    x_pos += bathroom_width

    # 4 classrooms on south side
    for i in range(4):
        room_walls = create_room(
            x_pos, south_room_y,
            classroom_width, classroom_depth,
            exterior_wall, interior_wall,
            ground, f"West Classroom S{i+1}",
            south_exterior=True
        )
        all_walls.extend(room_walls)
        classroom_door = Door(single_door, room_walls[0], offset=classroom_width/2 - 450)
        all_doors.append(classroom_door)
        x_pos += classroom_width

    # =========================================================================
    # EAST WING - North side classrooms (4) + Boys bathroom
    # =========================================================================
    x_pos = lobby_right

    # 4 classrooms on north side
    for i in range(4):
        room_walls = create_room(
            x_pos, corridor_y_top,
            classroom_width, classroom_depth,
            exterior_wall, interior_wall,
            ground, f"East Classroom N{i+1}",
            north_exterior=True
        )
        all_walls.extend(room_walls)
        classroom_door = Door(single_door, room_walls[3], offset=classroom_width/2 - 450)
        all_doors.append(classroom_door)
        x_pos += classroom_width

    # Boys bathroom (at end of wing)
    boys_bath_east_walls = create_room(
        x_pos, corridor_y_top,
        bathroom_width, bathroom_depth,
        exterior_wall, interior_wall,
        ground, "East Boys Bathroom",
        north_exterior=True, east_exterior=True
    )
    all_walls.extend(boys_bath_east_walls)
    boys_bath_east_door = Door(single_door, boys_bath_east_walls[3], offset=bathroom_width/2 - 450)
    all_doors.append(boys_bath_east_door)

    # =========================================================================
    # EAST WING - South side classrooms (4) + Girls bathroom
    # =========================================================================
    x_pos = lobby_right

    # 4 classrooms on south side
    for i in range(4):
        room_walls = create_room(
            x_pos, south_room_y,
            classroom_width, classroom_depth,
            exterior_wall, interior_wall,
            ground, f"East Classroom S{i+1}",
            south_exterior=True
        )
        all_walls.extend(room_walls)
        classroom_door = Door(single_door, room_walls[0], offset=classroom_width/2 - 450)
        all_doors.append(classroom_door)
        x_pos += classroom_width

    # Girls bathroom (at end of wing)
    girls_bath_east_walls = create_room(
        x_pos, south_room_y,
        bathroom_width, bathroom_depth,
        exterior_wall, interior_wall,
        ground, "East Girls Bathroom",
        south_exterior=True, east_exterior=True
    )
    all_walls.extend(girls_bath_east_walls)
    girls_bath_east_door = Door(single_door, girls_bath_east_walls[0], offset=bathroom_width/2 - 450)
    all_doors.append(girls_bath_east_door)

    # =========================================================================
    # WING END WALLS (exterior)
    # =========================================================================
    # West end - close off the corridor and connect to bathrooms
    west_end_north = Wall(exterior_wall, (0, corridor_y_top + bathroom_depth), (0, corridor_y_top), ground, name="West End North")
    west_end_corridor = Wall(exterior_wall, (0, corridor_y_top), (0, corridor_y_bottom), ground, name="West End Corridor")
    west_end_south = Wall(exterior_wall, (0, corridor_y_bottom), (0, south_room_y), ground, name="West End South")
    all_walls.extend([west_end_north, west_end_corridor, west_end_south])

    # East end - close off the corridor and connect to bathrooms
    east_end_x = center_x * 2
    east_end_north = Wall(exterior_wall, (east_end_x, corridor_y_top), (east_end_x, corridor_y_top + bathroom_depth), ground, name="East End North")
    east_end_corridor = Wall(exterior_wall, (east_end_x, corridor_y_bottom), (east_end_x, corridor_y_top), ground, name="East End Corridor")
    east_end_south = Wall(exterior_wall, (east_end_x, south_room_y), (east_end_x, corridor_y_bottom), ground, name="East End South")
    all_walls.extend([east_end_north, east_end_corridor, east_end_south])

    # =========================================================================
    # LOBBY SIDE WALLS (connecting to corridors)
    # =========================================================================
    # North side of lobby to corridor
    lobby_north_west = Wall(interior_wall, (lobby_left, lobby_top), (lobby_left, corridor_y_top), ground, name="Lobby NW")
    lobby_north_east = Wall(interior_wall, (lobby_right, corridor_y_top), (lobby_right, lobby_top), ground, name="Lobby NE")

    # South side of lobby to corridor
    lobby_south_west = Wall(interior_wall, (lobby_left, corridor_y_bottom), (lobby_left, lobby_bottom), ground, name="Lobby SW")
    lobby_south_east = Wall(interior_wall, (lobby_right, lobby_bottom), (lobby_right, corridor_y_bottom), ground, name="Lobby SE")

    all_walls.extend([lobby_north_west, lobby_north_east, lobby_south_west, lobby_south_east])

    # Doors from lobby to corridors
    west_corridor_door = Door(double_door, lobby_north_west, offset=500)
    east_corridor_door = Door(double_door, lobby_north_east, offset=500)
    all_doors.extend([west_corridor_door, east_corridor_door])

    # Process wall joins
    print(f"  Processing {len(all_walls)} walls...")
    adjustments = detect_and_process_wall_joins(all_walls, end_cap_type=EndCapType.EXTERIOR)
    for wall, adj in adjustments.items():
        wall._trim_adjustments = adj
    print(f"  Processed {len(adjustments)} wall join adjustments")

    print(f"  Created {len(all_walls)} walls")
    print(f"  Created {len(all_doors)} doors")

    # Create floor
    floor_type = FloorType("Concrete Slab")
    floor_type.add_layer(concrete, 200, LayerFunction.STRUCTURE, structural=True)

    # Simple rectangular floor boundary
    floor_boundary = [
        (0, south_room_y),
        (center_x * 2, south_room_y),
        (center_x * 2, corridor_y_top + classroom_depth),
        (0, corridor_y_top + classroom_depth),
    ]
    floor = Floor(floor_type, floor_boundary, ground, name="Ground Floor Slab")

    return building, ground, all_walls, all_doors, [floor]


def create_room(x, y, width, depth, exterior_type, interior_type, level, name,
                north_exterior=False, south_exterior=False,
                east_exterior=False, west_exterior=False):
    """
    Create walls for a rectangular room.

    Args:
        x, y: Bottom-left corner position
        width, depth: Room dimensions
        exterior_type, interior_type: Wall types
        level: Building level
        name: Room name prefix
        north/south/east/west_exterior: Which walls are exterior

    Returns:
        List of walls [north, east, south, west]
    """
    walls = []

    # North wall (y + depth)
    wall_type = exterior_type if north_exterior else interior_type
    north = Wall(wall_type, (x, y + depth), (x + width, y + depth), level, name=f"{name} North")
    walls.append(north)

    # East wall (x + width)
    wall_type = exterior_type if east_exterior else interior_type
    east = Wall(wall_type, (x + width, y + depth), (x + width, y), level, name=f"{name} East")
    walls.append(east)

    # South wall (y)
    wall_type = exterior_type if south_exterior else interior_type
    south = Wall(wall_type, (x + width, y), (x, y), level, name=f"{name} South")
    walls.append(south)

    # West wall (x)
    wall_type = exterior_type if west_exterior else interior_type
    west = Wall(wall_type, (x, y), (x, y + depth), level, name=f"{name} West")
    walls.append(west)

    return walls


def generate_floor_plan(level, walls, doors, floors, output_path):
    """Generate floor plan DXF."""
    print(f"\nGenerating floor plan: {output_path}")

    # Create spatial index and populate with elements
    spatial_index = SpatialIndex()
    all_elements = walls + doors + floors

    for element in all_elements:
        spatial_index.insert(element)

    print(f"  Indexed {len(all_elements)} elements")

    # Create representation cache
    cache = RepresentationCache()

    # Create floor plan view
    view_range = ViewRange(
        cut_height=1200,
        top_clip=2700,
        bottom_clip=0,
    )

    floor_plan = FloorPlanView(
        name="School Ground Floor Plan",
        level=level,
        view_range=view_range,
    )

    # Generate the view
    result = floor_plan.generate(spatial_index, cache)

    print(f"  Generated {result.element_count} elements")
    print(f"  Total geometry: {result.total_geometry_count} items")
    print(f"    - Lines: {len(result.lines)}")
    print(f"    - Arcs: {len(result.arcs)}")
    print(f"    - Polylines: {len(result.polylines)}")
    print(f"    - Hatches: {len(result.hatches)}")
    print(f"  Generation time: {result.generation_time*1000:.1f}ms")

    # Export to DXF
    exporter = DXFExporter()
    exporter.export(result, str(output_path))
    print(f"  DXF export complete: {output_path}")


def main():
    """Run the demo."""
    print("=" * 60)
    print("School Floor Plan Demo")
    print("=" * 60)

    # Create output directory
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Create school
    building, level, walls, doors, floors = create_school()

    # Export IFC
    ifc_path = output_dir / "school.ifc"
    print(f"\nExporting to IFC: {ifc_path}")
    building.export_ifc(str(ifc_path))
    print(f"  IFC export complete")

    # Generate floor plan
    dxf_path = output_dir / "school_floor_plan.dxf"
    generate_floor_plan(level, walls, doors, floors, dxf_path)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print(f"\nOutput files:")
    print(f"  IFC: {ifc_path}")
    print(f"  DXF: {dxf_path}")
    print("\nSchool layout:")
    print("  - Central lobby with main entrance")
    print("  - West wing: 4 classrooms (north) + 4 classrooms (south)")
    print("  - West wing: Girls bathroom (north end) + Boys bathroom (south end)")
    print("  - East wing: 4 classrooms (north) + 4 classrooms (south)")
    print("  - East wing: Boys bathroom (north end) + Girls bathroom (south end)")
    print("  - Total: 16 classrooms, 4 bathrooms")
    print("=" * 60)


if __name__ == "__main__":
    main()
