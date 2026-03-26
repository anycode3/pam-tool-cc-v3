from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas.device import (
    DeviceUpdateRequest,
    DeviceUpdateResponse,
    VersionSaveRequest,
    VersionListResponse,
    VersionRollbackRequest
)
from app.schemas.diff import VersionDiffRequest, VersionDiffResponse
from app.services.version_manager import version_manager
from app.services.device_manager import device_manager
from app.services.diff_service import diff_service

router = APIRouter(prefix="/device", tags=["Device"])


@router.post("/update", response_model=DeviceUpdateResponse)
async def update_device(request: DeviceUpdateRequest):
    """
    更新单个器件参数

    Args:
        request: 器件更新请求

    Returns:
        DeviceUpdateResponse: 更新结果
    """
    try:
        success = device_manager.update_device(
            request.file_name,
            request.device_name,
            request.parameters
        )

        if success:
            return DeviceUpdateResponse(
                success=True,
                message=f"器件 {request.device_name} 已更新"
            )
        else:
            raise HTTPException(status_code=500, detail="更新器件失败")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新器件失败: {str(e)}")


@router.get("/list/{file_name}")
async def list_devices(file_name: str):
    """
    获取文件的所有器件

    Args:
        file_name: GDS文件名

    Returns:
        List[dict]: 器件列表
    """
    try:
        devices = device_manager.load_current_devices(file_name)
        return devices

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取器件列表失败: {str(e)}")


@router.post("/version/save", response_model=VersionListResponse)
async def save_version(request: VersionSaveRequest):
    """
    保存当前版本

    Args:
        request: 版本保存请求

    Returns:
        VersionListResponse: 版本列表
    """
    try:
        # 获取当前器件列表
        devices = device_manager.load_current_devices(request.file_name)

        # 保存版本
        version_info = version_manager.save_version(
            request.file_name,
            devices,
            request.description,
            request.force
        )

        if version_info:
            # 返回更新后的版本列表
            versions = version_manager.get_versions(request.file_name)
            return VersionListResponse(
                file_name=request.file_name,
                versions=versions
            )
        else:
            raise HTTPException(status_code=500, detail="保存版本失败")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存版本失败: {str(e)}")


@router.get("/version/list/{file_name}", response_model=VersionListResponse)
async def list_versions(file_name: str):
    """
    获取文件的所有版本

    Args:
        file_name: GDS文件名

    Returns:
        VersionListResponse: 版本列表
    """
    try:
        versions = version_manager.get_versions(file_name)
        return VersionListResponse(
            file_name=file_name,
            versions=versions
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本列表失败: {str(e)}")


@router.post("/version/rollback")
async def rollback_version(request: VersionRollbackRequest):
    """
    回滚到指定版本

    Args:
        request: 版本回滚请求

    Returns:
        dict: 回滚结果
    """
    try:
        devices = version_manager.rollback(request.file_name, request.version_id)

        if devices is None:
            raise HTTPException(status_code=404, detail="版本不存在")

        # 保存回滚后的器件列表
        device_manager.save_devices(request.file_name, devices)

        return {
            "success": True,
            "message": f"已回滚到版本 {request.version_id}",
            "device_count": len(devices)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")


@router.delete("/version/{file_name}/{version_id}")
async def delete_version(file_name: str, version_id: str):
    """
    删除指定版本

    Args:
        file_name: GDS文件名
        version_id: 版本ID

    Returns:
        dict: 删除结果
    """
    try:
        success = version_manager.delete_version(file_name, version_id)

        if success:
            return {
                "success": True,
                "message": f"版本 {version_id} 已删除"
            }
        else:
            raise HTTPException(status_code=404, detail="版本不存在")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除版本失败: {str(e)}")


@router.post("/version/diff", response_model=VersionDiffResponse)
async def compare_versions(request: VersionDiffRequest):
    """
    对比两个版本之间的差异

    Args:
        request: 版本对比请求

    Returns:
        VersionDiffResponse: 版本对比结果
    """
    try:
        diff_result = diff_service.compare_versions(
            request.file_name,
            request.version1_id,
            request.version2_id
        )

        if diff_result is None:
            raise HTTPException(status_code=404, detail="版本不存在或对比失败")

        return diff_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"版本对比失败: {str(e)}")

