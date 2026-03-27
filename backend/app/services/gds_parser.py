import os
import logging
from typing import List, Dict, Optional
from pathlib import Path

import gdstk

from app.core.config import settings
from app.schemas.gds import DeviceInfo, GDSParseResponse, GDSLayerInfo
from app.schemas.gds_mapping import LayerMapping
from app.services.device_recognizer import DeviceRecognizer, DeviceCandidate
from app.services.layer_mapping_storage import LayerMappingStorage

logger = logging.getLogger(__name__)


class GDSParserService:
    """GDS文件解析服务"""

    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.layer_mapping_storage = LayerMappingStorage(self.storage_path)

    def parse_gds_file_with_mapping(
        self,
        file_name: str,
        layer_mapping: LayerMapping
    ) -> GDSParseResponse:
        """
        使用图层映射解析GDS文件并提取器件信息

        Args:
            file_name: GDS文件名
            layer_mapping: 图层映射配置

        Returns:
            GDSParseResponse: 解析结果
        """
        try:
            file_path = self.storage_path / file_name

            if not file_path.exists():
                return GDSParseResponse(
                    file_name=file_name,
                    cell_count=0,
                    devices=[],
                    success=False,
                    message=f"文件不存在: {file_name}"
                )

            # 使用gdstk读取GDS文件
            library = gdstk.read_gds(str(file_path))

            # 使用图层映射提取设备信息
            devices = self.extract_devices_with_mapping(library, layer_mapping)

            return GDSParseResponse(
                file_name=file_name,
                cell_count=len(library.cells),
                devices=devices,
                success=True,
                message=f"成功解析文件: {file_name}（使用图层映射）"
            )

        except Exception as e:
            logger.error(f"解析GDS文件失败: {e}")
            return GDSParseResponse(
                file_name=file_name,
                cell_count=0,
                devices=[],
                success=False,
                message=f"解析失败: {str(e)}"
            )

    def parse_gds_file(self, file_name: str) -> GDSParseResponse:
        """
        解析GDS文件并提取设备信息

        Args:
            file_name: GDS文件名

        Returns:
            GDSParseResponse: 解析结果
        """
        try:
            file_path = self.storage_path / file_name

            if not file_path.exists():
                return GDSParseResponse(
                    file_name=file_name,
                    cell_count=0,
                    devices=[],
                    success=False,
                    message=f"文件不存在: {file_name}"
                )

            # 使用gdstk读取GDS文件
            library = gdstk.read_gds(str(file_path))

            # 提取设备信息
            devices = self._extract_devices(library)

            return GDSParseResponse(
                file_name=file_name,
                cell_count=len(library.cells),
                devices=devices,
                success=True,
                message=f"成功解析文件: {file_name}"
            )

        except Exception as e:
            logger.error(f"解析GDS文件失败: {e}")
            return GDSParseResponse(
                file_name=file_name,
                cell_count=0,
                devices=[],
                success=False,
                message=f"解析失败: {str(e)}"
            )

    def set_layer_mapping(self, file_name: str, layer_mapping: LayerMapping) -> bool:
        """设置GDS文件的图层映射（持久化）"""
        return self.layer_mapping_storage.save(file_name, layer_mapping)

    def get_layer_mapping(self, file_name: str) -> Optional[LayerMapping]:
        """获取GDS文件的图层映射（从持久化存储读取）"""
        return self.layer_mapping_storage.load(file_name)

    def delete_layer_mapping(self, file_name: str) -> bool:
        """删除GDS文件的图层映射"""
        return self.layer_mapping_storage.delete(file_name)

    def list_all_layer_mappings(self) -> Dict[str, LayerMapping]:
        """列出所有图层映射"""
        return self.layer_mapping_storage.list_all()

    def _extract_devices(self, library: gdstk.Library) -> List[DeviceInfo]:
        """
        从GDS库中提取设备信息
        如果设置了图层映射，则使用DeviceRecognizer进行器件识别

        Args:
            library: GDS库对象

        Returns:
            List[DeviceInfo]: 设备信息列表
        """
        devices = []
        polygons = []
        labels = []

        # 收集所有多边形和标签
        for cell in library.cells:
            polygons.extend(cell.polygons)
            labels.extend(cell.labels)

        # 如果设置了图层映射，使用器件识别器
        # 注意：这里简化实现，实际需要关联file名
        # 暂时使用非器件识别的方式

        # 遍历cell中的所有多边形，假设它们代表设备
        for polygon in polygons:
            device_info = self._polygon_to_device(polygon)
            if device_info:
                devices.append(device_info)

        # 遍历cell中的标签
        for label in labels:
            device_info = self._label_to_device(label)
            if device_info:
                devices.append(device_info)

        return devices

    def extract_devices_with_mapping(
        self,
        library: gdstk.Library,
        layer_mapping: LayerMapping
    ) -> List[DeviceInfo]:
        """
        使用图层映射识别器件

        Args:
            library: GDS库对象
            layer_mapping: 图层映射配置

        Returns:
            List[DeviceInfo]: 设备信息列表
        """
        devices = []
        polygons = []
        labels = []

        # 收集所有多边形和标签
        for cell in library.cells:
            polygons.extend(cell.polygons)
            labels.extend(cell.labels)

        # 使用器件识别器
        recognizer = DeviceRecognizer(layer_mapping)
        device_candidates = recognizer.recognize_devices(polygons, labels)

        # 转换为DeviceInfo格式
        for i, candidate in enumerate(device_candidates):
            if candidate.polygons:
                # 计算边界框
                bbox = self._calculate_bbox(candidate.polygons)
                devices.append(DeviceInfo(
                    name=f"{candidate.device_type}_{i+1}",
                    device_type=candidate.device_type,
                    x=bbox['min_x'],
                    y=bbox['min_y'],
                    width=bbox['max_x'] - bbox['min_x'],
                    height=bbox['max_y'] - bbox['min_y'],
                    layer=candidate.polygons[0].layer,
                    parameters={
                        "value": candidate.value,
                        "unit": candidate.unit,
                        "polygon_count": len(candidate.polygons),
                        "label_count": len(candidate.labels)
                    }
                ))

        return devices

    def _calculate_bbox(self, polygons: List[gdstk.Polygon]) -> Dict[str, float]:
        """计算多个多边形的边界框"""
        all_points = []
        for poly in polygons:
            all_points.extend(poly.points.tolist())

        if not all_points:
            return {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0}

        x_coords = [p[0] for p in all_points]
        y_coords = [p[1] for p in all_points]

        return {
            'min_x': min(x_coords),
            'max_x': max(x_coords),
            'min_y': min(y_coords),
            'max_y': max(y_coords)
        }

    def _polygon_to_device(self, polygon: gdstk.Polygon) -> DeviceInfo:
        """
        将多边形转换为设备信息

        Args:
            polygon: gdstk多边形对象

        Returns:
            DeviceInfo: 设备信息
        """
        # 获取多边形边界
        coordinates = polygon.points.tolist()
        x_coords = [coord[0] for coord in coordinates]
        y_coords = [coord[1] for coord in coordinates]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        return DeviceInfo(
            name=f"poly_{polygon.datatype}",
            device_type="polygon",
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            layer=polygon.layer,
            parameters={
                "datatype": polygon.datatype,
                "point_count": len(coordinates)
            }
        )

    def _label_to_device(self, label: gdstk.Label) -> Optional[DeviceInfo]:
        """
        将标签转换为设备信息

        Args:
            label: gdstk标签对象

        Returns:
            DeviceInfo: 设备信息，如果标签不包含设备信息则返回None
        """
        text = label.text

        # 简单假设：如果标签包含特定关键词，则为设备
        if any(keyword in text.upper() for keyword in ["RES", "CAP", "IND", "NMOS", "PMOS"]):
            return DeviceInfo(
                name=text,
                device_type="label",
                x=label.origin[0],
                y=label.origin[1],
                width=0.0,
                height=0.0,
                layer=label.layer,
                parameters={
                    "datatype": label.datatype,
                    "rotation": label.rotation,
                    "magnification": label.magnification
                }
            )

        return None

    def get_geometry_info(self, file_name: str) -> Dict:
        """
        获取GDS文件的几何信息

        Args:
            file_name: GDS文件名

        Returns:
            Dict: 几何信息
        """
        try:
            file_path = self.storage_path / file_name

            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_name}")

            library = gdstk.read_gds(str(file_path))

            # 计算全局边界框
            min_x, max_x, min_y, max_y = 0, 0, 0, 0

            for cell in library.cells:
                for polygon in cell.polygons:
                    coords = polygon.points.tolist()
                    for coord in coords:
                        min_x = min(min_x, coord[0])
                        max_x = max(max_x, coord[0])
                        min_y = min(min_y, coord[1])
                        max_y = max(max_y, coord[1])

            return {
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
                "width": max_x - min_x,
                "height": max_y - min_y,
                "cell_count": len(library.cells)
            }

        except Exception as e:
            logger.error(f"获取几何信息失败: {e}")
            raise

    def get_layer_info(self, file_name: str) -> List[GDSLayerInfo]:
        """
        获取GDS文件的图层信息

        Args:
            file_name: GDS文件名

        Returns:
            List[GDSLayerInfo]: 图层信息列表
        """
        try:
            file_path = self.storage_path / file_name

            if not file_path.exists():
                return []

            library = gdstk.read_gds(str(file_path))
            layer_info_dict: Dict[int, GDSLayerInfo] = {}

            for cell in library.cells:
                for polygon in cell.polygons:
                    if polygon.layer not in layer_info_dict:
                        layer_info_dict[polygon.layer] = GDSLayerInfo(
                            layer_number=polygon.layer,
                            layer_name=f"Layer_{polygon.layer}",
                            datatype=polygon.datatype,
                            polygon_count=0
                        )
                    layer_info_dict[polygon.layer].polygon_count += 1

            return list(layer_info_dict.values())

        except Exception as e:
            logger.error(f"获取图层信息失败: {e}")
            return []


# 创建服务实例
gds_parser_service = GDSParserService()
