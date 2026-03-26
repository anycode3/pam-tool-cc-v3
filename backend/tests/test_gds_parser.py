import pytest
from app.schemas.gds import DeviceInfo, GDSParseRequest, GDSLayerInfo
from app.services.gds_parser import GDSParserService


def test_device_info_creation():
    """测试DeviceInfo模型创建"""
    device = DeviceInfo(
        name="test_device",
        device_type="resistor",
        x=0.0,
        y=0.0,
        width=10.0,
        height=5.0,
        layer=1,
        parameters={"value": "1k"}
    )
    assert device.name == "test_device"
    assert device.device_type == "resistor"
    assert device.x == 0.0
    assert device.y == 0.0
    assert device.width == 10.0
    assert device.height == 5.0
    assert device.layer == 1
    assert device.parameters["value"] == "1k"


def test_gds_parse_request_creation():
    """测试GDSParseRequest模型创建"""
    request = GDSParseRequest(file_name="test.gds")
    assert request.file_name == "test.gds"


def test_gds_parser_service_creation():
    """测试GDSParserService创建"""
    service = GDSParserService()
    assert service.storage_path is not None


def test_parse_nonexistent_file():
    """测试解析不存在的文件"""
    service = GDSParserService()
    result = service.parse_gds_file("nonexistent.gds")
    assert result.success is False
    assert "不存在" in result.message
    assert result.cell_count == 0
    assert len(result.devices) == 0


def test_get_layer_info_nonexistent_file():
    """测试获取不存在文件的图层信息"""
    service = GDSParserService()
    layers = service.get_layer_info("nonexistent.gds")
    assert len(layers) == 0


def test_parse_mock_gds_file():
    """测试解析模拟GDS文件"""
    from pathlib import Path
    import os

    # 创建storage目录
    storage_path = Path("storage")
    storage_path.mkdir(exist_ok=True)

    # 创建一个空的测试文件（mock模块会忽略实际内容）
    test_file = storage_path / "test.gds"
    test_file.touch()

    try:
        service = GDSParserService()
        result = service.parse_gds_file("test.gds")
        assert result.success is True
        assert result.cell_count == 1
        assert len(result.devices) > 0
        assert result.message == "成功解析文件: test.gds"

    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()
