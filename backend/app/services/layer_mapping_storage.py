import json
import logging
from pathlib import Path
from typing import Dict, Optional

from app.schemas.gds_mapping import LayerMapping

logger = logging.getLogger(__name__)


class LayerMappingStorage:
    """图层映射持久化存储"""

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path("storage/mappings")
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, file_name: str, mapping: LayerMapping) -> bool:
        """保存图层映射"""
        try:
            mapping_file = self.storage_path / f"{file_name}.json"
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping.dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"图层映射已保存: {file_name}")
            return True
        except Exception as e:
            logger.error(f"保存图层映射失败 {file_name}: {e}")
            return False

    def load(self, file_name: str) -> Optional[LayerMapping]:
        """加载图层映射"""
        try:
            mapping_file = self.storage_path / f"{file_name}.json"
            if not mapping_file.exists():
                return None

            with open(mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return LayerMapping(**data)
        except Exception as e:
            logger.error(f"加载图层映射失败 {file_name}: {e}")
            return None

    def delete(self, file_name: str) -> bool:
        """删除图层映射"""
        try:
            mapping_file = self.storage_path / f"{file_name}.json"
            if mapping_file.exists():
                mapping_file.unlink()
                logger.info(f"图层映射已删除: {file_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除图层映射失败 {file_name}: {e}")
            return False

    def list_all(self) -> Dict[str, LayerMapping]:
        """列出所有图层映射"""
        try:
            mappings = {}
            for mapping_file in self.storage_path.glob("*.json"):
                file_name = mapping_file.stem
                mapping = self.load(file_name)
                if mapping:
                    mappings[file_name] = mapping
            return mappings
        except Exception as e:
            logger.error(f"列出图层映射失败: {e}")
            return {}
