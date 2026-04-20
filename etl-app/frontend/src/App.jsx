import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { 
  LayoutDashboard, 
  FileText, 
  Settings, 
  FileSpreadsheet, 
  Upload, 
  Play, 
  LogOut,
  CheckCircle,
  AlertCircle,
  Loader
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

// --- Components ---

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const handleLogout = () => {
    localStorage.removeItem("isLoggedIn");
    navigate("/login");
  };

  const menuItems = [
    { name: 'Dashboard', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Processing', path: '/processing', icon: <FileText size={20} /> },
    { name: 'Rules', path: '/rules', icon: <Settings size={20} /> },
    { name: 'Excels', path: '/excels', icon: <FileSpreadsheet size={20} /> },
  ];

  return (
    <div className="sidebar">
      <h2>ETL Billing</h2>
      <nav>
        {menuItems.map(item => (
          <Link 
            key={item.path} 
            to={item.path} 
            className={location.pathname === item.path ? 'active' : ''}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {item.icon} {item.name}
            </span>
          </Link>
        ))}
      </nav>
      <button onClick={handleLogout} className="btn" style={{ marginTop: 'auto', background: 'transparent', color: '#cbd5e1', textAlign: 'left', padding: '10px 15px' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <LogOut size={20} /> Logout
        </span>
      </button>
    </div>
  );
};

const Login = () => {
  const [pass, setPass] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    localStorage.setItem("isLoggedIn", "true");
    navigate("/");
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#1e293b' }}>
      <form onSubmit={handleLogin} className="card" style={{ width: '300px' }}>
        <h2 style={{ textAlign: 'center' }}>Login</h2>
        <input 
          type="password" 
          placeholder="Password (any)" 
          className="btn" 
          style={{ width: '100%', marginBottom: '15px', border: '1px solid #ddd', boxSizing: 'border-box' }}
          onChange={(e) => setPass(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Enter Dashboard</button>
      </form>
    </div>
  );
};

const Dashboard = () => {
  const [stats, setStats] = useState({ uploaded: 0, processed: 0, rules: 0 });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [filesRes, rulesRes] = await Promise.all([
          axios.get(`${API_BASE}/files`),
          axios.get(`${API_BASE}/rules`)
        ]);
        setStats({
          uploaded: filesRes.data.uploaded.length,
          processed: filesRes.data.processed.length,
          rules: rulesRes.data.length
        });
      } catch (err) { console.error(err); }
    };
    fetchStats();
  }, []);

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="stats-grid">
        <div className="stat-card"><h3>{stats.uploaded}</h3><p>Uploaded Files</p></div>
        <div className="stat-card"><h3>{stats.processed}</h3><p>Processed Bills</p></div>
        <div className="stat-card"><h3>{stats.rules}</h3><p>Active Rules</p></div>
      </div>
      
      <div className="card">
        <h3>Pipeline Status</h3>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px', position: 'relative' }}>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: '#2563eb', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>1</div>
            <p>Upload</p>
          </div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: stats.processed > 0 ? '#2563eb' : '#e2e8f0', color: stats.processed > 0 ? 'white' : '#64748b', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>2</div>
            <p>Process</p>
          </div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: stats.processed > 0 ? '#2563eb' : '#e2e8f0', color: stats.processed > 0 ? 'white' : '#64748b', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>3</div>
            <p>Output</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const Processing = () => {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    const res = await axios.get(`${API_BASE}/files`);
    setFiles(res.data.uploaded);
  };

  const handleUpload = async (e) => {
    const formData = new FormData();
    Array.from(e.target.files).forEach(f => formData.append("files", f));
    await axios.post(`${API_BASE}/upload`, formData);
    fetchFiles();
  };

  const handleProcess = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/process`);
      setResults(res.data.results);
    } catch (err) { alert(err.response?.data?.detail || "Processing failed"); }
    setLoading(false);
  };

  return (
    <div>
      <h1>File Processing</h1>
      <div className="grid-3">
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <input type="file" multiple onChange={handleUpload} style={{ display: 'none' }} id="file-upload" />
            <label htmlFor="file-upload" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <Upload size={18} /> Upload Files
            </label>
            <button className="btn btn-primary" onClick={handleProcess} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {loading ? <Loader size={18} className="animate-spin" /> : <Play size={18} />} Process Files
            </button>
          </div>
          
          <h3>Files in Queue</h3>
          <table>
            <thead><tr><th>Filename</th><th>Status</th></tr></thead>
            <tbody>
              {files.map(f => (
                <tr key={f} onClick={() => setSelectedFile(f)} style={{ cursor: 'pointer' }}>
                  <td>{f}</td>
                  <td>Pending</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>Recent Processing</h3>
          {results.length === 0 ? <p>No files processed yet.</p> : (
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {results.map((r, i) => (
                <li key={i} style={{ marginBottom: '10px', padding: '10px', background: '#f8fafc', borderRadius: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {r.status.includes("Failed") ? <AlertCircle size={16} color="red" /> : <CheckCircle size={16} color="green" />}
                    <strong>{r.filename}</strong>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: '#64748b', margin: '5px 0 0' }}>{r.status}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {results.length > 0 && (
        <div className="card">
          <h3>Preview Section</h3>
          <div className="preview-container">
            <div className="preview-box">
              <h4>Input Preview</h4>
              <div style={{ height: '100%', overflow: 'hidden' }}>
                <iframe src={`${API_BASE}/previews/${results[0].filename}`} width="100%" height="300px" title="preview" />
              </div>
            </div>
            <div className="preview-box">
              <h4>Extracted Text</h4>
              <pre style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap', maxHeight: '300px', overflowY: 'auto' }}>
                {results[0].text}
              </pre>
            </div>
            <div className="preview-box">
              <h4>Rules Applied</h4>
              <p>Active Rules Found: {results[0].rules_applied}</p>
              <ul style={{ fontSize: '0.8rem' }}>
                {results[0].line_items.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
              {results[0].line_items.length === 0 && <p style={{ color: 'red' }}>No line items detected.</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const Rules = () => {
  const [rules, setRules] = useState([]);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    const res = await axios.get(`${API_BASE}/rules`);
    setRules(res.data);
  };

  const handleUpdate = async () => {
    await axios.post(`${API_BASE}/rules/update`, rules);
    alert("Rules saved!");
  };

  const handleChange = (index, field, value) => {
    const newRules = [...rules];
    newRules[index][field] = value;
    setRules(newRules);
  };

  const addRule = () => {
    setRules([...rules, { "Rule Name": "", "Pattern": "", "Description": "" }]);
  };

  return (
    <div>
      <h1>Extraction Rules</h1>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginBottom: '15px' }}>
          <button className="btn btn-primary" onClick={addRule}>+ Add Rule</button>
          <button className="btn btn-primary" onClick={handleUpdate}>Save Changes</button>
        </div>
        <table>
          <thead>
            <tr><th>Rule Name</th><th>Pattern</th><th>Description</th></tr>
          </thead>
          <tbody>
            {rules.map((rule, i) => (
              <tr key={i}>
                <td><input value={rule["Rule Name"]} onChange={(e) => handleChange(i, "Rule Name", e.target.value)} style={{ width: '100%', border: 'none', padding: '5px' }} /></td>
                <td><input value={rule["Pattern"]} onChange={(e) => handleChange(i, "Pattern", e.target.value)} style={{ width: '100%', border: 'none', padding: '5px' }} /></td>
                <td><input value={rule["Description"]} onChange={(e) => handleChange(i, "Description", e.target.value)} style={{ width: '100%', border: 'none', padding: '5px' }} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const Excels = () => {
  const [files, setFiles] = useState([]);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    const res = await axios.get(`${API_BASE}/excel`);
    setFiles(res.data);
  };

  return (
    <div>
      <h1>Generated Excel Files</h1>
      <div className="card">
        {files.length === 0 ? <p>No Excel files generated yet.</p> : (
          <table>
            <thead><tr><th>File Name</th><th>Action</th></tr></thead>
            <tbody>
              {files.map(f => (
                <tr key={f.name}>
                  <td>{f.name}</td>
                  <td>
                    <a href={`${API_BASE}${f.url}`} download className="btn btn-primary">Download</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// --- App Structure ---

const ProtectedRoute = ({ children }) => {
  const isLoggedIn = localStorage.getItem("isLoggedIn");
  return isLoggedIn ? children : <Login />;
};

const MainApp = () => {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={
          <ProtectedRoute>
            <div className="app-container">
              <Sidebar />
              <div className="main-content">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/processing" element={<Processing />} />
                  <Route path="/rules" element={<Rules />} />
                  <Route path="/excels" element={<Excels />} />
                </Routes>
              </div>
            </div>
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
};

export default MainApp;
