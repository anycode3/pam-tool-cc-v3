import pytest
from pathlib import Path
import json
import tempfile
import os

from app.services.version_manager import version_manager
from app.services.device_manager import device_manager


def test_save_version():
    """测试保存版本功能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 临时修改存储路径
        old_path = version_manager.versions_path
        version_manager.versions_path = Path(tmpdir)

        try:
            devices = [
                {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5},
                {"name": "C1", "device_type": "C", "x": 20, "y": 20, "width": 15, "height": 15}
            ]

            version = version_manager.save_version("test.gds", devices, "initial_version")
            assert version is not None
            assert version.version_id is not None
            assert version.file_name == "test.gds"
            assert version.device_count == 2
        finally:
            version_manager.versions_path = old_path


def test_get_versions():
    """测试获取版本列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = version_manager.versions_path
        version_manager.versions_path = Path(tmpdir)

        try:
            devices = [{"name": "D1", "device_type": "D", "x": 0, "y": 0, "width": 5, "height": 5}]
            version_manager.save_version("test.gds", devices, "version1")
            version_manager.save_version("test.gds", devices, "version2", force=True)

            versions = version_manager.get_versions("test.gds")
            assert len(versions) == 2
            # 验证两个版本都被保存（不依赖顺序，因为时间戳可能相同）
            descriptions = [v.description for v in versions]
            assert "version1" in descriptions
            assert "version2" in descriptions
        finally:
            version_manager.versions_path = old_path


def test_rollback():
    """测试版本回滚"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = version_manager.versions_path
        version_manager.versions_path = Path(tmpdir)

        try:
            devices_v1 = [{"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5}]
            devices_v2 = [{"name": "R1", "device_type": "R", "x": 5, "y": 5, "width": 10, "height": 5}]

            v1 = version_manager.save_version("test.gds", devices_v1, "version1")
            v2 = version_manager.save_version("test.gds", devices_v2, "version2", force=True)

            devices = version_manager.rollback("test.gds", v1.version_id)
            assert devices is not None
            assert devices[0]["x"] == 0
        finally:
            version_manager.versions_path = old_path


def test_delete_version():
    """测试删除版本"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = version_manager.versions_path
        version_manager.versions_path = Path(tmpdir)

        try:
            devices = [{"name": "D2", "device_type": "D", "x": 0, "y": 0, "width": 5, "height": 5}]
            version = version_manager.save_version("test.gds", devices, "test_version")

            success = version_manager.delete_version("test.gds", version.version_id)
            assert success is True

            versions = version_manager.get_versions("test.gds")
            assert len(versions) == 0
        finally:
            version_manager.versions_path = old_path


def test_update_device():
    """测试更新器件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = device_manager.devices_path
        device_manager.devices_path = Path(tmpdir)

        try:
            initial_devices = [{"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5}]
            device_manager.save_devices("test.gds", initial_devices)

            new_params = {"value": 200, "unit": "Omega"}
            success = device_manager.update_device("test.gds", "R1", new_params)
            assert success is True

            devices = device_manager.load_current_devices("test.gds")
            # update_device 保存的是参数字典，不是器件列表
            assert devices[0]["parameters"] is not None
        finally:
            device_manager.devices_path = old_path


def test_save_devices():
    """测试保存器件列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = device_manager.devices_path
        device_manager.devices_path = Path(tmpdir)

        try:
            devices = [
                {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5},
                {"name": "C1", "device_type": "C", "x": 20, "y": 20, "width": 15, "height": 15}
            ]

            success = device_manager.save_devices("test.gds", devices)
            assert success is True

            loaded = device_manager.load_current_devices("test.gds")
            assert len(loaded) == 2
        finally:
            device_manager.devices_path = old_path


def test_load_current_devices():
    """测试加载当前器件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = device_manager.devices_path
        device_manager.devices_path = Path(tmpdir)

        try:
            devices = [{"name": "L1", "device_type": "L", "x": 0, "y": 0, "width": 20, "height": 20}]
            device_manager.save_devices("test.gds", devices)

            loaded = device_manager.load_current_devices("test.gds")
            assert len(loaded) == 1
            assert loaded[0]["name"] == "L1"
        finally:
            device_manager.devices_path = old_path
