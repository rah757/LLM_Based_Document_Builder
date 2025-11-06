import React, { useState } from 'react';
import './Upload.css';

function Upload({ onSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.name.endsWith('.docx')) {
      setFile(selectedFile);
      setError('');
    } else {
      setError('Please select a .docx file');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith('.docx')) {
      setFile(droppedFile);
      setError('');
    } else {
      setError('Please drop a .docx file');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        onSuccess(data.data);
      } else {
        setError(data.error || 'Upload failed');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <div className="header">
        <h1>📄 Document Placeholder Filler</h1>
        <p>Upload a document with placeholders to get started</p>
      </div>
      
      <div className="container">
        <div
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById('fileInput').click()}
        >
          <input
            id="fileInput"
            type="file"
            accept=".docx"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          
          {!file ? (
            <>
              <div className="upload-icon">📁</div>
              <p className="upload-text">Drop your .docx file here or click to browse</p>
              <p className="upload-hint">Supports: [Name], double-brace, and single-brace placeholders</p>
            </>
          ) : (
            <>
              <div className="upload-icon">✓</div>
              <p className="upload-text">{file.name}</p>
              <p className="upload-hint">{(file.size / 1024).toFixed(1)} KB</p>
            </>
          )}
        </div>

        {error && <div className="error">{error}</div>}

        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          style={{ width: '100%', marginTop: '20px' }}
        >
          {uploading ? 'Processing...' : 'Upload & Start Filling'}
        </button>
      </div>
    </>
  );
}

export default Upload;

