"""
Mullion cross-section profiles for curtain walls.

Mullion profiles define the 2D cross-section shape that gets extruded
along grid lines to create 3D mullion geometry.
"""

from __future__ import annotations

from build123d import Face, Polygon, Rectangle

from bimascode.utils.units import Length, normalize_length


class MullionProfile:
    """
    Cross-section profile for curtain wall mullions.

    Profiles are defined in a local coordinate system where:
    - X axis is the face width (visible from exterior)
    - Y axis is the depth (projection from glass plane)
    - Origin is at the centerline of the profile

    Common mullion shapes include rectangular, T-section, and I-section.
    For thermal break mullions, a gap can be specified to split the profile.
    """

    def __init__(
        self,
        width: Length | float,
        depth: Length | float,
        web_thickness: Length | float | None = None,
        flange_thickness: Length | float | None = None,
        thermal_break_gap: Length | float = 0.0,
        name: str | None = None,
    ):
        """
        Create a mullion profile.

        Args:
            width: Face width visible from exterior (mm)
            depth: Total depth/projection from glass plane (mm)
            web_thickness: Center web thickness for I/T sections (mm).
                          If None, creates solid rectangular profile.
            flange_thickness: Flange thickness at top/bottom for I/T sections (mm).
                             If None, creates solid rectangular profile.
            thermal_break_gap: Gap for thermal break (mm). Default 0 = no break.
            name: Optional name for the profile
        """
        self._width = normalize_length(width).mm
        self._depth = normalize_length(depth).mm
        self._web_thickness = (
            normalize_length(web_thickness).mm if web_thickness is not None else None
        )
        self._flange_thickness = (
            normalize_length(flange_thickness).mm
            if flange_thickness is not None
            else None
        )
        self._thermal_break_gap = normalize_length(thermal_break_gap).mm

        # Determine profile type
        if self._web_thickness is None or self._flange_thickness is None:
            self._profile_type = "rectangular"
        else:
            self._profile_type = "i_section"

        self.name = name or self._generate_name()

    def _generate_name(self) -> str:
        """Generate a default name based on dimensions."""
        if self._profile_type == "rectangular":
            return f"Mullion_{self._width:.0f}x{self._depth:.0f}"
        else:
            return f"Mullion_I_{self._width:.0f}x{self._depth:.0f}"

    @property
    def width(self) -> float:
        """Get profile face width in millimeters."""
        return self._width

    @property
    def depth(self) -> float:
        """Get profile depth in millimeters."""
        return self._depth

    @property
    def web_thickness(self) -> float | None:
        """Get web thickness in millimeters (None for rectangular)."""
        return self._web_thickness

    @property
    def flange_thickness(self) -> float | None:
        """Get flange thickness in millimeters (None for rectangular)."""
        return self._flange_thickness

    @property
    def thermal_break_gap(self) -> float:
        """Get thermal break gap in millimeters."""
        return self._thermal_break_gap

    @property
    def has_thermal_break(self) -> bool:
        """Check if profile has a thermal break."""
        return self._thermal_break_gap > 0

    @property
    def profile_type(self) -> str:
        """Get profile type: 'rectangular' or 'i_section'."""
        return self._profile_type

    @property
    def area(self) -> float:
        """Get cross-sectional area in square millimeters."""
        if self._profile_type == "rectangular":
            return self._width * self._depth
        else:
            # I-section: two flanges + web
            flange_area = 2 * self._width * self._flange_thickness
            web_height = self._depth - 2 * self._flange_thickness
            web_area = self._web_thickness * web_height
            return flange_area + web_area

    def to_build123d(self) -> Face:
        """
        Convert profile to a build123d Face for extrusion.

        Returns:
            build123d Face centered at origin, oriented in XY plane.
            X = width direction, Y = depth direction.
        """
        if self._profile_type == "rectangular":
            return self._create_rectangular_face()
        else:
            return self._create_i_section_face()

    def _create_rectangular_face(self) -> Face:
        """Create a simple rectangular profile face."""
        return Rectangle(self._width, self._depth)

    def _create_i_section_face(self) -> Face:
        """Create an I-section profile face using polygon points."""
        # Create I-section as a single polygon for clean geometry
        points = self._get_i_section_points()
        return Polygon(points)

    def to_ifc(self, ifc_file) -> any:
        """
        Export profile to IFC.

        For rectangular profiles, uses IfcRectangleProfileDef.
        For I-sections, uses IfcArbitraryClosedProfileDef.

        Args:
            ifc_file: IFC file object

        Returns:
            IFC profile definition entity
        """
        # Create axis placement at origin
        location = ifc_file.createIfcCartesianPoint((0.0, 0.0))
        x_axis = ifc_file.createIfcDirection((1.0, 0.0))
        axis_placement = ifc_file.createIfcAxis2Placement2D(location, x_axis)

        if self._profile_type == "rectangular":
            return ifc_file.create_entity(
                "IfcRectangleProfileDef",
                ProfileType="AREA",
                ProfileName=self.name,
                Position=axis_placement,
                XDim=float(self._width),
                YDim=float(self._depth),
            )
        else:
            # I-section: create arbitrary closed profile from polygon points
            points = self._get_i_section_points()
            ifc_points = [
                ifc_file.createIfcCartesianPoint((p[0], p[1])) for p in points
            ]
            # Close the polyline
            ifc_points.append(ifc_points[0])

            polyline = ifc_file.createIfcPolyline(ifc_points)

            return ifc_file.create_entity(
                "IfcArbitraryClosedProfileDef",
                ProfileType="AREA",
                ProfileName=self.name,
                OuterCurve=polyline,
            )

    def _get_i_section_points(self) -> list[tuple[float, float]]:
        """Get polygon points for I-section profile (counter-clockwise)."""
        w = self._width / 2
        d = self._depth / 2
        wt = self._web_thickness / 2
        ft = self._flange_thickness

        # Start at bottom-left of bottom flange, go counter-clockwise
        return [
            (-w, -d),  # Bottom-left
            (w, -d),  # Bottom-right
            (w, -d + ft),  # Bottom flange top-right
            (wt, -d + ft),  # Web bottom-right
            (wt, d - ft),  # Web top-right
            (w, d - ft),  # Top flange bottom-right
            (w, d),  # Top-right
            (-w, d),  # Top-left
            (-w, d - ft),  # Top flange bottom-left
            (-wt, d - ft),  # Web top-left
            (-wt, -d + ft),  # Web bottom-left
            (-w, -d + ft),  # Bottom flange top-left
        ]

    def __repr__(self) -> str:
        if self._profile_type == "rectangular":
            return (
                f"MullionProfile(name='{self.name}', "
                f"width={self._width:.0f}mm, depth={self._depth:.0f}mm)"
            )
        else:
            return (
                f"MullionProfile(name='{self.name}', type='I-section', "
                f"width={self._width:.0f}mm, depth={self._depth:.0f}mm, "
                f"web={self._web_thickness:.0f}mm, flange={self._flange_thickness:.0f}mm)"
            )

    def __eq__(self, other) -> bool:
        if not isinstance(other, MullionProfile):
            return False
        return (
            abs(self._width - other._width) < 1e-6
            and abs(self._depth - other._depth) < 1e-6
            and self._profile_type == other._profile_type
            and (
                self._web_thickness == other._web_thickness
                or (
                    self._web_thickness is not None
                    and other._web_thickness is not None
                    and abs(self._web_thickness - other._web_thickness) < 1e-6
                )
            )
            and (
                self._flange_thickness == other._flange_thickness
                or (
                    self._flange_thickness is not None
                    and other._flange_thickness is not None
                    and abs(self._flange_thickness - other._flange_thickness) < 1e-6
                )
            )
        )


# Factory functions for common mullion profiles


def create_rectangular_mullion_profile(
    width: Length | float,
    depth: Length | float,
    name: str | None = None,
) -> MullionProfile:
    """
    Create a simple rectangular mullion profile.

    Args:
        width: Face width (mm)
        depth: Depth/projection (mm)
        name: Optional profile name

    Returns:
        Rectangular MullionProfile
    """
    return MullionProfile(width=width, depth=depth, name=name)


def create_i_section_mullion_profile(
    width: Length | float,
    depth: Length | float,
    web_thickness: Length | float,
    flange_thickness: Length | float,
    thermal_break_gap: Length | float = 0.0,
    name: str | None = None,
) -> MullionProfile:
    """
    Create an I-section mullion profile.

    Args:
        width: Face width (mm)
        depth: Total depth (mm)
        web_thickness: Center web thickness (mm)
        flange_thickness: Top/bottom flange thickness (mm)
        thermal_break_gap: Gap for thermal break (mm)
        name: Optional profile name

    Returns:
        I-section MullionProfile
    """
    return MullionProfile(
        width=width,
        depth=depth,
        web_thickness=web_thickness,
        flange_thickness=flange_thickness,
        thermal_break_gap=thermal_break_gap,
        name=name,
    )
