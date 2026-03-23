"""
School Views Demo - Testing Section and Elevation Views

This extends the school floor plan demo to also generate:
- Section views (through the lobby and wings)
- Elevation views (North, South, East, West)
"""

from datetime import datetime
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
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.elevation_view import ElevationView, ElevationDirection
from bimascode.drawing.view_base import ViewRange, ViewScale
from bimascode.drawing.dxf_exporter import DXFExporter
from bimascode.export import IFCExporter


def create_school():
    """Create a school floor plan (from school_floor_plan.py)."""
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
    lobby_width = 12000
    lobby_depth = 10000
    corridor_width = 3000
    classroom_width = 9000
    classroom_depth = 7000
    bathroom_width = 6000
    bathroom_depth = 5000

    wing_length = 4 * classroom_width + bathroom_width

    center_x = wing_length + lobby_width / 2
    center_y = lobby_depth / 2 + classroom_depth

    all_walls = []
    all_doors = []

    # CENTRAL LOBBY
    lobby_left = center_x - lobby_width / 2
    lobby_right = center_x + lobby_width / 2
    lobby_bottom = center_y - lobby_depth / 2
    lobby_top = center_y + lobby_depth / 2

    lobby_front = Wall(exterior_wall, (lobby_left, lobby_bottom), (lobby_right, lobby_bottom), ground, name="Lobby Front")
    lobby_back = Wall(exterior_wall, (lobby_right, lobby_top), (lobby_left, lobby_top), ground, name="Lobby Back")
    all_walls.extend([lobby_front, lobby_back])

    main_entrance = Door(double_door, lobby_front, offset=lobby_width/2 - 900)
    all_doors.append(main_entrance)

    # CORRIDORS
    corridor_y_bottom = center_y - corridor_width / 2
    corridor_y_top = center_y + corridor_width / 2

    west_corridor_north = Wall(corridor_wall, (0, corridor_y_top), (lobby_left, corridor_y_top), ground, name="West Corridor North")
    west_corridor_south = Wall(corridor_wall, (lobby_left, corridor_y_bottom), (0, corridor_y_bottom), ground, name="West Corridor South")
    all_walls.extend([west_corridor_north, west_corridor_south])

    east_corridor_north = Wall(corridor_wall, (lobby_right, corridor_y_top), (center_x * 2, corridor_y_top), ground, name="East Corridor North")
    east_corridor_south = Wall(corridor_wall, (center_x * 2, corridor_y_bottom), (lobby_right, corridor_y_bottom), ground, name="East Corridor South")
    all_walls.extend([east_corridor_north, east_corridor_south])

    # WEST WING - North side
    x_pos = 0
    girls_bath_walls = create_room(x_pos, corridor_y_top, bathroom_width, bathroom_depth,
                                   exterior_wall, interior_wall, ground, "West Girls Bathroom",
                                   north_exterior=True, west_exterior=True)
    all_walls.extend(girls_bath_walls)
    girls_bath_door = Door(single_door, girls_bath_walls[3], offset=bathroom_width/2 - 450)
    all_doors.append(girls_bath_door)
    x_pos += bathroom_width

    for i in range(4):
        room_walls = create_room(x_pos, corridor_y_top, classroom_width, classroom_depth,
                                exterior_wall, interior_wall, ground, f"West Classroom N{i+1}",
                                north_exterior=True)
        all_walls.extend(room_walls)
        classroom_door = Door(single_door, room_walls[3], offset=classroom_width/2 - 450)
        all_doors.append(classroom_door)
        x_pos += classroom_width

    # WEST WING - South side
    x_pos = 0
    south_room_y = corridor_y_bottom - classroom_depth

    boys_bath_walls = create_room(x_pos, south_room_y, bathroom_width, bathroom_depth,
                                  exterior_wall, interior_wall, ground, "West Boys Bathroom",
                                  south_exterior=True, west_exterior=True)
    all_walls.extend(boys_bath_walls)
    boys_bath_door = Door(single_door, boys_bath_walls[0], offset=bathroom_width/2 - 450)
    all_doors.append(boys_bath_door)
    x_pos += bathroom_width

    for i in range(4):
        room_walls = create_room(x_pos, south_room_y, classroom_width, classroom_depth,
                                exterior_wall, interior_wall, ground, f"West Classroom S{i+1}",
                                south_exterior=True)
        all_walls.extend(room_walls)
        classroom_door = Door(single_door, room_walls[0], offset=classroom_width/2 - 450)
        all_doors.append(classroom_door)
        x_pos += classroom_width

    # EAST WING - North side
    x_pos = lobby_right
    for i in range(4):
        room_walls = create_room(x_pos, corridor_y_top, classroom_width, classroom_depth,
                                exterior_wall, interior_wall, ground, f"East Classroom N{i+1}",
                                north_exterior=True)
        all_walls.extend(room_walls)
        classroom_door = Door(single_door, room_walls[3], offset=classroom_width/2 - 450)
        all_doors.append(classroom_door)
        x_pos += classroom_width

    boys_bath_east_walls = create_room(x_pos, corridor_y_top, bathroom_width, bathroom_depth,
                                       exterior_wall, interior_wall, ground, "East Boys Bathroom",
                                       north_exterior=True, east_exterior=True)
    all_walls.extend(boys_bath_east_walls)
    boys_bath_east_door = Door(single_door, boys_bath_east_walls[3], offset=bathroom_width/2 - 450)
    all_doors.append(boys_bath_east_door)

    # EAST WING - South side
    x_pos = lobby_right
    for i in range(4):
        room_walls = create_room(x_pos, south_room_y, classroom_width, classroom_depth,
                                exterior_wall, interior_wall, ground, f"East Classroom S{i+1}",
                                south_exterior=True)
        all_walls.extend(room_walls)
        classroom_door = Door(single_door, room_walls[0], offset=classroom_width/2 - 450)
        all_doors.append(classroom_door)
        x_pos += classroom_width

    girls_bath_east_walls = create_room(x_pos, south_room_y, bathroom_width, bathroom_depth,
                                        exterior_wall, interior_wall, ground, "East Girls Bathroom",
                                        south_exterior=True, east_exterior=True)
    all_walls.extend(girls_bath_east_walls)
    girls_bath_east_door = Door(single_door, girls_bath_east_walls[0], offset=bathroom_width/2 - 450)
    all_doors.append(girls_bath_east_door)

    # WING END WALLS
    # West end - close off the corridor and connect to bathrooms
    west_end_north = Wall(exterior_wall, (0, corridor_y_top + bathroom_depth), (0, corridor_y_top), ground, name="West End North")
    west_end_corridor = Wall(exterior_wall, (0, corridor_y_top), (0, corridor_y_bottom), ground, name="West End Corridor")
    west_end_south = Wall(exterior_wall, (0, corridor_y_bottom), (0, south_room_y + bathroom_depth), ground, name="West End South")
    all_walls.extend([west_end_north, west_end_corridor, west_end_south])

    # East end - close off the corridor and connect to bathrooms
    east_end_x = center_x * 2
    east_end_north = Wall(exterior_wall, (east_end_x, corridor_y_top), (east_end_x, corridor_y_top + bathroom_depth), ground, name="East End North")
    east_end_corridor = Wall(exterior_wall, (east_end_x, corridor_y_bottom), (east_end_x, corridor_y_top), ground, name="East End Corridor")
    east_end_south = Wall(exterior_wall, (east_end_x, south_room_y + bathroom_depth), (east_end_x, corridor_y_bottom), ground, name="East End South")
    all_walls.extend([east_end_north, east_end_corridor, east_end_south])

    # LOBBY SIDE WALLS
    lobby_north_west = Wall(interior_wall, (lobby_left, lobby_top), (lobby_left, corridor_y_top), ground, name="Lobby NW")
    lobby_north_east = Wall(interior_wall, (lobby_right, corridor_y_top), (lobby_right, lobby_top), ground, name="Lobby NE")
    lobby_south_west = Wall(interior_wall, (lobby_left, corridor_y_bottom), (lobby_left, lobby_bottom), ground, name="Lobby SW")
    lobby_south_east = Wall(interior_wall, (lobby_right, lobby_bottom), (lobby_right, corridor_y_bottom), ground, name="Lobby SE")
    all_walls.extend([lobby_north_west, lobby_north_east, lobby_south_west, lobby_south_east])

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

    floor_boundary = [
        (0, south_room_y),
        (center_x * 2, south_room_y),
        (center_x * 2, corridor_y_top + classroom_depth),
        (0, corridor_y_top + classroom_depth),
    ]
    floor = Floor(floor_type, floor_boundary, ground, name="Ground Floor Slab")

    # Return building dimensions for view generation
    building_dims = {
        "center_x": center_x,
        "center_y": center_y,
        "lobby_left": lobby_left,
        "lobby_right": lobby_right,
        "lobby_bottom": lobby_bottom,
        "lobby_top": lobby_top,
        "corridor_y_bottom": corridor_y_bottom,
        "corridor_y_top": corridor_y_top,
        "south_room_y": south_room_y,
        "north_room_y": corridor_y_top + classroom_depth,
        "west_x": 0,
        "east_x": center_x * 2,
    }

    return building, ground, all_walls, all_doors, [floor], building_dims


