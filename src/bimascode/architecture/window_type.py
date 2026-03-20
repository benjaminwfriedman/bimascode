"""
Window types for BIM as Code.

This module implements the WindowType class which defines window assemblies
with frame and glazing geometry. Window types specify standard dimensions
that can be instantiated as Window elements hosted in walls.
"""

from typing import Optional
from enum import Enum
from build123d import Box, Location, Compound
from bimascode.core.type_instance import ElementType
from bimascode.utils.materials import Material
from bimascode.utils.units import Length, normalize_length


class WindowOperationType(Enum):
    """IFC window operation type."""
    SINGLE_PANEL = "SINGLE_PANEL"
    DOUBLE_PANEL_VERTICAL = "DOUBLE_PANEL_VERTICAL"
    DOUBLE_PANEL_HORIZONTAL = "DOUBLE_PANEL_HORIZONTAL"
    TRIPLE_PANEL_VERTICAL = "TRIPLE_PANEL_VERTICAL"
    SLIDING_HORIZONTAL = "SLIDING_HORIZONTAL"
    SLIDING_VERTICAL = "SLIDING_VERTICAL"
    FIXED = "FIXED"
    CASEMENT = "CASEMENT"
    AWNING = "AWNING"
    HOPPER = "HOPPER"


class WindowType(ElementType):
    """
    Window type defining standard window dimensions and geometry.

    A window type specifies the width, height, frame dimensions,
    sill height, and mullion configuration for window instances.
    """

    def __init__(
        self,
        name: str,
        width: Length | float = 1200.0,
        height: Length | float = 1500.0,
        frame_width: Length | float = 50.0,
        frame_depth: Length | float = 70.0,
        glazing_thickness: Length | float = 24.0,
        mullion_count: int = 0,
        mullion_width: Length | float = 50.0,
        default_sill_height: Length | float = 900.0,
        operation_type: WindowOperationType = WindowOperationType.SINGLE_PANEL,
        frame_material: Optional[Material] = None,
        glazing_material: Optional[Material] = None,
        description: Optional[str] = None
    ):
        """
        Create a window type.

        Args:
            name: Name for this window type
            width: Clear opening width (default 1200mm)
            height: Clear opening height (default 1500mm)
            frame_width: Frame width/thickness (default 50mm)
            frame_depth: Frame depth into wall (default 70mm)
            glazing_thickness: Glazing unit thickness (default 24mm)
            mullion_count: Number of vertical mullions (0 = no divisions)
            mullion_width: Mullion width (default 50mm)
            default_sill_height: Default height from floor (default 900mm)
            operation_type: IFC operation type
            frame_material: Material for window frame
            glazing_material: Material for glazing
            description: Optional description
        """
        super().__init__(name)
        self.description = description
        self.operation_type = operation_type
        self.frame_material = frame_material
        self.glazing_material = glazing_material

        # Store dimensions as type parameters
        self.set_parameter("width", normalize_length(width).mm)
        self.set_parameter("height", normalize_length(height).mm)
        self.set_parameter("frame_width", normalize_length(frame_width).mm)
        self.set_parameter("frame_depth", normalize_length(frame_depth).mm)
        self.set_parameter("glazing_thickness", normalize_length(glazing_thickness).mm)
        self.set_parameter("mullion_count", mullion_count)
        self.set_parameter("mullion_width", normalize_length(mullion_width).mm)
        self.set_parameter("default_sill_height", normalize_length(default_sill_height).mm)

    @property
    def width(self) -> float:
        """Get window width in millimeters."""
        return self.get_parameter("width")

    @property
    def height(self) -> float:
        """Get window height in millimeters."""
        return self.get_parameter("height")

    @property
    def frame_width(self) -> float:
        """Get frame width in millimeters."""
        return self.get_parameter("frame_width")

    @property
    def frame_depth(self) -> float:
        """Get frame depth in millimeters."""
        return self.get_parameter("frame_depth")

    @property
    def glazing_thickness(self) -> float:
        """Get glazing thickness in millimeters."""
        return self.get_parameter("glazing_thickness")

    @property
    def mullion_count(self) -> int:
        """Get number of mullions."""
        return self.get_parameter("mullion_count")

    @property
    def mullion_width(self) -> float:
        """Get mullion width in millimeters."""
        return self.get_parameter("mullion_width")

    @property
    def default_sill_height(self) -> float:
        """Get default sill height in millimeters."""
        return self.get_parameter("default_sill_height")

    @property
    def overall_width(self) -> float:
        """Get overall window width including frame."""
        return self.width + 2 * self.frame_width

    @property
    def overall_height(self) -> float:
        """Get overall window height including frame."""
        return self.height + 2 * self.frame_width

    def create_geometry(self, instance: 'Window') -> Compound:
        """
        Create 3D geometry for a window instance.

        The window is created in LOCAL coordinates:
        - Origin at bottom-left corner of window frame
        - X-axis along window width
        - Y-axis through window thickness (into wall)
        - Z-axis upward

        Args:
            instance: Window instance to create geometry for

        Returns:
            build123d Compound representing the window (frame + glazing)
        """
        from bimascode.architecture.window import Window  # Avoid circular import

        # Get dimensions
        width = self.width
        height = self.height
        frame_w = self.frame_width
        frame_d = self.frame_depth
        glazing_t = self.glazing_thickness
        mullions = self.mullion_count
        mullion_w = self.mullion_width

        parts = []

        # Create frame pieces
        # Bottom sill
        sill = Box(width + 2 * frame_w, frame_d, frame_w)
        sill = sill.locate(Location(
            ((width + 2 * frame_w) / 2, frame_d / 2, frame_w / 2),
            (0, 0, 1), 0
        ))
        parts.append(sill)

        # Top rail
        top_rail = Box(width + 2 * frame_w, frame_d, frame_w)
        top_rail = top_rail.locate(Location(
            ((width + 2 * frame_w) / 2, frame_d / 2, frame_w + height + frame_w / 2),
            (0, 0, 1), 0
        ))
        parts.append(top_rail)

        # Left jamb
        left_jamb = Box(frame_w, frame_d, height)
        left_jamb = left_jamb.locate(Location(
            (frame_w / 2, frame_d / 2, frame_w + height / 2),
            (0, 0, 1), 0
        ))
        parts.append(left_jamb)

        # Right jamb
        right_jamb = Box(frame_w, frame_d, height)
        right_jamb = right_jamb.locate(Location(
            (frame_w + width + frame_w / 2, frame_d / 2, frame_w + height / 2),
            (0, 0, 1), 0
        ))
        parts.append(right_jamb)

        # Add mullions if specified
        if mullions > 0:
            panel_width = (width - mullions * mullion_w) / (mullions + 1)
            for i in range(mullions):
                mullion_x = frame_w + panel_width * (i + 1) + mullion_w * i + mullion_w / 2
                mullion = Box(mullion_w, frame_d, height)
                mullion = mullion.locate(Location(
                    (mullion_x, frame_d / 2, frame_w + height / 2),
                    (0, 0, 1), 0
                ))
                parts.append(mullion)

        # Create glazing panels
        glazing_y = (frame_d - glazing_t) / 2
        num_panels = mullions + 1

        if mullions == 0:
            # Single glazing panel
            glazing = Box(width - 4, glazing_t, height - 4)
            glazing = glazing.locate(Location(
                (frame_w + width / 2, glazing_y + glazing_t / 2, frame_w + height / 2),
                (0, 0, 1), 0
            ))
            parts.append(glazing)
        else:
            # Multiple glazing panels
            panel_width = (width - mullions * mullion_w) / num_panels
            for i in range(num_panels):
                panel_x = frame_w + panel_width / 2 + i * (panel_width + mullion_w)
                glazing = Box(panel_width - 4, glazing_t, height - 4)
                glazing = glazing.locate(Location(
                    (panel_x, glazing_y + glazing_t / 2, frame_w + height / 2),
                    (0, 0, 1), 0
                ))
                parts.append(glazing)

        return Compound(children=parts)

    def create_opening_geometry(self, instance: 'Window') -> Box:
        """
        Create the void geometry for cutting into the host wall.

        The opening is created in the wall's LOCAL coordinate system.
        The window instance provides the position along the wall.

        Args:
            instance: Window instance to create opening for

        Returns:
            build123d Box for boolean subtraction from wall
        """
        from bimascode.architecture.window import Window  # Avoid circular import

        # Get window dimensions
        width = self.overall_width
        height = self.overall_height

        # Get host wall thickness (opening goes through entire wall)
        host_wall = instance.host_wall
        wall_thickness = host_wall.width + 2  # +2mm for clean cut

        # Get position along wall
        offset = instance.offset
        sill_height = instance.sill_height

        # Create opening box in wall's local coordinates
        opening_box = Box(width, wall_thickness, height)

        # Position the opening
        opening_box = opening_box.locate(Location(
            (offset + width / 2, wall_thickness / 2 - 1, sill_height + height / 2),
            (0, 0, 1), 0
        ))

        return opening_box

    def _generate_guid(self) -> str:
        """Generate a unique IFC GUID."""
        import uuid
        return str(uuid.uuid4().hex[:22])

    def to_ifc(self, ifc_file):
        """
        Export window type to IFC as IfcWindowType with lining and panel properties.

        Creates proper IFC structure with:
        - IfcWindowType with ParameterTakesPrecedence=False (explicit geometry)
        - IfcWindowLiningProperties for frame dimensions
        - IfcWindowPanelProperties for each panel

        Args:
            ifc_file: IFC file object

        Returns:
            IfcWindowType entity
        """
        # Map operation type to IFC
        operation_map = {
            WindowOperationType.SINGLE_PANEL: "SINGLE_PANEL",
            WindowOperationType.DOUBLE_PANEL_VERTICAL: "DOUBLE_PANEL_VERTICAL",
            WindowOperationType.DOUBLE_PANEL_HORIZONTAL: "DOUBLE_PANEL_HORIZONTAL",
            WindowOperationType.TRIPLE_PANEL_VERTICAL: "TRIPLE_PANEL_VERTICAL",
            WindowOperationType.SLIDING_HORIZONTAL: "SLIDING_HORIZONTAL",
            WindowOperationType.SLIDING_VERTICAL: "SLIDING_VERTICAL",
            WindowOperationType.FIXED: "FIXED",
            WindowOperationType.CASEMENT: "CASEMENT",
            WindowOperationType.AWNING: "AWNING",
            WindowOperationType.HOPPER: "HOPPER",
        }

        # Map panel operation type
        panel_operation_map = {
            WindowOperationType.SINGLE_PANEL: "SIDEHUNGRIGHTHAND",
            WindowOperationType.DOUBLE_PANEL_VERTICAL: "SIDEHUNGRIGHTHAND",
            WindowOperationType.DOUBLE_PANEL_HORIZONTAL: "TOPHUNG",
            WindowOperationType.TRIPLE_PANEL_VERTICAL: "SIDEHUNGRIGHTHAND",
            WindowOperationType.SLIDING_HORIZONTAL: "SLIDINGHORIZONTAL",
            WindowOperationType.SLIDING_VERTICAL: "SLIDINGVERTICAL",
            WindowOperationType.FIXED: "FIXEDCASEMENT",
            WindowOperationType.CASEMENT: "SIDEHUNGRIGHTHAND",
            WindowOperationType.AWNING: "TOPHUNG",
            WindowOperationType.HOPPER: "BOTTOMHUNG",
        }

        partitioning = "SINGLE_PANEL"
        if self.mullion_count == 1:
            partitioning = "DOUBLE_PANEL_VERTICAL"
        elif self.mullion_count == 2:
            partitioning = "TRIPLE_PANEL_VERTICAL"

        # Create IfcWindowLiningProperties - defines frame dimensions
        lining_props = ifc_file.create_entity(
            "IfcWindowLiningProperties",
            GlobalId=self._generate_guid(),
            Name=f"{self.name}_LiningProperties",
            LiningDepth=float(self.frame_depth),
            LiningThickness=float(self.frame_width),
            FirstTransomOffset=0.0,  # No horizontal division
            SecondTransomOffset=0.0,
            FirstMullionOffset=float(self.width / (self.mullion_count + 1)) if self.mullion_count > 0 else 0.0,
            SecondMullionOffset=float(2 * self.width / (self.mullion_count + 1)) if self.mullion_count > 1 else 0.0,
            LiningToPanelOffsetX=2.0,  # Small clearance
            LiningToPanelOffsetY=float((self.frame_depth - self.glazing_thickness) / 2)
        )

        # Create IfcWindowPanelProperties for each panel
        num_panels = self.mullion_count + 1
        panel_positions = ["LEFT", "MIDDLE", "RIGHT"]
        property_sets = [lining_props]

        for i in range(num_panels):
            # Determine panel position
            if num_panels == 1:
                position = "MIDDLE"
            elif num_panels == 2:
                position = "LEFT" if i == 0 else "RIGHT"
            else:
                position = panel_positions[min(i, 2)]

            panel_props = ifc_file.create_entity(
                "IfcWindowPanelProperties",
                GlobalId=self._generate_guid(),
                Name=f"{self.name}_PanelProperties_{i + 1}",
                OperationType=panel_operation_map.get(self.operation_type, "FIXEDCASEMENT"),
                PanelPosition=position,
                FrameDepth=float(self.frame_depth),
                FrameThickness=float(self.frame_width)
            )
            property_sets.append(panel_props)

        # Create IfcWindowType with property sets
        ifc_window_type = ifc_file.create_entity(
            "IfcWindowType",
            GlobalId=self.guid,
            Name=self.name,
            Description=self.description,
            PartitioningType=partitioning,
            PredefinedType="WINDOW",
            ParameterTakesPrecedence=False,  # We provide explicit BREP geometry
            HasPropertySets=property_sets
        )

        return ifc_window_type

    def __repr__(self) -> str:
        return (
            f"WindowType(name='{self.name}', width={self.width:.0f}mm, "
            f"height={self.height:.0f}mm, mullions={self.mullion_count})"
        )


