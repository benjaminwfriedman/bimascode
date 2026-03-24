"""
Door types for BIM as Code.

This module implements the DoorType class which defines door assemblies
with frame and panel geometry. Door types specify standard dimensions
that can be instantiated as Door elements hosted in walls.
"""

from enum import Enum
from typing import TYPE_CHECKING

from build123d import Box, Compound, Location

from bimascode.core.type_instance import ElementType
from bimascode.utils.materials import Material
from bimascode.utils.units import Length, normalize_length

if TYPE_CHECKING:
    from bimascode.architecture.door import Door


class SwingDirection(Enum):
    """Door swing direction relative to the wall face."""

    LEFT_HAND = "LEFT_HAND"  # Hinges on left, swings left
    RIGHT_HAND = "RIGHT_HAND"  # Hinges on right, swings right
    DOUBLE = "DOUBLE"  # Double door


class DoorOperationType(Enum):
    """IFC door operation type."""

    SINGLE_SWING_LEFT = "SINGLE_SWING_LEFT"
    SINGLE_SWING_RIGHT = "SINGLE_SWING_RIGHT"
    DOUBLE_DOOR_SINGLE_SWING = "DOUBLE_DOOR_SINGLE_SWING"
    SLIDING = "SLIDING"
    FOLDING = "FOLDING"
    REVOLVING = "REVOLVING"