def create_room(x, y, width, depth, exterior_type, interior_type, level, name,
                north_exterior=False, south_exterior=False,
                east_exterior=False, west_exterior=False):
    """Create walls for a rectangular room."""
    walls = []

    wall_type = exterior_type if north_exterior else interior_type
    north = Wall(wall_type, (x, y + depth), (x + width, y + depth), level, name=f"{name} North")
    walls.append(north)

    wall_type = exterior_type if east_exterior else interior_type
    east = Wall(wall_type, (x + width, y + depth), (x + width, y), level, name=f"{name} East")
    walls.append(east)

    wall_type = exterior_type if south_exterior else interior_type
    south = Wall(wall_type, (x + width, y), (x, y), level, name=f"{name} South")
    walls.append(south)

    wall_type = exterior_type if west_exterior else interior_type
    west = Wall(wall_type, (x, y), (x, y + depth), level, name=f"{name} West")
    walls.append(west)

    return walls


def create_spatial_index(walls, doors, floors):
    """Create and populate spatial index."""
    spatial_index = SpatialIndex()
    all_elements = walls + doors + floors

    for element in all_elements:
        spatial_index.insert(element)

    return spatial_index


def generate_floor_plan(level, spatial_index, cache, output_path):
    """Generate floor plan DXF."""
    print(f"\nGenerating floor plan: {output_path.name}")

    view_range = ViewRange(
        cut_height=1200,
        top=2700,
        bottom=0,
        view_depth=0,
    )

    floor_plan = FloorPlanView(
        name="School Ground Floor Plan",
        level=level,
        view_range=view_range,
    )

    result = floor_plan.generate(spatial_index, cache)
    print_result_stats(result)

    exporter = DXFExporter()
    exporter.export(result, str(output_path))
    print(f"  Exported to: {output_path}")


