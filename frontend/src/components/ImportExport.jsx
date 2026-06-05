import React, { useState, useRef } from 'react';
import { UploadCloud, Download, X, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function ImportExport({ onClose, onImportSuccess }) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null); // { success: boolean, message: string }
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = async (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file) => {
    if (file.type !== "application/json" && !file.name.endsWith(".json")) {
      setResult({ success: false, message: "Only JSON files are supported" });
      return;
    }

    setUploading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/recipes/import", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Import failed");
      }

      setResult({
        success: true,
        message: data.message || `Successfully imported recipes!`,
      });
      
      if (onImportSuccess) {
        onImportSuccess();
      }
    } catch (err) {
      setResult({
        success: false,
        message: err.message || "Failed to parse or upload the recipe file",
      });
    } finally {
      setUploading(false);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  const handleExport = async () => {
    try {
      const response = await fetch("/api/recipes/export");
      if (!response.ok) throw new Error("Failed to export");
      
      const blob = await response.json();
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(blob, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", "recipe-export.json");
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err) {
      alert("Failed to export: " + err.message);
    }
  };

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h2>Backup & Import Collection</h2>
          <button className="drawer-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="dialog-content import-section">
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Import a list of recipes formatted as a JSON array or backup your current local collection to a file.
          </p>

          <input 
            type="file" 
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleChange}
            accept=".json"
          />

          <div 
            className={`dropzone ${dragActive ? 'active' : ''}`}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={triggerFileInput}
          >
            <UploadCloud size={48} className="dropzone-icon animate-pulse" />
            <div className="dropzone-text">
              {uploading ? 'Processing file...' : 'Drag & drop your recipe JSON here or click to browse'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Maximum file size: 1MB
            </div>
          </div>

          {result && (
            <div 
              style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.75rem',
                padding: '1rem', 
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.9rem',
                fontWeight: 600,
                backgroundColor: result.success ? 'var(--color-success-light)' : 'var(--color-error-light)',
                color: result.success ? 'var(--color-success)' : 'var(--color-error)'
              }}
            >
              {result.success ? <CheckCircle2 size={20} /> : <AlertTriangle size={20} />}
              <span>{result.message}</span>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Export Collection</h3>
            <button className="btn btn-secondary" onClick={handleExport} style={{ justifyContent: 'center' }}>
              <Download size={16} /> Download Recipes Backup (.json)
            </button>
          </div>
        </div>

        <div className="dialog-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
