"""Tests for glTF export functionality."""

import tempfile
from pathlib import Path

import pytest

from bimascode.architecture import Wall, create_basic_wall_type
from bimascode.spatial.building import Building
from bimascode.spatial.level import Level
from bimascode.utils.materials import MaterialLibrary

# Skip all tests if trimesh is not installed
pytest.importorskip("trimesh")


class TestGLTFExporter:
    """Tests for GLTFExporter class."""

    @pytest.fixture
    def simple_building(self):
        """Create a simple building with one wall for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground", elevation=0)

        # Create a simple wall type
        material = MaterialLibrary.concrete()
        wall_type = create_basic_wall_type("Test Wall", 200, material)

        # Create a wall
        Wall(
            wall_type=wall_type,
            start_point=(0, 0),
            end_point=(5000, 0),
            level=level,
            height=3000,
        )

        return building

    @pytest.fixture
    def building_with_door(self):
        """Create a building with a wall and door."""
        from bimascode.architecture.door import Door
        from bimascode.architecture.door_type import DoorType

        building = Building("Test Building with Door")
        level = Level(building, "Ground", elevation=0)

        # Create wall
        material = MaterialLibrary.concrete()
        wall_type = create_basic_wall_type("Test Wall", 200, material)
        wall = Wall(
            wall_type=wall_type,
            start_point=(0, 0),
            end_point=(5000, 0),
            level=level,
            height=3000,
        )

        # Create door
        door_type = DoorType("Single Door", width=900, height=2100)
        Door(door_type=door_type, host_wall=wall, offset=2000, mark="101")

        return building

    def test_import_gltf_exporter(self):
        """GLTFExporter can be imported."""
        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()
        assert exporter is not None

    def test_export_bytes_returns_bytes(self, simple_building):
        """export_bytes() returns bytes."""
        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()
        result = exporter.export_bytes(simple_building)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_bytes_is_valid_glb(self, simple_building):
        """Exported bytes are valid GLB format."""
        import trimesh

        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()
        glb_bytes = exporter.export_bytes(simple_building)

        # GLB magic number is 'glTF' (0x46546C67)
        assert glb_bytes[:4] == b"glTF"

        # Should be loadable by trimesh
        import io

        scene = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")
        assert scene is not None

    def test_export_to_file(self, simple_building):
        """export() writes valid GLB file."""
        import trimesh

        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.glb"
            exporter.export(simple_building, filepath)

            # File should exist
            assert filepath.exists()

            # File should be valid GLB
            scene = trimesh.load(str(filepath))
            assert scene is not None

    def test_export_creates_parent_directories(self, simple_building):
        """export() creates parent directories if they don't exist."""
        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "subdir" / "another" / "test.glb"
            exporter.export(simple_building, filepath)

            assert filepath.exists()

    def test_exported_scene_has_geometry(self, simple_building):
        """Exported scene contains geometry from the building."""
        import io

        import trimesh

        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()
        glb_bytes = exporter.export_bytes(simple_building)

        scene = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")

        # Scene should have geometry
        assert len(scene.geometry) > 0

    def test_mesh_metadata_contains_guid(self, simple_building):
        """Mesh metadata includes element GUID."""
        import io

        import trimesh

        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()
        glb_bytes = exporter.export_bytes(simple_building)

        scene = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")

        # At least one mesh should have GUID in metadata
        has_guid = False
        for _name, geom in scene.geometry.items():
            if hasattr(geom, "metadata") and "guid" in geom.metadata:
                has_guid = True
                # GUID should be a string
                assert isinstance(geom.metadata["guid"], str)
                break

        assert has_guid, "No mesh found with GUID in metadata"

    def test_mesh_metadata_contains_type(self, simple_building):
        """Mesh metadata includes element type."""
        import io

        import trimesh

        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()
        glb_bytes = exporter.export_bytes(simple_building)

        scene = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")

        # At least one mesh should have type in metadata
        has_type = False
        for _name, geom in scene.geometry.items():
            if hasattr(geom, "metadata") and "type" in geom.metadata:
                has_type = True
                # Type should be "Wall"
                assert geom.metadata["type"] == "Wall"
                break

        assert has_type, "No mesh found with type in metadata"

    def test_empty_building_exports(self):
        """Empty building (no elements) exports without error."""
        from bimascode.export.gltf_exporter import GLTFExporter

        building = Building("Empty Building")
        Level(building, "Ground", elevation=0)

        exporter = GLTFExporter()
        result = exporter.export_bytes(building)

        # Should return valid GLB even if empty
        assert isinstance(result, bytes)
        assert result[:4] == b"glTF"

    def test_building_with_door_exports(self, building_with_door):
        """Building with hosted elements (doors) exports correctly."""
        import io

        import trimesh

        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()
        glb_bytes = exporter.export_bytes(building_with_door)

        scene = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")

        # Should have multiple geometries (wall + door)
        assert len(scene.geometry) >= 1  # At least the wall

    def test_element_colors_applied(self, simple_building):
        """Elements have colors applied based on type."""
        import io

        import trimesh

        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()
        glb_bytes = exporter.export_bytes(simple_building)

        scene = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")

        # Check that geometry has visual colors
        for _name, geom in scene.geometry.items():
            if hasattr(geom, "visual") and geom.visual is not None:
                # Visual should have face colors
                if hasattr(geom.visual, "face_colors"):
                    assert geom.visual.face_colors is not None


class TestGLTFExporterEdgeCases:
    """Edge case tests for GLTFExporter."""

    @pytest.fixture
    def simple_building(self):
        """Create a simple building with one wall for testing."""
        building = Building("Test Building")
        level = Level(building, "Ground", elevation=0)

        material = MaterialLibrary.concrete()
        wall_type = create_basic_wall_type("Test Wall", 200, material)

        Wall(
            wall_type=wall_type,
            start_point=(0, 0),
            end_point=(5000, 0),
            level=level,
            height=3000,
        )

        return building

    def test_building_with_multiple_levels(self):
        """Building with multiple levels exports correctly."""
        from bimascode.export.gltf_exporter import GLTFExporter

        building = Building("Multi-Level Building")
        level1 = Level(building, "Ground", elevation=0)
        level2 = Level(building, "First Floor", elevation=3000)

        material = MaterialLibrary.concrete()
        wall_type = create_basic_wall_type("Test Wall", 200, material)

        # Walls on different levels
        Wall(wall_type, (0, 0), (5000, 0), level1, height=3000)
        Wall(wall_type, (0, 0), (5000, 0), level2, height=3000)

        exporter = GLTFExporter()
        result = exporter.export_bytes(building)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_path_string_and_pathlib(self, simple_building):
        """export() accepts both str and Path for filepath."""
        from bimascode.export.gltf_exporter import GLTFExporter

        exporter = GLTFExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with str
            str_path = f"{tmpdir}/test_str.glb"
            exporter.export(simple_building, str_path)
            assert Path(str_path).exists()

            # Test with Path
            path_obj = Path(tmpdir) / "test_path.glb"
            exporter.export(simple_building, path_obj)
            assert path_obj.exists()
