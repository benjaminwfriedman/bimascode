"""Drawing generation module for BIMasCode.

This module provides 2D view generation from 3D BIM models,
including floor plans, sections, and elevations.

Sprint 6: Drawing Generation
"""

# Primitives
from bimascode.drawing.dxf_exporter import DXFExporter, DXFSheetExporter, get_dxf_exporter
from bimascode.drawing.elevation_view import (
    ElevationDirection,
    ElevationView,
    ReflectedCeilingPlanView,
)

# View types
from bimascode.drawing.floor_plan_view import FloorPlanView

# Hatch patterns
from bimascode.drawing.hatch_patterns import (
    HatchPattern,
    get_hatch_pattern_for_layer,
    get_hatch_pattern_for_material,
)
from bimascode.drawing.hlr_processor import HLRProcessor, get_hlr_processor

# Line styles
from bimascode.drawing.line_styles import (
    Layer,
    LineStyle,
    LineType,
    LineWeight,
)
from bimascode.drawing.primitives import (
    Arc2D,
    Geometry2D,
    Hatch2D,
    Line2D,
    LinearDimension2D,
    Point2D,
    Polyline2D,
    ViewResult,
)

# Protocols
from bimascode.drawing.protocols import (
    Drawable2D,
    HasBoundingBox,
    HasGeometry,
    Linework2D,
)

# Utilities
from bimascode.drawing.section_cutter import SectionCutter, get_section_cutter
from bimascode.drawing.section_view import SectionView

# Sheets
from bimascode.drawing.sheet import Sheet, SheetMetadata
from bimascode.drawing.sheet_sizes import SheetSize

# Symbology
from bimascode.drawing.symbology import (
    ElementSymbology,
    FillMode,
    SymbologySettings,
    get_default_symbology,
)

# Tags and Section Symbols
from bimascode.drawing.tags import (
    DoorTag,
    RoomTag,
    SectionSymbol,
    SectionSymbolStyle,
    Tag2D,
    TagShape,
    TagStyle,
    WindowTag,
)
from bimascode.drawing.title_block import (
    TitleBlock,
    TitleBlockField,
    TitleBlockFieldDefinition,
    TitleBlockTemplate,
    get_title_block_template,
    list_title_block_templates,
    register_title_block_template,
)

# View base classes
from bimascode.drawing.view_base import (
    ViewBase,
    ViewCropRegion,
    ViewRange,
    ViewScale,
)

# Templates
from bimascode.drawing.view_templates import (
    CategoryVisibility,
    GraphicOverride,
    ViewTemplate,
    ViewVisibilitySettings,
)
from bimascode.drawing.viewport import SheetViewport

__all__ = [
    # Primitives
    "Point2D",
    "Line2D",
    "Arc2D",
    "Polyline2D",
    "Hatch2D",
    "LinearDimension2D",
    "ViewResult",
    "Geometry2D",
    # Line styles
    "LineWeight",
    "LineType",
    "LineStyle",
    "Layer",
    # Hatch patterns
    "HatchPattern",
    "get_hatch_pattern_for_material",
    "get_hatch_pattern_for_layer",
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
    # Symbology
    "ElementSymbology",
    "FillMode",
    "SymbologySettings",
    "get_default_symbology",
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
    # Sheets
    "Sheet",
    "SheetMetadata",
    "SheetSize",
    "SheetViewport",
    "TitleBlock",
    "TitleBlockField",
    "TitleBlockFieldDefinition",
    "TitleBlockTemplate",
    "get_title_block_template",
    "list_title_block_templates",
    "register_title_block_template",
    # Utilities
    "SectionCutter",
    "get_section_cutter",
    "HLRProcessor",
    "get_hlr_processor",
    "DXFExporter",
    "DXFSheetExporter",
    "get_dxf_exporter",
    # Tags and Section Symbols
    "DoorTag",
    "WindowTag",
    "RoomTag",
    "TagStyle",
    "TagShape",
    "Tag2D",
    "SectionSymbol",
    "SectionSymbolStyle",
]