def generate_section_view(name, spatial_index, cache, plane_point, plane_normal, output_path):
    """Generate a section view DXF."""
    print(f"\nGenerating section: {name}")
    print(f"  Plane point: {plane_point}")
    print(f"  Plane normal: {plane_normal}")

    section = SectionView(
        name=name,
        plane_point=plane_point,
        plane_normal=plane_normal,
        depth=50000,  # 50m look depth
        height_range=(0, 4000),  # Ground floor only
        scale=ViewScale.SCALE_1_50,
        show_hidden_lines=True,
    )

    result = section.generate(spatial_index, cache)
    print_result_stats(result)

    exporter = DXFExporter()
    exporter.export(result, str(output_path))
    print(f"  Exported to: {output_path}")


def generate_elevation_view(name, spatial_index, cache, direction, output_path, front_clip_depth=500):
    """Generate an elevation view DXF."""
    print(f"\nGenerating elevation: {name}")
    print(f"  Direction: {direction}")
    print(f"  Front clip depth: {front_clip_depth}mm")

    elevation = ElevationView(
        name=name,
        direction=direction,
        front_clip_depth=front_clip_depth,  # Only include elements near the facade
        scale=ViewScale.SCALE_1_100,
        show_hidden_lines=False,
    )

    result = elevation.generate(spatial_index, cache)
    print_result_stats(result)

    exporter = DXFExporter()
    exporter.export(result, str(output_path))
    print(f"  Exported to: {output_path}")


