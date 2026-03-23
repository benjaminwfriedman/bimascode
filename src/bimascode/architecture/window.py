"""
Window element class for BIM as Code.

Windows are hosted in walls and create openings (voids) in their host.
They define position along the wall and sill height.
"""

from typing import Optional, List, Union, TYPE_CHECKING
from bimascode.core.type_instance import ElementInstance
from bimascode.core.world_geometry import HostedElementMixin
from bimascode.performance.bounding_box import BoundingBox
from bimascode.utils.units import Length, normalize_length
import math

if TYPE_CHECKING:
    from build123d import Location
    from bimascode.architecture.window_type import WindowType
    from bimascode.architecture.wall import Wall
    from bimascode.drawing.view_base import ViewRange
    from bimascode.drawing.primitives import Line2D, Arc2D, Polyline2D, Hatch2D


class Window(ElementInstance, HostedElementMixin):
    """
    A window element hosted in a wall.

    Windows are positioned along a wall by an offset from the wall's
    start point and a sill height (typically 900mm for standard windows).
    """

    def __init__(
        self,
        window_type: 'WindowType',
        host_wall: 'Wall',
        offset: Length | float,
        sill_height: Optional[Length | float] = None,
        name: Optional[str] = None
    ):
        """
        Create a window.

        Args:
            window_type: WindowType defining the window assembly
            host_wall: Wall that hosts this window
            offset: Distance from wall start point to window start
            sill_height: Height from floor to bottom of window
                        (defaults to type's default_sill_height)
            name: Optional name for this window
        """
        super().__init__(window_type, name)

        self._host_wall = host_wall

        # Store geometric parameters
        self.set_parameter("offset", normalize_length(offset).mm, override=False)

        # Use type's default sill height if not specified
        if sill_height is None:
            sill_height = window_type.default_sill_height
        self.set_parameter("sill_height", normalize_length(sill_height).mm, override=False)

        # Register with host wall
        if hasattr(host_wall, 'add_hosted_element'):
            host_wall.add_hosted_element(self)

    @property
    def host_wall(self) -> 'Wall':
        """Get the host wall."""
        return self._host_wall

    @property
    def offset(self) -> float:
        """Get offset from wall start in millimeters."""
        return self.get_parameter("offset")

    @property
    def sill_height(self) -> float:
        """Get sill height in millimeters."""
        return self.get_parameter("sill_height")

    @property
    def width(self) -> float:
        """Get window width in millimeters."""
        return self.type.overall_width

    @property
    def height(self) -> float:
        """Get window height in millimeters."""
        return self.type.overall_height

    @property
    def level(self):
        """Get the level from the host wall."""
        return self._host_wall.level

    def get_opening_geometry(self):
        """
        Get the void geometry for cutting into the host wall.

        Returns:
            build123d Box in wall's local coordinates
        """
        return self.type.create_opening_geometry(self)

    def get_world_position(self):
        """
        Get the window's position in world coordinates.

        Returns:
            (x, y, z) coordinates of window center
        """
        wall = self._host_wall
        wall_start = wall.start_point
        wall_angle = wall.angle

        # Calculate position along wall
        offset = self.offset + self.width / 2

        # Transform to world coordinates
        x = wall_start[0] + offset * math.cos(wall_angle)
        y = wall_start[1] + offset * math.sin(wall_angle)
        z = wall.level.elevation_mm + self.sill_height + self.height / 2

        return (x, y, z)

    def _get_host_transform(self) -> "Location":
        """Get the host wall's world transform.

        Returns:
            Location for wall position/rotation at window's Z elevation
        """
        from build123d import Location

        wall = self._host_wall
        wall_start = wall.start_point
        wall_angle_deg = wall.angle_degrees
        z = wall.level.elevation_mm + self.sill_height

        return Location(
            (wall_start[0], wall_start[1], z),
            (0, 0, 1),
            wall_angle_deg
        )

    def _get_local_transform(self) -> "Location":
        """Get window's position within the host wall.

        Window is positioned by offset along wall and centered in wall thickness.

        Returns:
            Location for window position in wall-local coordinates
        """
        from build123d import Location

        # Window local geometry: origin at bottom-left of frame, extends +X (width), +Y (depth), +Z (height)
        # Window frame_depth is how deep the window is (Y extent in window local coords)
        frame_depth = self.type.frame_depth

        # In wall-local coordinates:
        # - X runs along the wall length (from start to end)
        # - Y runs perpendicular to wall, with Y=0 at the wall centerline
        # - The wall extends from Y = -wall_thickness/2 to Y = +wall_thickness/2
        #
        # The window should be centered in the wall thickness:
        # - Window center Y should be at wall center Y (which is 0 in wall-local)
        # - So window Y ranges from -frame_depth/2 to +frame_depth/2
        # - Window local origin (Y=0) should map to wall-local Y = -frame_depth/2
        y_offset = -frame_depth / 2

        return Location((self.offset, y_offset, 0))

    def set_offset(self, offset: Length | float) -> None:
        """
        Set the offset from wall start.

        Args:
            offset: New offset value
        """
        self.set_parameter("offset", normalize_length(offset).mm, override=False)
        self.invalidate_geometry()
        self._host_wall.invalidate_geometry()

    def set_sill_height(self, sill_height: Length | float) -> None:
        """
        Set the sill height.

        Args:
            sill_height: New sill height value
        """
        self.set_parameter("sill_height", normalize_length(sill_height).mm, override=False)
        self.invalidate_geometry()
        self._host_wall.invalidate_geometry()

    def validate_position(self) -> bool:
        """
        Validate that the window fits within the host wall.

        Returns:
            True if window position is valid
        """
        wall = self._host_wall
        offset = self.offset
        width = self.width
        height = self.height
        sill = self.sill_height

        # Check horizontal bounds
        if offset < 0:
            return False
        if offset + width > wall.length:
            return False

        # Check vertical bounds
        if sill < 0:
            return False
        if sill + height > wall.height:
            return False

        return True

    def to_ifc(self, ifc_file, ifc_building_storey, ifc_wall):
        """
        Export window to IFC.

        Creates:
        - IfcOpeningElement (the void)
        - IfcRelVoidsElement (links opening to wall)
        - IfcWindow (the window element)
        - IfcRelFillsElement (links window to opening)

        Args:
            ifc_file: IFC file object
            ifc_building_storey: IFC building storey
            ifc_wall: IFC wall entity that hosts this window

        Returns:
            IfcWindow entity
        """
        from bimascode.export.ifc_geometry import build123d_to_ifc_brep

        wall = self._host_wall
        building = wall.level.building

        # Calculate window placement relative to wall
        offset = self.offset
        sill = self.sill_height

        # Create placement for opening (relative to wall)
        opening_location = ifc_file.createIfcCartesianPoint(
            (float(offset + self.width / 2), float(wall.width / 2), float(sill + self.height / 2))
        )

        opening_axis_placement = ifc_file.createIfcAxis2Placement3D(
            opening_location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0))
        )

        opening_placement = ifc_file.createIfcLocalPlacement(
            ifc_wall.ObjectPlacement,
            opening_axis_placement
        )

        # Create opening element
        ifc_opening = ifc_file.create_entity(
            "IfcOpeningElement",
            GlobalId=self._generate_guid(),
            OwnerHistory=building._ifc_owner_history,
            Name=f"{self.name}_Opening",
            Description="Window opening",
            ObjectPlacement=opening_placement,
            PredefinedType="OPENING"
        )

        # Create opening geometry (void box)
        opening_box = ifc_file.create_entity(
            "IfcBoundingBox",
            Corner=ifc_file.createIfcCartesianPoint((-self.width/2, -wall.width/2 - 1, -self.height/2)),
            XDim=self.width,
            YDim=wall.width + 2,
            ZDim=self.height
        )

        box_representation = ifc_file.createIfcShapeRepresentation(
            ifc_file.by_type("IfcGeometricRepresentationContext")[0],
            "Body",
            "BoundingBox",
            [opening_box]
        )

        opening_shape = ifc_file.createIfcProductDefinitionShape(
            None, None, [box_representation]
        )
        ifc_opening.Representation = opening_shape

        # Link opening to wall (IfcRelVoidsElement)
        ifc_file.createIfcRelVoidsElement(
            self._generate_guid(),
            building._ifc_owner_history,
            f"{self.name}VoidsWall",
            None,
            ifc_wall,
            ifc_opening
        )

        # Create window element
        window_location = ifc_file.createIfcCartesianPoint(
            (float(offset), 0.0, float(sill))
        )

        window_axis_placement = ifc_file.createIfcAxis2Placement3D(
            window_location,
            ifc_file.createIfcDirection((0.0, 0.0, 1.0)),
            ifc_file.createIfcDirection((1.0, 0.0, 0.0))
        )

        window_placement = ifc_file.createIfcLocalPlacement(
            ifc_wall.ObjectPlacement,
            window_axis_placement
        )

        ifc_window = ifc_file.create_entity(
            "IfcWindow",
            GlobalId=self.guid,
            OwnerHistory=building._ifc_owner_history,
            Name=self.name,
            Description=f"{self.type.name} window",
            ObjectPlacement=window_placement,
            OverallHeight=self.height,
            OverallWidth=self.width,
            PredefinedType="WINDOW"
        )

        # Create window geometry
        window_geom = self.get_geometry()
        if window_geom:
            ifc_brep = build123d_to_ifc_brep(window_geom, ifc_file)
            if ifc_brep:
                shape_representation = ifc_file.createIfcShapeRepresentation(
                    ifc_file.by_type("IfcGeometricRepresentationContext")[0],
                    "Body",
                    "Brep",
                    [ifc_brep]
                )

                product_shape = ifc_file.createIfcProductDefinitionShape(
                    None, None, [shape_representation]
                )
                ifc_window.Representation = product_shape

        # Link window to opening (IfcRelFillsElement)
        ifc_file.createIfcRelFillsElement(
            self._generate_guid(),
            building._ifc_owner_history,
            f"{self.name}FillsOpening",
            None,
            ifc_opening,
            ifc_window
        )

        # Associate with building storey
        ifc_file.createIfcRelContainedInSpatialStructure(
            self._generate_guid(),
            building._ifc_owner_history,
            f"Window{self.name}Container",
            None,
            [ifc_window],
            ifc_building_storey
        )

        # Associate with window type
        window_type_ifc = self.type.to_ifc(ifc_file)
        ifc_file.createIfcRelDefinesByType(
            self._generate_guid(),
            building._ifc_owner_history,
            None,
            None,
            [ifc_window],
            window_type_ifc
        )

        return ifc_window

    def get_bounding_box(self) -> BoundingBox:
        """Get axis-aligned bounding box for this window.

        The bounding box is calculated from the window's position
        in world coordinates relative to the host wall.

        Returns:
            BoundingBox encompassing the window geometry
        """
        wall = self._host_wall
        wall_start = wall.start_point
        wall_angle = wall.angle

        # Window position along wall
        offset = self.offset
        width = self.width
        height = self.height
        sill = self.sill_height

        # Calculate bounding box corners in world coordinates
        cos_a = math.cos(wall_angle)
        sin_a = math.sin(wall_angle)

        # Wall thickness for perpendicular extent
        wall_width = wall.width
        half_wall_width = wall_width / 2.0

        # Calculate the four corner points of the window footprint
        x1 = wall_start[0] + offset * cos_a - half_wall_width * sin_a
        y1 = wall_start[1] + offset * sin_a + half_wall_width * cos_a
        x2 = wall_start[0] + (offset + width) * cos_a - half_wall_width * sin_a
        y2 = wall_start[1] + (offset + width) * sin_a + half_wall_width * cos_a
        x3 = wall_start[0] + offset * cos_a + half_wall_width * sin_a
        y3 = wall_start[1] + offset * sin_a - half_wall_width * cos_a
        x4 = wall_start[0] + (offset + width) * cos_a + half_wall_width * sin_a
        y4 = wall_start[1] + (offset + width) * sin_a - half_wall_width * cos_a

        min_x = min(x1, x2, x3, x4)
        max_x = max(x1, x2, x3, x4)
        min_y = min(y1, y2, y3, y4)
        max_y = max(y1, y2, y3, y4)

        # Z coordinates
        base_z = wall.level.elevation_mm + sill
        top_z = base_z + height

        return BoundingBox(min_x, min_y, base_z, max_x, max_y, top_z)

    def get_plan_representation(
        self,
        cut_height: float,
        view_range: "ViewRange",
    ) -> List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]]:
        """Generate floor plan linework for this window.

        Windows are shown with three parallel lines (jambs and glass line).

        Args:
            cut_height: Z coordinate of the section cut
            view_range: View range parameters

        Returns:
            List of 2D geometry primitives
        """
        from bimascode.drawing.primitives import Point2D, Line2D
        from bimascode.drawing.line_styles import LineStyle, Layer

        result: List[Union["Line2D", "Arc2D", "Polyline2D", "Hatch2D"]] = []

        # Check if window is at the cut plane
        bbox = self.get_bounding_box()
        is_cut = bbox.min_z <= cut_height <= bbox.max_z

        if not is_cut:
            return result

        # Window style
        style = LineStyle.cut_wide()

        wall = self._host_wall
        wall_start = wall.start_point
        wall_angle = wall.angle
        half_wall = wall.width / 2.0

        # Calculate window position in world coordinates
        cos_a = math.cos(wall_angle)
        sin_a = math.sin(wall_angle)

        offset = self.offset
        width = self.width

        # Window jamb positions
        left_x = wall_start[0] + offset * cos_a
        left_y = wall_start[1] + offset * sin_a
        right_x = wall_start[0] + (offset + width) * cos_a
        right_y = wall_start[1] + (offset + width) * sin_a

        # Three lines representing the window:
        # 1. Outer jamb line
        # 2. Glass line (center)
        # 3. Inner jamb line

        # Glass line offset from wall center (typically small)
        glass_offset = 0.0  # At center

        for offset_mult, line_style in [
            (-0.35, style),  # Outer jamb (35% of half-wall towards outside)
            (0.0, style),    # Glass (center line)
            (0.35, style),   # Inner jamb (35% of half-wall towards inside)
        ]:
            perp_offset = half_wall * offset_mult

            line = Line2D(
                start=Point2D(
                    left_x - perp_offset * sin_a,
                    left_y + perp_offset * cos_a,
                ),
                end=Point2D(
                    right_x - perp_offset * sin_a,
                    right_y + perp_offset * cos_a,
                ),
                style=line_style,
                layer=Layer.WINDOW,
            )
            result.append(line)

        # Draw jamb end caps (perpendicular lines at each end)
        # Left jamb cap
        left_cap = Line2D(
            start=Point2D(
                left_x - half_wall * 0.35 * sin_a,
                left_y + half_wall * 0.35 * cos_a,
            ),
            end=Point2D(
                left_x + half_wall * 0.35 * sin_a,
                left_y - half_wall * 0.35 * cos_a,
            ),
            style=style,
            layer=Layer.WINDOW,
        )
        result.append(left_cap)

        # Right jamb cap
        right_cap = Line2D(
            start=Point2D(
                right_x - half_wall * 0.35 * sin_a,
                right_y + half_wall * 0.35 * cos_a,
            ),
            end=Point2D(
                right_x + half_wall * 0.35 * sin_a,
                right_y - half_wall * 0.35 * cos_a,
            ),
            style=style,
            layer=Layer.WINDOW,
        )
        result.append(right_cap)

        return result

    def __repr__(self) -> str:
        return (
            f"Window(name='{self.name}', type='{self.type.name}', "
            f"offset={self.offset:.1f}mm, sill={self.sill_height:.1f}mm, "
            f"host='{self._host_wall.name}')"
        )
