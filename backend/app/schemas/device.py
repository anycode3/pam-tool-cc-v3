from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class DeviceUpdateRequest(BaseModel):
    file_name: str
    device_name: str
    parameters: Dict[str, Any]


class DeviceUpdateResponse(BaseModel):
    success: bool
    message: str
    device: Optional[Dict[str, Any]] = None


class VersionInfo(BaseModel):
    """版本信息"""
    version_id: str
    file_name: str
    timestamp: str
    description: Optional[str] = None
    device_count: int
    total_devices: Optional[Dict[str, Dict[str, Any]]] = None  # 存储所有器件状态


class VersionSaveRequest(BaseModel):
    """版本保存请求"""
    file_name: str
    description: Optional[str] = None
    force: bool = False  # 强制保存（覆盖同名版本）


class VersionListResponse(BaseModel):
    """版本列表响应"""
    file_name: str
    versions: list[VersionInfo]


class VersionRollbackRequest(BaseModel):
    """版本回滚请求"""
    file_name: str
    version_id: str
