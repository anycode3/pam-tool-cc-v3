"""
电感识别器实现 - 三种完整算法
"""
import logging
import math
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

import numpy as np
from gdstk import Polygon, Label

from app.schemas.gds_mapping import InductorRecognitionMethod, LayerMapping, DeviceValue

logger = logging.getLogger(__name__)


@dataclass
class SpiralSegment:
    """螺旋线段"""
    polygon: Polygon
    layer: int
    bbox: Dict[str, float]
    center: Tuple[float, float]
    width: float
    height: float
    area: float


@dataclass
class InductorCandidate:
    """电感候选"""
    device_type: str = "L"
    polygons: List[Polygon] = None  # 组成器件的多边形
    labels: List[Label] = None  # 相关标签
    segments: List[SpiralSegment] = None  # 螺旋线段
    turns: int = 0  # 匝数
    value: Optional[float] = None  # 器件值
    unit: Optional[str] = None  # 单位
    parameters: Dict = None  # 几何参数


class InductorRecognizer:
    """电感识别器基类"""

    def __init__(self, layer_mapping: LayerMapping):
        self.mapping = layer_mapping
        self.mu0 = 4 * math.pi * 1e-7  # 真空磁导率 H/m

    def recognize(
        self,
        polygons: List[Polygon],
        labels: List[Label],
        method: InductorRecognitionMethod = InductorRecognitionMethod.HEURISTIC
    ) -> List[InductorCandidate]:
        """
        识别电感

        Args:
            polygons: 所有多边形
            labels: 所有标签
            method: 识别方法

        Returns:
            List[InductorCandidate]: 识别到的电感列表
        """
        if method == InductorRecognitionMethod.GEOMETRIC:
            return self._recognize_geometric(polygons, labels)
        elif method == InductorRecognitionMethod.TOPOLOGICAL:
            return self._recognize_topological(polygons, labels)
        else:  # HEURISTIC
            return self._recognize_heuristic(polygons, labels)

    # ==================== 方法1: 几何模板匹配法 ====================

    def _recognize_geometric(
        self,
        polygons: List[Polygon],
        labels: List[Label]
    ) -> List[InductorCandidate]:
        """
        几何模板匹配法

        策略：
        1. 空间分块索引多边形
        2. 质心聚类检测同心结构
        3. 边界框嵌套验证
        4. 跨层关联检测
        """
        logger.info("使用几何模板匹配法识别电感")

        # 按层分组
        polygons_by_layer = self._group_polygons_by_layer(polygons)

        # 只处理ME1和ME2层
        me1_segments = [self._to_segment(poly) for poly in polygons_by_layer.get(self.mapping.me1, [])]
        me2_segments = [self._to_segment(poly) for poly in polygons_by_layer.get(self.mapping.me2, [])]

        # 空间索引构建
        me1_spatial = self._build_spatial_index(me1_segments)
        me2_spatial = self._build_spatial_index(me2_segments)

        candidates = []

        # 检测同心结构
        for seg1 in me1_segments:
            # 查找空间邻近的ME2段
            nearby_segs = self._query_spatial_index(me2_spatial, seg1.center, radius=seg1.width * 2)

            # 质心聚类
            cluster = self._cluster_segments([seg1] + nearby_segs)

            # 边界框嵌套验证
            if self._is_nested_bounding_boxes(cluster):
                # 检测跨层连接
                paired_segments = self._find_cross_layer_pairs(cluster, me1_segments, me2_segments)

                if len(paired_segments) >= 2:  # 至少1圈
                    # 计算电感值
                    inductor = self._create_inductor(
                        paired_segments,
                        method="geometric"
                    )
                    candidates.append(inductor)

        return candidates

    def _build_spatial_index(
        self,
        segments: List[SpiralSegment]
    ) -> Dict[Tuple[int, int], List[SpiralSegment]]:
        """
        构建空间索引（grid-based）

        网格大小取平均多边形尺寸的10倍
        """
        if not segments:
            return {}

        avg_width = sum(s.width for s in segments) / len(segments)
        grid_size = max(avg_width * 10, 1.0)  # 至少1μm

        spatial_index: Dict[Tuple[int, int], List[SpiralSegment]] = {}

        for seg in segments:
            grid_x = int(seg.center[0] // grid_size)
            grid_y = int(seg.center[1] // grid_size)

            if (grid_x, grid_y) not in spatial_index:
                spatial_index[(grid_x, grid_y)] = []

            spatial_index[(grid_x, grid_y)].append(seg)

        return spatial_index

    def _query_spatial_index(
        self,
        spatial_index: Dict[Tuple[int, int], List[SpiralSegment]],
        center: Tuple[float, float],
        radius: float
    ) -> List[SpiralSegment]:
        """查询空间索引中的邻近段"""
        grid_size = max(radius, 1.0)

        center_x = int(center[0] // grid_size)
        center_y = int(center[1] // grid_size)

        grid_radius = math.ceil(radius / grid_size)

        nearby = []

        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                key = (center_x + dx, center_y + dy)
                if key in spatial_index:
                    nearby.extend(spatial_index[key])

        return nearby

    def _cluster_segments(
        self,
        segments: List[SpiralSegment]
    ) -> List[SpiralSegment]:
        """
        质心聚类

        将质心距离相近的段聚为一类
        """
        if len(segments) <= 1:
            return segments

        clusters: List[List[SpiralSegment]] = []

        for seg in segments:
            added = False

            # 尝试加入现有簇
            for cluster in clusters:
                cluster_center = self._compute_cluster_center(cluster)
                dist = self._euclidean_distance(seg.center, cluster_center)

                if dist < min(seg.width, seg.height):  # 距离小于段尺寸
                    cluster.append(seg)
                    added = True
                    break

            if not added:
                clusters.append([seg])

        # 返回最大的簇
        if clusters:
            return max(clusters, key=lambda c: len(c))

        return segments

    def _compute_cluster_center(
        self,
        cluster: List[SpiralSegment]
    ) -> Tuple[float, float]:
        """计算簇的质心"""
        if not cluster:
            return (0.0, 0.0)

        avg_x = sum(s.center[0] for s in cluster) / len(cluster)
        avg_y = sum(s.center[1] for s in cluster) / len(cluster)

        return (avg_x, avg_y)

    def _is_nested_bounding_boxes(
        self,
        segments: List[SpiralSegment]
    ) -> bool:
        """
        边界框嵌套检测

        检查是否存在外层包围内层的嵌套结构
        """
        if len(segments) < 2:
            return False

        # 按面积排序
        sorted_segs = sorted(segments, key=lambda s: s.area)

        # 检查每个外层是否包围内层
        for i in range(len(sorted_segs) - 1):
            inner = sorted_segs[i]
            outer = sorted_segs[i + 1]

            if not self._bbox_contains(outer.bbox, inner.bbox):
                return False

        # 检查长宽比一致性（规则螺旋特征）
        aspect_ratios = [s.width / s.height for s in segments]
        avg_ratio = sum(aspect_ratios) / len(aspect_ratios)

        max_deviation = max(abs(r - avg_ratio) / avg_ratio for r in aspect_ratios)

        return max_deviation < 0.3  # 偏差小于30%

    def _bbox_contains(
        self,
        outer: Dict[str, float],
        inner: Dict[str, float]
    ) -> bool:
        """检查外边界框是否包含内边界框"""
        return (outer['min_x'] <= inner['min_x'] and
                outer['max_x'] >= inner['max_x'] and
                outer['min_y'] <= inner['min_y'] and
                outer['max_y'] >= inner['max_y'])

    def _find_cross_layer_pairs(
        self,
        cluster: List[SpiralSegment],
        me1_segments: List[SpiralSegment],
        me2_segments: List[SpiralSegment]
    ) -> List[Tuple[SpiralSegment, SpiralSegment]]:
        """
        检测跨层连接

        寻找ME1和ME2中空间对齐的段对
        """
        pairs = []

        me1_in_cluster = [s for s in cluster if s.layer == self.mapping.me1]
        me2_in_cluster = [s for s in cluster if s.layer == self.mapping.me2]

        # 贪心匹配：找距离最近的配对
        for seg1 in me1_in_cluster:
            best_match = None
            min_dist = float('inf')

            for seg2 in me2_in_cluster:
                if seg2 in [p[1] for p in pairs]:
                    continue  # 已匹配

                dist = self._euclidean_distance(seg1.center, seg2.center)

                if dist < min_dist:
                    min_dist = dist
                    best_match = seg2

            # 检查边界框重叠率
            if best_match and min_dist < min(seg1.width, seg1.height):
                overlap_ratio = self._bbox_overlap_ratio(
                    seg1.bbox, best_match.bbox
                )

                if overlap_ratio > 0.5:  # 重叠率大于50%
                    pairs.append((seg1, best_match))

        return pairs

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

        return overlap_area / min(area1, area2)

    # ==================== 方法2: 拓扑连接分析法 ====================

    def _recognize_topological(
        self,
        polygons: List[Polygon],
        labels: List[Label]
    ) -> List[InductorCandidate]:
        """
        拓扑连接分析法

        策略：
        1. 构建网络图（节点=端点，边=线段）
        2. 深度优先搜索长路径
        3. 检测环路闭合
        4. 分析层间连接
        """
        logger.info("使用拓扑连接分析法识别电感")

        # 按层分组
        polygons_by_layer = self._group_polygons_by_layer(polygons)

        # 构建网络图
        graph = self._build_network_graph(polygons_by_layer)

        # 检测环路
        loops = self._detect_loops(graph)

        # 分析层间连接
        candidates = self._analyze_interlayer_connections(
            loops,
            polygons_by_layer
        )

        return candidates

    def _build_network_graph(
        self,
        polygons_by_layer: Dict[int, List[Polygon]]
    ) -> Dict[str, Dict]:
        """
        构建网络图

        返回:
        {
            'nodes': {(x, y, layer): node_data},
            'edges': [(node1, node2, polygon)],
            'adjacent': {node_id: [neighbor_ids]}
        }
        """
        graph = {
            'nodes': {},
            'edges': [],
            'adjacent': {}
        }

        node_id_counter = 0

        # 收集所有节点（线段端点）
        for layer, polys in polygons_by_layer.items():
            if layer not in [self.mapping.me1, self.mapping.me2]:
                continue

            for poly in polys:
                points = poly.points.tolist()

                # 创建节点
                node_ids = []
                for point in points:
                    node_key = (point[0], point[1], layer)

                    if node_key not in graph['nodes']:
                        graph['nodes'][node_key] = {
                            'id': node_id_counter,
                            'x': point[0],
                            'y': point[1],
                            'layer': layer
                        }
                        node_id_counter += 1

                    node_ids.append(graph['nodes'][node_key]['id'])

                # 创建边（连接线段端点）
                for i in range(len(node_ids)):
                    j = (i + 1) % len(node_ids)
                    graph['edges'].append((node_ids[i], node_ids[j], poly))

                # 更新邻接表
                for i in range(len(node_ids)):
                    neighbors = [node_ids[(i - 1) % len(node_ids)],
                                node_ids[(i + 1) % len(node_ids)]]

                    if node_ids[i] not in graph['adjacent']:
                        graph['adjacent'][node_ids[i]] = []

                    for neighbor in neighbors:
                        if neighbor not in graph['adjacent'][node_ids[i]]:
                            graph['adjacent'][node_ids[i]].append(neighbor)

        return graph

    def _detect_loops(
        self,
        graph: Dict
    ) -> List[List[int]]:
        """
        检测环路

        使用DFS查找闭合路径
        """
        visited: Set[int] = set()
        loops = []

        for start_node in graph['nodes']:
            if start_node[2] in visited:
                continue

            # 从每个未访问节点开始DFS
            path = [start_node]
            node_visited = {start_node}

            self._dfs_find_loops(
                graph,
                start_node,
                start_node,
                path,
                node_visited,
                loops,
                max_depth=100
            )

            visited.update(start_node[2] for start_node in graph['nodes'])

        return loops

    def _dfs_find_loops(
        self,
        graph: Dict,
        current: Tuple,
        start: Tuple,
        path: List[Tuple],
        visited: Set[Tuple],
        loops: List[List[int]],
        max_depth: int
    ):
        """DFS搜索环路"""
        if len(path) > max_depth:
            return

        current_id = graph['nodes'][current]['id']

        for neighbor_key in graph['adjacent'].get(current_id, []):
            neighbor = next(
                (k for k, v in graph['nodes'].items() if v['id'] == neighbor_key),
                None
            )

            if neighbor is None:
                continue

            # 回到起点，形成环路
            if neighbor == start and len(path) >= 4:
                # 提取环路节点
                loop_nodes = [graph['nodes'][n]['id'] for n in path]
                if loop_nodes not in loops:
                    loops.append(loop_nodes)
                return

            # 继续搜索
            if neighbor not in visited and neighbor not in path:
                self._dfs_find_loops(
                    graph,
                    neighbor,
                    start,
                    path + [neighbor],
                    visited | {neighbor},
                    loops,
                    max_depth
                )

    def _analyze_interlayer_connections(
        self,
        loops: List[List[int]],
        polygons_by_layer: Dict[int, List[Polygon]]
    ) -> List[InductorCandidate]:
        """
        分析层间连接

        将ME1和ME2层的环路关联起来
        """
        if not loops:
            return []

        candidates = []

        # 简化处理：每个环路视为一个电感
        for i, loop in enumerate(loops):
            # 估算匝数（环路长度相关）
            estimated_turns = max(1, len(loop) // 8)

            # 获取对应多边形
            me1_polys = polygons_by_layer.get(self.mapping.me1, [])
            me2_polys = polygons_by_layer.get(self.mapping.me2, [])

            combined_polys = me1_polys + me2_polys

            if combined_polys:
                # 创建电感候选
                inductor = InductorCandidate(
                    polygons=combined_polys[:min(estimated_turns * 2, len(combined_polys))],
                    labels=[],
                    segments=[],
                    turns=estimated_turns,
                    value=None,
                    unit=None,
                    parameters={}
                )

                # 计算电感值
                segments = [self._to_segment(p) for p in inductor.polygons[:estimated_turns * 2]]
                inductor.segments = segments

                if segments:
                    device_value = self._calculate_inductance_greenhouse(segments)
                    inductor.value = device_value.value
                    inductor.unit = device_value.unit
                    inductor.parameters = device_value.formula

                candidates.append(inductor)

        return candidates

    # ==================== 方法3: 启发式规则法 ====================

    def _recognize_heuristic(
        self,
        polygons: List[Polygon],
        labels: List[Label]
    ) -> List[InductorCandidate]:
        """
        启发式规则法

        策略：
        1. 同心矩形检测
        2. 螺旋完整性验证
        3. 层间耦合验证
        """
        logger.info("使用启发式规则法识别电感")

        # 按层分组
        polygons_by_layer = self._group_polygons_by_layer(polygons)

        me1_segments = [self._to_segment(poly) for poly in polygons_by_layer.get(self.mapping.me1, [])]
        me2_segments = [self._to_segment(poly) for poly in polygons_by_layer.get(self.mapping.me2, [])]

        candidates = []

        # 规则1: 同心矩形检测
        me1_concentric = self._find_concentric_rectangles(me1_segments)
        me2_concentric = self._find_concentric_rectangles(me2_segments)

        # 规则2: 螺旋完整性验证
        if len(me1_concentric) >= 2 and len(me2_concentric) >= 2:
            # 规则3: 层间耦合验证
            paired = self._verify_layer_coupling(me1_concentric, me2_concentric)

            if len(paired) >= 2:  # 至少1圈
                # 创建电感
                inductor = self._create_inductor(paired, method="heuristic")
                candidates.append(inductor)

        return candidates

    def _find_concentric_rectangles(
        self,
        segments: List[SpiralSegment]
    ) -> List[SpiralSegment]:
        """
        规则1: 同心矩形检测

        IF (多边形在同一层)
        AND (边界框质心距离 < min(width,height)/2)
        AND (外边界框包围内边界框)
        AND (长宽比差异 < 20%)
        THEN 候选同心矩形
        """
        if len(segments) < 2:
            return segments

        concentric = []

        # 按面积排序
        sorted_segs = sorted(segments, key=lambda s: s.area)

        # 从小到大检查嵌套关系
        for i in range(len(sorted_segs)):
            current = sorted_segs[i]
            is_concentric = True

            # 检查是否被外层包围
            for j in range(i + 1, len(sorted_segs)):
                outer = sorted_segs[j]

                if not self._bbox_contains(outer.bbox, current.bbox):
                    is_concentric = False
                    break

                # 检查长宽比差异
                ratio1 = current.width / current.height
                ratio2 = outer.width / outer.height
                ratio_diff = abs(ratio1 - ratio2) / max(ratio1, ratio2)

                if ratio_diff > 0.2:  # 差异超过20%
                    is_concentric = False
                    break

                # 检查质心距离
                dist = self._euclidean_distance(current.center, outer.center)
                threshold = min(current.width, current.height) / 2

                if dist > threshold:
                    is_concentric = False
                    break

            if is_concentric:
                concentric.append(current)

        return concentric

    def _verify_layer_coupling(
        self,
        me1_segments: List[SpiralSegment],
        me2_segments: List[SpiralSegment]
    ) -> List[Tuple[SpiralSegment, SpiralSegment]]:
        """
        规则3: 层间耦合验证

        IF (ME1和ME2段对齐)
        AND (存在VA1通孔连接)
        AND (ME1/ME2面积比在 0.8-1.2)
        THEN 确认为耦合螺旋
        """
        pairs = []

        # 按面积匹配
        me1_sorted = sorted(me1_segments, key=lambda s: s.area)
        me2_sorted = sorted(me2_segments, key=lambda s: s.area)

        # 找面积相似的配对
        for i in range(min(len(me1_sorted) - 1, len(me2_sorted) - 1)):
            seg1 = me1_sorted[i]
            seg2 = me2_sorted[i]

            # 检查面积比
            area_ratio = seg1.area / seg2.area

            if 0.8 <= area_ratio <= 1.2:
                # 检查质心对齐
                dist = self._euclidean_distance(seg1.center, seg2.center)
                alignment_threshold = min(seg1.width, seg2.width) / 2

                if dist < alignment_threshold:
                    # 检查边界框重叠
                    overlap_ratio = self._bbox_overlap_ratio(seg1.bbox, seg2.bbox)

                    if overlap_ratio > 0.6:  # 重叠率大于60%
                        pairs.append((seg1, seg2))

        return pairs

    # ==================== 公共方法 ====================

    def _group_polygons_by_layer(
        self,
        polygons: List[Polygon]
    ) -> Dict[int, List[Polygon]]:
        """按图层分组多边形"""
        result = {}
        for poly in polygons:
            if poly.layer not in result:
                result[poly.layer] = []
            result[poly.layer].append(poly)
        return result

    def _to_segment(self, polygon: Polygon) -> SpiralSegment:
        """将多边形转换为螺旋线段"""
        points = polygon.points.tolist()

        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        width = max_x - min_x
        height = max_y - min_y

        return SpiralSegment(
            polygon=polygon,
            layer=polygon.layer,
            bbox={'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y},
            center=((min_x + max_x) / 2, (min_y + max_y) / 2),
            width=width,
            height=height,
            area=width * height
        )

    def _euclidean_distance(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float]
    ) -> float:
        """计算欧氏距离"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def _create_inductor(
        self,
        paired_segments: List[Tuple[SpiralSegment, SpiralSegment]],
        method: str
    ) -> InductorCandidate:
        """创建电感候选"""
        # 提取所有段
        all_segments = [seg for pair in paired_segments for seg in pair]

        # 提取所有多边形
        polygons = [seg.polygon for seg in all_segments]

        # 计算匝数
        turns = len(paired_segments)

        # 计算电感值
        device_value = self._calculate_inductance_greenhouse(all_segments)

        return InductorCandidate(
            polygons=polygons,
            labels=[],
            segments=all_segments,
            turns=turns,
            value=device_value.value,
            unit=device_value.unit,
            parameters=device_value.formula
        )

    # ==================== Greenhouse电感计算公式 ====================

    def _calculate_inductance_greenhouse(
        self,
        segments: List[SpiralSegment]
    ) -> DeviceValue:
        """
        Greenhouse公式计算电感

        L = μ0 · n² · A / l · F(ρ)

        其中：
        n = 匝数
        A = 线圈平均面积
        l = 平均线圈长度
        F(ρ) = 修正函数，ρ = r_out/r_in
        """
        if not segments:
            return DeviceValue(value=0.0, unit="nH", formula="无多边形数据")

        # 计算匝数
        turns = max(1, len(segments) // 2)  # 每圈2层

        # 计算平均面积
        avg_area = sum(s.area for s in segments) / len(segments)

        # 计算平均周长
        avg_perimeter = sum(s.width * 2 + s.height * 2 for s in segments) / len(segments)

        # 计算内外径
        sorted_segments = sorted(segments, key=lambda s: s.area)
        inner_seg = sorted_segments[0]
        outer_seg = sorted_segments[-1]

        r_in = min(inner_seg.width, inner_seg.height) / 2
        r_out = max(outer_seg.width, outer_seg.height) / 2

        # 计算修正因子
        if r_out > 0:
            rho = r_out / r_in
        else:
            rho = 1.0

        # Greenhouse修正函数 F(ρ)
        # 经验公式：F(ρ) = 1 / (1 + 0.33 * ln(ρ))
        f_correction = 1.0 / (1.0 + 0.33 * math.log(rho) if rho > 1 else 1.0)

        # 计算电感
        # L (H) = μ0 * n² * A / l * F(ρ)
        l_henry = self.mu0 * (turns**2) * (avg_area * 1e-12) / (avg_perimeter * 1e-6) * f_correction

        # 转换为nH
        l_nh = l_henry * 1e9

        # 构造公式说明
        formula = (
            f"Greenhouse: L = μ₀·n²·A/l·F(ρ)\n"
            f"  n = {turns} 匝\n"
            f"  A = {avg_area:.2f} μm²\n"
            f"  l = {avg_perimeter:.2f} μm\n"
            f"  r_out/r_in = {rho:.2f}\n"
            f"  F(ρ) = {f_correction:.3f}\n"
            f"  L = {l_nh:.2f} nH"
        )

        return DeviceValue(
            value=round(l_nh, 3),
            unit="nH",
            formula=formula
        )
