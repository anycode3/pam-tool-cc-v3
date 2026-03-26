import pytest
from pathlib import Path
from app.schemas.gds import DeviceInfo, GDSParseRequest, GDSLayerInfo
from app.schemas.gds_mapping import LayerMapping, GDSLayerMappingConfig
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
    storage_path = Path("storage")
    storage_path.mkdir(exist_ok=True)

    test_file = storage_path / "test.gds"
    test_file_file = storage_path / "test.gds"
    test_file_file.touch()

    try:
        service = GDSParserService()
        result = service.parse_gds_file("test.gds")
        assert result.success is True
        assert result.cell_count == 1
        assert len(result.devices) > 0
        assert result.message == "成功解析文件: test.gds"
    finally:
        if test_file_file.exists():
            test_file_file.unlink()


def test_layer_mapping_setting_and_getting():
    """测试图层映射设置和获取"""
    service = GDSParserService()
    mapping = LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)

    service.set_layer_mapping("test.gds", mapping)
    retrieved = service.get_layer_mapping("test.gds")

    assert retrieved is not None
    assert retrieved.me1 == 1
    assert retrieved.me2 == 2
    assert retrieved.tfr == 3
    assert retrieved.gnd == 4
    assert retrieved.va1 == 5


def test_get_nonexistent_layer_mapping():
    """测试获取不存在的图层映射"""
    service = GDSParserService()
    result = service.get_layer_mapping("nonexistent.gds")
    assert result is None


def test_parse_with_mapping_without_config():
    """测试使用图层映射解析但未配置映射"""
    storage_path = Path("storage")
    storage_path.mkdir(exist_ok=True)

    test_file = storage_path / "test.gds"
    test_file.touch()

    try:
        service = GDSParserService()
        result = service.parse_gds_file_with_mapping(
            "test.gds",
            LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)
        )
        assert result.success is True
        assert result.cell_count == 1
        assert "使用图层映射" in result.message
    finally:
        if test_file.exists():
            test_file.unlink()


def test_parse_with_mapping_nonexistent_file():
    """测试使用图层映射解析不存在的文件"""
    service = GDSParserService()
    mapping = LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)

    result = service.parse_gds_file_with_mapping("nonexistent.gds", mapping)
    assert result.success is False
    assert "不存在" in result.message
    assert len(result.devices) == 0


def test_layer_mapping_config_creation():
    """测试GDSLayerMappingConfig模型创建"""
    config = GDSLayerMappingConfig(
        file_name="test.gds",
        layer_mapping=LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)
    )
    assert config.file_name == "test.gds"
    assert config.layer_mapping.me1 == 1


def test_layer_mapping_model_creation():
    """测试LayerMapping模型创建"""
    mapping = LayerMapping(me1=10, me2=20, tfr=30, gnd=40, va1=50)
    assert mapping.me1 == 10
    assert mapping.me2 == 20
    assert mapping.tfr == 30
    assert mapping.gnd == 40
    assert mapping.va1 == 50
