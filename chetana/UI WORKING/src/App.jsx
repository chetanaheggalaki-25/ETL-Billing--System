import React, { useState, useEffect, useRef } from 'react';
import {
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  RefreshCcw,
  LogOut,
  ShieldCheck,
  FileText,
  Activity,
  History,
  LayoutDashboard,
  Layers,
  Settings,
  FileSpreadsheet,
  Database,
  ChevronRight,
  Search,
  Upload,
  Zap,
  Download
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = '';              // Node.js auth server
const PYTHON_API_URL = 'http://localhost:5000'; // Direct connection to FastAPI


// --- Placeholder Pages for Dashboard ---
// --- High-Fidelity Dashboard Page Components ---
const ProcessingPage = ({ history, setHistory, selectedId, setSelectedId, onClearHistory }) => {
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('All');
  const [showAll, setShowAll] = useState(false);
  const fileInputRef = useRef();

  const getCurrentTime = () => {
    const now = new Date();
    return `Today, ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  };

  const filtered = history.filter(f => {
    const matchesSearch = f.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'All' || f.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const displayCount = showAll ? filtered.length : 10;
  const displayed = filtered.slice(0, displayCount);

  const handleFiles = async (selectedFiles) => {
    const filesArray = Array.from(selectedFiles);
    if (!filesArray.length) return;

    // Immediately add rows with "Processing" status
    const newEntries = filesArray.map((file, idx) => ({
      id: `${file.name}-${Date.now()}-${idx}-${Math.random().toString(36).substr(2, 5)}`,
      name: file.name,
      status: 'Processing',
      date: getCurrentTime(),
      confidence: '--',
      downloadUrl: null,
      previewData: null,
      error: null,
    }));
    setHistory((prev) => [...newEntries, ...prev]);
    setUploading(true);

    // Upload each file to the Python Flask backend
    const uploadPromises = filesArray.map(async (file, idx) => {
      const entryId = newEntries[idx].id;
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch(`${PYTHON_API_URL}/upload`, {
          method: 'POST',
          body: formData,
        });
        const data = await response.json();

        if (response.ok) {
          setHistory((prev) =>
            prev.map((item) => {
              if (item.id === entryId) {
                const updated = {
                  ...item,
                  status: 'Completed',
                  confidence: '✓ Extracted',
                  downloadUrl: `${PYTHON_API_URL}${data.download_url}`,
                  previewData: data.preview_data || [],
                  rawText: data.raw_text || '',
                  rules: data.rules || [],
                  error: null,
                };
                setSelectedId(entryId); // Auto-select the newly finished file
                return updated;
              }
              return item;
            })
          );
        } else {
          setHistory((prev) =>
            prev.map((item) =>
              item.id === entryId
                ? { ...item, status: 'Error', confidence: '--', error: data.error || 'Processing failed' }
                : item
            )
          );
        }
      } catch (err) {
        setHistory((prev) =>
          prev.map((item) =>
            item.id === entryId
              ? { ...item, status: 'Error', confidence: '--', error: 'Cannot reach ETL server on port 5000' }
              : item
          )
        );
      }
    });

    await Promise.all(uploadPromises);
    setUploading(false);
  };


  return (
    <div className="page-container animate-fade-in">
      <h1 style={{ fontSize: '1.875rem', fontWeight: 800, color: '#0f172a', marginBottom: '3rem' }}>Document Processing</h1>

      {/* Upload Zone */}
      <div className="upload-card">
        <p style={{ fontSize: '0.875rem', fontWeight: 700, color: '#1e293b', marginBottom: '1.5rem' }}>Upload Documents</p>
        <div
          className="dashed-dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); handleFiles(e.dataTransfer.files); }}
          onClick={() => fileInputRef.current.click()}
          style={{ cursor: uploading ? 'not-allowed' : 'pointer', opacity: uploading ? 0.6 : 1 }}
        >
          <div className="upload-icon-circle">
            {uploading ? (
              <RefreshCcw size={24} color="#2563eb" style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <Upload size={24} color="#2563eb" />
            )}
          </div>
          <p style={{ fontSize: '1rem', fontWeight: 700, color: '#1e293b', marginBottom: '0.5rem' }}>
            {uploading ? 'Processing files via ETL engine...' : 'Drop PDF / Image files here to extract data'}
          </p>
          <p style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Sends files to the Python Flask ETL server on port 5000 · Up to 16MB
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginTop: '1.5rem' }}>
            <button className="btn-primary" style={{ background: '#2563eb', padding: '10px 24px' }} disabled={uploading} onClick={() => fileInputRef.current.click()}>
              Browse Files
            </button>
            <button className="btn-primary" onClick={onClearHistory} style={{ background: '#ef4444', padding: '10px 24px' }} disabled={uploading}>
              Clear History
            </button>
          </div>
          <input
            type="file" multiple accept=".pdf,.jpg,.jpeg,.png" ref={fileInputRef}
            style={{ display: 'none' }}
            disabled={uploading}
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
      </div>

      {/* History Table */}
      {/* History Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['All', 'Completed', 'Processing', 'Error'].map(status => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              style={{
                padding: '6px 12px',
                borderRadius: '20px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s',
                background: filterStatus === status ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                color: filterStatus === status ? 'white' : 'var(--text-secondary)',
                border: '1px solid',
                borderColor: filterStatus === status ? 'var(--accent-primary)' : 'var(--border)'
              }}
            >
              {status}
            </button>
          ))}
        </div>
        
        <div style={{ display: 'flex', gap: '12px' }}>
          <div className="search-box">
            <Search size={16} color="#94a3b8" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button 
            className="btn-link" 
            style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-primary)' }}
            onClick={() => setShowAll(!showAll)}
          >
            {showAll ? 'Show Recent' : `View All (${filtered.length})`}
          </button>
        </div>
      </div>

      <div className="upload-card" style={{ padding: 0, overflow: 'hidden' }}>
        {filtered.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
            <FileText size={40} style={{ marginBottom: '1rem', opacity: 0.4 }} />
            <p style={{ fontWeight: 600 }}>No files processed yet.</p>
            <p style={{ fontSize: '0.8rem' }}>Upload a PDF or image above to begin.</p>
          </div>
        ) : (
          <table className="history-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>Timestamp</th>
                <th>Result</th>
                <th style={{ textAlign: 'right' }}>Download</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((file) => (
                <tr 
                  key={file.id} 
                  className={`table-row-hover ${selectedId === file.id ? 'selected-row' : ''}`}
                  onClick={() => file.status === 'Completed' && setSelectedId(file.id)}
                  style={{ cursor: file.status === 'Completed' ? 'pointer' : 'default' }}
                >
                  <td>
                    <div className="filename-cell">
                      <FileText size={18} color={selectedId === file.id ? '#2563eb' : '#64748b'} />
                      {file.name}
                    </div>
                  </td>
                  <td>
                    <span className={`status-badge ${file.status.toLowerCase()}`}>
                      {file.status === 'Processing' ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <RefreshCcw size={12} style={{ animation: 'spin 1s linear infinite' }} />
                          Processing
                        </span>
                      ) : file.status}
                    </span>
                  </td>
                  <td>{file.date}</td>
                  <td>
                    {file.error ? (
                      <span style={{ color: '#ef4444', fontSize: '0.75rem' }}>{file.error}</span>
                    ) : (
                      <strong style={{ color: '#1e293b' }}>{file.confidence}</strong>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {file.downloadUrl ? (
                      <a
                        href={file.downloadUrl}
                        download={file.name.replace('.jpeg', '').replace('.jpg', '') + '.xlsx'}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => console.log('Downloading from:', file.downloadUrl)}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '6px',
                          padding: '6px 14px', borderRadius: '8px', fontSize: '0.75rem',
                          fontWeight: 700, background: '#10b981', color: 'white',
                          textDecoration: 'none', transition: 'opacity 0.2s'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.opacity = '0.8'}
                        onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
                      >
                        <FileSpreadsheet size={14} />
                        Download Excel
                      </a>
                    ) : (
                      <ChevronRight size={18} color="#94a3b8" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Multi-File Preview Section */}
      {(() => {
        const completedFiles = history.filter(f => f.rawText).slice(0, 5);
        if (completedFiles.length === 0) return null;

        return (
          <div className="animate-fade-in" style={{ marginTop: '3rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.5rem', color: '#1e293b', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Activity size={20} color="#2563eb" />
              Latest Extraction Results ({completedFiles.length})
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {completedFiles.map(file => (
                <div key={file.id} style={{ 
                  border: selectedId === file.id ? '2px solid #2563eb' : '1px solid #e2e8f0',
                  borderRadius: '20px',
                  overflow: 'hidden',
                  background: 'white',
                  boxShadow: selectedId === file.id ? '0 10px 25px -5px rgba(37, 99, 235, 0.1)' : '0 4px 6px -1px rgba(0,0,0,0.05)'
                }}>
                  <div style={{ padding: '1.25rem 1.5rem', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <FileText size={18} color="#2563eb" />
                      <span style={{ fontWeight: 700, color: '#1e293b' }}>{file.name}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <a href={file.downloadUrl} download target="_blank" rel="noopener noreferrer" className="btn-primary" style={{ margin: 0, padding: '6px 14px', fontSize: '0.75rem', background: '#10b981' }}>
                        Download Excel
                      </a>
                    </div>
                  </div>
                  <div style={{ padding: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '1.5rem' }}>
                    {/* Raw Text Column */}
                    <div>
                      <p style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', marginBottom: '0.75rem', textTransform: 'uppercase' }}>Layout-Aware Text</p>
                      <div style={{ 
                        background: '#1e293b', 
                        color: '#e2e8f0',
                        padding: '15px', 
                        borderRadius: '10px', 
                        maxHeight: '250px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap',
                        fontSize: '0.75rem',
                        lineHeight: '1.5',
                        fontFamily: 'monospace'
                      }}>
                        {file.rawText}
                      </div>
                    </div>
                    {/* Table Column */}
                    <div>
                      <p style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', marginBottom: '0.75rem', textTransform: 'uppercase' }}>Extracted Rows Preview</p>
                      <div style={{ overflowX: 'auto', maxHeight: '250px' }}>
                        {file.previewData && file.previewData.length > 0 ? (
                          <table className="history-table" style={{ fontSize: '0.75rem' }}>
                            <thead>
                              <tr>{Object.keys(file.previewData[0]).map(k => <th key={k}>{k}</th>)}</tr>
                            </thead>
                            <tbody>
                              {file.previewData.map((row, i) => (
                                <tr key={i}>{Object.keys(file.previewData[0]).map(k => <td key={k}>{row[k] ?? '—'}</td>)}</tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '10px' }}>
                            No tabular data extracted.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
};


const RulesPage = ({ history, selectedId, setSelectedId, onUpdateRule, onApplyRules, onClearHistory, loading }) => {
  const [ruleSearch, setRuleSearch] = useState('');
  const selectedFile = history.find(f => f.id === selectedId) || history.find(f => f.rules);
  const rules = selectedFile?.rules || [];

  const filteredDocs = history.filter(f => f.rules && f.name.toLowerCase().includes(ruleSearch.toLowerCase()));

  return (
    <div className="page-container" style={{ maxWidth: '1400px' }}>
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'var(--accent-primary)', p: '10px', borderRadius: '12px' }}>
            <Settings size={28} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Rule Engine Config</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Tailor the extraction logic for each document signature.</p>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '2rem', height: 'calc(100vh - 250px)' }}>
        {/* Sidebar: File List */}
        <div className="glass-panel" style={{ padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', padding: '0 0.5rem' }}>
             <p style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', margin: 0 }}>Documents</p>
             <button onClick={onClearHistory} style={{ background: 'none', border: 'none', color: '#ef4444', fontSize: '0.65rem', fontWeight: 700, cursor: 'pointer' }}>CLEAR</button>
          </div>
          
          <div className="search-box" style={{ marginBottom: '1rem', background: 'var(--bg-tertiary)' }}>
            <Search size={14} color="#94a3b8" />
            <input
              type="text"
              placeholder="Filter bills..."
              value={ruleSearch}
              onChange={(e) => setRuleSearch(e.target.value)}
              style={{ fontSize: '0.75rem' }}
            />
          </div>

          {filteredDocs.map(file => (
            <div 
              key={file.id} 
              onClick={() => setSelectedId(file.id)}
              style={{ 
                padding: '12px 16px', borderRadius: '12px', cursor: 'pointer',
                background: selectedId === file.id ? 'var(--accent-primary)' : 'transparent',
                color: selectedId === file.id ? 'white' : 'var(--text-primary)',
                transition: 'all 0.2s', border: '1px solid',
                borderColor: selectedId === file.id ? 'var(--accent-primary)' : 'transparent'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileText size={16} />
                <span style={{ fontSize: '0.85rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{file.name}</span>
              </div>
              <div style={{ fontSize: '0.65rem', opacity: 0.8, marginTop: '4px' }}>{file.rules.length} extraction rules</div>
            </div>
          ))}
          {history.filter(f => f.rules).length === 0 && (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>
              No bills processed yet.
            </div>
          )}
        </div>

        {/* Content: Editable Rules Table */}
        <div className="glass-panel" style={{ padding: '0', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {selectedFile ? (
            <>
              <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', background: 'var(--bg-tertiary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>{selectedFile.name} Ruleset</h3>
                  <p style={{ fontSize: '0.75rem', color: '#64748b' }}>Edits are saved locally and applied to future exports.</p>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button 
                    className="btn-primary" 
                    disabled={loading}
                    style={{ margin: 0, padding: '8px 16px', fontSize: '0.75rem', opacity: loading ? 0.7 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
                    onClick={() => onApplyRules(selectedFile.id)}
                  >
                    {loading ? 'Applying...' : 'Apply All'}
                  </button>
                </div>
              </div>
              <div style={{ overflowX: 'auto', overflowY: 'auto', flex: 1 }}>
                <table className="history-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
                    <tr>
                      <th style={{ width: '80px' }}>ID</th>
                      <th style={{ width: '150px' }}>Field Name</th>
                      <th>Sample Content / Target</th>
                      <th style={{ width: '120px' }}>Datatype</th>
                      <th style={{ width: '80px' }}>Row</th>
                      <th style={{ width: '100px' }}>Section</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rules.map((rule, idx) => (
                      <tr key={idx} className="table-row-hover">
                        <td style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--accent-primary)' }}>{rule["Rule ID"]}</td>
                        <td>
                          <input 
                            value={rule["Field Name"]} 
                            onChange={(e) => onUpdateRule(selectedFile.id, idx, "Field Name", e.target.value)}
                            style={{ width: '100%', background: 'transparent', border: 'none', color: 'inherit', fontWeight: 700, fontSize: '0.875rem' }}
                          />
                        </td>
                        <td>
                          <input 
                            value={rule["Sample Text"]} 
                            onChange={(e) => onUpdateRule(selectedFile.id, idx, "Sample Text", e.target.value)}
                            style={{ width: '100%', background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: '4px', padding: '4px 8px', fontSize: '0.8rem' }}
                          />
                        </td>
                        <td>
                          <select 
                            value={rule["Field Datatype"]} 
                            onChange={(e) => onUpdateRule(selectedFile.id, idx, "Field Datatype", e.target.value)}
                            style={{ width: '100%', background: 'transparent', border: 'none', fontSize: '0.75rem' }}
                          >
                            <option>Alphanumeric</option>
                            <option>Numeric</option>
                            <option>Date</option>
                          </select>
                        </td>
                        <td>{rule["Row"]}</td>
                        <td style={{ fontSize: '0.7rem' }}>
                          <span className="status-badge processing" style={{ padding: '2px 6px' }}>{rule["Section"]}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
              <Settings size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
              <p>Select a document to manage its rules</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ExcelsPage = ({ history, onClearHistory }) => {
  // Be more inclusive: show anything that has a download link or is marked successful
  const successfulFiles = history.filter(f => 
    (f.status?.toLowerCase() === 'completed' || f.downloadUrl) && !f.error
  );
  const [search, setSearch] = useState('');
  
  const filteredExcels = successfulFiles.filter(f => f.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="page-container" style={{ maxWidth: '1200px' }}>
      <div className="page-header" style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: '#10b981', p: '10px', borderRadius: '12px' }}>
            <FileSpreadsheet size={28} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Master Excel Repository</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Access and download all processed document exports.</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '15px' }}>
           <div className="search-box" style={{ width: '250px' }}>
              <Search size={16} color="#94a3b8" />
              <input 
                placeholder="Search excels..." 
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
           </div>
           <button className="btn-primary" onClick={onClearHistory} style={{ background: '#ef4444' }}>Clear Storage</button>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
        {filteredExcels.length > 0 ? (
          <table className="history-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Export Filename</th>
                <th>Processing Time</th>
                <th>Data Quality</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredExcels.map((file) => (
                <tr key={file.id} className="table-row-hover">
                  <td>
                    <div className="filename-cell">
                      <FileSpreadsheet size={20} color="#10b981" />
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{file.name}</div>
                        <div style={{ fontSize: '0.7rem', color: '#64748b' }}>.xlsx OpenXML Format</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#64748b' }}>{file.date}</td>
                  <td>
                    <span className="status-badge completed" style={{ background: '#ecfdf5', color: '#059669', border: '1px solid #10b98133' }}>
                      {file.confidence}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <a 
                      href={file.downloadUrl} 
                      download 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn-primary"
                      style={{ 
                        margin: 0, padding: '8px 16px', fontSize: '0.75rem', 
                        background: '#10b981', color: 'white', textDecoration: 'none',
                        display: 'inline-flex', alignItems: 'center', gap: '8px'
                      }}
                    >
                      <Download size={14} />
                      Download Final
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '60px', textAlign: 'center' }}>
            <div style={{ width: '64px', height: '64px', background: 'var(--bg-tertiary)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
              <Search size={32} color="#94a3b8" />
            </div>
            <h3>No Excel Files Found</h3>
            <p style={{ color: 'var(--text-secondary)' }}>
              {search ? `No results matching "${search}"` : 'Successfully process a document to see exports here.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// --- Refined Dashboard Components ---
const Sidebar = ({ activeTab, setActiveTab, user, onLogout }) => (
  <aside className="sidebar">
    <div className="sidebar-logo">
      <img src="/logo.png" alt="IntelliExtract Logo" className="sidebar-logo-img" />
    </div>

    <div className="sidebar-nav">
      <NavItem active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} icon={<LayoutDashboard size={18} />} label="Dashboard" />
      <NavItem active={activeTab === 'processing'} onClick={() => setActiveTab('processing')} icon={<Layers size={18} />} label="Processing" />
      <NavItem active={activeTab === 'rules'} onClick={() => setActiveTab('rules')} icon={<Settings size={18} />} label="Rules" />
      <NavItem active={activeTab === 'excels'} onClick={() => setActiveTab('excels')} icon={<FileSpreadsheet size={18} />} label="Excels" />
    </div>

    <div style={{ marginTop: '2rem' }}>
      <p className="sidebar-section-label">Data Assets</p>
      <div className="nav-item">
        <FileSpreadsheet size={18} color="#059669" />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span>Rules.xlsx</span>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Central Config</span>
        </div>
      </div>
      <div className="nav-item">
        <FileSpreadsheet size={18} color="#4f46e5" />
        <span>Main.xlsx</span>
      </div>
    </div>

    <div style={{ marginTop: 'auto' }}>
      <div className="user-profile" style={{ padding: '1rem', background: 'var(--bg-tertiary)', borderRadius: '12px', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '12px', border: '1px solid var(--border)' }}>
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 700, fontSize: '0.8rem', flexShrink: 0 }}>
          {user?.name?.[0]?.toUpperCase() || 'U'}
        </div>
        <div style={{ overflow: 'hidden' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{user?.name}</div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{user?.email}</div>
        </div>
      </div>
      <button className="nav-item" style={{ width: '100%', background: 'none', border: 'none', color: '#ef4444', marginBottom: 0, paddingLeft: '12px' }} onClick={onLogout}>
        <LogOut size={18} />
        <span>Logout</span>
      </button>
    </div>
  </aside>
);

const NavItem = ({ active, onClick, icon, label }) => (
  <div className={`nav-item ${active ? 'active' : ''}`} onClick={onClick}>
    {icon}
    <span>{label}</span>
  </div>
);

const DashboardHero = ({ user }) => (
  <div style={{ marginBottom: '3rem' }}>
    <h1 style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.5rem', letterSpacing: '-0.02em' }}>
      Welcome back, {user?.name?.split(' ')[0]}!
    </h1>
    <p style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Monitor your document extraction pipeline and system performance.</p>
  </div>
);

const StatsGrid = ({ history }) => {
  const processed = history.filter(f => f.status === 'Completed').length;
  const rulesCount = history.reduce((acc, f) => acc + (f.rules?.length || 0), 0);
  
  return (
    <div className="stats-grid">
      <StatCard label="Processed Docs" value={processed.toLocaleString()} icon={<CheckCircle2 size={24} color="#059669" />} trend="+ New Data" />
      <StatCard label="Active Rules" value={rulesCount.toLocaleString()} icon={<Settings size={24} color="var(--accent-primary)" />} trend="Auto-generated" />
      <StatCard label="Pipeline Load" value={history.length > 0 ? "Optimal" : "Idle"} icon={<Layers size={24} color="#7c3aed" />} trend="High performance" />
      <StatCard label="System Status" value="Online" icon={<Zap size={24} color="#d97706" />} trend="All systems go" />
    </div>
  );
};

const StatCard = ({ label, value, icon, trend }) => (
  <div className="auth-card stat-card" style={{ maxWidth: 'none', padding: '24px', animation: 'none' }}>
    <div className="stat-header">
      <span className="stat-label">{label}</span>
      <div style={{ background: 'var(--bg-tertiary)', padding: '0.5rem', borderRadius: '10px' }}>
        {icon}
      </div>
    </div>
    <div className="stat-value">{value}</div>
    <div style={{ fontSize: '0.75rem', color: '#059669', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '0.75rem', fontWeight: 600 }}>
      {trend}
    </div>
  </div>
);

const RecentProcessingPreview = () => (
  <div className="auth-card" style={{ maxWidth: 'none', padding: '1.5rem', flex: 1, animation: 'none' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
      <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Recent Executions</h3>
      <button className="btn-link">View All</button>
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <MiniTableRow name="Invoice_Amazon.pdf" status="Completed" time="10m ago" />
      <MiniTableRow name="Utility_04_24.pdf" status="Completed" time="2h ago" />
      <MiniTableRow name="Cloud_Compute_Usage.pdf" status="Pending" time="5h ago" />
    </div>
  </div>
);

const MiniTableRow = ({ name, status, time }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-tertiary)' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
      <FileText size={16} color="var(--text-secondary)" />
      <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{name}</span>
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{time}</span>
      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: status === 'Completed' ? '#10b981' : '#f59e0b' }} />
    </div>
  </div>
);

const RecentActivity = () => (
  <div className="auth-card" style={{ maxWidth: 'none', padding: '1.5rem', animation: 'none' }}>
    <h3 style={{ marginBottom: '1.5rem', fontSize: '1.1rem', fontWeight: 700 }}>System Pipeline</h3>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <ActivityItem icon={<Database size={14} />} title="Batch extraction started" time="12 mins ago" />
      <ActivityItem icon={<Settings size={14} />} title="Rule 'Vendor_Tax_ID' updated" time="2 hours ago" />
      <ActivityItem icon={<CheckCircle2 size={14} />} title="System maintenance complete" time="5 hours ago" />
    </div>
  </div>
);

const ActivityItem = ({ icon, title, time }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.5rem 0' }}>
    <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {icon}
    </div>
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{title}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{time}</div>
    </div>
  </div>
);

const PipelineVisualization = () => (
  <section className="pipeline-section">
    <h2 className="pipeline-title">File Processing Pipeline</h2>
    <div className="pipeline-container">
      <div className="pipeline-step">
        <div className="step-icon-wrapper">
          <FileText size={24} />
        </div>
        <span className="step-label">Input File</span>
      </div>

      <div className="pipeline-arrow">
        <ArrowRight size={24} />
      </div>

      <div className="pipeline-step">
        <div className="step-icon-wrapper">
          <RefreshCcw size={24} />
        </div>
        <span className="step-label">Convert to<br />.TXT</span>
      </div>

      <div className="pipeline-arrow">
        <ArrowRight size={24} />
      </div>

      <div className="pipeline-step">
        <div className="step-icon-wrapper">
          <FileSpreadsheet size={24} />
        </div>
        <span className="step-label">Generate<br />Rules.XLSX</span>
      </div>

      <div className="pipeline-arrow">
        <ArrowRight size={24} />
      </div>

      <div className="pipeline-step">
        <div className="step-icon-wrapper">
          <Database size={24} />
        </div>
        <span className="step-label">Generate<br />Main.XLSX</span>
      </div>
    </div>
  </section>
);

const App = () => {
  const [step, setStep] = useState('auth'); // auth, otp, dashboard
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isSignup, setIsSignup] = useState(true);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [toast, setToast] = useState(null);
  const [resendCooldown, setResendCooldown] = useState(0);

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: ''
  });

  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const otpRefs = useRef([]);

  // --- Persistent History Loading ---
  useEffect(() => {
    const savedHistory = localStorage.getItem('processing_history');
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory);
        setHistory(parsed);
        if (parsed.length > 0 && !selectedId) setSelectedId(parsed[0].id);
      } catch (e) {
        console.error("Failed to load history", e);
      }
    }
  }, []);

  // --- Persistent History Saving ---
  useEffect(() => {
    if (history.length > 0) {
      localStorage.setItem('processing_history', JSON.stringify(history));
    }
  }, [history]);

  const handleUpdateRule = (fileId, ruleIdx, field, value) => {
    setHistory(prev => prev.map(file => {
      if (file.id === fileId) {
        const newRules = [...file.rules];
        newRules[ruleIdx] = { ...newRules[ruleIdx], [field]: value };
        return { ...file, rules: newRules };
      }
      return file;
    }));
  };

  const handleApplyRules = async (fileId) => {
    const file = history.find(f => f.id === fileId);
    if (!file || !file.rules) return;

    setLoading(true);
    try {
      const response = await fetch(`${PYTHON_API_URL}/reprocess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raw_text: file.rawText,
          rules: file.rules,
          filename: file.name
        }),
      });

      const data = await response.json();
      if (response.ok) {
        setHistory(prev => prev.map(f => f.id === fileId ? {
          ...f,
          previewData: data.preview_data,
          downloadUrl: `${PYTHON_API_URL}${data.download_url}`
        } : f));
        showToast(`Rules applied and data re-extracted for ${file.name}`, 'success');
      } else {
        throw new Error(data.error || 'Reprocessing failed');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = () => {
    if (window.confirm("Are you sure you want to clear all processing history? This action cannot be undone.")) {
      setHistory([]);
      setSelectedId(null);
      localStorage.removeItem('processing_history');
      showToast("History cleared successfully", "success");
    }
  };

  // Auto-hide toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const showToast = (message, type = 'error') => {
    setToast({ message, type });
  };

  const validateEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const validatePassword = (pass) => {
    const hasUpper = /[A-Z]/.test(pass);
    const hasNumber = /[0-9]/.test(pass);
    return pass.length >= 8 && hasUpper && hasNumber;
  };

  const handleAuthSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();

    if (isSignup && !formData.name) return showToast('Please enter your full name');
    if (!validateEmail(formData.email)) return showToast('Please enter a valid email address');

    if (isSignup && !validatePassword(formData.password)) {
      return showToast('Password must be 8+ characters with 1 uppercase and 1 number');
    }

    setLoading(true);
    try {
      const endpoint = isSignup ? '/api/signup' : '/api/signin';
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (response.ok) {
        showToast(data.message, 'success');
        setStep('otp');
        setResendCooldown(30);
      } else {
        showToast(data.error);
      }
    } catch (error) {
      showToast('Connection failed. Is the server running?');
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = (index, value) => {
    if (isNaN(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value.substring(value.length - 1);
    setOtp(newOtp);

    // Focus next
    if (value && index < 5) {
      otpRefs.current[index + 1].focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1].focus();
    }
  };

  const handleOtpVerify = async () => {
    const otpString = otp.join('');
    if (otpString.length < 6) return showToast('Please enter the full 6-digit code');

    setLoading(true);
    try {
      const endpoint = isSignup ? '/api/verify-signup' : '/api/verify-signin';
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: formData.email, otp: otpString })
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('token', data.token);
        setUser(data.user);
        setStep('dashboard');
        showToast('Login successful', 'success');
      } else {
        showToast(data.error);
      }
    } catch (error) {
      showToast('Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setStep('auth');
    setUser(null);
    setFormData({ name: '', email: '', password: '' });
    setOtp(['', '', '', '', '', '']);
  };

  // --- Real Google One Tap & Account Native Logic (Optimized for Speed) ---
  useEffect(() => {
    const initializeGoogle = () => {
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: "1065332449181-mcu8s35ddeugnsfb4q1vhsqqe94lt3n1.apps.googleusercontent.com",
          callback: handleGoogleCallback,
          auto_select: true,
          cancel_on_tap_outside: false
        });

        const googleBtnEl = document.getElementById("googleButton");
        if (googleBtnEl) {
          window.google.accounts.id.renderButton(googleBtnEl, {
            theme: "outline",
            size: "large",
            width: "200",
            shape: "pill",
            text: "continue_with"
          });
        }
        window.google.accounts.id.prompt();
        return true; // Successfully initialized
      }
      return false;
    };

    // Immediate check + Fast polling fallback
    if (!initializeGoogle()) {
      const interval = setInterval(() => {
        if (initializeGoogle()) clearInterval(interval);
      }, 100);
      return () => clearInterval(interval);
    }
  }, []);

  const handleGoogleCallback = async (response) => {
    setLoading(true);
    try {
      // Strictly verify this REAL Google credential on our backend
      const res = await fetch(`${API_URL}/api/google-verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: response.credential })
      });

      if (!res.ok) throw new Error('Verification failed');
      const data = await res.json();

      localStorage.setItem('token', data.token);
      setUser(data.user);
      setStep('dashboard');
      showToast(`Automatically signed in as ${data.user.email}`, 'success');
    } catch (error) {
      showToast('Google identity verification failed.');
    } finally {
      setLoading(false);
    }
  };

  // --- Strict Session Verification ---
  useEffect(() => {
    const checkSession = async () => {
      const token = localStorage.getItem('token');
      if (step === 'dashboard' && token) {
        try {
          const response = await fetch(`${API_URL}/api/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (!response.ok) throw new Error('Invalid session');
          const data = await response.json();
          setUser(data.user);
        } catch (err) {
          handleLogout();
          showToast('Session expired or invalid. Please sign in again.');
        }
      }
    };
  checkSession();
  }, [step]);

  const videoRef = useRef(null);

  // --- Ghost Listener Audio System ---
  useEffect(() => {
    const unlockAudio = async () => {
      if (videoRef.current && step !== 'dashboard') {
        try {
          videoRef.current.muted = false;
          await videoRef.current.play();
          // If successful, stop listening
          window.removeEventListener('mousemove', unlockAudio);
          window.removeEventListener('mousedown', unlockAudio);
          window.removeEventListener('keydown', unlockAudio);
        } catch (e) {
          // Keep muted if browser still blocks
          videoRef.current.muted = true;
          videoRef.current.play();
        }
      }
    };

    window.addEventListener('mousemove', unlockAudio, { once: true });
    window.addEventListener('mousedown', unlockAudio, { once: true });
    window.addEventListener('keydown', unlockAudio, { once: true });

    return () => {
      window.removeEventListener('mousemove', unlockAudio);
      window.removeEventListener('mousedown', unlockAudio);
      window.removeEventListener('keydown', unlockAudio);
    };
  }, [step]);

  return (
    <div className="app-root">
      {step === 'dashboard' ? (
        <div className="dashboard-root">
          <video
            autoPlay
            muted
            loop
            playsInline
            className="app-bg-video"
          >
            <source src="/background.mp4" type="video/mp4" />
          </video>

          <Sidebar
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            user={user}
            onLogout={handleLogout}
          />
          <main className="main-content">
            <AnimatePresence mode="wait">
              {activeTab === 'dashboard' && (
                <motion.div
                  key="dashboard-view"
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{ duration: 0.2 }}
                >
                  <DashboardHero user={user} />
                  <PipelineVisualization />
                  <StatsGrid history={history} />
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
                    <RecentProcessingPreview />
                    <RecentActivity />
                  </div>
                </motion.div>
              )}

              {activeTab === 'processing' && (
                <motion.div
                  key="processing-view"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <ProcessingPage 
                    history={history} 
                    setHistory={setHistory} 
                    selectedId={selectedId} 
                    setSelectedId={setSelectedId} 
                    onClearHistory={handleClearHistory}
                  />
                </motion.div>
              )}

              {activeTab === 'rules' && (
                <motion.div
                  key="rules-view"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <RulesPage 
                    history={history} 
                    selectedId={selectedId} 
                    setSelectedId={setSelectedId} 
                    onUpdateRule={handleUpdateRule}
                    onApplyRules={handleApplyRules}
                    onClearHistory={handleClearHistory}
                    loading={loading}
                  />
                </motion.div>
              )}

              {activeTab === 'excels' && (
                <motion.div
                  key="excels-view"
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{ duration: 0.2 }}
                >
                  <ExcelsPage 
                    history={history} 
                    onClearHistory={handleClearHistory}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </main>
        </div>
      ) : (
        <div className="auth-split-container">
          <div className="auth-visual-panel">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              className="auth-split-video"
              onEnded={(e) => {
                e.target.muted = true;
                e.target.play();
              }}
            >
              <source src="/IMG_6445.MP4" type="video/mp4" />
            </video>
            <div className="auth-split-overlay" />
          </div>

          <div className="auth-form-panel">
            {toast && (
              <div className={toast.type === 'error' ? 'error-popup' : 'success-popup'}>
                {toast.type === 'error' ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
                {toast.message}
              </div>
            )}

            <div className="auth-card" style={{ maxWidth: '400px', boxShadow: 'none', background: 'transparent' }}>
              <div className="auth-header">
                <img src="/logo.png" alt="IntelliExtract logo" className="auth-logo-img" />
                <h1 className="auth-title">
                  {step === 'auth' ? (isSignup ? 'Create Account' : 'Welcome Back') : 'Verify Email'}
                </h1>
                <p className="auth-subtitle">
                  {step === 'auth'
                    ? (isSignup ? 'Start your automated extraction journey' : 'Access your dashboard securely')
                    : `We've sent a 6-digit code to ${formData.email}`}
                </p>
              </div>

              {step === 'auth' && (
                <>
                  <div className="auth-toggle">
                    <button
                      className={!isSignup ? 'active' : ''}
                      onClick={() => setIsSignup(false)}
                    >
                      Sign In
                    </button>
                    <button
                      className={isSignup ? 'active' : ''}
                      onClick={() => setIsSignup(true)}
                    >
                      Sign Up
                    </button>
                  </div>

                  <form onSubmit={handleAuthSubmit}>
                    {isSignup && (
                      <div className="input-group">
                        <label className="input-label">Full Name</label>
                        <div className="input-wrapper">
                          <User className="input-icon" size={18} />
                          <input
                            type="text"
                            className="input-field"
                            placeholder="John Doe"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          />
                        </div>
                      </div>
                    )}

                    <div className="input-group">
                      <label className="input-label">Email Address</label>
                      <div className="input-wrapper">
                        <Mail className="input-icon" size={18} />
                        <input
                          type="email"
                          className="input-field"
                          placeholder="name@company.com"
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        />
                      </div>
                    </div>

                    <div className="input-group">
                      <label className="input-label">Password</label>
                      <div className="input-wrapper">
                        <Lock className="input-icon" size={18} />
                        <input
                          type={showPassword ? 'text' : 'password'}
                          className="input-field"
                          placeholder="••••••••"
                          value={formData.password}
                          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        />
                        <div className="password-toggle" onClick={() => setShowPassword(!showPassword)}>
                          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </div>
                      </div>
                    </div>

                    <div className="auth-actions-row">
                      <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? '...' : (isSignup ? 'Create Account' : 'Continue')}
                      </button>
                      <div id="googleButton"></div>
                    </div>
                  </form>
                </>
              )}

              {step === 'otp' && (
                <div style={{ animation: 'slideUp 0.4s ease' }}>
                  <div className="otp-inputs">
                    {otp.map((digit, index) => (
                      <input
                        key={index}
                        ref={(el) => (otpRefs.current[index] = el)}
                        type="text"
                        maxLength="1"
                        className="otp-field"
                        value={digit}
                        onChange={(e) => handleOtpChange(index, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(index, e)}
                        autoFocus={index === 0}
                      />
                    ))}
                  </div>

                  <button
                    className="btn-primary"
                    onClick={handleOtpVerify}
                    disabled={loading}
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                  >
                    {loading ? 'Verifying...' : (
                      <>
                        Verify & Continue
                        <ArrowRight size={18} />
                      </>
                    )}
                  </button>

                  <div className="resend-timer">
                    Didn't receive the code? {' '}
                    <span
                      className={`resend-link ${resendCooldown > 0 ? 'disabled' : ''}`}
                      onClick={() => handleAuthSubmit()}
                    >
                      {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend Code'}
                    </span>
                  </div>

                  <p
                    onClick={() => setStep('auth')}
                    style={{ textAlign: 'center', marginTop: '24px', fontSize: '14px', color: '#64748b', cursor: 'pointer' }}
                  >
                    Back to registration
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
