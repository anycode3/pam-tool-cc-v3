import { useState } from 'react';
import './App.css';

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

interface Layer {
  layer_number: number;
  layer_name: string;
  datatype: number;
  polygon_count: number;
}

interface FileWithDevices {
  id: string;
  name: string;
  uploadTime: string;
  deviceCount: number;
  devices: Device[];
  layers: Layer[];
}

function App() {
  const [uploadedFiles, setUploadedFiles] = useState<FileWithDevices[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileWithDevices | null>(null);
  const [scale, setScale] = useState(1);
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);

  const handleFileUpload = async (file: File) => {
    try {
      // 1. 上传文件
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await fetch('http://localhost:8000/gds/upload', {
        method: 'POST',
        body: formData
      });

      if (!uploadResponse.ok) {
        const error = await uploadResponse.json();
        throw new Error(error.detail || '上传失败');
      }

      const uploadResult = await uploadResponse.json();
      console.log('上传成功:', uploadResult);

      // 2. 解析文件获取器件
      const parseResponse = await fetch('http://localhost:8000/gds/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_name: file.name })
      });

      if (!parseResponse.ok) {
        const error = await parseResponse.json();
        throw new Error(error.detail || '解析失败');
      }

      const parseResult = await parseResponse.json();
      console.log('解析成功:', parseResult);

      // 3. 获取图层信息
      const layersResponse = await fetch(`http://localhost:8000/gds/layers/${file.name}`);
      const layers = await layersResponse.json();

      const fileData: FileWithDevices = {
        id: Date.now().toString(),
        name: file.name,
        uploadTime: new Date().toLocaleString(),
        deviceCount: parseResult.devices?.length || 0,
        devices: parseResult.devices || [],
        layers: layers || []
      };

      setUploadedFiles([...uploadedFiles, fileData]);
      setSelectedFile(fileData);
    } catch (error) {
      console.error('上传失败:', error);
      alert(`文件处理失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const handleFileSelect = (file: FileWithDevices) => {
    setSelectedFile(file);
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

  const calculateBounds = () => {
    if (!selectedFile || selectedFile.devices.length === 0) {
      return { minX: 0, maxX: 1000, minY: 0, maxY: 1000 };
    }

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    selectedFile.devices.forEach(d => {
      minX = Math.min(minX, d.x);
      maxX = Math.max(maxX, d.x + d.width);
      minY = Math.min(minY, d.y);
      maxY = Math.max(maxY, d.y + d.height);
    });

    return { minX, maxX, minY, maxY };
  };

  const bounds = calculateBounds();

  return (
    <div className="App">
      <header className="App-header">
        <h1>GDS 器件管理工具</h1>
        <button
          className="upload-btn"
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
          上传 GDS 文件
        </button>
      </header>
      <main className="App-main">
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
                  <span className="device-count">{file.deviceCount} 个器件</span>
                </div>
              ))
            )}
          </div>
        </div>
        <div className="content">
          {selectedFile ? (
            <div className="gds-viewer-container">
              <svg
                width="100%"
                height="100%"
                viewBox={`${bounds.minX} ${bounds.minY} ${bounds.maxX - bounds.minX} ${bounds.maxY - bounds.minY}`}
                style={{
                  background: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '8px'
                }}
              >
                {/* 绘制图层信息 */}
                {selectedFile.layers.map((layer, index) => (
                  <g key={layer.layer_number} opacity="0.3">
                    <text
                      x={bounds.minX + 10}
                      y={bounds.minY + 20 + index * 20}
                      fill="#64748b"
                      fontSize="12"
                      style={{ fontFamily: 'monospace' }}
                    >
                      Layer {layer.layer_number}: {layer.layer_name}
                    </text>
                  </g>
                ))}

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
                      {device.parameters?.value && (
                        <text
                          x={device.x + device.width / 2}
                          y={device.y + device.height / 2 + 16}
                          fill="white"
                          fontSize="10"
                          textAnchor="middle"
                          dominantBaseline="middle"
                          style={{ fontFamily: 'monospace' }}
                        >
                          {device.parameters.value} {device.parameters.unit}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>
          ) : (
            <div className="empty-state">
              <p>请上传一个 GDS 文件开始</p>
              <div className="info-text">
                <p>支持格式: .gds, .gdsii, .gds.gz</p>
                <p>确保后端服务运行在 http://localhost:8000</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
