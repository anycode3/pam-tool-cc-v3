import axios from 'axios'

const API_BASE = 'http://localhost:8000'


export interface LayerMapping {
  ME1: number
  ME2: number
  TFR: number
  GND: number
  VA1: number
}


export interface DeviceInfo {
  name: string
  device_type: string
  x: number
  y: number
  width: number
  height: number
  layer: number
  parameters: {
    value?: number
    unit?: string
    [key: string]: any
  }
}


export interface GDSParseResponse {
  file_name: string
  cell_count: number
  devices: DeviceInfo[]
  success: boolean
  message?: string
}


export interface LayerInfo {
  layer_number: number
  layer_name: string
  datatype: number
  polygon_count: number
}


// 上传GDS文件
export const uploadGDS = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await axios.post(`${API_BASE}/gds/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}


// 设置图层映射
export const setLayerMapping = async (fileName: string, mapping: LayerMapping) => {
  const response = await axios.post(`${API_BASE}/gds/layer-mapping`, {
    file_name: fileName,
    layer_mapping: mapping
  })
  return response.data
}


// 获取图层映射
export const getLayerMapping = async (fileName: string) => {
  const response = await axios.get(`${API_BASE}/gds/layer-mapping/${fileName}`)
  return response.data
}


// 删除图层映射
export const deleteLayerMapping = async (fileName: string) => {
  const response = await axios.delete(`${API_BASE}/gds/layer-mapping/${fileName}`)
  return response.data
}


// 获取所有图层映射
export const listLayerMappings = async () => {
  const response = await axios.get(`${API_BASE}/gds/layer-mapping`)
  return response.data
}


// 解析GDS文件
export const parseGDS = async (fileName: string) => {
  const response = await axios.post(`${API_BASE}/gds/parse`, {
    file_name: fileName
  })
  return response.data as GDSParseResponse
}


// 使用图层映射解析GDS文件
export const parseGDSWithMapping = async (fileName: string) => {
  const response = await axios.post(`${API_BASE}/gds/parse-with-mapping`, {
    file_name: fileName
  })
  return response.data as GDSParseResponse
}


// 获取图层信息
export const getGDSLayers = async (fileName: string) => {
  const response = await axios.get(`${API_BASE}/gds/layers/${fileName}`)
  return response.data as LayerInfo[]
}
