"""Drawing generation module for BIMasCode.

This module provides 2D view generation from 3D BIM models,
including floor plans, sections, and elevations.

Sprint 6: Drawing Generation
"""

# Primitives
from bimascode.drawing.primitives import (
    Arc2D,
    Geometry2D,
    Hatch2D,
    Line2D,
    Point2D,
    Polyline2D,
    ViewResult,
)

# Line styles
from bimascode.drawing.line_styles import (
    Layer,
    LineStyle,
    LineType,
    LineWeight,
)

# View base classes
from bimascode.drawing.view_base import (
    ViewBase,
    ViewCropRegion,
    ViewRange,
    ViewScale,
)

# Protocols
from bimascode.drawing.protocols import (
    Drawable2D,
    HasBoundingBox,
    HasGeometry,
    Linework2D,
)

# View types
from bimascode.drawing.floor_plan_view import FloorPlanView
from bimascode.drawing.section_view import SectionView
from bimascode.drawing.elevation_view import (
    ElevationDirection,
    ElevationView,
    ReflectedCeilingPlanView,
)

# Templates
from bimascode.drawing.view_templates import (
    CategoryVisibility,
    GraphicOverride,
    ViewTemplate,
    ViewVisibilitySettings,
)

# Utilities
from bimascode.drawing.section_cutter import SectionCutter, get_section_cutter
from bimascode.drawing.hlr_processor import HLRProcessor, get_hlr_processor
from bimascode.drawing.dxf_exporter import DXFExporter, get_dxf_exporter

__all__ = [
    # Primitives
    "Point2D",
    "Line2D",
    "Arc2D",
    "Polyline2D",
    "Hatch2D",
    "ViewResult",
    "Geometry2D",
    # Line styles
    "LineWeight",
    "LineType",
    "LineStyle",
    "Layer",
    # View base
    "ViewRange",
    "ViewScale",
    "ViewCropRegion",
    "ViewBase",
    # Protocols
    "Drawable2D",
    "HasBoundingBox",
    "HasGeometry",
    "Linework2D",
    # Views
    "FloorPlanView",
    "SectionView",
    "ElevationView",
    "ElevationDirection",
    "ReflectedCeilingPlanView",
    # Templates
    "CategoryVisibility",
    "GraphicOverride",
    "ViewTemplate",
    "ViewVisibilitySettings",
    # Utilities
    "SectionCutter",
    "get_section_cutter",
    "HLRProcessor",
    "get_hlr_processor",
    "DXFExporter",
    "get_dxf_exporter",
]
