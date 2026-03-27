import { useState, useRef } from 'react';
import './App.css';

interface PolygonData {
  points: number[][];
  layer: number;
  datatype: number;
}

interface Layer {
  layer_number: number;
  layer_name: string;
  datatype: number;
  polygon_count: number;
  polygons: PolygonData[];
}

interface Device {
  id: string;
  name: string;
  device_type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  layer: number;
  parameters: Record<string, any>;
}

interface GeometryInfo {
  min_x: number;
  max_x: number;
  min_y: number;
  max_y: number;
  width: number;
  height: number;
  cell_count: number;
}

interface GDSFile {
  id: string;
  name: string;
  uploadTime: string;
  layers: Layer[];
  geometry: GeometryInfo | null;
  devices: Device[];
  hasMapping: boolean;
  layerMapping?: {
    ME1: number;
    ME2: number;
    TFR: number;
    GND: number;
    VA1: number;
  };
  parsed: boolean;
}

function App() {
  const [uploadedFiles, setUploadedFiles] = useState<GDSFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<GDSFile | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // 层级映射配置
  const [layerMapping, setLayerMapping] = useState({
    ME1: '',
    ME2: '',
    TFR: '',
    GND: '',
    VA1: ''
  });

  // 视图控制状态
  const [viewState, setViewState] = useState({
    scale: 1,
    offsetX: 0,
    offsetY: 0,
  });

  // 拖拽平滑处理（使用ref避免闭包问题）
  const dragRef = React.useRef({
    isDragging: false,
    startX: 0,
    startY: 0,
    currentOffsetX: 0,
    currentOffsetY: 0
  });

  // 图层过滤
  const [visibleLayers, setVisibleLayers] = useState<Set<number>>(new Set());

  // 选中的多边形
  const [selectedPolygon, setSelectedPolygon] = useState<string | null>(null);

  const API_BASE = 'http://localhost:8000';

  // 上传文件
  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setMessage('正在上传文件...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/gds/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '上传失败');
      }

      const result = await response.json();

      // 获取图层信息
      const layersResponse = await fetch(`${API_BASE}/gds/layers/${file.name}`);
      if (!layersResponse.ok) {
        throw new Error('获取图层信息失败');
      }
      const layers = await layersResponse.json();

      // 获取几何信息
      const geoResponse = await fetch(`${API_BASE}/gds/geometry/${file.name}`);
      let geometry = null;
      if (geoResponse.ok) {
        geometry = await geoResponse.json();
      }

      // 检查是否有层级映射
      const mappingResponse = await fetch(`${API_BASE}/gds/layer-mapping/${file.name}`);
      let hasMapping = false;
      let existingMapping = undefined;
      if (mappingResponse.ok) {
        hasMapping = true;
        const mappingData = await mappingResponse.json();
        existingMapping = mappingData.mapping;
      }

      const newFile: GDSFile = {
        id: Date.now().toString(),
        name: file.name,
        uploadTime: new Date().toLocaleString(),
        layers: layers || [],
        geometry,
        devices: [],
        hasMapping,
        layerMapping: existingMapping,
        parsed: false
      };

      setUploadedFiles([...uploadedFiles, newFile]);
      setSelectedFile(newFile);
      setMessage('文件上传成功！');
    } catch (error) {
      console.error('上传失败:', error);
      setMessage(`错误: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  // 选择文件
  const handleFileSelect = (file: GDSFile) => {
    setSelectedFile(file);
    setLayerMapping({
      ME1: file.layerMapping?.ME1?.toString() || '',
      ME2: file.layerMapping?.ME2?.toString() || '',
      TFR: file.layerMapping?.TFR?.toString() || '',
      GND: file.layerMapping?.GND?.toString() || '',
      VA1: file.layerMapping?.VA1?.toString() || ''
    });
  };

  // 保存层级映射
  const saveLayerMapping = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setMessage('正在保存层级映射...');

    try {
      const mapping = {
        ME1: parseInt(layerMapping.ME1) || 0,
        ME2: parseInt(layerMapping.ME2) || 0,
        TFR: parseInt(layerMapping.TFR) || 0,
        GND: parseInt(layerMapping.GND) || 0,
        VA1: parseInt(layerMapping.VA1) || 0
      };

      const response = await fetch(`${API_BASE}/gds/layer-mapping`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_name: selectedFile.name,
          layer_mapping: mapping
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '保存映射失败');
      }

      // 更新文件信息
      const updatedFile = {
        ...selectedFile,
        hasMapping: true,
        layerMapping: mapping
      };

      const updatedFiles = uploadedFiles.map(f =>
        f.id === selectedFile.id ? updatedFile : f
      );

      setUploadedFiles(updatedFiles);
      setSelectedFile(updatedFile);
      setMessage('层级映射保存成功！');
    } catch (error) {
      console.error('保存映射失败:', error);
      setMessage(`错误: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  // 删除层级映射
  const deleteLayerMapping = async () => {
    if (!selectedFile || !selectedFile.hasMapping) return;

    setLoading(true);
    setMessage('正在删除层级映射...');

    try {
      const response = await fetch(`${API_BASE}/gds/layer-mapping/${selectedFile.name}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '删除映射失败');
      }

      const updatedFile = {
        ...selectedFile,
        hasMapping: false,
        layerMapping: undefined
      };

      const updatedFiles = uploadedFiles.map(f =>
        f.id === selectedFile.id ? updatedFile : f
      );

      setUploadedFiles(updatedFiles);
      setSelectedFile(updatedFile);
      setLayerMapping({ ME1: '', ME2: '', TFR: '', GND: '', VA1: '' });
      setMessage('层级映射已删除！');
    } catch (error) {
      console.error('删除映射失败:', error);
      setMessage(`错误: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  // 解析器件
  const parseDevices = async (useMapping: boolean) => {
    if (!selectedFile) return;

    setLoading(true);
    setMessage('正在解析器件...');

    try {
      const endpoint = useMapping ? '/gds/parse-with-mapping' : '/gds/parse';

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_name: selectedFile.name })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '解析失败');
      }

      const result = await response.json();

      const updatedFile = {
        ...selectedFile,
        devices: result.devices || [],
        parsed: true
      };

      const updatedFiles = uploadedFiles.map(f =>
        f.id === selectedFile.id ? updatedFile : f
      );

      setUploadedFiles(updatedFiles);
      setSelectedFile(updatedFile);
      setMessage(`解析成功！找到 ${result.devices?.length || 0} 个器件`);
    } catch (error) {
      console.error('解析失败:', error);
      setMessage(`错误: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  const getDeviceColor = (deviceType: string) => {
    const colors: Record<string, string> = {
      'L': '#3b82f6',
      'C': '#10b981',
      'R': '#ef4444',
      'PAD': '#6b7280',
      'GND': '#64748b'
    };
    return colors[deviceType] || '#9ca3af';
  };

  const getLayerColor = (layerNumber: number) => {
    const colors = ['#3b82f6', '#10b981', '#ef4444', '#6b7280', '#64748b', '#8b5cf6', '#06b6d4', '#f59e0b'];
    return colors[layerNumber % colors.length];
  };

  const calculateBounds = () => {
    if (!selectedFile) {
      return { minX: 0, maxX: 1000, minY: 0, maxY: 1000 };
    }

    // 优先使用几何信息
    if (selectedFile.geometry) {
      return {
        minX: selectedFile.geometry.min_x,
        maxX: selectedFile.geometry.max_x,
        minY: selectedFile.geometry.min_y,
        maxY: selectedFile.geometry.max_y
      };
    }

    // 如果没有几何信息，从多边形计算边界
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    // 从图层的多边形计算
    selectedFile.layers.forEach(layer => {
      layer.polygons.forEach(polygon => {
        polygon.points.forEach(point => {
          minX = Math.min(minX, point[0]);
          maxX = Math.max(maxX, point[0]);
          minY = Math.min(minY, point[1]);
          maxY = Math.max(maxY, point[1]);
        });
      });
    });

    // 如果没有多边形，从器件计算
    if (minX === Infinity) {
      selectedFile.devices.forEach(d => {
        minX = Math.min(minX, d.x);
        maxX = Math.max(maxX, d.x + d.width);
        minY = Math.min(minY, d.y);
        maxY = Math.max(maxY, d.y + d.height);
      });
    }

    return minX === Infinity ? { minX: 0, maxX: 1000, minY: 0, maxY: 1000 } : { minX, maxX, minY, maxY };
  };

  const bounds = calculateBounds();

  // 处理鼠标滚轮缩放
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(10, viewState.scale * delta));
    setViewState({ ...viewState, scale: newScale });
  };

  // 重置视图
  const handleResetView = () => {
    setViewState({ scale: 1, offsetX: 0, offsetY: 0 });
    dragRef.current = { isDragging: false, startX: 0, startY: 0, currentOffsetX: 0, currentOffsetY: 0 };
  };

  // 处理拖拽开始
  const handleMouseDown = (e: React.MouseEvent) => {
    dragRef.current = {
      isDragging: true,
      startX: e.clientX,
      startY: e.clientY,
      currentOffsetX: viewState.offsetX,
      currentOffsetY: viewState.offsetY
    };
  };

  // 处理拖拽移动
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragRef.current.isDragging) return;

    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;

    // 使用移动速度系数（0.3）使拖拽更平滑
    const smoothFactor = 0.3;
    const newOffsetX = dragRef.current.currentOffsetX + dx * smoothFactor;
    const newOffsetY = dragRef.current.currentOffsetY + dy * smoothFactor;

    setViewState({
      ...viewState,
      offsetX: newOffsetX,
      offsetY: newOffsetY
    });
  };

  // 处理拖拽结束
  const handleMouseUp = () => {
    dragRef.current = { isDragging: false, startX: 0, startY: 0, currentOffsetX: 0, currentOffsetY: 0 };
  };

  // 鼠标离开也结束拖拽
  const handleMouseLeave = () => {
    if (dragRef.current.isDragging) {
      dragRef.current = { isDragging: false, startX: 0, startY: 0, currentOffsetX: 0, currentOffsetY: 0 };
    }
  };

  // 切换图层可见性
  const toggleLayerVisibility = (layerNumber: number) => {
    const newVisibleLayers = new Set(visibleLayers);
    if (newVisibleLayers.has(layerNumber)) {
      newVisibleLayers.delete(layerNumber);
    } else {
      newVisibleLayers.add(layerNumber);
    }
    setVisibleLayers(newVisibleLayers);
  };

  // 全选/取消所有图层
  const toggleAllLayers = () => {
    if (visibleLayers.size === selectedFile?.layers.length) {
      setVisibleLayers(new Set());
    } else {
      setVisibleLayers(new Set(selectedFile?.layers.map(l => l.layer_number) || []));
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>GDS 器件管理工具</h1>
        <button
          className="upload-btn"
          disabled={loading}
          onClick={() => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.gds,.gdsii,.gds.gz';
            input.onchange = (e) => {
              const file = (e.target as HTMLInputElement).files?.[0];
              if (file) {
                handleFileUpload(file);
              }
            };
            input.click();
          }}
        >
          {loading ? '处理中...' : '上传 GDS 文件'}
        </button>
      </header>

      <main className="App-main">
        {/* 左侧：文件列表 */}
        <div className="sidebar">
          <h2>已上传文件</h2>
          <div className="file-list">
            {uploadedFiles.length === 0 ? (
              <p className="empty-message">暂无文件</p>
            ) : (
              uploadedFiles.map((file) => (
                <div
                  key={file.id}
                  className={`file-item ${selectedFile?.id === file.id ? 'selected' : ''}`}
                  onClick={() => handleFileSelect(file)}
                >
                  <div className="file-info">
                    <span className="file-name">{file.name}</span>
                    <span className="file-time">{file.uploadTime}</span>
                  </div>
                  <div className="file-status">
                    {file.hasMapping && (
                      <span className="status-badge mapping">已配置映射</span>
                    )}
                    {file.parsed && (
                      <span className="status-badge parsed">已解析器件</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 中间：GDS 查看器 */}
        <div className="content">
          {selectedFile ? (
            <div className="viewer-container">
              {/* 信息栏 */}
              <div className="info-bar">
                <div className="file-info-item">
                  <strong>文件:</strong> {selectedFile.name}
                </div>
                <div className="file-info-item">
                  <strong>图层数:</strong> {selectedFile.layers.length}
                </div>
                {selectedFile.geometry && (
                  <>
                    <div className="file-info-item">
                      <strong>尺寸:</strong> {selectedFile.geometry.width} × {selectedFile.geometry.height}
                    </div>
                    <div className="file-info-item">
                      <strong>单元数:</strong> {selectedFile.geometry.cell_count}
                    </div>
                  </>
                )}
                {selectedFile.parsed && (
                  <div className="file-info-item">
                    <strong>器件数:</strong> {selectedFile.devices.length}
                  </div>
                )}
              </div>

              {/* GDS 显示区域 */}
              <div className="gds-viewer-container">
                {/* 工具栏 */}
                <div className="viewer-toolbar">
                  <div className="toolbar-group">
                    <button
                      className="toolbar-btn"
                      onClick={() => setViewState({ ...viewState, scale: viewState.scale * 0.9 })}
                      disabled={viewState.scale <= 0.1}
                      title="缩小"
                    >
                      −
                    </button>
                    <span className="zoom-level">{Math.round(viewState.scale * 100)}%</span>
                    <button
                      className="toolbar-btn"
                      onClick={() => setViewState({ ...viewState, scale: viewState.scale * 1.1 })}
                      disabled={viewState.scale >= 10}
                      title="放大"
                    >
                      +
                    </button>
                    <button
                      className="toolbar-btn"
                      onClick={handleResetView}
                      title="重置视图"
                    >
                      ⤢
                    </button>
                  </div>
                </div>

                <svg
                  width="100%"
                  height="100%"
                  viewBox={`${bounds.minX} ${bounds.minY} ${bounds.maxX - bounds.minX} ${bounds.maxY - bounds.minY}`}
                  onWheel={handleWheel}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseLeave}
                  style={{
                    background: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    cursor: dragRef.current.isDragging ? 'grabbing' : 'grab'
                  }}
                >
                  <g
                    transform={`translate(${viewState.offsetX}, ${viewState.offsetY}) scale(${viewState.scale})`}
                    transform-origin="0 0"
                  >
                    {/* 绘制图层和多边形 */}
                    {selectedFile.layers.map((layer, layerIndex) => {
                      const layerColor = getLayerColor(layer.layer_number);
                      const isVisible = visibleLayers.size === 0 || visibleLayers.has(layer.layer_number);
                      return (
                        <g key={layer.layer_number} opacity={isVisible ? 0.7 : 0.1}>
                          {/* 图层标签 */}
                          <text
                            x={bounds.minX + 10}
                            y={bounds.minY + 20 + layerIndex * 20}
                            fill="#64748b"
                            fontSize="12"
                            style={{ fontFamily: 'monospace' }}
                          >
                            Layer {layer.layer_number}: {layer.layer_name} ({layer.polygons.length} polygons)
                          </text>

                          {/* 绘制多边形 */}
                          {layer.polygons.map((polygon, polygonIndex) => {
                            const polygonKey = `${layer.layer_number}-${polygonIndex}`;
                            const isSelected = selectedPolygon === polygonKey;
                            return (
                              <polygon
                                key={polygonKey}
                                points={polygon.points.map(p => `${p[0]},${p[1]}`).join(' ')}
                                fill={layerColor}
                                stroke={isSelected ? '#ffffff' : layerColor}
                                strokeWidth={isSelected ? 3 : 1}
                                fillOpacity={isSelected ? 0.5 : 0.3}
                                strokeOpacity={isSelected ? 1 : 0.7}
                                style={{ cursor: 'pointer' }}
                                onClick={() => setSelectedPolygon(isSelected ? null : polygonKey)}
                              />
                            );
                          })}
                        </g>
                      );
                    })}

                    {/* 绘制器件 */}
                    {selectedFile.devices.map((device, index) => {
                    const color = getDeviceColor(device.device_type);
                    return (
                      <g key={index} style={{ cursor: 'pointer' }}>
                        <rect
                          x={device.x}
                          y={device.y}
                          width={device.width}
                          height={device.height}
                          fill={color}
                          stroke={color}
                          strokeWidth="2"
                          opacity="0.7"
                        />
                        <text
                          x={device.x + device.width / 2}
                          y={device.y + device.height / 2}
                          fill="white"
                          fontSize="14"
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fontWeight="bold"
                          style={{ fontFamily: 'monospace' }}
                        >
                          {device.name}
                        </text>
                      </g>
                    );
                  })}
                  </g>
                </svg>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>请上传或选择一个 GDS 文件</p>
              <div className="info-text">
                <p>支持格式: .gds, .gdsii, .gds.gz</p>
                <p>确保后端服务运行在 http://localhost:8000</p>
              </div>
            </div>
          )}
        </div>

        {/* 右侧：操作面板 */}
        {selectedFile && (
          <div className="panel">
            <h2>操作面板</h2>

            {/* 消息显示 */}
            {message && (
              <div className="message-box">
                {message}
                <button
                  className="close-msg"
                  onClick={() => setMessage('')}
                >
                  ×
                </button>
              </div>
            )}

            {/* 层级映射配置 */}
            <div className="panel-section">
              <h3>层级映射配置</h3>
              <p className="section-desc">配置不同器件类型对应的图层号</p>

              <div className="mapping-inputs">
                <div className="mapping-input">
                  <label>ME1 (电感1层)</label>
                  <input
                    type="number"
                    value={layerMapping.ME1}
                    onChange={(e) => setLayerMapping({ ...layerMapping, ME1: e.target.value })}
                    placeholder="层级号"
                  />
                </div>
                <div className="mapping-input">
                  <label>ME2 (电感2层)</label>
                  <input
                    type="number"
                    value={layerMapping.ME2}
                    onChange={(e) => setLayerMapping({ ...layerMapping, ME2: e.target.value })}
                    placeholder="层级号"
                  />
                </div>
                <div className="mapping-input">
                  <label>TFR (传输线层)</label>
                  <input
                    type="number"
                    value={layerMapping.TFR}
                    onChange={(e) => setLayerMapping({ ...layerMapping, TFR: e.target.value })}
                    placeholder="层级号"
                  />
                </div>
                <div className="mapping-input">
                  <label>GND (接地层)</label>
                  <input
                    type="number"
                    value={layerMapping.GND}
                    onChange={(e) => setLayerMapping({ ...layerMapping, GND: e.target.value })}
                    placeholder="层级号"
                  />
                </div>
                <div className="mapping-input">
                  <label>VA1 (电容层)</label>
                  <input
                    type="number"
                    value={layerMapping.VA1}
                    onChange={(e) => setLayerMapping({ ...layerMapping, VA1: e.target.value })}
                    placeholder="层级号"
                  />
                </div>
              </div>

              <div className="mapping-actions">
                <button
                  className="action-btn save"
                  disabled={loading}
                  onClick={saveLayerMapping}
                >
                  保存映射
                </button>
                <button
                  className="action-btn delete"
                  disabled={loading || !selectedFile?.hasMapping}
                  onClick={deleteLayerMapping}
                >
                  删除映射
                </button>
              </div>
            </div>

            {/* 器件解析 */}
            <div className="panel-section">
              <h3>器件解析</h3>
              <p className="section-desc">从 GDS 文件中提取器件信息</p>

              <div className="parse-actions">
                <button
                  className="action-btn parse"
                  disabled={loading}
                  onClick={() => parseDevices(false)}
                >
                  默认解析（无映射）
                </button>
                <button
                  className={`action-btn parse ${!selectedFile?.hasMapping ? 'disabled' : ''}`}
                  disabled={loading || !selectedFile?.hasMapping}
                  onClick={() => parseDevices(true)}
                >
                  使用映射解析
                </button>
              </div>

              {!selectedFile?.hasMapping && (
                <p className="hint-text">
                  💡 需要先配置并保存层级映射才能使用映射解析
                </p>
              )}
            </div>

            {/* 图层信息 */}
            {selectedFile && selectedFile.layers.length > 0 && (
              <div className="panel-section">
                <h3>图层控制</h3>
                <div className="layer-controls">
                  <button
                    className="toggle-all-btn"
                    onClick={toggleAllLayers}
                  >
                    {visibleLayers.size === selectedFile.layers.length ? '隐藏全部' : '显示全部'}
                  </button>
                </div>
                <div className="layers-list">
                  {selectedFile.layers.map((layer) => {
                    const isVisible = visibleLayers.size === 0 || visibleLayers.has(layer.layer_number);
                    return (
                      <div
                        key={layer.layer_number}
                        className={`layer-item ${isVisible ? 'visible' : 'hidden'}`}
                        onClick={() => toggleLayerVisibility(layer.layer_number)}
                      >
                        <span className="layer-checkbox">
                          {isVisible ? '✓' : '○'}
                        </span>
                        <span className="layer-number">Layer {layer.layer_number}</span>
                        <span className="layer-name">{layer.layer_name}</span>
                        <span className="layer-poly">{layer.polygon_count} 多边形</span>
                      </div>
                    );
                  })}
                </div>
                {visibleLayers.size > 0 && (
                  <p className="layer-hint">
                    已选择 {visibleLayers.size} / {selectedFile.layers.length} 个图层
                  </p>
                )}
              </div>
            )}

            {/* 选中多边形信息 */}
            {selectedPolygon && (
              <div className="panel-section">
                <h3>多边形信息</h3>
                <div className="polygon-info">
                  <p><strong>ID:</strong> {selectedPolygon}</p>
                  <button
                    className="action-btn"
                    onClick={() => setSelectedPolygon(null)}
                  >
                    取消选择
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