def print_result_stats(result):
    """Print statistics about a view result."""
    print(f"  Elements: {result.element_count}")
    print(f"  Total geometry: {result.total_geometry_count}")
    print(f"    - Lines: {len(result.lines)}")
    print(f"    - Arcs: {len(result.arcs)}")
    print(f"    - Polylines: {len(result.polylines)}")
    print(f"    - Hatches: {len(result.hatches)}")
    print(f"  Cache hits: {result.cache_hits}")
    print(f"  Generation time: {result.generation_time*1000:.1f}ms")


def main():
    """Run the demo."""
    print("=" * 70)
    print("School Views Demo - Section and Elevation Testing")
    print("=" * 70)

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / "output" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Create school
    building, level, walls, doors, floors, dims = create_school()

    # Create spatial index and cache
    spatial_index = create_spatial_index(walls, doors, floors)
    cache = RepresentationCache()

    print(f"\nSpatial index created with {len(walls) + len(doors) + len(floors)} elements")
    print(f"Building bounds: X=[{dims['west_x']:.0f}, {dims['east_x']:.0f}], Y=[{dims['south_room_y']:.0f}, {dims['north_room_y']:.0f}]")

    # =========================================================================
    # IFC EXPORT
    # =========================================================================
    ifc_file = output_dir / "school.ifc"
    building.export_ifc(str(ifc_file))
    print(f"\nExported IFC: {ifc_file}")

    # =========================================================================
    # FLOOR PLAN
    # =========================================================================
    generate_floor_plan(
        level, spatial_index, cache,
        output_dir / "school_floor_plan.dxf"
    )

    # =========================================================================
    # SECTION VIEWS
    # =========================================================================

    # Section A-A: Through the center of the lobby (East-West cut)
    # Looking North (from the front entrance toward the back)
    generate_section_view(
        "Section A-A (Through Lobby, Looking North)",
        spatial_index, cache,
        (dims['center_x'], dims['center_y'], 0),
        (0, 1, 0),  # Normal points North, section cuts E-W
        output_dir / "school_section_AA.dxf"
    )

    # Section A-A Reversed: Same cut, looking South
    generate_section_view(
        "Section A-A (Through Lobby, Looking South)",
        spatial_index, cache,
        (dims['center_x'], dims['center_y'], 0),
        (0, -1, 0),  # Normal points South
        output_dir / "school_section_AA_south.dxf"
    )

    # Section B-B: Through the corridor (North-South cut)
    # Looking West (from East wing toward West wing)
    generate_section_view(
        "Section B-B (Through Corridor)",
        spatial_index, cache,
        (dims['center_x'], dims['center_y'], 0),
        (-1, 0, 0),  # Normal points West, section cuts N-S
        output_dir / "school_section_BB.dxf"
    )

    # =========================================================================
    # ELEVATION VIEWS
    # =========================================================================

    # Use small front_clip_depth to only capture facade elements
    # (exterior wall thickness is 300mm, so 500mm captures walls + doors in them)
    elevation_depth = 500

    # North Elevation - shows the North face (back of building)
    generate_elevation_view(
        "North Elevation",
        spatial_index, cache,
        ElevationDirection.NORTH,
        output_dir / "school_elevation_north.dxf",
        front_clip_depth=elevation_depth
    )

    # South Elevation - shows the South face (main entrance)
    generate_elevation_view(
        "South Elevation",
        spatial_index, cache,
        ElevationDirection.SOUTH,
        output_dir / "school_elevation_south.dxf",
        front_clip_depth=elevation_depth
    )

    # East Elevation - shows the East face (East wing end)
    generate_elevation_view(
        "East Elevation",
        spatial_index, cache,
        ElevationDirection.EAST,
        output_dir / "school_elevation_east.dxf",
        front_clip_depth=elevation_depth
    )

    # West Elevation - shows the West face (West wing end)
    generate_elevation_view(
        "West Elevation",
        spatial_index, cache,
        ElevationDirection.WEST,
        output_dir / "school_elevation_west.dxf",
        front_clip_depth=elevation_depth
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print(f"  Floor Plan:  school_floor_plan.dxf")
    print(f"  Sections:    school_section_AA.dxf (through lobby)")
    print(f"               school_section_BB.dxf (through corridor)")
    print(f"               school_section_CC.dxf (through west wing)")
    print(f"  Elevations:  school_elevation_north.dxf")
    print(f"               school_elevation_south.dxf")
    print(f"               school_elevation_east.dxf")
    print(f"               school_elevation_west.dxf")
    print(f"\nOutput directory: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
