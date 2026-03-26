import logging
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.schemas.gds_mapping import LayerMapping, GDSLayerMappingConfig, DeviceValue
from app.utils.gds_mock import Polygon, Label

logger = logging.getLogger(__name__)


@dataclass
class DeviceCandidate:
    """器件候选"""
    device_type: str  # L, C, R, PAD, GND
    polygons: List[Polygon]  # 组成器件的多边形
    labels: List[Label]  # 相关标签
    value: Optional[float] = None  # 器件值
    unit: Optional[str] = None  # 单位


class DeviceRecognizer:
    """器件识别器 - 根据形态和图层规则识别器件"""

    def __init__(self, layer_mapping: LayerMapping):
        self.mapping = layer_mapping

    def recognize_devices(
        self,
        polygons: List[Polygon],
        labels: List[Label]
    ) -> List[DeviceCandidate]:
        """
        识别器件

        Args:
            polygons: 所有多边形
            labels: 所有标签

        Returns:
            List[DeviceCandidate]: 识别到的器件列表
        """
        devices = []

        # 按图层分组
        polygons_by_layer = self._group_polygons_by_layer(polygons)

        # 识别螺旋电感 (L) - 包含ME1. ME2层，螺旋形态
        inductors = self._recognize_inductors(polygons_by_layer)
        devices.extend(inductors)

        # 识别平板电容 (C) - 包含ME1. ME2层，平行板形态
        capacitors = self._recognize_capacitors(polygons_by_layer)
        devices.extend(capacitors)

        # 识别薄片电阻 (R) - 只有TFR层
        resistors = self._recognize_resistors(polygons_by_layer)
        devices.extend(resistors)

        # 识别焊盘 (PAD) - 穿透ME1. ME2. VA1
        pads = self._recognize_pads(polygons_by_layer)
        devices.extend(pads)

        # 识别地孔 (GND) - 穿透GND. ME1. ME2. VA1
        gnd_vias = self._recognize_gnd_vias(polygons_by_layer)
        devices.extend(gnd_vias)

        return devices

    def _group_polygons_by_layer(self, polygons: List[Polygon]) -> Dict[int, List[Polygon]]:
        """按图层分组多边形"""
        result = {}
        for poly in polygons:
            if poly.layer not in result:
                result[poly.layer] = []
            result[poly.layer].append(poly)
        return result

    def _recognize_inductors(
        self,
        polygons_by_layer: Dict[int, List[Polygon]]
    ) -> List[DeviceCandidate]:
        """
        识别螺旋电感

        特征：
        - 包含ME1和ME2两层
        - 存在螺旋形态（多个矩形按螺旋排列）
        """
        inductors = []
        me1_polys = polygons_by_layer.get(self.mapping.me1, [])
        me2_polys = polygons_by_layer.get(self.mapping.me2, [])

        # 简单实现：寻找ME1和ME2中形状相似的矩形组合
        # 实际需要更复杂的螺旋检测算法
        for poly1 in me1_polys:
            for poly2 in me2_polys:
                if self._is_spiral_pattern([poly1, poly2]):
                    value = self._calculate_inductance([poly1, poly2])
                    inductors.append(DeviceCandidate(
                        device_type="L",
                        polygons=[poly1, poly2],
                        labels=[],
                        value=value.value,
                        unit=value.unit
                    ))
                    break  # 避免重复匹配

        return inductors

    def _recognize_capacitors(
        self,
        polygons_by_layer: Dict[int, List[Polygon]]
    ) -> List[DeviceCandidate]:
        """
        识别平板电容

        特征：
        - 包含ME1和ME2两层
        - 两个矩形重叠形成平行板结构
        """
        capacitors = []
        me1_polys = polygons_by_layer.get(self.mapping.me1, [])
        me2_polys = polygons_by_layer.get(self.mapping.me2, [])

        # 寻找ME1和ME2中重叠的矩形对
        for poly1 in me1_polys:
            for poly2 in me2_polys:
                if self._is_overlapping(poly1, poly2):
                    value = self._calculate_capacitance([poly1, poly2])
                    capacitors.append(DeviceCandidate(
                        device_type="C",
                        polygons=[poly1, poly2],
                        labels=[],
                        value=value.value,
                        unit=value.unit
                    ))

        return capacitors

    def _recognize_resistors(
        self,
        polygons_by_layer: Dict[int, List[Polygon]]
    ) -> List[DeviceCandidate]:
        """
        识别薄片电阻

        特征：
        - 只有TFR层
        - 长条形矩形
        """
        resistors = []
        tfr_polys = polygons_by_layer.get(self.mapping.tfr, [])

        for poly in tfr_polys:
            if self._is_rectangular_shape(poly):
                value = self._calculate_resistance(poly)
                resistors.append(DeviceCandidate(
                    device_type="R",
                    polygons=[poly],
                    labels=[],
                    value=value.value,
                    unit=value.unit
                ))

        return resistors

    def _recognize_pads(
        self,
        polygons_by_layer: Dict[int, List[Polygon]]
    ) -> List[DeviceCandidate]:
        """
        识别焊盘

        特征：
        - 穿透ME1、ME2、VA1层
        - 较大的矩形块
        """
        pads = []

        # 寻找ME1中的大矩形
        me1_polys = polygons_by_layer.get(self.mapping.me1, [])
        for poly in me1_polys:
            if self._is_large_rectangle(poly):
                pads.append(DeviceCandidate(
                    device_type="PAD",
                    polygons=[poly],
                    labels=[],
                    value=None,
                    unit=None
                ))

        return pads

    def _recognize_gnd_vias(
        self,
        polygons_by_layer: Dict[int, List[Polygon]]
    ) -> List[DeviceCandidate]:
        """
        识别地孔

        特征：
        - 穿透GND、ME1、ME2、VA1层
        - 小的圆形或方形
        """
        gnd_vias = []

        gnd_polys = polygons_by_layer.get(self.mapping.gnd, [])
        for poly in gnd_polys:
            if self._is_via_shape(poly):
                gnd_vias.append(DeviceCandidate(
                    device_type="GND",
                    polygons=[poly],
                    labels=[],
                    value=None,
                    unit=None
                ))

        return gnd_vias

    # ============ 形态判断方法 ============

    def _is_spiral_pattern(self, polygons: List[Polygon]) -> bool:
        """判断是否为螺旋形态（简化实现）"""
        # 实际需要实现螺旋检测算法
        # 这里简化判断：多个矩形且有一定层次关系
        return len(polygons) >= 2

    def _is_overlapping(self, poly1: Polygon, poly2: Polygon) -> bool:
        """判断两个矩形是否重叠"""
        bbox1 = self._get_bbox(poly1)
        bbox2 = self._get_bbox(poly2)

        return not (
            bbox1['max_x'] < bbox2['min_x'] or
            bbox1['min_x'] > bbox2['max_x'] or
            bbox1['max_y'] < bbox2['min_y'] or
            bbox1['min_y'] > bbox2['max_y']
        )

    def _is_rectangular_shape(self, poly: Polygon) -> bool:
        """判断是否为矩形形状"""
        points = poly.tolist()
        if len(points) != 4:
            return False

        # 检查是否为矩形（简化：4个点）
        # 实际需要检查直角和平行边
        return True

    def _is_large_rectangle(self, poly: Polygon) -> bool:
        """判断是否为大矩形（焊盘特征）"""
        bbox = self._get_bbox(poly)
        width = bbox['max_x'] - bbox['min_x']
        height = bbox['max_y'] - bbox['min_y']

        # 假设焊盘大于10x10微米
        return width > 10 and height > 10

    def _is_via_shape(self, poly: Polygon) -> bool:
        """判断是否为通孔形状"""
        bbox = self._get_bbox(poly)
        width = bbox['max_x'] - bbox['min_x']
        height = bbox['max_y'] - bbox['min_y']

        # 通孔相对较小
        return width < 5 and height < 5

    # ============ 器件值计算方法 ============

    def _calculate_inductance(self, polygons: List[Polygon]) -> DeviceValue:
        """
        计算电感值

        简化公式：L ≈ μ₀n²A/l
        实际需要使用复杂的三维电磁场计算
        """
        # 简化实现：基于矩形面积估算
        total_area = 0
        for poly in polygons:
            bbox = self._get_bbox(poly)
            area = (bbox['max_x'] - bbox['min_x']) * (bbox['max_y'] - bbox['min_y'])
            total_area += area

        # 简化公式（仅示例）
        value = total_area * 0.1  # nH

        return DeviceValue(
            value=value,
            unit="nH",
            formula=f"L ≈ {value:.2f} nH"
        )

    def _calculate_capacitance(self, polygons: List[Polygon]) -> DeviceValue:
        """
        计算电容值

        公式：C = ε₀εr A/d
        """
        if len(polygons) < 2:
            return DeviceValue(value=0, unit="pF")

        # 计算重叠面积
        poly1, poly2 = polygons[0], polygons[1]
        bbox1 = self._get_bbox(poly1)
        bbox2 = self._get_bbox(poly2)

        overlap_width = min(bbox1['max_x'], bbox2['max_x']) - max(bbox1['min_x'], bbox2['min_x'])
        overlap_height = min(bbox1['max_y'], bbox2['max_y']) - max(bbox1['min_y'], bbox2['min_y'])

        overlap_area = overlap_width * overlap_height

        # 简化公式（假设d=1μm, εr≈1）
        epsilon_0 = 8.854e-12  # F/m
        d = 1e-6  # 板间距1μm
        value = epsilon_0 * (overlap_area * 1e-12) / d  # 转换为F，再转为pF
        value *= 1e12  # F → pF

        return DeviceValue(
            value=value,
            unit="pF",
            formula=f"C = {value:.2f} pF"
        )

    def _calculate_resistance(self, poly: Polygon) -> DeviceValue:
        """
        计算电阻值

        公式：R = ρ L / (W t)
        或者用方块电阻：R = Rs * (L/W)
        """
        bbox = self._get_bbox(poly)
        length = max(bbox['max_x'] - bbox['min_x'], bbox['max_y'] - bbox['min_y'])
        width = min(bbox['max_x'] - bbox['min_x'], bbox['max_y'] - bbox['min_y'])

        # 使用方块电阻计算（默认Rs=100 Ω/square）
        rs = 100  # Ω/square
        value = rs * (length / width)

        return DeviceValue(
            value=value,
            unit="Ω",
            formula=f"R = {value:.2f} Ω (Rs={rs} Ω/□, L/W={length/width:.2f})"
        )

    def _get_bbox(self, poly: Polygon) -> Dict[str, float]:
        """获取多边形边界框"""
        points = poly.tolist()
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]

        return {
            'min_x': min(x_coords),
            'max_x': max(x_coords),
            'min_y': min(y_coords),
            'max_y': max(y_coords)
        }
