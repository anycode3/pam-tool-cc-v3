import pytest
from app.schemas.gds_mapping import LayerMapping, GDSLayerMappingConfig
from app.services.device_recognizer import DeviceRecognizer, DeviceCandidate
from app.utils.gds_mock import Polygon, Label


def test_layer_mapping_creation():
    """测试图层映射创建"""
    mapping = LayerMapping(
        me1=1,
        me2=2,
        tfr=3,
        gnd=4,
        va1=5
    )
    assert mapping.me1 == 1
    assert mapping.me2 == 2
    assert mapping.tfr == 3
    assert mapping.gnd == 4
    assert mapping.va1 == 5


def test_gds_layer_mapping_config_creation():
    """测试GDS图层映射配置创建"""
    config = GDSLayerMappingConfig(
        file_name="test.gds",
        layer_mapping=LayerMapping(
            me1=1,
            me2=2,
            tfr=3,
            gnd=4,
            va1=5
        )
    )
    assert config.file_name == "test.gds"
    assert config.layer_mapping.me1 == 1


def test_device_recognizer_creation():
    """测试器件识别器创建"""
    mapping = LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)
    recognizer = DeviceRecognizer(mapping)
    assert recognizer.mapping.me1 == 1


def test_recognize_resistors():
    """测试电阻识别"""
    mapping = LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)
    recognizer = DeviceRecognizer(mapping)

    # 创建一个TFR层的矩形
    resistor_poly = Polygon(
        layer=3,  # TFR层
        datatype=0,
        points=[[0, 0], [50, 0], [50, 10], [0, 10]]
    )

    polygons_by_layer = {3: [resistor_poly]}
    resistors = recognizer._recognize_resistors(polygons_by_layer)

    assert len(resistors) == 1
    assert resistors[0].device_type == "R"
    assert resistors[0].value is not None
    assert resistors[0].unit == "Ω"


def test_recognize_capacitors():
    """测试电容识别"""
    mapping = LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)
    recognizer = DeviceRecognizer(mapping)

    # 创建ME1和ME2层的重叠矩形
    cap_poly1 = Polygon(
        layer=1,  # ME1层
        datatype=0,
        points=[[0, 0], [20, 0], [20, 20], [0, 20]]
    )
    cap_poly2 = Polygon(
        layer=2,  # ME2层
        datatype=0,
        points=[[5, 5], [15, 5], [15, 15], [5, 15]]
    )

    polygons_by_layer = {1: [cap_poly1], 2: [cap_poly2]}
    capacitors = recognizer._recognize_capacitors(polygons_by_layer)

    assert len(capacitors) > 0
    assert capacitors[0].device_type == "C"
    assert capacitors[0].unit == "pF"


def test_is_rectangular_shape():
    """测试矩形形状判断"""
    mapping = LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)
    recognizer = DeviceRecognizer(mapping)

    # 矩形
    rect_poly = Polygon(
        layer=1,
        datatype=0,
        points=[[0, 0], [10, 0], [10, 5], [0, 5]]
    )
    assert recognizer._is_rectangular_shape(rect_poly) is True


def test_is_overlapping():
    """测试重叠判断"""
    mapping = LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)
    recognizer = DeviceRecognizer(mapping)

    # 重叠的矩形
    poly1 = Polygon(
        layer=1,
        datatype=0,
        points=[[0, 0], [20, 0], [20, 20], [0, 20]]
    )
    poly2 = Polygon(
        layer=2,
        datatype=0,
        points=[[10, 10], [30, 10], [30, 30], [10, 30]]
    )
    assert recognizer._is_overlapping(poly1, poly2) is True

    # 不重叠的矩形
    poly3 = Polygon(
        layer=3,
        datatype=0,
        points=[[100, 100], [120, 100], [120, 120], [100, 120]]
    )
    assert recognizer._is_overlapping(poly1, poly3) is False


def test_resistance_calculation():
    """测试电阻值计算"""
    mapping = LayerMapping(me1=1, me2=2, tfr=3, gnd=4, va1=5)
    recognizer = DeviceRecognizer(mapping)

    # 50x10的电阻条
    resistor_poly = Polygon(
        layer=3,
        datatype=0,
        points=[[0, 0], [50, 0], [50, 10], [0, 10]]
    )

    value = recognizer._calculate_resistance(resistor_poly)
    assert value.unit == "Ω"
    # Rs * (L/W) = 100 * (50/10) = 500
    assert abs(value.value - 500) < 10  # 允许一定误差
