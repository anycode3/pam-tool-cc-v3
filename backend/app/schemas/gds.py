from typing import List, Optional
from pydantic import BaseModel


class DeviceInfo(BaseModel):
    """设备信息模型"""
    name: str
    device_type: str
    x: float
    y: float
    width: float
    height: float
    layer: int
    parameters: dict


class GDSParseRequest(BaseModel):
    """GDS解析请求模型"""
    file_name: str


class GDSParseResponse(BaseModel):
    """GDS解析响应模型"""
    file_name: str
    cell_count: int
    devices: List[DeviceInfo]
    success: bool
    message: Optional[str] = None


class PolygonData(BaseModel):
    """多边形数据模型"""
    points: List[List[float]]  # 坐标点列表 [[x1, y1], [x2, y2], ...]
    layer: int
    datatype: int


class GDSLayerInfo(BaseModel):
    """图层信息模型"""
    layer_number: int
    layer_name: str
    datatype: int
    polygon_count: int
    polygons: List[PolygonData] = []  # 该图层的所有多边形
