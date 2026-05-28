import React, { useState, useEffect } from 'react';
import axios from 'axios';


const LiveTraffic = () => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);

    // --- STATE CHO BỘ LỌC (FILTERS) ---
    const [methodFilter, setMethodFilter] = useState('All');
    const [actionFilter, setActionFilter] = useState('All');
    const [WTFilter, setWTFilter] = useState('All');

    // STATE cho Pagination
    const [totalRequest, setTotalRequest] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [jumpPage, setJumpPage] = useState('');
    const totalPages = Math.ceil(totalRequest / pageSize);


    useEffect(() => {
        fetchLogs();
        // Khai báo biến isMounted để tránh memory leak
        let isMounted = true;
        let ws = null;
        let lastFetchTime = 0;

        const timeoutID = setTimeout(() => {
            if (!isMounted) return;
            ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/ws/waf`);
            ws.onopen = () => {
                console.log('Websocket is connected to LiveTraffic');
            };
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    //Có log mới => cập nhật bảng
                    if (data.type === "NEW_LOG" || data.type === "NEW_BLOCK") {
                        const currentTime = Date.now();
                        // Chỉ cho phép gọi API nếu request cách lần gọi trước đó trên 1000ms (1 giây)
                        if (currentPage === 1 && (currentTime - lastFetchTime > 1000)) {
                            fetchLogs(); // Gọi hàm cập nhật dữ liệu của bạn
                            lastFetchTime = currentTime; // Cập nhật lại mốc thời gian
                        }
                    }
                } catch (err) {
                    console.error("Error while fetching data:", err);
                }
            };
            ws.onerror = (error) => {
                console.error("WebSocket error:", error);
            };
        }, 100);
        return () => {
            //khai báo về false để tránh memory leak
            isMounted = false;
            clearTimeout(timeoutID);
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
        }
    }, [currentPage, pageSize, methodFilter, actionFilter, WTFilter]);

    const fetchLogs = async () => {
        try {
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/logs?page=${currentPage}&limit=${pageSize}&method=${methodFilter}&action=${actionFilter}&type_filter=${WTFilter}`);
            setLogs(response.data.data);
            setTotalRequest(response.data.total_requests);
            setLoading(false);
        } catch (error) {
            console.error("Lỗi khi tải dữ liệu:", error);
            setLoading(false);
        }
    };

    const getPageNumbers = () => {
        const pages = [];
        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            if (currentPage <= 4) {
                pages.push(1, 2, 3, 4, 5, '...', totalPages);
            } else if (currentPage >= totalPages - 3) {
                pages.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
            } else {
                pages.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
            }
        }
        return pages;
    };

    // --- LOGIC LỌC DỮ LIỆU CHO BẢNG ---
    const filteredLogs = logs.filter((log) => {
        const matchMethod = methodFilter === 'All' || log.method.toUpperCase() === methodFilter;
        const matchAction = actionFilter === 'All' || log.action === actionFilter;
        const matchWF = WTFilter === 'All' || log.reason === WTFilter || (WTFilter === 'Violated WebACL Rules' && log.reason?.startsWith('Triggered rule:'));
        return matchMethod && matchAction && matchWF;
    });

    return (
        // Thêm thẻ main bọc ngoài cùng để có padding chuẩn giống trang Dashboard
        <main className="p-7.5 bg-gray-50/30 min-h-screen">
            <div className="bg-white rounded-[10px] border border-gray-100 shadow-sm p-5">
                {/* THANH CÔNG CỤ: TIÊU ĐỀ & DROPDOWNS */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
                    <div>
                        <h2 className="text-xl font-bold text-gray-800">Live Attack & Traffic Logs</h2>
                        <p className="text-sm text-gray-400 mt-1">Showing {logs.length} request(s)</p>
                    </div>

                    {/* Khu vực 2 Dropdowns */}
                    <div className="flex items-center gap-3">
                        <select
                            value={methodFilter}
                            onChange={(e) => {
                                setMethodFilter(e.target.value);
                                setCurrentPage(1);
                            }}
                            className="bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-primary focus:border-primary block p-2 outline-none cursor-pointer hover:bg-gray-100 transition-colors"
                        >
                            <option value="All">All Methods</option>
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                            <option value="PUT">PUT</option>
                            <option value="DELETE">DELETE</option>
                        </select>
                        <select
                            value={WTFilter}
                            onChange={(e) => {
                                setWTFilter(e.target.value);
                                setCurrentPage(1);
                            }}
                            className='"bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-primary focus:border-primary block p-2 outline-none cursor-pointer hover:bg-gray-100 transition-colors'
                        >
                            <option value="All">All Type</option>
                            <option value="Safe Traffic">Safe Traffic</option>
                            <option value="Known Signature Detected">Known Signature Threat</option>
                            <option value="Zero-day Anomaly">Zero-Day Threat</option>
                            <option value="HTTP Flood / DoS Attempt">HTTP Flood/DoS Attempt</option>
                            <option value="Violated WebACL Rules">Violated WebACL Rules</option>
                        </select>

                        <select
                            value={actionFilter}
                            onChange={(e) => {
                                setActionFilter(e.target.value);
                                setCurrentPage(1);
                            }}
                            className="bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-primary focus:border-primary block p-2 outline-none cursor-pointer hover:bg-gray-100 transition-colors"
                        >
                            <option value="All">All Actions</option>
                            <option value="PASSED">Allowed</option>
                            <option value="BLOCKED">Blocked</option>
                        </select>
                    </div>
                </div>

                {loading ? (
                    <div className="flex justify-center items-center py-20">
                        <p className="text-[#8c92ac] animate-pulse font-medium">Syncing data from AI-WAF...</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto custom-scrollbar">
                        <table className="w-full border-collapse text-sm">
                            <thead className="bg-gray-50/50 sticky top-0">
                                <tr>
                                    <th className="text-left p-4 text-[#8c92ac] border-b-2 border-gray-100 font-semibold">Timeline</th>
                                    <th className="text-left p-4 text-[#8c92ac] border-b-2 border-gray-100 font-semibold">IP Client</th>
                                    <th className="text-left p-4 text-[#8c92ac] border-b-2 border-gray-100 font-semibold">Method</th>
                                    <th className="text-left p-4 text-[#8c92ac] border-b-2 border-gray-100 font-semibold">Path</th>
                                    <th className="text-left p-4 text-[#8c92ac] border-b-2 border-gray-100 font-semibold">Warning Type</th>
                                    <th className="text-left p-4 text-[#8c92ac] border-b-2 border-gray-100 font-semibold">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {/* NẾU LỌC RA KHÔNG CÓ DỮ LIỆU */}
                                {logs.length === 0 && (
                                    <tr>
                                        <td colSpan="6" className="text-center py-12 text-gray-400">
                                            No logs found matching your filters.
                                        </td>
                                    </tr>
                                )}

                                {/* Đã bỏ .slice(0,15) để hiện full bảng */}
                                {logs.map((log) => (
                                    <tr key={log._id} className="hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0">
                                        <td className="py-4 px-4 text-gray-600 whitespace-nowrap">
                                            {new Date(log.timestamp).toLocaleString('vi-VN')}
                                        </td>
                                        <td className="py-4 px-4 font-mono text-gray-600 whitespace-nowrap">
                                            {log.client_ip}
                                        </td>
                                        <td className="py-4 px-4">
                                            <span className={`py-1 px-2.5 rounded text-xs font-bold uppercase ${log.method.toLowerCase() === 'get' ? 'bg-[#2ed573]/20 text-[#2ed573]' :
                                                log.method.toLowerCase() === 'post' ? 'bg-[#ffa502]/20 text-[#ffa502]' :
                                                    log.method.toLowerCase() === 'put' ? 'bg-[#3498db]/20 text-[#3498db]' :
                                                        log.method.toLowerCase() === 'options' ? 'bg-[#9b59b6]/20 text-[#9b59b6]' :
                                                            log.method.toLowerCase() === 'delete' ? 'bg-[#ff4757]/20 text-[#ff4757]' : 'bg-gray-200 text-gray-600'
                                                }`}>
                                                {log.method}
                                            </span>
                                        </td>
                                        <td className="py-4 px-4 text-gray-600">
                                            <div className="max-w-75 overflow-hidden text-ellipsis whitespace-nowrap font-mono" title={log.raw_payload}>
                                                {log.path_accessed}
                                            </div>
                                        </td>
                                        <td className="py-4 px-4">
                                            {log.attack_type === 'None' ? (
                                                <span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded text-xs font-bold bg-[#2ed573]/10 text-[#2ed573]  border-[#2ed573]/30">
                                                    {log.reason}
                                                </span>
                                            ) : (
                                                <span className={`inline-flex items-center py-1 px-2.5 rounded text-xs font-bold  ${log.blocked_by_engine === 'Autoencoder'
                                                    ? 'bg-[#ff4757]/10 text-[#ff4757] border-[#ff4757]/30'
                                                    : 'bg-[#ff4757]/10 text-[#ff4757] border-[#ff4757]/30'
                                                    }`}>
                                                    {log.attack_type}
                                                </span>
                                            )}
                                        </td>
                                        <td className="py-4 px-4">
                                            {log.action === 'PASSED' ? (
                                                <span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded text-xs font-bold bg-[#2ed573]/10 text-[#2ed573]  border-[#2ed573]/30">
                                                    ALLOWED
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1.5 py-1 px-2.5 rounded text-xs font-bold bg-[#ff4757]/10 text-[#ff4757]  border-[#ff4757]/30">
                                                    BLOCKED
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {!loading && (
                    <div className="flex flex-wrap items-center justify-between mt-6 pt-4 border-t border-gray-100 text-[14px] text-gray-500">
                        {/* Khu vực trái: Dropdown & Tổng số */}
                        <div className="flex items-center gap-3">
                            <select
                                className="border border-gray-200 rounded text-gray-600 px-2 py-1 focus:outline-none focus:border-blue-400 cursor-pointer"
                                value={pageSize}
                                onChange={(e) => {
                                    setPageSize(Number(e.target.value));
                                    setCurrentPage(1); // Reset về trang 1 khi đổi limit
                                }}
                            >
                                <option value={20}>20 / page</option>
                                <option value={100}>100 / page</option>
                                <option value={500}>500 / page</option>
                                <option value={1000}>1000 / page</option>
                            </select>
                            <span>total {totalRequest}</span>
                        </div>

                        {/* Khu vực phải: Chuyển trang & Nhập số */}
                        <div className="flex items-center gap-2">
                            {/* Nút Prev */}
                            <button
                                disabled={currentPage === 1}
                                onClick={() => setCurrentPage(prev => prev - 1)}
                                className="w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                                &lt;
                            </button>

                            {/* Render danh sách số trang */}
                            {getPageNumbers().map((page, index) => (
                                <button
                                    key={index}
                                    disabled={page === '...'}
                                    onClick={() => typeof page === 'number' && setCurrentPage(page)}
                                    className={`min-w-8 h-8 px-1 rounded flex items-center justify-center font-medium transition-colors
                                        ${page === currentPage
                                            ? 'bg-primary text-white border border-primary' // Màu xanh giống ảnh
                                            : page === '...'
                                                ? 'text-gray-400 cursor-default'
                                                : 'text-gray-600 hover:text-primary border border-transparent'}`}
                                >
                                    {page}
                                </button>
                            ))}

                            {/* Nút Next */}
                            <button
                                disabled={currentPage === totalPages || totalPages === 0}
                                onClick={() => setCurrentPage(prev => prev + 1)}
                                className="w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                                &gt;
                            </button>

                            {/* Khung Jump to Page */}
                            <div className="flex items-center gap-2 ml-4">
                                <span>go to</span>
                                <input
                                    type="number"
                                    className="w-14 h-8 border border-gray-200 rounded px-2 text-center focus:outline-none focus:border-blue-400"
                                    value={jumpPage}
                                    onChange={(e) => setJumpPage(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            const p = Number(jumpPage);
                                            if (p >= 1 && p <= totalPages) {
                                                setCurrentPage(p);
                                                setJumpPage('');
                                            }
                                        }
                                    }}
                                />
                                <span>/ {totalPages}</span>
                            </div>
                        </div>
                    </div>
                )}
                {/* HẾT PHẦN THANH PHÂN TRANG */}

            </div>
        </main>
    );
};

export default LiveTraffic;
