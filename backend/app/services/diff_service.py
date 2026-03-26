import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from copy import deepcopy

from app.core.config import settings
from app.schemas.diff import DeviceChange, VersionDiffResponse
from app.services.version_manager import version_manager

logger = logging.getLogger(__name__)


class DiffService:
    """版本对比服务"""

    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.versions_path = self.storage_path / "versions"

    def compare_versions(
        self,
        file_name: str,
        version1_id: str,
        version2_id: str
    ) -> Optional[VersionDiffResponse]:
        """
        对比两个版本之间的差异

        Args:
            file_name: GDS文件名
            version1_id: 版本1 ID
            version2_id: 版本2 ID

        Returns:
            VersionDiffResponse: 版本对比结果
        """
        try:
            # 加载两个版本
            v1_data = self._load_version_data(file_name, version1_id)
            v2_data = self._load_version_data(file_name, version2_id)

            if not v1_data or not v2_data:
                return None

            # 提取器件数据
            devices1 = v1_data.get('total_devices', {})
            devices2 = v2_data.get('total_devices', {})

            # 计算差异
            changes = self._compute_diff(devices1, devices2)

            # 统计汇总
            summary = {
                "added": len([c for c in changes if c.change_type == "added"]),
                "removed": len([c for c in changes if c.change_type == "removed"]),
                "modified": len([c for c in changes if c.change_type == "modified"])
            }

            return VersionDiffResponse(
                file_name=file_name,
                version1_id=version1_id,
                version1_description=v1_data.get('description'),
                version1_timestamp=v1_data.get('timestamp'),
                version2_id=version2_id,
                version2_description=v2_data.get('description'),
                version2_timestamp=v2_data.get('timestamp'),
                changes=changes,
                summary=summary
            )

        except Exception as e:
            logger.error(f"版本对比失败: {e}")
            return None

    def _load_version_data(self, file_name: str, version_id: str) -> Optional[Dict]:
        """
        加载版本数据

        Args:
            file_name: GDS文件名
            version_id: 版本ID

        Returns:
            Dict: 版本数据
        """
        try:
            version_file = self.versions_path / f"{file_name}_{version_id}.json"
            if not version_file.exists():
                logger.warning(f"版本文件不存在: {version_file}")
                return None

            with open(version_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"加载版本数据失败: {e}")
            return None

    def _compute_diff(
        self,
        devices1: Dict[str, Dict[str, Any]],
        devices2: Dict[str, Dict[str, Any]]
    ) -> List[DeviceChange]:
        """
        计算两个版本之间的差异

        Args:
            devices1: 版本1的器件字典
            devices2: 版本2的器件字典

        Returns:
            List[DeviceChange]: 变化列表
        """
        changes = []
        device_names1 = set(devices1.keys())
        device_names2 = set(devices2.keys())

        # 查找新增的器件
        added_devices = device_names2 - device_names1
        for device_name in added_devices:
            device_data = devices2[device_name]
            changes.append(DeviceChange(
                device_name=device_name,
                device_type=device_data.get('device_type', ''),
                change_type="added",
                new_value=self._clean_device_data(device_data),
                diff_fields=None
            ))

        # 查找删除的器件
        removed_devices = device_names1 - device_names2
        for device_name in removed_devices:
            device_data = devices1[device_name]
            changes.append(DeviceChange(
                device_name=device_name,
                device_type=device_data.get('device_type', ''),
                change_type="removed",
                old_value=self._clean_device_data(device_data),
                diff_fields=None
            ))

        # 查找修改的器件
        common_devices = device_names1 & device_names2
        for device_name in common_devices:
            old_data = devices1[device_name]
            new_data = devices2[device_name]

            diff_fields = self._compare_device_data(old_data, new_data)
            if diff_fields:
                changes.append(DeviceChange(
                    device_name=device_name,
                    device_type=old_data.get('device_type', ''),
                    change_type="modified",
                    old_value=self._clean_device_data(old_data),
                    new_value=self._clean_device_data(new_data),
                    diff_fields=diff_fields
                ))

        return changes

    def _compare_device_data(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> List[str]:
        """
        比较两个器件数据，返回发生变化的字段列表

        Args:
            old_data: 旧数据
            new_data: 新数据

        Returns:
            List[str]: 发生变化的字段列表
        """
        diff_fields = []

        # 基础字段
        for field in ['device_type', 'x', 'y', 'width', 'height', 'layer']:
            old_val = old_data.get(field)
            new_val = new_data.get(field)
            if old_val != new_val:
                diff_fields.append(field)

        # 参数字段
        old_params = old_data.get('parameters', {})
        new_params = new_data.get('parameters', {})
        if old_params != new_params:
            diff_fields.append('parameters')

        return diff_fields

    def _clean_device_data(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理器件数据，移除不必要的信息

        Args:
            device_data: 原始器件数据

        Returns:
            Dict: 清理后的数据
        """
        cleaned = {}
        for key, value in device_data.items():
            if key not in ['layer', 'points']:
                cleaned[key] = deepcopy(value)
        return cleaned


# 创建服务实例
diff_service = DiffService()
