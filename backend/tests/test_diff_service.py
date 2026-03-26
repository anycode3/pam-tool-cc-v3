import pytest
from pathlib import Path
import tempfile
import json

from app.services.diff_service import diff_service
from app.services.version_manager import version_manager


def test_compare_added_devices():
    """测试新增器件的对比"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = diff_service.versions_path
        diff_service.versions_path = Path(tmpdir)
        version_manager.versions_path = Path(tmpdir)

        try:
            # 版本1: 只有R1
            devices_v1 = [
                {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5, "parameters": {"value": 100}}
            ]
            v1 = version_manager.save_version("test.gds", devices_v1, "version1")

            # 版本2: R1 + 新增C1
            devices_v2 = [
                {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5, "parameters": {"value": 100}},
                {"name": "C1", "device_type": "C", "x": 20, "y": 20, "width": 15, "height": 15, "parameters": {"value": "1pF"}}
            ]
            v2 = version_manager.save_version("test.gds", devices_v2, "version2", force=True)

            # 对比
            diff = diff_service.compare_versions("test.gds", v1.version_id, v2.version_id)

            assert diff is not None
            assert diff.file_name == "test.gds"
            assert diff.version1_id == v1.version_id
            assert diff.version2_id == v2.version_id
            assert diff.summary["added"] == 1
            assert diff.summary["removed"] == 0
            assert diff.summary["modified"] == 0

            # 查找新增的C1
            added_changes = [c for c in diff.changes if c.change_type == "added"]
            assert len(added_changes) == 1
            assert added_changes[0].device_name == "C1"
        finally:
            diff_service.versions_path = old_path
            version_manager.versions_path = old_path


def test_compare_removed_devices():
    """测试删除器件的对比"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = diff_service.versions_path
        diff_service.versions_path = Path(tmpdir)
        version_manager.versions_path = Path(tmpdir)

        try:
            # 版本1: R1 + C1
            devices_v1 = [
                {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5},
                {"name": "C1", "device_type": "C", "x": 20, "y": 20, "width": 15, "height": 15}
            ]
            v1 = version_manager.save_version("test.gds", devices_v1, "version1")

            # 版本2: 只有R1
            devices_v2 = [
                {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5}
            ]
            v2 = version_manager.save_version("test.gds", devices_v2, "version2", force=True)

            # 对比
            diff = diff_service.compare_versions("test.gds", v1.version_id, v2.version_id)

            assert diff is not None
            assert diff.summary["added"] == 0
            assert diff.summary["removed"] == 1
            assert diff.summary["modified"] == 0

            # 查找删除的C1
            removed_changes = [c for c in diff.changes if c.change_type == "removed"]
            assert len(removed_changes) == 1
            assert removed_changes[0].device_name == "C1"
        finally:
            diff_service.versions_path = old_path
            version_manager.versions_path = old_path


def test_compare_modified_devices():
    """测试修改器件的对比"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = diff_service.versions_path
        diff_service.versions_path = Path(tmpdir)
        version_manager.versions_path = Path(tmpdir)

        try:
            # 版本1: R1 at (0, 0)
            devices_v1 = [
                {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5, "parameters": {"value": 100}}
            ]
            v1 = version_manager.save_version("test.gds", devices_v1, "version1")

            # 版本2: R1 moved to (10, 10) with different value
            devices_v2 = [
                {"name": "R1", "device_type": "R", "x": 10, "y": 10, "width": 10, "height": 5, "parameters": {"value": 200}}
            ]
            v2 = version_manager.save_version("test.gds", devices_v2, "version2", force=True)

            # 对比
            diff = diff_service.compare_versions("test.gds", v1.version_id, v2.version_id)

            assert diff is not None
            assert diff.summary["added"] == 0
            assert diff.summary["removed"] == 0
            assert diff.summary["modified"] == 1

            # 查找修改的R1
            modified_changes = [c for c in diff.changes if c.change_type == "modified"]
            assert len(modified_changes) == 1
            assert modified_changes[0].device_name == "R1"
            assert 'x' in modified_changes[0].diff_fields
            assert 'y' in modified_changes[0].diff_fields
            assert 'parameters' in modified_changes[0].diff_fields
        finally:
            diff_service.versions_path = old_path
            version_manager.versions_path = old_path


def test_compare_no_changes():
    """测试无变化的对比"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = diff_service.versions_path
        diff_service.versions_path = Path(tmpdir)
        version_manager.versions_path = Path(tmpdir)

        try:
            devices = [
                {"name": "R1", "device_type": "R", "x": 0, "y": 0, "width": 10, "height": 5}
            ]

            v1 = version_manager.save_version("test.gds", devices, "version1")
            v2 = version_manager.save_version("test.gds", devices, "version2", force=True)

            # 对比
            diff = diff_service.compare_versions("test.gds", v1.version_id, v2.version_id)

            assert diff is not None
            assert diff.summary["added"] == 0
            assert diff.summary["removed"] == 0
            assert diff.summary["modified"] == 0
            assert len(diff.changes) == 0
        finally:
            diff_service.versions_path = old_path
            version_manager.versions_path = old_path


def test_compare_nonexistent_version():
    """测试不存在的版本"""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = diff_service.versions_path
        diff_service.versions_path = Path(tmpdir)

        try:
            # 不存在的版本ID
            diff = diff_service.compare_versions("test.gds", "nonexistent1", "nonexistent2")
            assert diff is None
        finally:
            diff_service.versions_path = old_path