# Common window type constructors
def create_standard_window_type(
    name: str,
    width: Length | float = 1200.0,
    height: Length | float = 1500.0,
    sill_height: Length | float = 900.0
) -> WindowType:
    """
    Create a standard single-panel window type.

    Args:
        name: Window type name
        width: Clear opening width (default 1200mm)
        height: Clear opening height (default 1500mm)
        sill_height: Default sill height (default 900mm)

    Returns:
        WindowType with standard dimensions
    """
    return WindowType(
        name=name,
        width=width,
        height=height,
        default_sill_height=sill_height,
        mullion_count=0,
        operation_type=WindowOperationType.SINGLE_PANEL,
        description=f"{name} - Standard Window"
    )


def create_double_window_type(
    name: str,
    width: Length | float = 2400.0,
    height: Length | float = 1500.0,
    sill_height: Length | float = 900.0
) -> WindowType:
    """
    Create a double-panel window type with center mullion.

    Args:
        name: Window type name
        width: Total clear opening width (default 2400mm)
        height: Clear opening height (default 1500mm)
        sill_height: Default sill height (default 900mm)

    Returns:
        WindowType for double-panel windows
    """
    return WindowType(
        name=name,
        width=width,
        height=height,
        default_sill_height=sill_height,
        mullion_count=1,
        operation_type=WindowOperationType.DOUBLE_PANEL_VERTICAL,
        description=f"{name} - Double Panel Window"
    )


def create_fixed_window_type(
    name: str,
    width: Length | float = 1200.0,
    height: Length | float = 1500.0,
    sill_height: Length | float = 900.0
) -> WindowType:
    """
    Create a fixed (non-opening) window type.

    Args:
        name: Window type name
        width: Clear opening width (default 1200mm)
        height: Clear opening height (default 1500mm)
        sill_height: Default sill height (default 900mm)

    Returns:
        WindowType for fixed windows
    """
    return WindowType(
        name=name,
        width=width,
        height=height,
        default_sill_height=sill_height,
        mullion_count=0,
        operation_type=WindowOperationType.FIXED,
        description=f"{name} - Fixed Window"
    )
