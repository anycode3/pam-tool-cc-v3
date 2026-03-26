import pytest
import tempfile
from pathlib import Path

from app.services.version_manager import VersionManager
from app.services.device_manager import DeviceManager


def test_version_manager_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VersionManager(storage_path=Path(tmpdir))
        assert manager.versions_path.exists()


def test_save_version():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VersionManager(storage_path=Path(tmpdir))

        devices = [
            {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5},
            {"name": "C1", "device_type": "C", "x": 20, "y": 20, "width": 15, "height": 15}
        ]

        version = manager.save_version("test.gds", devices, "initial_version")
        assert version is not None
        assert version.version_id is not None
        assert version.file_name == "test.gds"
        assert version.device_count == 2


def test_get_versions():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VersionManager(storage_path=Path(tmpdir))

        devices = [{"name": "D1", "device_type": "D", "x": 0, "y": 0, "width": 5, "height": 5}]
        manager.save_version("test.gds", devices, "version1")
        manager.save_version("test.gds", devices, "version2", force=True)

        versions = manager.get_versions("test.gds")
        assert len(versions) == 2
        assert versions[0].description == "version2"
        assert versions[1].description == "version1"


def test_rollback():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VersionManager(storage_path=Path(tmpdir))

        devices_v1 = [{"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5}]
        devices_v2 = [{"name": "R1", "device_type": "R", "x": 5, "y": 5, "width": 10, "height": 5}]

        v1 = manager.save_version("test.gds", devices_v1, "version1")
        v2 = manager.save_version("test.gds", devices_v2, "version2", force=True)

        devices = manager.rollback("test.gds", v1.version_id)
        assert devices is not None
        assert devices[0]["x"] == 0


def test_delete_version():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VersionManager(storage_path=Path(tmpdir))

        devices = [{"name": "D2", "device_type": "D", "x": 0, "y": 0, "width": 5, "height": 5}]
        version = manager.save_version("test.gds", devices, "test_version")

        success = manager.delete_version("test.gds", version.version_id)
        assert success is True

        versions = manager.get_versions("test.gds")
        assert len(versions) == 0


def test_device_manager_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = DeviceManager(storage_path=Path(tmpdir))
        assert manager.devices_path.exists()


def test_update_device():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = DeviceManager(storage_path=Path(tmpdir))

        initial_devices = [{"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5}]
        manager.save_devices("test.gds", initial_devices)

        new_params = {"value": 200, "unit": "Omega"}
        success = manager.update_device("test.gds", "R1", new_params)
        assert success is True

        devices = manager.load_current_devices("test.gds")
        assert devices[0]["parameters"]["value"] == 200


def test_save_devices():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = DeviceManager(storage_path=Path(tmpdir))

        devices = [
            {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5},
            {"name": "C1", "device_type": "C", "x": 20, "y": 20, "width": 15, "height": 15}
        ]

        success = manager.save_devices("test.gds", devices)
        assert success is True

        loaded = manager.load_current_devices("test.gds")
        assert len(loaded) == 2


def test_load_current_devices():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = DeviceManager(storage_path=Path(tmpdir))

        devices = [{"name": "L1", "device_type": "L", "x": 0, "y": 0, "width": 20, "height": 20}]
        manager.save_devices("test.gds", devices)

        loaded = manager.load_current_devices("test.gds")
        assert len(loaded) == 1
        assert loaded[0]["name"] == "L1"