class DoorType(ElementType):
    """
    Door type defining standard door dimensions and geometry.

    A door type specifies the width, height, frame dimensions,
    and swing direction for door instances.
    """

    def __init__(
        self,
        name: str,
        width: Length | float = 900.0,
        height: Length | float = 2100.0,
        frame_width: Length | float = 50.0,
        frame_depth: Length | float = 100.0,
        panel_thickness: Length | float = 44.0,
        swing_direction: SwingDirection = SwingDirection.RIGHT_HAND,
        operation_type: DoorOperationType = DoorOperationType.SINGLE_SWING_RIGHT,
        frame_material: Material | None = None,
        panel_material: Material | None = None,
        description: str | None = None,
    ):
        """
        Create a door type.

        Args:
            name: Name for this door type
            width: Clear opening width (default 900mm)
            height: Clear opening height (default 2100mm)
            frame_width: Frame width/thickness (default 50mm)
            frame_depth: Frame depth into wall (default 100mm)
            panel_thickness: Door panel thickness (default 44mm)
            swing_direction: Door swing direction
            operation_type: IFC operation type
            frame_material: Material for door frame
            panel_material: Material for door panel
            description: Optional description
        """
        super().__init__(name)
        self.description = description
        self.swing_direction = swing_direction
        self.operation_type = operation_type
        self.frame_material = frame_material
        self.panel_material = panel_material

        # Store dimensions as type parameters
        self.set_parameter("width", normalize_length(width).mm)
        self.set_parameter("height", normalize_length(height).mm)
        self.set_parameter("frame_width", normalize_length(frame_width).mm)
        self.set_parameter("frame_depth", normalize_length(frame_depth).mm)
        self.set_parameter("panel_thickness", normalize_length(panel_thickness).mm)

    @property
    def width(self) -> float:
        """Get door width in millimeters."""
        return self.get_parameter("width")

    @property
    def height(self) -> float:
        """Get door height in millimeters."""
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
    def panel_thickness(self) -> float:
        """Get panel thickness in millimeters."""
        return self.get_parameter("panel_thickness")

    @property
    def overall_width(self) -> float:
        """Get overall door width including frame."""
        return self.width + 2 * self.frame_width

    @property
    def overall_height(self) -> float:
        """Get overall door height including frame."""
        return self.height + self.frame_width  # Top frame only

    def create_geometry(self, instance: "Door") -> Compound:
        """
        Create 3D geometry for a door instance.

        The door is created in LOCAL coordinates:
        - Origin at bottom-left corner of door frame
        - X-axis along door width
        - Y-axis through door thickness (into wall)
        - Z-axis upward

        Args:
            instance: Door instance to create geometry for

        Returns:
            build123d Compound representing the door (frame + panel)
        """

        # Get dimensions
        width = self.width
        height = self.height
        frame_w = self.frame_width
        frame_d = self.frame_depth
        panel_t = self.panel_thickness

        parts = []

        # Create frame pieces
        # Left jamb
        left_jamb = Box(frame_w, frame_d, height + frame_w)
        left_jamb = left_jamb.locate(
            Location((frame_w / 2, frame_d / 2, (height + frame_w) / 2), (0, 0, 1), 0)
        )
        parts.append(left_jamb)

        # Right jamb
        right_jamb = Box(frame_w, frame_d, height + frame_w)
        right_jamb = right_jamb.locate(
            Location(
                (frame_w + width + frame_w / 2, frame_d / 2, (height + frame_w) / 2), (0, 0, 1), 0
            )
        )
        parts.append(right_jamb)

        # Head (top piece)
        head = Box(width, frame_d, frame_w)
        head = head.locate(
            Location((frame_w + width / 2, frame_d / 2, height + frame_w / 2), (0, 0, 1), 0)
        )
        parts.append(head)

        # Door panel (centered in frame depth)
        panel_y = (frame_d - panel_t) / 2
        panel = Box(width - 4, panel_t, height - 4)  # Small gap for clearance
        panel = panel.locate(
            Location((frame_w + width / 2, panel_y + panel_t / 2, height / 2), (0, 0, 1), 0)
        )
        parts.append(panel)

        return Compound(children=parts)

    def create_opening_geometry(self, instance: "Door") -> Box:
        """
        Create the void geometry for cutting into the host wall.

        The opening is created in the wall's LOCAL coordinate system.
        The door instance provides the position along the wall.

        Args:
            instance: Door instance to create opening for

        Returns:
            build123d Box for boolean subtraction from wall
        """

        # Get door dimensions
        width = self.overall_width
        height = self.overall_height

        # Get host wall thickness (opening goes through entire wall)
        host_wall = instance.host_wall
        wall_thickness = host_wall.width + 2  # +2mm for clean cut

        # Get position along wall
        offset = instance.offset
        sill_height = instance.sill_height

        # Create opening box in wall's local coordinates
        # Wall local coords: X along length, Y through thickness (centered on Y=0), Z vertical
        opening_box = Box(width, wall_thickness, height)

        # Position the opening:
        # X: offset along wall + half opening width
        # Y: centered on wall centerline (Y=0)
        # Z: sill height + half opening height
        opening_box = opening_box.locate(
            Location((offset + width / 2, 0, sill_height + height / 2), (0, 0, 1), 0)
        )

        return opening_box

    def _generate_guid(self) -> str:
        """Generate a unique IFC GUID."""
        import uuid

        return str(uuid.uuid4().hex[:22])

    def to_ifc(self, ifc_file):
        """
        Export door type to IFC as IfcDoorType with lining and panel properties.

        Creates proper IFC structure with:
        - IfcDoorType with ParameterTakesPrecedence=False (explicit geometry)
        - IfcDoorLiningProperties for frame dimensions
        - IfcDoorPanelProperties for panel dimensions

        Args:
            ifc_file: IFC file object

        Returns:
            IfcDoorType entity
        """
        # Map operation type to IFC
        operation_map = {
            DoorOperationType.SINGLE_SWING_LEFT: "SINGLE_SWING_LEFT",
            DoorOperationType.SINGLE_SWING_RIGHT: "SINGLE_SWING_RIGHT",
            DoorOperationType.DOUBLE_DOOR_SINGLE_SWING: "DOUBLE_DOOR_SINGLE_SWING",
            DoorOperationType.SLIDING: "SLIDING_TO_LEFT",
            DoorOperationType.FOLDING: "FOLDING_TO_LEFT",
            DoorOperationType.REVOLVING: "REVOLVING",
        }

        # Map panel operation
        panel_operation_map = {
            DoorOperationType.SINGLE_SWING_LEFT: "SWINGING",
            DoorOperationType.SINGLE_SWING_RIGHT: "SWINGING",
            DoorOperationType.DOUBLE_DOOR_SINGLE_SWING: "DOUBLE_ACTING",
            DoorOperationType.SLIDING: "SLIDING",
            DoorOperationType.FOLDING: "FOLDING",
            DoorOperationType.REVOLVING: "REVOLVING",
        }

        # Map panel position based on swing direction
        panel_position_map = {
            SwingDirection.LEFT_HAND: "LEFT",
            SwingDirection.RIGHT_HAND: "RIGHT",
            SwingDirection.DOUBLE: "MIDDLE",
        }

        # Create IfcDoorLiningProperties - defines frame dimensions
        lining_props = ifc_file.create_entity(
            "IfcDoorLiningProperties",
            GlobalId=self._generate_guid(),
            Name=f"{self.name}_LiningProperties",
            LiningDepth=float(self.frame_depth),
            LiningThickness=float(self.frame_width),
            ThresholdThickness=0.0,  # No threshold for standard doors
            LiningToPanelOffsetX=2.0,  # Small clearance gap
            LiningToPanelOffsetY=float((self.frame_depth - self.panel_thickness) / 2),
        )

        # Create IfcDoorPanelProperties - defines panel dimensions
        # For double doors, we'd create two panel properties
        if self.swing_direction == SwingDirection.DOUBLE:
            # Double door - two panels, each half width
            panel_props_left = ifc_file.create_entity(
                "IfcDoorPanelProperties",
                GlobalId=self._generate_guid(),
                Name=f"{self.name}_PanelProperties_Left",
                PanelDepth=float(self.panel_thickness),
                PanelOperation=panel_operation_map.get(self.operation_type, "SWINGING"),
                PanelWidth=0.5,  # Half width
                PanelPosition="LEFT",
            )
            panel_props_right = ifc_file.create_entity(
                "IfcDoorPanelProperties",
                GlobalId=self._generate_guid(),
                Name=f"{self.name}_PanelProperties_Right",
                PanelDepth=float(self.panel_thickness),
                PanelOperation=panel_operation_map.get(self.operation_type, "SWINGING"),
                PanelWidth=0.5,  # Half width
                PanelPosition="RIGHT",
            )
            property_sets = [lining_props, panel_props_left, panel_props_right]
        else:
            # Single door - one panel, full width
            panel_props = ifc_file.create_entity(
                "IfcDoorPanelProperties",
                GlobalId=self._generate_guid(),
                Name=f"{self.name}_PanelProperties",
                PanelDepth=float(self.panel_thickness),
                PanelOperation=panel_operation_map.get(self.operation_type, "SWINGING"),
                PanelWidth=1.0,  # Full width
                PanelPosition=panel_position_map.get(self.swing_direction, "MIDDLE"),
            )
            property_sets = [lining_props, panel_props]

        # Create IfcDoorType with property sets
        ifc_door_type = ifc_file.create_entity(
            "IfcDoorType",
            GlobalId=self.guid,
            Name=self.name,
            Description=self.description,
            OperationType=operation_map.get(self.operation_type, "SINGLE_SWING_RIGHT"),
            PredefinedType="DOOR",
            ParameterTakesPrecedence=False,  # We provide explicit BREP geometry
            HasPropertySets=property_sets,
        )

        return ifc_door_type

    def __repr__(self) -> str:
        return (
            f"DoorType(name='{self.name}', width={self.width:.0f}mm, "
            f"height={self.height:.0f}mm, swing={self.swing_direction.value})"
        )


