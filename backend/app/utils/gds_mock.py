"""
Mock gdstk module for development/testing purposes
Used when gdstk cannot be installed (e.g., Python 3.6)
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class GdsLibrary:
    """Mock GDS library"""
    cells: List = field(default_factory=list)

    @staticmethod
    def read(filename):
        """Mock read method"""
        # 创建一个模拟的cell
        mock_cell = GdsCell(
            name="test_cell",
            polygons=[
                Polygon(
                    layer=1,
                    datatype=0,
                    points=[[0, 0], [10, 0], [10, 5], [0, 5]]
                ),
                Polygon(
                    layer=2,
                    datatype=1,
                    points=[[5, 5], [15, 5], [15, 10], [5, 10]]
                )
            ],
            labels=[
                Label(
                    text="RES_1k",
                    origin=[2, 2],
                    layer=1,
                    datatype=0
                ),
                Label(
                    text="CAP_100p",
                    origin=[7, 7],
                    layer=2,
                    datatype=1
                )
            ]
        )
        return GdsLibrary(cells=[mock_cell])


@dataclass
class GdsCell:
    """Mock cell"""
    name: str = ""
    polygons: List = field(default_factory=list)
    labels: List = field(default_factory=list)


@dataclass
class Polygon:
    """Mock polygon"""
    layer: int
    datatype: int
    points: List

    def tolist(self):
        """Convert points to list"""
        return self.points


@dataclass
class Label:
    """Mock label"""
    text: str
    origin: List
    layer: int
    datatype: int
    rotation: float = 0.0
    magnification: float = 1.0


# 模拟gdstk模块
class GDSTKModule:
    """模拟gdstk模块"""
    Library = GdsLibrary
    GdsCell = GdsCell
    Polygon = Polygon
    Label = Label


# 创建实例作为模块
gdstk = GDSTKModule()
