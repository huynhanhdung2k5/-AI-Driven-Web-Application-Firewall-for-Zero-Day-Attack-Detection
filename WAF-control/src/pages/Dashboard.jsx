import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Zap, Brain } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Sector } from 'recharts';

const Dashboard = () => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);


    // State để nhớ xem chuột đang trỏ vào miếng bánh số mấy
    // --- STATE CHO BIỂU ĐỒ 1: ALLOWED VS BLOCKED ---
    const [activeActionIndex, setActiveActionIndex] = useState(null);
    const onActionPieEnter = (_, index) => setActiveActionIndex(index);
    const onActionPieLeave = () => setActiveActionIndex(null);
    const [activeMethodIndex, setActiveMethodIndex] = useState(null);
    const onMethodPieEnter = (_, index) => setActiveMethodIndex(index);
    const onMethodPieLeave = () => setActiveMethodIndex(null);
    // --- STATE CHO BIỂU ĐỒ 2: HTTP VERSIONS ---
    const [activeHttpIndex, setActiveHttpIndex] = useState(null);
    const onHttpPieEnter = (_, index) => setActiveHttpIndex(index);
    const onHttpPieLeave = () => setActiveHttpIndex(null);


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

    const passedCount = logs.filter(l => l.action === 'PASSED').length;
    const blockedCount = logs.filter(l => l.action === 'BLOCKED').length;

    const actionData = [
        { name: 'Allowed Requests', value: passedCount },
        { name: 'Blocked Requests', value: blockedCount }
    ];
    const COLORS = ['#2ed573', '#ff4757'];

    const ipCounts = {};
    logs.forEach(l => {
        ipCounts[l.client_ip] = (ipCounts[l.client_ip] || 0) + 1;
    });
    const topIpsData = Object.keys(ipCounts)
        .map(ip => ({ ip, count: ipCounts[ip] }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);

    // --- 2. DATA MỚI CHO TOP HOST, USER-AGENT & HTTP VERSION ---
    const hostCounts = {};
    const uaCounts = {};
    const httpVerCounts = {};
    const methodCounts = {};
    const engineBlocks = { "Random Forest": 0, "Autoencoder": 0, "WebACL Rules": 0 };


    logs.forEach(l => {
        // Đếm Method
        const m = l.method || 'Unknown';
        methodCounts[m] = (methodCounts[m] || 0) + 1;

        // Đếm Engine chặn
        if (l.action === 'BLOCKED' || l.action === 'RATE LIMIT EXCEEDED') {
            const engine = l.blocked_by_engine || 'None';
            if (engineBlocks.hasOwnProperty(engine)) {
                engineBlocks[engine]++;
            }
        }
        const host = l.host || 'Unknown';
        const ua = l.user_agent || 'Unknown';
        // Hỗ trợ cả trường hợp bạn đặt tên biến là http_version hoặc http_versions
        const httpVer = l.http_versions || 'Unknown';

        hostCounts[host] = (hostCounts[host] || 0) + 1;
        uaCounts[ua] = (uaCounts[ua] || 0) + 1;
        httpVerCounts[httpVer] = (httpVerCounts[httpVer] || 0) + 1;
    });

    const topHostsData = Object.keys(hostCounts)
        .map(k => ({ name: k, count: hostCounts[k] }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);

    const topUaData = Object.keys(uaCounts)
        .map(k => ({ name: k, count: uaCounts[k] }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);

    const methodData = Object.keys(methodCounts).map(k => ({ name: k, value: methodCounts[k] }));
    // Gán cứng màu sắc cho từng loại Method (Đồng bộ với màu dưới bảng)
    const METHOD_COLORS_MAP = {
        'GET': '#2ed573',     // Xanh lá
        'POST': '#ffa502',    // Cam
        'PUT': '#3498db',     // Xanh dương
        'DELETE': '#ff4757',  // Đỏ
        'OPTIONS': '#9b59b6', // Tím
        'Unknown': '#8c92ac'  // Xám
    };
    const httpVersionData = Object.keys(httpVerCounts).map(k => ({ name: k, value: httpVerCounts[k] }));
    const HTTP_COLORS = ['#9b59b6', '#8c92ac', '#e67e22', '#2c3e50']; // Tông màu tím giống AWS WAF


    return (
        <main className="flex-1 p-7.5 overflow-y-auto">


            {/* THỐNG KÊ NHANH (KPI CARDS) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-7.5">
                <div className="bg-white p-5 rounded-[10px] border border-gray-50 shadow-md">
                    <h3 className="text-[14px] text-[#8c92ac] mb-2.5 uppercase font-semibold">Number of Requests</h3>
                    <p className="text-[32px] font-bold text-black">{logs.length}</p>
                </div>
                <div className="bg-white p-5 rounded-[10px] border border-gray-50 shadow-md">
                    <h3 className="text-[14px] text-[#8c92ac] mb-2.5 uppercase font-semibold">Number of Blocked Requests </h3>
                    <p className="text-[32px] font-bold text-black">{blockedCount}</p>
                </div>
                <div className="bg-white p-5 rounded-[10px] border border-gray-50 shadow-md">
                    <h3 className="text-[14px] text-[#8c92ac] mb-2.5 uppercase font-semibold">Number of Allowed Requests  </h3>
                    <p className="text-[32px] font-bold text-black">{passedCount}</p>
                </div>
            </div>

            {/* KHU VỰC BIỂU ĐỒ (CHARTS) */}
            <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-5 mb-7.5">
                <div className="bg-white p-5 rounded-[10px] border border-gray-50 shadow-md h-75 flex flex-col">
                    <h3 className="text-[16px] text-black mb-3.75 font-semibold">Allowed vs Blocked Requests</h3>
                    <div className="flex-1 w-full relative">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart onMouseLeave={onActionPieLeave}>
                                <Pie
                                    data={actionData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={50}
                                    outerRadius={75}
                                    paddingAngle={0}
                                    dataKey="value"
                                    stroke="none"
                                    /* Thay vì dùng activeShape, ta chỉ cần bắt sự kiện chuột */
                                    onMouseEnter={onActionPieEnter}
                                    onMouseLeave={onActionPieLeave}
                                >
                                    {actionData.map((entry, index) => {
                                        // Xác định xem miếng bánh nào đang được trỏ chuột vào
                                        const isActive = activeActionIndex === index;
                                        // Xác định các miếng bánh bị bỏ lại (để làm mờ)
                                        const isDimmed = activeActionIndex !== null && !isActive;

                                        return (
                                            <Cell
                                                key={`cell-${index}`}
                                                fill={COLORS[index % COLORS.length]}
                                                style={{
                                                    // 1. Chuyển động lụa là trong 0.3s cho tất cả hiệu ứng
                                                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',

                                                    // 2. Làm mờ các miếng không được chọn
                                                    opacity: isDimmed ? 0.3 : 1,

                                                    // 3. Đổ bóng và làm sáng miếng đang chọn
                                                    filter: isActive ? 'drop-shadow(0px 8px 16px rgba(0,0,0,0.2)) brightness(1.1)' : 'none',

                                                    // 4. HIỆU ỨNG NỔI LÊN: Phóng to miếng bánh lên 5% (1.05)
                                                    transform: isActive ? 'scale(1.05)' : 'scale(1)',
                                                    transformOrigin: 'center', // Lấy tâm là giữa biểu đồ để phóng to đều

                                                    outline: 'none',
                                                    cursor: 'pointer'
                                                }}
                                            />
                                        );
                                    })}
                                </Pie>
                                <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', color: '#374151' }} />
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="flex justify-center gap-3.75 text-[12px] font-bold mt-1">
                            <span className="text-[#2ed573]">● Allowed</span>
                            <span className="text-[#ff4757]">● Blocked</span>
                        </div>
                    </div>
                </div>

                <div className="bg-white p-5 rounded-[10px] border border-gray-50 shadow-md h-75 flex flex-col">
                    <h3 className="text-[16px] text-black mb-3.75 font-semibold">Top IP Addresses</h3>
                    <div className="flex-1 w-full relative">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={topIpsData}>
                                <XAxis dataKey="ip" stroke="#8c92ac" fontSize={12} />
                                <YAxis stroke="#8c92ac" fontSize={12} allowDecimals={false} />

                                {/* 1. SỬA TOOLTIP: Nền trắng, viền xám, cursor (cột xám chìm) khi hover */}
                                <Tooltip
                                    cursor={{ fill: 'rgba(0, 0, 0, 0.04)' }}
                                    contentStyle={{
                                        backgroundColor: '#ffffff',
                                        borderRadius: '8px',
                                        border: '1px solid #e5e7eb',
                                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                                        color: '#374151'
                                    }}
                                />

                                {/* 2. SỬA MÀU BAR: Gọi trực tiếp biến CSS của Tailwind */}
                                <Bar
                                    dataKey="count"
                                    fill="var(--color-primary)"
                                    radius={[4, 4, 0, 0]}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* HÀNG BIỂU ĐỒ 2 (MỚI): TOP HOSTS, TOP USER-AGENTS, HTTP VERSIONS */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-7.5">
                {/* Bảng Top Hosts */}
                <div className="bg-white p-5 rounded-[10px] border border-gray-100 shadow-md h-75 flex flex-col">
                    <h3 className="text-[16px] text-black mb-3.75 font-semibold">Top 5 Hosts</h3>
                    <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                        <table className="w-full text-md">
                            <thead className="text-[#8c92ac] border-b border-gray-100 sticky top-0 bg-white">
                                <tr>
                                    <th className="text-left py-2 font-semibold">Host</th>
                                    <th className="text-right py-2 font-semibold">Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {topHostsData.map((item, index) => (
                                    <tr key={index} className="border-b border-gray-50 last:border-0">
                                        <td className="py-2.5 text-gray-700 truncate max-w-37.5" title={item.name}>{item.name}</td>
                                        <td className="py-2.5 text-right font-bold text-gray-900">{item.count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Bảng Top User-Agents */}
                <div className="bg-white p-5 rounded-[10px] border border-gray-100 shadow-md h-75 flex flex-col">
                    <h3 className="text-[16px] text-black mb-3.75 font-semibold">Top 5 User-Agents</h3>
                    <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                        <table className="w-full text-md">
                            <thead className="text-[#8c92ac] border-b border-gray-100 sticky top-0 bg-white">
                                <tr>
                                    <th className="text-left py-2 font-semibold">User-Agent</th>
                                    <th className="text-right py-2 font-semibold">Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {topUaData.map((item, index) => (
                                    <tr key={index} className="border-b border-gray-50 last:border-0">
                                        {/* truncate giúp cắt gọn UA quá dài thành dấu '...', đưa chuột vào sẽ hiện full nhờ title */}
                                        <td className="py-2.5 text-gray-700 truncate max-w-37.5" title={item.name}>{item.name}</td>
                                        <td className="py-2.5 text-right font-bold text-gray-900">{item.count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Bảng Engine Stats (Đã tối giản UI) */}
                <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-md h-75 flex flex-col">
                    <h3 className="text-[16px] font-bold text-gray-800 mb-3.75">Detection Efficiency</h3>
                    <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                        <table className="w-full text-md">
                            <thead className="text-[#8c92ac] border-b border-gray-100 sticky top-0 bg-white">
                                <tr>
                                    <th className="text-left py-2 font-semibold">Engine</th>
                                    <th className="text-right py-2 font-semibold">Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr className="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                                    <td className="py-2.5 text-gray-700">Random Forest</td>
                                    <td className="py-2.5 text-right font-bold text-gray-900">{engineBlocks["Random Forest"]}</td>
                                </tr>
                                <tr className="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                                    <td className="py-2.5 text-gray-700">Autoencoder</td>
                                    <td className="py-2.5 text-right font-bold text-gray-900">{engineBlocks["Autoencoder"]}</td>
                                </tr>
                                <tr className="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                                    <td className="py-2.5 text-gray-700">WebACL Rules</td>
                                    <td className="py-2.5 text-right font-bold text-gray-900">{engineBlocks["WebACL Rules"]}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-7.5">
                {/* Biểu đồ Method */}
                <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm h-80 flex flex-col">
                    <h3 className="text-md font-bold text-gray-800 mb-2">HTTP Methods</h3>
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart onMouseLeave={onMethodPieLeave}>
                            <Pie
                                data={methodData}
                                cx="50%"
                                cy="50%"
                                innerRadius={50}
                                outerRadius={75}
                                paddingAngle={0}
                                dataKey="value"
                                stroke="none"
                                /* Thay vì dùng activeShape, ta chỉ cần bắt sự kiện chuột */
                                onMouseEnter={onMethodPieEnter}
                                onMouseLeave={onMethodPieLeave}
                            >
                                {methodData.map((entry, index) => {
                                    // Xác định xem miếng bánh nào đang được trỏ chuột vào
                                    const isActive = activeMethodIndex === index;
                                    // Xác định các miếng bánh bị bỏ lại (để làm mờ)
                                    const isDimmed = activeMethodIndex !== null && !isActive;
                                    // Lấy màu từ Map, nếu Method lạ thì cho màu xám
                                    const cellColor = METHOD_COLORS_MAP[entry.name.toUpperCase()] || METHOD_COLORS_MAP['Unknown'];

                                    return (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={cellColor}
                                            style={{
                                                // 1. Chuyển động lụa là trong 0.3s cho tất cả hiệu ứng
                                                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',

                                                // 2. Làm mờ các miếng không được chọn
                                                opacity: isDimmed ? 0.3 : 1,

                                                // 3. Đổ bóng và làm sáng miếng đang chọn
                                                filter: isActive ? 'drop-shadow(0px 8px 16px rgba(0,0,0,0.2)) brightness(1.1)' : 'none',

                                                // 4. HIỆU ỨNG NỔI LÊN: Phóng to miếng bánh lên 5% (1.05)
                                                transform: isActive ? 'scale(1.05)' : 'scale(1)',
                                                transformOrigin: 'center', // Lấy tâm là giữa biểu đồ để phóng to đều

                                                outline: 'none',
                                                cursor: 'pointer'
                                            }}
                                        />
                                    );
                                })}
                            </Pie>
                            <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', color: '#374151' }} />
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-wrap justify-center gap-2 mt-2">
                        {methodData.map((entry, i) => (
                            <span key={i} className="text-[10px] font-bold" style={{ color: METHOD_COLORS_MAP[entry.name.toUpperCase()] || METHOD_COLORS_MAP['Unknown'] }}>● {entry.name}</span>
                        ))}
                    </div>
                </div>
                {/* Biểu đồ Donut: HTTP Versions */}
                <div className="bg-white p-5 rounded-[10px] border border-gray-100 shadow-md h-80 flex flex-col">
                    <h3 className="text-[16px] text-black mb-3.75 font-semibold">HTTP Versions</h3>
                    <div className="flex-1 w-full relative">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart onMouseLeave={onHttpPieLeave}>
                                <Pie
                                    data={httpVersionData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={50}
                                    outerRadius={75}
                                    paddingAngle={0}
                                    dataKey="value"
                                    stroke="none"
                                    /* Thay vì dùng activeShape, ta chỉ cần bắt sự kiện chuột */
                                    onMouseEnter={onHttpPieEnter}
                                    onMouseLeave={onHttpPieLeave}
                                >
                                    {httpVersionData.map((entry, index) => {
                                        // Xác định xem miếng bánh nào đang được trỏ chuột vào
                                        const isActive = activeHttpIndex === index;
                                        // Xác định các miếng bánh bị bỏ lại (để làm mờ)
                                        const isDimmed = activeHttpIndex !== null && !isActive;

                                        return (
                                            <Cell
                                                key={`cell-${index}`}
                                                fill={HTTP_COLORS[index % HTTP_COLORS.length]}
                                                style={{
                                                    // 1. Chuyển động lụa là trong 0.3s cho tất cả hiệu ứng
                                                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',

                                                    // 2. Làm mờ các miếng không được chọn
                                                    opacity: isDimmed ? 0.3 : 1,

                                                    // 3. Đổ bóng và làm sáng miếng đang chọn
                                                    filter: isActive ? 'drop-shadow(0px 8px 16px rgba(0,0,0,0.2)) brightness(1.1)' : 'none',

                                                    // 4. HIỆU ỨNG NỔI LÊN: Phóng to miếng bánh lên 5% (1.05)
                                                    transform: isActive ? 'scale(1.05)' : 'scale(1)',
                                                    transformOrigin: 'center', // Lấy tâm là giữa biểu đồ để phóng to đều

                                                    outline: 'none',
                                                    cursor: 'pointer'
                                                }}
                                            />
                                        );
                                    })}
                                </Pie>
                                <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', color: '#374151' }} />
                            </PieChart>
                        </ResponsiveContainer>
                        {/* Legend cho HTTP Versions */}
                        <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 text-[12px] font-bold mt-1">
                            {httpVersionData.map((entry, index) => (
                                <span key={index} style={{ color: HTTP_COLORS[index % HTTP_COLORS.length] }}>
                                    ● {entry.name}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
};

export default Dashboard;