# Common door type constructors
def create_standard_door_type(
    name: str,
    width: Length | float = 900.0,
    height: Length | float = 2100.0,
    swing_direction: SwingDirection = SwingDirection.RIGHT_HAND,
) -> DoorType:
    """
    Create a standard single-leaf door type.

    Args:
        name: Door type name
        width: Clear opening width (default 900mm)
        height: Clear opening height (default 2100mm)
        swing_direction: Door swing direction

    Returns:
        DoorType with standard dimensions
    """
    operation = (
        DoorOperationType.SINGLE_SWING_LEFT
        if swing_direction == SwingDirection.LEFT_HAND
        else DoorOperationType.SINGLE_SWING_RIGHT
    )

    return DoorType(
        name=name,
        width=width,
        height=height,
        swing_direction=swing_direction,
        operation_type=operation,
        description=f"{name} - Standard Door",
    )


def create_double_door_type(
    name: str, width: Length | float = 1800.0, height: Length | float = 2100.0
) -> DoorType:
    """
    Create a double door type.

    Args:
        name: Door type name
        width: Total clear opening width (default 1800mm)
        height: Clear opening height (default 2100mm)

    Returns:
        DoorType for double doors
    """
    return DoorType(
        name=name,
        width=width,
        height=height,
        swing_direction=SwingDirection.DOUBLE,
        operation_type=DoorOperationType.DOUBLE_DOOR_SINGLE_SWING,
        description=f"{name} - Double Door",
    )
