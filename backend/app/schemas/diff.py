from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class DeviceChange(BaseModel):
    """单个器件的变化"""
    device_name: str
    device_type: str
    change_type: str  # "added", "removed", "modified"
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    diff_fields: Optional[List[str]] = None  # 发生变化的字段列表


class VersionDiffResponse(BaseModel):
    """版本对比响应"""
    file_name: str
    version1_id: str
    version1_description: Optional[str] = None
    version1_timestamp: Optional[str] = None
    version2_id: str
    version2_description: Optional[str] = None
    version2_timestamp: Optional[str] = None
    changes: List[DeviceChange]
    summary: Dict[str, int]  # {"added": 0, "removed": 0, "modified": 0}


class VersionDiffRequest(BaseModel):
    """版本对比请求"""
    file_name: str
    version1_id: str
    version2_id: str
