import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from copy import deepcopy

from app.core.config import settings
from app.schemas.device import DeviceUpdateRequest

logger = logging.getLogger(__name__)


class DeviceManager:
    """器件管理服务"""

    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.devices_path = self.storage_path / "current"
        self.devices_path.mkdir(parents=True, exist_ok=True)

    def update_device(
        self,
        file_name: str,
        device_name: str,
        parameters: Dict[str, any]
    ) -> bool:
        """
        更新单个器件

        Args:
            file_name: GDS文件名
            device_name: 器件名称
            parameters: 新的参数

        Returns:
            bool: 是否更新成功
        """
        try:
            devices_file = self.devices_path / f"{file_name}.json"

            if not devices_file.exists():
                logger.error(f"器件文件不存在: {devices_file}")
                return False

            with open(devices_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 更新指定器件
            if 'devices' not in data:
                data['devices'] = {}

            data['devices'][device_name] = parameters

            # 保存
            with open(devices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"器件已更新: {device_name}")
            return True

        except Exception as e:
            logger.error(f"更新器件失败: {e}")
            return False

    def get_devices(self, file_name: str) -> Dict[str, Dict[str, any]]:
        """
        获取文件的所有器件

        Args:
            file_name: GDS文件名

        Returns:
            Dict: 器件字典
        """
        try:
            devices_file = self.devices_path / f"{file_name}.json"

            if not devices_file.exists():
                return {}

            with open(devices_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return data.get('devices', {})

        except Exception as e:
            logger.error(f"获取器件列表失败: {e}")
            return {}

    def save_devices(
        self,
        file_name: str,
        devices: List[dict]
    ) -> bool:
        """
        保存器件列表（用于版本管理）

        Args:
            file_name: GDS文件名
            devices: 器件列表

        Returns:
            bool: 是否保存成功
        """
        try:
            devices_file = self.devices_path / f"{file_name}.json"

            # 构建保存数据
            devices_dict = {d['name']: d for d in devices}

            data = {
                'file_name': file_name,
                'devices': devices_dict,
                'updated_at': json.dumps(None)
            }

            with open(devices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"器件列表已保存: {file_name}")
            return True

        except Exception as e:
            logger.error(f"保存器件列表失败: {e}")
            return False

    def load_current_devices(self, file_name: str) -> List[dict]:
        """
        加载当前器件列表

        Args:
            file_name: GDS文件名

        Returns:
            List[dict]: 器件列表
        """
        try:
            devices_file = self.devices_path / f"{file_name}.json"

            if not devices_file.exists():
                return []

            with open(devices_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            devices = data.get('devices', {})

            # 转换为列表格式
            result = []
            for name, params in devices.items():
                result.append({
                    'name': name,
                    'device_type': params.get('device_type', ''),
                    'x': params.get('x', 0),
                    'y': params.get('y', 0),
                    'width': params.get('width', 0),
                    'height': params.get('height', 0),
                    'layer': params.get('layer', 0),
                    'parameters': params.get('parameters', {})
                })

            return result

        except Exception as e:
            logger.error(f"加载当前器件失败: {e}")
            return []


# 创建服务实例
device_manager = DeviceManager()
