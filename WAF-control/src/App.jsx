import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './layout/Layout';
import Dashboard from './pages/Dashboard';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        {/* Route cha bọc Layout */}
        <Route path="/" element={<Layout />}>
          {/* Index route: Đường dẫn gốc "/" sẽ trỏ thẳng vào Dashboard */}
          <Route index path="dashboard" element={<Dashboard />} />

          {/* Về sau bạn tạo thêm file LiveTraffic.jsx, Settings.jsx thì cứ ném thêm Route vào đây */}
          {/* <Route path="live-traffic" element={<LiveTraffic />} /> */}
          {/* <Route path="settings" element={<Settings />} /> */}
        </Route>
      </Routes>
    </Router>
  );
}

export default App;