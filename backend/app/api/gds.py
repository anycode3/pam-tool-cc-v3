from fastapi import APIRouter, HTTPException, UploadFile, File, status, Query
from pathlib import Path
from typing import List, Optional

from app.core.config import settings
from app.schemas.gds import GDSParseRequest, GDSParseResponse, GDSLayerInfo
from app.schemas.gds_mapping import GDSLayerMappingConfig, InductorRecognitionMethod
from app.services.gds_parser import gds_parser_service

router = APIRouter(prefix="/gds", tags=["GDS"])


class InductorMethodEnum(str, Enum):
    """电感识别方法枚举（API端点使用）"""
    GEOMETRIC = "geometric"
    TOPOLOGICAL = "topological"
    HEURISTIC = "heuristic"


def to_inductor_method(method: Optional[str]) -> Optional[InductorRecognitionMethod]:
    """将字符串转换为电感识别方法枚举"""
    if not method:
        return None
    try:
        return InductorRecognitionMethod(method)
    except ValueError:
        return InductorRecognitionMethod.HEURISTIC


# 支持的GDS文件后缀
ALLOWED_EXTENSIONS = {".gds", ".gdsii", ".gdsiii"}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_gds_file(file: UploadFile = File(...)):
    """
    上传GDS文件

    Args:
        file: 上传的GDS文件

    Returns:
        dict: 上传结果
    """
    try:
        # 验证文件扩展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 读取文件内容
        content = await file.read()

        # 验证文件大小
        max_size_bytes = settings.MAX_GDS_SIZE_MB * 1024 * 1024
        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制: {settings.MAX_GDS_SIZE_MB}MB"
            )

        # 保存文件
        storage_path = Path(settings.STORAGE_PATH)
        storage_path.mkdir(parents=True, exist_ok=True)

        file_path = storage_path / file.filename

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        return {
            "success": True,
            "message": f"文件上传成功: {file.filename}",
            "file_size": len(content),
            "file_path": str(file_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/parse", response_model=GDSParseResponse)
async def parse_gds(request: GDSParseRequest):
    """
    解析GDS文件

    Args:
        request: GDS解析请求

    Returns:
        GDSParseResponse: 解析结果
    """
    result = gds_parser_service.parse_gds_file(request.file_name)
    return result


@router.get("/layers/{file_name}", response_model=List[GDSLayerInfo])
async def get_gds_layers(file_name: str):
    """
    获取GDS文件的图层信息

    Args:
        file_name: GDS文件名

    Returns:
        List[GDSLayerInfo]: 图层信息列表
    """
    layers = gds_parser_service.get_layer_info(file_name)
    return layers


@router.get("/geometry/{file_name}")
async def get_gds_geometry(file_name: str):
    """
    获取GDS文件的几何信息

    Args:
        file_name: GDS文件名

    Returns:
        dict: 几何信息
    """
    try:
        geometry = gds_parser_service.get_geometry_info(file_name)
        return geometry
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取几何信息失败: {str(e)}")


@router.post("/layer-mapping")
async def set_layer_mapping(config: GDSLayerMappingConfig):
    """
    设置GDS文件的图层映射配置

    Args:
        config: 图层映射配置

    Returns:
        dict: 设置结果
    """
    try:
        success = gds_parser_service.set_layer_mapping(
            config.file_name,
            config.layer_mapping
        )
        if success:
            return {
                "success": True,
                "message": f"图层映射配置已保存: {config.file_name}",
                "mapping": {
                    "ME1": config.layer_mapping.me1,
                    "ME2": config.layer_mapping.me2,
                    "TFR": config.layer_mapping.tfr,
                    "GND": config.layer_mapping.gnd,
                    "VA1": config.layer_mapping.va1
                }
            }
        else:
            raise HTTPException(status_code=500, detail="保存图层映射失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置图层映射失败: {str(e)}")


@router.get("/layer-mapping/{file_name}")
async def get_layer_mapping(file_name: str):
    """
    获取GDS文件的图层映射配置

    Args:
        file_name: GDS文件名

    Returns:
        dict: 图层映射配置
    """
    mapping = gds_parser_service.get_layer_mapping(file_name)
    if mapping is None:
        raise HTTPException(status_code=404, detail=f"未找到文件 {file_name} 的图层映射配置")

    return {
        "file_name": file_name,
        "mapping": {
            "ME1": mapping.me1,
            "ME2": mapping.me2,
            "TFR": mapping.tfr,
            "GND": mapping.gnd,
            "VA1": mapping.va1
        }
    }


@router.delete("/layer-mapping/{file_name}")
async def delete_layer_mapping(file_name: str):
    """
    删除GDS文件的图层映射配置

    Args:
        file_name: GDS文件名

    Returns:
        dict: 删除结果
    """
    success = gds_parser_service.delete_layer_mapping(file_name)
    if success:
        return {
            "success": True,
            "message": f"图层映射配置已删除: {file_name}"
        }
    else:
        raise HTTPException(status_code=404, detail=f"未找到文件 {file_name} 的图层映射配置")


@router.get("/layer-mapping")
async def list_all_layer_mappings():
    """
    列出所有GDS文件的图层映射配置

    Returns:
        dict: 所有图层映射
    """
    mappings = gds_parser_service.list_all_layer_mappings()
    result = {}
    for file_name, mapping in mappings.items():
        result[file_name] = {
            "ME1": mapping.me1,
            "ME2": mapping.me2,
            "TFR": mapping.tfr,
            "GND": mapping.gnd,
            "VA1": mapping.va1
        }
    return {"mappings": result}


@router.post("/parse-with-mapping", response_model=GDSParseResponse)
async def parse_gds_with_mapping(
    request: GDSParseRequest,
    inductor_method: Optional[str] = Query(None, description="电感识别方法: geometric, topological, heuristic")
):
    """
    使用图层映射解析GDS文件（识别器件类型和计算器件值）

    Args:
        request: GDS解析请求
        inductor_method: 电感识别方法（可选）

    Returns:
        GDSParseResponse: 解析结果
    """
    try:
        # 获取图层映射
        layer_mapping = gds_parser_service.get_layer_mapping(request.file_name)
        if not layer_mapping:
            return GDSParseResponse(
                file_name=request.file_name,
                cell_count=0,
                devices=[],
                success=False,
                message="未找到图层映射配置，请先设置图层映射"
            )

        # 转换电感识别方法
        method = to_inductor_method(inductor_method)
        logger.info(f"使用电感识别方法: {method.value if method else 'default'}")

        # 使用图层映射解析
        result = gds_parser_service.parse_gds_file_with_mapping(
            request.file_name,
            layer_mapping,
            inductor_method=method
        )
        return result

    except Exception as e:
        logger.error(f"解析失败: {e}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
