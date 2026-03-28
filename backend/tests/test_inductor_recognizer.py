"""
电感识别器完整测试用例
"""
import pytest
import numpy as np
import gdstk

from app.services.inductor_recognizers import InductorRecognizer
from app.schemas.gds_mapping import LayerMapping, InductorRecognitionMethod


class TestGDSGenerator:
    """GDS测试文件生成器"""

    @staticmethod
    def create_spiral_inductor_gds(
        tmp_path,
        me1_layer=10,
        me2_layer=11,
        turns=3,
        center=(0, 0),
        wire_width=2.0,
        spacing=1.0
    ):
        """创建螺旋电感GDS文件"""
        lib = gdstk.Library("test_spiral", 1.0)
        cell = lib.new_cell("TOP")

        cx, cy = center

        for turn in range(turns):
            outer_radius = (turn + 1) * (wire_width + spacing) * 2
            inner_radius = turn * (wire_width + spacing) * 2 + wire_width

            outer_poly = gdstk.Polygon(
                points=np.array([
                    [cx - outer_radius/2, cy - outer_radius/2],
                    [cx + outer_radius/2, cy - outer_radius/2],
                    [cx + outer_radius/2, cy + outer_radius/2],
                    [cx - outer_radius/2, cy + outer_radius/2]
                ]),
                layer=me1_layer
            )

            inner_poly = gdstk.Polygon(
                points=np.array([
                    [cx - inner_radius/2, cy - inner_radius/2],
                    [cx + inner_radius/2, cy - inner_radius/2],
                    [cx + inner_radius/2, cy + inner_radius/2],
                    [cx - inner_radius/2, cy + inner_radius/2]
                ]),
                layer=me2_layer
            )

            cell.add(outer_poly)
            cell.add(inner_poly)

        file_path = tmp_path / "test_spiral.gds"
        lib.write_gds(str(file_path))
        return file_path


class TestInductorRecognition:
    """电感识别测试"""

    def test_geometric_method_recognizes_spiral(self, tmp_path):
        """测试几何模板匹配法识别螺旋电感"""
        gds_file = TestGDSGenerator.create_spiral_inductor_gds(tmp_path, turns=3)

        library = gdstk.read_gds(str(gds_file))

        polygons = []
        labels = []
        for cell in library.cells:
            polygons.extend(cell.polygons)
            labels.extend(cell.labels)

        layer_mapping = LayerMapping(me1=10, me2=11, tfr=20, gnd=0, va1=50)
        recognizer = InductorRecognizer(layer_mapping)

        inductors = recognizer.recognize(
            polygons,
            labels,
            method=InductorRecognitionMethod.GEOMETRIC
        )

        assert len(inductors) > 0, "应该识别到至少一个电感"
        assert inductors[0].device_type == "L", "器件类型应为电感"
        assert inductors[0].value is not None, "电感应有值"
        assert inductors[0].unit == "nH", "电感单位应为nH"
        assert inductors[0].turns >= 1, "匝数应至少为1"

    def test_topological_method_recognizes_spiral(self, tmp_path):
        """测试拓扑连接分析法识别螺旋电感"""
        gds_file = TestGDSGenerator.create_spiral_inductor_gds(tmp_path, turns=2)

        library = gdstk.read_gds(str(gds_file))

        polygons = []
        labels = []
        for cell in library.cells:
            polygons.extend(cell.polygons)
            labels.extend(cell.labels)

        layer_mapping = LayerMapping(me1=10, me2=11, tfr=20, gnd=0, va1=50)
        recognizer = InductorRecognizer(layer_mapping)

        inductors = recognizer.recognize(
            polygons,
            labels,
            method=InductorRecognitionMethod.TOPOLOGICAL
        )

        assert len(inductors) > 0, "应该识别到至少一个电感"
        assert inductors[0].device_type == "L", "器件类型应为电感"

    def test_heuristic_method_recognizes_spiral(self, tmp_path):
        """测试启发式规则法识别螺旋电感"""
        gds_file = TestGDSGenerator.create_spiral_inductor_gds(tmp_path, turns=3)

        library = gdstk.read_gds(str(gds_file))

        polygons = []
        labels = []
        for cell in library.cells:
            polygons.extend(cell.polygons)
            labels.extend(cell.labels)

        layer_mapping = LayerMapping(me1=10, me2=11, tfr=20, gnd=0, va1=50)
        recognizer = InductorRecognizer(layer_mapping)

        inductors = recognizer.recognize(
            polygons,
            labels,
            method=InductorRecognitionMethod.HEURISTIC
        )

        assert len(inductors) > 0, "应该识别到至少一个电感"
        assert inductors[0].device_type == "L", "器件类型应为电感"
        assert inductors[0].value is not None, "电感应有值"
        assert inductors[0].unit == "nH", "电感单位应为nH"

    def test_greenhouse_formula_calculation(self, tmp_path):
        """测试Greenhouse公式电感计算"""
        gds_file = TestGDSGenerator.create_spiral_inductor_gds(
            tmp_path, turns=3, wire_width=2.0, spacing=1.0
        )

        library = gdstk.read_gds(str(gds_file))

        polygons = []
        for cell in library.cells:
            polygons.extend(cell.polygons)

        layer_mapping = LayerMapping(me1=10, me2=11, tfr=20, gnd=0, va1=50)
        recognizer = InductorRecognizer(layer_mapping)

        inductors = recognizer.recognize(
            polygons,
            [],
            method=InductorRecognitionMethod.HEURISTIC
        )

        assert len(inductors) > 0, "应识别到电感"

        inductance = inductors[0].value
        assert inductance > 0, "电感应为正值"
        assert inductance < 100, "电感应小于100nH（测试电感很小）"

    def test_all_methods_recognize(self, tmp_path):
        """测试三种方法都能识别电感"""
        gds_file = TestGDSGenerator.create_spiral_inductor_gds(tmp_path, turns=2)

        library = gdstk.read_gds(str(gds_file))

        polygons = []
        labels = []
        for cell in library.cells:
            polygons.extend(cell.polygons)
            labels.extend(cell.labels)

        layer_mapping = LayerMapping(me1=10, me2=11, tfr=20, gnd=0, va1=50)

        methods = [
            InductorRecognitionMethod.GEOMETRIC,
            InductorRecognitionMethod.TOPOLOGICAL,
            InductorRecognitionMethod.HEURISTIC
        ]

        for method in methods:
            recognizer = InductorRecognizer(layer_mapping)
            inductors = recognizer.recognize(polygons, labels, method=method)

            assert len(inductors) > 0, f"方法{method.value}应识别到至少一个电感"
            assert inductors[0].device_type == "L", "器件类型应为电感"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
