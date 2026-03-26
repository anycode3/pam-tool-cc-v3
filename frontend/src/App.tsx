import { useState } from 'react';
import GDSViewer from './components/GDSViewer';
import './App.css';

interface FileWithDevices {
  id: string;
  name: string;
  uploadTime: string;
  deviceCount: number;
  devices: any[];
}

function App() {
  const [uploadedFiles, setUploadedFiles] = useState<FileWithDevices[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileWithDevices | null>(null);

  const handleFileUpload = (fileData: FileWithDevices) => {
    setUploadedFiles([...uploadedFiles, fileData]);
    setSelectedFile(fileData);
  };

  const handleFileSelect = (file: FileWithDevices) => {
    setSelectedFile(file);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>GDS 器件管理工具</h1>
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
            <GDSViewer
              file={selectedFile}
              onFileUpdate={(updatedFile) => {
                setSelectedFile(updatedFile);
                const updatedFiles = uploadedFiles.map(f =>
                  f.id === updatedFile.id ? updatedFile : f
                );
                setUploadedFiles(updatedFiles);
              }}
            />
          ) : (
            <div className="empty-state">
              <p>请上传一个 GDS 文件开始</p>
              <button
                className="upload-btn"
                onClick={() => {
                  // 触发文件选择对话框
                  const input = document.createElement('input');
                  input.type = 'file';
                  input.accept = '.gds,.gdsii,.gds.gz';
                  input.onchange = (e) => {
                    const file = (e.target as HTMLInputElement).files?.[0];
                    if (file) {
                      // TODO: 实现文件上传逻辑
                      alert(`文件上传功能开发中: ${file.name}`);
                    }
                  };
                  input.click();
                }}
              >
                上传 GDS 文件
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
