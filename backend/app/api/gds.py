from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path

from app.core.config import settings
from app.schemas.gds import GDSParseRequest, GDSParseResponse, GDSLayerInfo
from app.schemas.gds_mapping import GDSLayerMappingConfig
from app.services.gds_parser import gds_parser_service

router = APIRouter(prefix="/gds", tags=["GDS"])


@router.post("/upload")
async def upload_gds_file(file: UploadFile = File(...)):
    """
    上传GDS文件

    Args:
        file: 上传的GDS文件

    Returns:
        dict: 上传结果
    """
    try:
        storage_path = Path(settings.STORAGE_PATH)
        storage_path.mkdir(parents=True, exist_ok=True)

        file_path = storage_path / file.filename

        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return {
            "success": True,
            "message": f"文件上传成功: {file.filename}",
            "file_size": len(content)
        }

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


@router.get("/layers/{file_name}", response_model=list[GDSLayerInfo])
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
        gds_parser_service.set_layer_mapping(
            config.file_name,
            config.layer_mapping
        )
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置图层映射失败: {str(e)}")


@router.post("/parse-with-mapping", response_model=GDSParseResponse)
async def parse_gds_with_mapping(request: GDSParseRequest):
    """
    使用图层映射解析GDS文件（识别器件类型和计算器件值）

    Args:
        request: GDS解析请求

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

        # 使用图层映射解析
        result = gds_parser_service.parse_gds_file_with_mapping(
            request.file_name,
            layer_mapping
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
