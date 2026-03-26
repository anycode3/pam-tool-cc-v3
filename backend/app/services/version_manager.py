import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from copy import deepcopy

from app.core.config import settings
from app.schemas.device import VersionInfo, VersionSaveRequest, DeviceUpdateRequest

logger = logging.getLogger(__name__)


class VersionManager:
    """版本管理服务"""

    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.versions_path = self.storage_path / "versions"
        self.versions_path.mkdir(parents=True, exist_ok=True)

    def save_version(
        self,
        file_name: str,
        devices: List[dict],
        description: Optional[str] = None,
        force: bool = False
    ) -> Optional[VersionInfo]:
        """
        保存当前版本

        Args:
            file_name: GDS文件名
            devices: 当前器件列表
            description: 版本描述
            force: 是否强制保存

        Returns:
            VersionInfo: 保存的版本信息
        """
        try:
            # 获取文件的历史版本列表
            versions = self._get_versions(file_name)

            # 如果不强制且当前版本与最新版本相同，则不保存
            if not force and versions:
                latest_version = versions[-1]
                latest_devices = latest_version.total_devices or {}
                current_devices = {d['name']: d for d in devices}

                if self._devices_equal(latest_devices, current_devices):
                    logger.info(f"当前版本与最新版本相同，跳过保存")
                    return None

            # 生成版本ID
            version_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 构建版本信息
            version_info = {
                "version_id": version_id,
                "file_name": file_name,
                "timestamp": timestamp,
                "description": description,
                "device_count": len(devices),
                "total_devices": {d['name']: deepcopy(d) for d in devices}
            }

            # 保存到文件
            version_file = self.versions_path / f"{file_name}_{version_id}.json"
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, ensure_ascii=False, indent=2)

            logger.info(f"版本已保存: {file_name} v{version_id}")
            return VersionInfo(**version_info)

        except Exception as e:
            logger.error(f"保存版本失败: {e}")
            return None

    def get_versions(self, file_name: str) -> List[VersionInfo]:
        """
        获取文件的所有版本

        Args:
            file_name: GDS文件名

        Returns:
            List[VersionInfo]: 版本列表（按时间倒序）
        """
        return self._get_versions(file_name)

    def _get_versions(self, file_name: str) -> List[VersionInfo]:
        """内部方法：获取并排序版本列表"""
        try:
            version_files = list(self.versions_path.glob(f"{file_name}_*.json"))

            versions = []
            for vf in version_files:
                try:
                    with open(vf, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        versions.append(VersionInfo(**data))
                except Exception as e:
                    logger.warning(f"读取版本文件失败 {vf}: {e}")
                    continue

            # 按时间戳排序（新的在前）
            versions.sort(key=lambda x: x.timestamp, reverse=True)
            return versions

        except Exception as e:
            logger.error(f"获取版本列表失败: {e}")
            return []

    def rollback(
        self,
        file_name: str,
        version_id: str
    ) -> Optional[List[dict]]:
        """
        回滚到指定版本

        Args:
            file_name: GDS文件名
            version_id: 版本ID

        Returns:
            List[dict]: 回滚后的器件列表
        """
        try:
            version_file = self.versions_path / f"{file_name}_{version_id}.json"

            if not version_file.exists():
                logger.error(f"版本文件不存在: {version_id}")
                return None

            with open(version_file, 'r', encoding='utf-8') as f:
                version_info = json.load(f)

            devices = version_info.get('total_devices', [])
            logger.info(f"回滚到版本: {file_name} v{version_id}")
            return list(devices.values())

        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return None

    def delete_version(self, file_name: str, version_id: str) -> bool:
        """
        删除指定版本

        Args:
            file_name: GDS文件名
            version_id: 版本ID

        Returns:
            bool: 是否删除成功
        """
        try:
            version_file = self.versions_path / f"{file_name}_{version_id}.json"

            if not version_file.exists():
                return False

            version_file.unlink()
            logger.info(f"版本已删除: {file_name} v{version_id}")
            return True

        except Exception as e:
            logger.error(f"删除版本失败: {e}")
            return False

    def _devices_equal(self, devices1: Dict, devices2: Dict) -> bool:
        """
        比较两个设备字典是否相等（忽略时间戳参数）

        Args:
            devices1: 设备字典1
            devices2: 设备字典2

        Returns:
            bool: 是否相等
        """
        if set(devices1.keys()) != set(devices2.keys()):
            return False

        for key in devices1:
            d1 = deepcopy(devices1[key])
            d2 = deepcopy(devices2[key])

            # 移除比较时忽略的字段
            for field in ['parameters', 'layer']:
                d1.pop(field, None)
                d2.pop(field, None)

            if d1 != d2:
                return False

        return True


# 创建服务实例
version_manager = VersionManager()
