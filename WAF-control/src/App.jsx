import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Activity, LayoutDashboard, Settings, Server, ShieldCheck } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import './App.css';

function App() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/logs');
      setLogs(response.data.data);
      setLoading(false);
    } catch (error) {
      console.error("Lỗi khi tải dữ liệu:", error);
      setLoading(false);
    }
  };

  // --- XỬ LÝ DỮ LIỆU CHO BIỂU ĐỒ ---
  const passedCount = logs.filter(l => l.action === 'PASSED').length;
  const blockedCount = logs.filter(l => l.action === 'BLOCKED').length;

  // 1. Dữ liệu Biểu đồ Tròn (Allowed vs Blocked)
  const actionData = [
    { name: 'Allowed Requests', value: passedCount },
    { name: 'Blocked Requests', value: blockedCount }
  ];
  const COLORS = ['#2ed573', '#ff4757'];

  // 2. Dữ liệu Biểu đồ Cột (Top 5 IP)
  const ipCounts = {};
  logs.forEach(l => {
    ipCounts[l.client_ip] = (ipCounts[l.client_ip] || 0) + 1;
  });
  const topIpsData = Object.keys(ipCounts)
    .map(ip => ({ ip, count: ipCounts[ip] }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  return (
    <div className="dashboard-container">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="logo">
          <ShieldAlert color="#ff4757" size={32} />
          <h2>AI-WAF Pro</h2>
        </div>
        <nav className="nav-menu">
          <a href="#" className="nav-item active"><LayoutDashboard size={20} /> Dashboard</a>
          <a href="#" className="nav-item"><Activity size={20} /> Live Traffic</a>
          <a href="#" className="nav-item"><Server size={20} /> Assets Target</a>
          <a href="#" className="nav-item"><Settings size={20} /> Settings</a>
        </nav>
      </aside>

      {/* MAIN CONTENT */}
      <main className="main-content">
        <header className="header">
          <h1>Security Overview</h1>
          <div className="status-badge">
            <span className="pulse-dot"></span> System Active
          </div>
        </header>

        {/* THỐNG KÊ NHANH (KPI CARDS) */}
        <div className="stats-grid">
          <div className="stat-card">
            <h3>Tổng số Requests</h3>
            <p className="stat-number">{logs.length}</p>
          </div>
          <div className="stat-card">
            <h3>Bảo vệ thành công (Blocked)</h3>
            <p className="stat-number text-danger">{blockedCount}</p>
          </div>
          <div className="stat-card">
            <h3>Truy cập hợp lệ (Allowed)</h3>
            <p className="stat-number text-success">{passedCount}</p>
          </div>
        </div>

        {/* KHU VỰC BIỂU ĐỒ (CHARTS) */}
        <div className="charts-grid">
          <div className="chart-card">
            <h3>Allowed vs Blocked Requests</h3>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={actionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {actionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#161925', borderColor: '#282c44' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="chart-legend">
                <span style={{ color: '#2ed573' }}>● Allowed</span>
                <span style={{ color: '#ff4757' }}>● Blocked</span>
              </div>
            </div>
          </div>

          <div className="chart-card">
            <h3>Top 5 IP Truy Cập</h3>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topIpsData}>
                  <XAxis dataKey="ip" stroke="#8c92ac" fontSize={12} />
                  <YAxis stroke="#8c92ac" fontSize={12} allowDecimals={false} />
                  <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: '#161925', borderColor: '#282c44' }} />
                  <Bar dataKey="count" fill="#70a1ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* BẢNG DỮ LIỆU (DATA TABLE) */}
        <div className="table-container">
          <div className="table-header">
            <h2>Live Attack & Traffic Logs</h2>
          </div>
          {loading ? (
            <p className="loading-text">Đang đồng bộ dữ liệu...</p>
          ) : (
            <table className="threat-table">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>IP Client</th>
                  <th>Method</th>
                  <th>Đường dẫn (Path)</th>
                  <th>Loại Cảnh Báo</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {logs.slice(0, 15).map((log) => ( // Chỉ hiện 15 dòng mới nhất cho gọn
                  <tr key={log._id}>
                    <td>{new Date(log.timestamp).toLocaleString('vi-VN')}</td>
                    <td className="ip-cell">{log.client_ip}</td>
                    <td><span className={`method ${log.method.toLowerCase()}`}>{log.method}</span></td>
                    <td className="path-cell" title={log.raw_payload}>{log.path_accessed}</td>
                    <td>
                      {log.attack_type === 'None' ? (
                        <span style={{ color: '#8c92ac' }}>Safe Traffic</span>
                      ) : (
                        <span className={`engine-badge ${log.blocked_by_engine === 'Autoencoder' ? 'ae' : 'rf'}`}>
                          {log.attack_type}
                        </span>
                      )}
                    </td>
                    <td>
                      {log.action === 'PASSED' ? (
                        <span className="action-badge passed"><ShieldCheck size={14} /> ALLOWED</span>
                      ) : (
                        <span className="action-badge blocked"><ShieldAlert size={14} /> BLOCKED</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;