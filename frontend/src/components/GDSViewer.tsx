import React from 'react'
import { DeviceInfo, LayerInfo } from '../api'


interface GDSViewerProps {
  devices: DeviceInfo[]
  layers: LayerInfo[]
  scale: number
  offsetX: number
  offsetY: number
}


// 简单的GDS渲染组件
const GDSViewer: React.FC<GDSViewerProps> = ({ devices, layers, scale, offsetX, offsetY }) => {
  // 计算边界
  const bounds = React.useMemo(() => {
    if (devices.length === 0) return { minX: 0, maxX: 1000, minY: 0, maxY: 1000 }

    let minX = Infinity
    let maxX = -Infinity
    let minY = Infinity
    let maxY = -Infinity

    devices.forEach(d => {
      minX = Math.min(minX, d.x)
      maxX = Math.max(maxX, d.x + d.width)
      minY = Math.min(minY, d.y)
      maxY = Math.max(maxY, d.y + d.height)
    })

    return { minX, maxX, minY, maxY }
  }, [devices])

  // 设备颜色映射
  const getDeviceColor = (deviceType: string) => {
    const colors: Record<string, string> = {
      'L': '#3b82f6',
      'C': '#10b981',
      'R': '#ef4444',
      'PAD': '#6b7280',
      'GND': '#64748b'
    }
    return colors[deviceType] || '#9ca3af'
  }

  return (
    <div className="gds-viewer-container">
      <svg
        width={800}
        height={600}
        viewBox={`${bounds.minX} ${bounds.minY} ${bounds.maxX - bounds.minX} ${bounds.maxY - bounds.minY}`}
        style={{
          background: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '8px'
        }}
      >
        {/* 绘制图层（简化显示） */}
        {layers.map(layer => (
          <g key={layer.layer_number} opacity="0.1">
            <text
              x={bounds.minX + 10}
              y={bounds.minY + 20 + layer.layer_number * 20}
              fill="#64748b"
              fontSize="12"
            >
              Layer {layer.layer_number}: {layer.layer_name} ({layer.polygon_count} polys)
            </text>
          </g>
        ))}

        {/* 绘制设备 */}
        {devices.map((device, index) => {
          const color = getDeviceColor(device.device_type)
          const strokeColor = color

          return (
            <g key={index}>
              {/* 设备边框 */}
              <rect
                x={device.x}
                y={device.y}
                width={device.width}
                height={device.height}
                fill={color}
                stroke={strokeColor}
                strokeWidth="2"
                opacity="0.7"
              />

              {/* 设备标签 */}
              <text
                x={device.x + device.width / 2}
                y={device.y + device.height / 2}
                fill="white"
                fontSize="14"
                textAnchor="middle"
                dominantBaseline="middle"
                fontWeight="bold"
              >
                {device.name}
              </text>

              {/* 器件值 */}
              {device.parameters.value && (
                <text
                  x={device.x + device.width / 2}
                  y={device.y + device.height / 2 + 16}
                  fill="white"
                  fontSize="10"
                  textAnchor="middle"
                  dominantBaseline="middle"
                >
                  {device.parameters.value} {device.parameters.unit}
                </text>
              )}
            </g>
          ))}
      </svg>
    </div>
  )
}


export default GDSViewer
