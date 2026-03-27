"""
Mock gdstk module for development/testing purposes
Used when gdstk cannot be installed (e.g., Python 3.6)
"""
import sys
from dataclasses import dataclass, field
from typing import List


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


@dataclass
class GdsCell:
    """Mock cell"""
    name: str = ""
    polygons: List = field(default_factory=list)
    labels: List = field(default_factory=list)


@dataclass
class Library:
    """Mock GDS library"""
    cells: List = field(default_factory=list)

    @staticmethod
    def read(filename):
        """Mock read method"""
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
        return Library(cells=[mock_cell])


# 创建模块对象
class GDSMockModule:
    Polygon = Polygon
    Label = Label
    Library = Library

    @staticmethod
    def read(filename):
        """Mock read method - gdstk.read() convenience function"""
        return Library.read(filename)


# 注册到 sys.modules
gdstk = GDSMockModule()
sys.modules['gdstk'] = gdstk

