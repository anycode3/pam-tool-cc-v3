"""
器件识别器 - 根据形态和图层规则识别器件
集成了三种电感识别方法
"""
import logging
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.schemas.gds_mapping import LayerMapping, GDSLayerMappingConfig, DeviceValue, InductorRecognitionMethod
from app.services.inductor_recognizers import InductorRecognizer, InductorCandidate

from gdstk import Polygon, Label

logger = logging.getLogger(__name__)


@dataclass
class DeviceCandidate:
    """器件候选"""
    device_type: str  # L, C, R, PAD, GND
    polygons: List[Polygon]  # 组成器件的多边形
    labels: List[Label]  # 相关标签
    value: Optional[float] = None  # 器件值
    unit: Optional[str] = None  # 单位
    parameters: Optional[Dict] = None  # 额外参数


class DeviceRecognizer:
    """器件识别器 - 根据形态和图层规则识别器件"""

    def __init__(self, layer_mapping: LayerMapping, inductor_method: InductorRecognitionMethod = InductorRecognitionMethod.HEURISTIC):
        self.mapping = layer_mapping
        self.inductor_method = inductor_method
        # 初始化电感识别器
        self.inductor_recognizer = InductorRecognizer(layer_mapping)

    def recognize_devices(
        self,
        polygons: List[Polygon],
        labels: List[Label],
        inductor_method: Optional[InductorRecognitionMethod] = None
    ) -> List[DeviceCandidate]:
        """
        识别器件

        Args:
            polygons: 所有多边形
            labels: 所有标签
            inductor_method: 电感识别方法（可选，优先级高于初始化时的设置）

        Returns:
            List[DeviceCandidate]: 识别到的器件列表
        """
        # 使用指定的方法或默认方法
        method = inductor_method if inductor_method else self.inductor_method

        devices = []

        # 按图层分组
        polygons_by_layer = self._group_polygons_by_layer(polygons)

        # 识别螺旋电感 (L) - 包含ME1、ME2层，螺旋形态
        logger.info(f"使用方法 {method.value} 识别电感")
        inductors = self.inductor_recognizer.recognize(polygons, labels, method)

        # 转换InductorCandidate为DeviceCandidate
        for ind in inductors:
            if ind.polygons:
                devices.append(DeviceCandidate(
                    device_type="L",
                    polygons=ind.polygons,
                    labels=ind.labels or [],
                    value=ind.value,
                    unit=ind.unit,
                    parameters={
                        "turns": ind.turns,
                        "formula": ind.parameters if isinstance(ind.parameters, str) else str(ind.parameters)
                    }
                ))

        # 识别平板电容 (C) - 包含ME1、ME2层，平行板形态
        capacitors = self._recognize_capacitors(polygons_by_layer)
        devices.extend(capacitors)

        # 识别薄片电阻 (R) - 只有TFR层
        resistors = self._recognize_resistors(polygons_by_layer)
        devices.extend(resistors)

        # 识别焊盘 (PAD) - 穿透ME1、ME2、VA1
        pads = self._recognize_pads(polygons_by_layer)
        devices.extend(pads)

        # 识别地孔 (GND) - 穿透GND、ME1、ME2、VA1
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

        if not me1_polys or not me2_polys:
            return capacitors

        # 收集已匹配的ME2多边形索引，避免重复
        matched_me2_indices = set()

        # 寻找ME1和ME2中重叠的矩形对
        for i, poly1 in enumerate(me1_polys):
            best_match_idx = None
            max_overlap = 0

            for j, poly2 in enumerate(me2_polys):
                if j in matched_me2_indices:
                    continue  # 已匹配

                overlap_area = self._calculate_overlap_area(poly1, poly2)

                if overlap_area > max_overlap:
                    max_overlap = overlap_area
                    best_match_idx = j

            # 如果找到最佳匹配且重叠面积有意义
            if best_match_idx is not None and max_overlap > 0:
                poly2 = me2_polys[best_match_idx]
                matched_me2_indices.add(best_match_idx)

                # 计算边界框重叠率验证
                bbox1 = self._get_bbox(poly1)
                bbox2 = self._get_bbox(poly2)
                overlap_ratio = self._bbox_overlap_ratio(bbox1, bbox2)

                if overlap_ratio > 0.5:  # 重叠率大于50%
                    value = self._calculate_capacitance([poly1, poly2])
                    capacitors.append(DeviceCandidate(
                        device_type="C",
                        polygons=[poly1, poly2],
                        labels=[],
                        value=value.value,
                        unit=value.unit,
                        parameters={"formula": value.formula}
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
                    unit=value.unit,
                    parameters={"formula": value.formula}
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

        # 收集所有大矩形
        large_rectangles = []

        for layer_num in [self.mapping.me1, self.mapping.me2, self.mapping.va1]:
            polys = polygons_by_layer.get(layer_num, [])
            for poly in polys:
                if self._is_large_rectangle(poly):
                    # 检查是否已经在其他层有类似焊盘（空间邻近）
                    is_new_pad = True
                    for existing_pad in large_rectangles:
                        if self._are_spatially_proximate(poly, existing_pad, threshold=5.0):
                            is_new_pad = False
                            break

                    if is_new_pad:
                        large_rectangles.append(poly)

        # 转换为焊盘候选
        for poly in large_rectangles:
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

        # 优先在GND层查找
        gnd_polys = polygons_by_layer.get(self.mapping.gnd, [])

        # 收集已检测位置的集合，避免重复
        detected_positions = set()

        for poly in gnd_polys:
            if self._is_via_shape(poly):
                # 记录位置（使用边界框中心作为位置标识）
                bbox = self._get_bbox(poly)
                center_key = (
                    int((bbox['min_x'] + bbox['max_x']) / 2),
                    int((bbox['min_y'] + bbox['max_y']) / 2)
                )

                if center_key in detected_positions:
                    continue

                detected_positions.add(center_key)

                gnd_vias.append(DeviceCandidate(
                    device_type="GND",
                    polygons=[poly],
                    labels=[],
                    value=None,
                    unit=None
                ))

        return gnd_vias

    # ============ 形态判断方法 ============

    def _is_rectangular_shape(self, poly: Polygon) -> bool:
        """
        判断是否为矩形形状

        检查：
        1. 4个顶点
        2. 对角线相等
        3. 邻边垂直
        """
        points = poly.points.tolist()

        if len(points) != 4:
            return False

        # 计算边向量
        def vector(p1, p2):
            return (p2[0] - p1[0], p2[1] - p1[1])

        # 检查四边形
        v0 = vector(points[0], points[1])
        v1 = vector(points[1], points[2])
        v2 = vector(points[2], points[3])
        v3 = vector(points[3], points[0])

        # 检查对边是否平行（叉积为0）
        def cross_product(a, b):
            return a[0] * b[1] - a[1] * b[0]

        # 对边平行：v0与v2平行，v1与v3平行
        parallel1 = abs(cross_product(v0, v2)) < 1e-6
        parallel2 = abs(cross_product(v1, v3)) < 1e-6

        # 检查邻边垂直（点积为0）
        def dot_product(a, b):
            return a[0] * b[0] + a[1] * b[1]

        # 邻边垂直：v0与v1垂直，v1与v2垂直
        perpendicular1 = abs(dot_product(v0, v1)) < 1e-6
        perpendicular2 = abs(dot_product(v1, v2)) < 1e-6

        return parallel1 and parallel2 and perpendicular1 and perpendicular2

    def _is_large_rectangle(self, poly: Polygon) -> bool:
        """
        判断是否为大矩形（焊盘特征）

        焊盘通常：
        - 面积较大
        - 形状规则
        """
        bbox = self._get_bbox(poly)
        width = bbox['max_x'] - bbox['min_x']
        height = bbox['max_y'] - bbox['min_y']
        area = width * height

        # 焊盘特征参数
        min_area = 100.0  # 最小面积 100μm²
        min_dimension = 10.0  # 最小尺寸 10μm

        # 检查是否为矩形
        if not self._is_rectangular_shape(poly):
            return False

        return area >= min_area and width >= min_dimension and height >= min_dimension

    def _is_via_shape(self, poly: Polygon) -> bool:
        """
        判断是否为通孔形状

        通孔特征：
        - 尺寸较小
        - 形状规整（正方形或圆形）
        """
        bbox = self._get_bbox(poly)
        width = bbox['max_x'] - bbox['min_x']
        height = bbox['max_y'] - bbox['min_y']
        area = width * height

        # 通孔特征参数
        max_area = 25.0  # 最大面积 25μm² (5x5)
        max_dimension = 5.0  # 最大尺寸 5μm

        if area > max_area or width > max_dimension or height > max_dimension:
            return False

        # 检查形状规整度：正方形或接近正方形
        aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else float('inf')

        return aspect_ratio <= 1.5  # 长宽比不超过1.5

    def _are_spatially_proximate(
        self,
        poly1: Polygon,
        poly2: Polygon,
        threshold: float = 5.0
    ) -> bool:
        """
        判断两个多边形在空间上是否邻近

        比较边界框中心的欧氏距离
        """
        bbox1 = self._get_bbox(poly1)
        bbox2 = self._get_bbox(poly2)

        center1_x = (bbox1['min_x'] + bbox1['max_x']) / 2
        center1_y = (bbox1['min_y'] + bbox1['max_y']) / 2

        center2_x = (bbox2['min_x'] + bbox2['max_x']) / 2
        center2_y = (bbox2['min_y'] + bbox2['max_y']) / 2

        distance = math.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)

        return distance < threshold

    # ============ 器件值计算方法 ============

    def _calculate_capacitance(self, polygons: List[Polygon]) -> DeviceValue:
        """
        计算电容值

        公式：C = ε₀εr A/d
        """
        if len(polygons) < 2:
            return DeviceValue(value=0.0, unit="pF", formula="无多边形数据")

        # 计算重叠面积
        poly1, poly2 = polygons[0], polygons[1]
        bbox1 = self._get_bbox(poly1)
        bbox2 = self._get_bbox(poly2)

        overlap_width = min(bbox1['max_x'], bbox2['max_x']) - max(bbox1['min_x'], bbox2['min_x'])
        overlap_height = min(bbox1['max_y'], bbox2['max_y']) - max(bbox1['min_y'], bbox2['min_y'])

        overlap_area = overlap_width * overlap_height

        if overlap_area <= 0:
            return DeviceValue(value=0.0, unit="pF", formula="无重叠区域")

        # 简化公式（假设d=1μm, εr≈1）
        epsilon_0 = 8.854e-12  # F/m 真空介电常数
        epsilon_r = 4.0  # 相对介电常数（假设氧化硅）
        d = 1e-6  # 板间距1μm

        # C = ε₀·εr·A/d
        value = epsilon_0 * epsilon_r * (overlap_area * 1e-12) / d  # 转换为F
        value_pf = value * 1e12  # F → pF

        formula = (
            f"C = ε₀·εr·A/d\n"
            f"  ε₀ = {epsilon_0:.3e} F/m\n"
            f"  εr = {epsilon_r}\n"
            f"  A = {overlap_area:.2f} μm²\n"
            f"  d = {d*1e6:.1f} μm\n"
            f"  C = {value_pf:.2f} pF"
        )

        return DeviceValue(
            value=round(value_pf, 3),
            unit="pF",
            formula=formula
        )

    def _calculate_resistance(self, poly: Polygon) -> DeviceValue:
        """
        计算电阻值

        公式：R = Rs * (L/W)
        使用方块电阻计算
        """
        bbox = self._get_bbox(poly)
        width = bbox['max_x'] - bbox['min_x']
        height = bbox['max_y'] - bbox['min_y']

        # 确定长边和短边
        length = max(width, height)
        short_side = min(width, height)

        if short_side <= 0:
            return DeviceValue(value=0.0, unit="Ω", formula="宽度为零")

        # 使用方块电阻计算（默认Rs=100 Ω/square）
        rs = 100  # Ω/square，典型的薄膜电阻方块电阻

        # R = Rs * (L/W)
        value = rs * (length / short_side)

        lw_ratio = length / short_side

        formula = (
            f"R = Rs · (L/W)\n"
            f"  Rs = {rs} Ω/□ (方块电阻)\n"
            f"  L = {length:.2f} μm\n"
            f"  W = {short_side:.2f} μm\n"
            f"  L/W = {lw_ratio:.2f}\n"
            f"  R = {value:.2f} Ω"
        )

        return DeviceValue(
            value=round(value, 2),
            unit="Ω",
            formula=formula
        )

    # ============ 辅助方法 ============

    def _get_bbox(self, poly: Polygon) -> Dict[str, float]:
        """获取多边形边界框"""
        points = poly.points.tolist()
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]

        return {
            'min_x': min(x_coords),
            'max_x': max(x_coords),
            'min_y': min(y_coords),
            'max_y': max(y_coords)
        }

    def _calculate_overlap_area(
        self,
        poly1: Polygon,
        poly2: Polygon
    ) -> float:
        """计算两个多边形的重叠面积（简化为边界框重叠）"""
        bbox1 = self._get_bbox(poly1)
        bbox2 = self._get_bbox(poly2)

        overlap_width = min(bbox1['max_x'], bbox2['max_x']) - max(bbox1['min_x'], bbox2['min_x'])
        overlap_height = min(bbox1['max_y'], bbox2['max_y']) - max(bbox1['min_y'], bbox2['min_y'])

        if overlap_width <= 0 or overlap_height <= 0:
            return 0.0

        return overlap_width * overlap_height

    def _bbox_overlap_ratio(
        self,
        bbox1: Dict[str, float],
        bbox2: Dict[str, float]
    ) -> float:
        """计算两个边界框的重叠率"""
        overlap_width = min(bbox1['max_x'], bbox2['max_x']) - max(bbox1['min_x'], bbox2['min_x'])
        overlap_height = min(bbox1['max_y'], bbox2['max_y']) - max(bbox1['min_y'], bbox2['min_y'])

        if overlap_width <= 0 or overlap_height <= 0:
            return 0.0

        overlap_area = overlap_width * overlap_height

        area1 = (bbox1['max_x'] - bbox1['min_x']) * (bbox1['max_y'] - bbox1['min_y'])
        area2 = (bbox2['max_x'] - bbox2['min_x']) * (bbox2['max_y'] - bbox2['min_y'])

        # 返回相对于较小面积的重叠率
        return overlap_area / min(area1, area2)
