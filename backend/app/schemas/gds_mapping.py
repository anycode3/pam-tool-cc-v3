from pydantic import BaseModel
from typing import Dict, Optional


class LayerMapping(BaseModel):
    """图层映射配置"""
    me1: int  # 金属层1
    me2: int  # 金属层2
    tfr: int  # 电阻层
    gnd: int  # 地层
    va1: int  # 通孔层1


class GDSLayerMappingConfig(BaseModel):
    """GDS文件图层映射配置"""
    file_name: str
    layer_mapping: LayerMapping
    # 器件值计算参数（可选）
    resistor_sheet_resistance: Optional[float] = None  # 电阻方块电阻 (Ω/square)
    capacitor_plate_separation: Optional[float] = None  # 电容板间距 (μm)


class DeviceValue(BaseModel):
    """器件值"""
    value: float
    unit: str
    formula: Optional[str] = None  # 计算公式说明
