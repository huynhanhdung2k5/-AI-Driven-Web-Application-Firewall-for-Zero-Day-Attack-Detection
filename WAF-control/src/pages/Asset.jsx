import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Calendar, Settings, X, Plus, Trash2, ArrowLeft, RefreshCw } from 'lucide-react';

const Asset = () => {
    const [viewMode, setViewMode] = useState('table');
    const [isModalOpen, setIsModalOpen] = useState(false);

    // State chứa dữ liệu thật
    const [blockedRecords, setBlockedRecords] = useState([]);
    const [rules, setRules] = useState([]);
    const [loading, setLoading] = useState(true);

    // State quản lý form tạo Rule mới
    const [newRule, setNewRule] = useState({
        category: 'Access Limiting', // Mặc định
        name: '',
        matchTarget: 'URL Path',
        operator: 'Equals',
        content: '',
        duration: 0,
        access: 0,
        action: 'Challenge',
        challenge: 0
    });

    // Hàm gửi dữ liệu lên Backend
    const handleAddRule = async () => {
        // Ràng buộc nhập liệu cơ bản
        if (!newRule.name || !newRule.content) {
            alert("Please fill Rule name and Content!");
            return;
        }

        try {
            // Tự động tạo câu Description cho đẹp dựa trên các thông số
            let desc = "";
            if (newRule.content === ".*") {
                desc = `An IP with any content that makes ${newRule.access} requests within ${newRule.duration} seconds will require ${newRule.action} for ${newRule.challenge} minutes.`;
            } else {
                desc = `An IP with content ${newRule.content} that makes ${newRule.access} requests within ${newRule.duration} seconds will require ${newRule.action} for ${newRule.challenge} minutes.`;
            }

            const payload = {
                category: newRule.category,
                name: newRule.name,
                desc: desc,
                enabled: true, // Tạo xong là kích hoạt luôn
                match_target: newRule.matchTarget,
                operator: newRule.operator,
                content: newRule.content,
                duration_sec: Number(newRule.duration),
                access_count: Number(newRule.access),
                action: newRule.action,
                challenge_min: Number(newRule.challenge)
            };

            await axios.post('http://localhost:8000/api/waf/rules', payload);

            // Thành công: Đóng modal, tải lại danh sách, reset form
            setIsModalOpen(false);
            fetchRules();
            setNewRule({
                category: 'Access Limiting', name: '', matchTarget: 'URL Path', operator: 'Equals',
                content: '', duration: 0, access: 0, action: 'Challenge', challenge: 0
            });
        } catch (error) {
            console.error("Lỗi khi tạo Rule:", error);
            alert("There was an error while making rule!");
        }
    };

    const handleDeleteRule = async (rule_id) => {
        const isConfirmed = window.confirm("Are you sure to delete this rule?");
        if (isConfirmed) {
            try {
                await axios.delete(`http://localhost:8000/api/waf/rules/${rule_id}`);
                setRules(rules.filter(rule => rule.rule_id != rule_id));
            } catch (error) {
                console.error("Error while delete rule:", error);
                alert("There was an error while delete rule!");
            }
        }
    };

    // Kéo dữ liệu khi trang vừa mở
    useEffect(() => {
        fetchBlockedIps();
        fetchRules();
    }, []);

    const fetchBlockedIps = async () => {
        setLoading(true);
        try {
            const res = await axios.get('http://localhost:8000/api/waf/blocked-ips');
            setBlockedRecords(res.data.data);
        } catch (error) {
            console.error("Lỗi lấy danh sách IP:", error);
        }
        setLoading(false);
    };

    const fetchRules = async () => {
        try {
            const res = await axios.get('http://localhost:8000/api/waf/rules');
            setRules(res.data.data);
        } catch (error) {
            console.error("Lỗi lấy danh sách Rules:", error);
        }
    };

    // Hàm gọi API để bật/tắt Rule thật trên Backend
    const toggleRule = async (rule_id, currentEnabled) => {
        // Optimistic UI Update (Đổi màu ngay lập tức cho mượt, không cần chờ mạng)
        setRules(rules.map(r => r.rule_id === rule_id ? { ...r, enabled: !currentEnabled } : r));

        try {
            // Gọi API lưu xuống DB
            await axios.put(`http://localhost:8000/api/waf/rules/${rule_id}`, {
                enabled: !currentEnabled
            });
        } catch (error) {
            console.error("Lỗi cập nhật Rule:", error);
            // Nếu lỗi thì hoàn tác lại UI
            fetchRules();
        }
    };

    return (
        <main className="p-7.5 bg-gray-50/50 min-h-screen">
            {/* GÓC NHÌN 1: BẢNG DANH SÁCH IP BỊ CHẶN */}
            {viewMode === 'table' && (
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                    <div className="p-4 border-b border-gray-100 flex flex-wrap gap-4 items-center justify-between">
                        <div className="flex flex-wrap gap-3 flex-1">
                            {/* Thanh công cụ tìm kiếm */}
                            <input type="text" placeholder="IP Addr" className="px-3 py-2 border border-gray-200 rounded-lg text-sm w-40 outline-none focus:border-primary" />
                            <input type="text" placeholder="Application" className="px-3 py-2 border border-gray-200 rounded-lg text-sm w-40 outline-none focus:border-primary" />
                        </div>

                        <div className="flex gap-3">
                            <button onClick={fetchBlockedIps} className="p-2 border border-gray-200 text-gray-500 rounded-lg hover:bg-gray-50 transition-colors" title="Làm mới dữ liệu">
                                <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
                            </button>
                            <button onClick={() => setViewMode('settings')} className="flex items-center gap-2 px-4 py-2 bg-primary text-white font-bold text-sm rounded-lg hover:brightness-110 transition-all shadow-md shadow-primary/20">
                                <Settings size={16} /> SETTINGS
                            </button>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-gray-50 text-gray-500 font-semibold border-b border-gray-100">
                                <tr>
                                    <th className="px-6 py-3">IP Addr</th>
                                    <th className="px-6 py-3">Application</th>
                                    <th className="px-6 py-3 w-1/3">Detail</th>
                                    <th className="px-6 py-3">Blocked Count</th>
                                    <th className="px-6 py-3">Last Attacked</th>
                                    <th className="px-6 py-3">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && (
                                    <tr><td colSpan="6" className="text-center py-10 text-gray-400">Fetching data from MongoDB...</td></tr>
                                )}
                                {!loading && blockedRecords.length === 0 && (
                                    <tr><td colSpan="6" className="text-center py-10 text-gray-400">There is no IP that been blocked.</td></tr>
                                )}
                                {!loading && blockedRecords.map((record) => (
                                    <tr key={record.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <p className="font-bold text-gray-800 font-mono">{record.ip}</p>
                                            <p className="text-gray-400 text-xs mt-1">{record.location}</p>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">

                                                <p className="font-bold text-gray-700">{record.app}</p>
                                            </div>
                                            <p className="text-gray-400 text-xs mt-1 ml-6">{record.host}</p>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="grid grid-cols-[60px_1fr] gap-y-2 text-xs">
                                                <span className="text-gray-400">Reason</span>
                                                <span className="text-red-500 font-bold">{record.reason}</span>
                                                <span className="text-gray-400">Action</span>
                                                <span className="text-gray-700 font-medium">{record.action}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 font-black text-red-500">{record.blockedCount}</td>
                                        <td className="px-6 py-4 font-mono text-gray-600 text-xs whitespace-nowrap">{record.startAt}</td>
                                        <td className="px-6 py-4">
                                            <button className="text-primary font-semibold hover:underline">Unblock</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* GÓC NHÌN 2: CÀI ĐẶT WEBACL (SETTINGS) */}
            {viewMode === 'settings' && (
                <div className="max-w-5xl mx-auto">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-4">
                            <button onClick={() => setViewMode('table')} className="p-2 hover:bg-white rounded-lg transition-colors border border-transparent hover:border-gray-200">
                                <ArrowLeft className="text-gray-600" size={20} />
                            </button>
                            <div>
                                <h1 className="text-2xl font-bold text-gray-800">Rules Settings</h1>
                            </div>
                        </div>

                        {/* NÚT "ADD RULES" */}
                        <button
                            onClick={() => setIsModalOpen(true)}
                            className="flex items-center gap-2 px-4 py-2 bg-primary text-white font-bold text-sm rounded-lg hover:brightness-110 transition-colors shadow-sm"
                        >
                            ADD RULES <Plus size={16} />
                        </button>
                    </div>

                    {/* HIỂN THỊ "KHÔNG CÓ LUẬT NÀO" NẾU DANH SÁCH TRỐNG */}
                    {rules.length === 0 ? (
                        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-10 flex flex-col items-center justify-center text-center">

                            <h3 className="text-gray-500 font-medium text-lg">There is no rule in WAF</h3>
                            <p className="text-gray-400 text-sm mt-1">Click "ADD RULES" button to create protection rule.</p>
                        </div>
                    ) : (
                        <div className="space-y-8">
                            {['Access Limiting', 'Attack Limiting', 'Error Limiting'].map((category) => {
                                const categoryRules = rules.filter(r => r.category === category);
                                if (categoryRules.length === 0) return null;

                                return (
                                    <div key={category}>
                                        <h3 className="text-lg font-bold text-gray-800 mb-3">{category}</h3>
                                        {categoryRules.map((rule) => (
                                            <div key={rule.rule_id} className={`bg-white p-5 rounded-xl border ${rule.enabled ? 'border-primary shadow-md' : 'border-gray-100 shadow-sm'} flex items-center justify-between gap-6 mb-3 transition-all`}>
                                                <div className="flex items-start gap-4 flex-1">
                                                    <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-1">
                                                        <input type="checkbox" checked={rule.enabled} onChange={() => toggleRule(rule.rule_id, rule.enabled)} className="sr-only peer" />
                                                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                                                    </label>

                                                    <div>
                                                        <h4 className="font-bold text-gray-800">{rule.name}</h4>
                                                        <p className="text-sm text-gray-500 mt-1">{rule.desc}</p>
                                                    </div>
                                                </div>
                                                {rule.enabled && <span className="px-3 py-1 bg-green-100 text-green-600 text-xs font-bold rounded-full">ACTIVE</span>}
                                                <button onClick={() => handleDeleteRule(rule.rule_id)}
                                                    className="text-gray-300 hover:text-red-500 transition-colors p-2 rounded-lg "
                                                    title="Xóa Rule này"><Trash2 size={18} /></button>
                                            </div>
                                        ))}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* MODAL THÊM RULE MỚI (PHẦN BỊ THIẾU TRƯỚC ĐÓ) */}
            {isModalOpen && (
                <div className="fixed inset-0 z-[999] flex items-center justify-center bg-gray-900/40 backdrop-blur-sm px-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                        {/* Header Modal */}
                        <div className="flex items-center justify-between p-5 border-b border-gray-100">
                            <h2 className="text-lg font-bold text-gray-800">Add rules</h2>
                            <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-red-500 transition-colors">
                                <X size={20} />
                            </button>
                        </div>

                        {/* Body Modal */}
                        <div className="p-6 space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Category <span className="text-red-500">*</span></label>
                                    <select
                                        value={newRule.category} onChange={e => setNewRule({ ...newRule, category: e.target.value })}
                                        className="w-full border border-gray-200 rounded-lg p-2.5 outline-none focus:border-primary text-sm bg-white"
                                    >
                                        <option value="Access Limiting">Access Limiting</option>
                                        <option value="Attack Limiting">Attack Limiting</option>
                                        <option value="Error Limiting">Error Limiting</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Name <span className="text-red-500">*</span></label>
                                    <input
                                        type="text" placeholder="e.g. Block request abc"
                                        value={newRule.name} onChange={e => setNewRule({ ...newRule, name: e.target.value })}
                                        className="w-full border border-gray-200 rounded-lg p-2.5 outline-none focus:border-primary text-sm"
                                    />
                                </div>
                            </div>

                            <div className="bg-gray-50/50 border border-gray-100 rounded-lg p-4">
                                <div className="flex flex-wrap gap-3 items-start mb-4">
                                    <div className="flex-1 min-w-[150px]">
                                        <label className="block text-xs text-gray-500 mb-1">Match Target</label>
                                        <select value={newRule.matchTarget} onChange={e => setNewRule({ ...newRule, matchTarget: e.target.value })} className="w-full border border-gray-200 rounded-lg p-2 outline-none text-sm bg-white focus:border-primary">
                                            <option value="URL Path">URL Path</option>
                                            <option value="Client IP">Client IP</option>
                                            <option value="User Agent">User Agent</option>
                                        </select>
                                    </div>
                                    <div className="flex-1 min-w-[120px]">
                                        <label className="block text-xs text-gray-500 mb-1">Operator <span className="text-red-500">*</span></label>
                                        <select value={newRule.operator} onChange={e => setNewRule({ ...newRule, operator: e.target.value })} className="w-full border border-gray-200 rounded-lg p-2 outline-none text-sm bg-white focus:border-primary">
                                            <option value="Equals">Equals</option>
                                            <option value="Contains">Contains</option>
                                            <option value="Matches Regex">Matches Regex</option>
                                        </select>
                                    </div>
                                    <div className="flex-[2] min-w-[200px]">
                                        <label className="block text-xs text-gray-500 mb-1">Content <span className="text-red-500">*</span></label>
                                        <input
                                            type="text" placeholder="e.g. /api/login"
                                            value={newRule.content} onChange={e => setNewRule({ ...newRule, content: e.target.value })}
                                            className="w-full border border-gray-200 rounded-lg p-2 outline-none text-sm bg-white focus:border-primary"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                <div>
                                    <label className="block text-xs text-gray-500 mb-1">Duration <span className="text-red-500">*</span></label>
                                    <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden focus-within:border-primary">
                                        <input type="number" value={newRule.duration} onChange={e => setNewRule({ ...newRule, duration: e.target.value })} className="w-full p-2 outline-none text-sm" />
                                        <span className="px-3 text-sm text-gray-500 bg-gray-50 border-l border-gray-200">Sec</span>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-xs text-gray-500 mb-1">Access <span className="text-red-500">*</span></label>
                                    <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden focus-within:border-primary">
                                        <input type="number" value={newRule.access} onChange={e => setNewRule({ ...newRule, access: e.target.value })} className="w-full p-2 outline-none text-sm" />
                                        <span className="px-2 text-gray-400 bg-gray-50 border-l border-gray-200">↕</span>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-xs text-gray-500 mb-1">Action</label>
                                    <select value={newRule.action} onChange={e => setNewRule({ ...newRule, action: e.target.value })} className="w-full border border-gray-200 rounded-lg p-2.5 outline-none text-sm bg-white focus:border-primary">
                                        <option value="Challenge">Challenge</option>
                                        <option value="Block">Block</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-gray-500 mb-1">Challenge <span className="text-red-500">*</span></label>
                                    <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden focus-within:border-primary">
                                        <input type="number" value={newRule.challenge} onChange={e => setNewRule({ ...newRule, challenge: e.target.value })} className="w-full p-2 outline-none text-sm" />
                                        <span className="px-3 text-sm text-gray-500 bg-gray-50 border-l border-gray-200">Min</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Footer Modal */}
                        <div className="flex items-center justify-end gap-3 p-5 border-t border-gray-100 bg-gray-50/50">
                            <button onClick={() => setIsModalOpen(false)} className="px-5 py-2 text-gray-500 font-bold text-sm hover:text-gray-700 transition-colors">
                                CANCEL
                            </button>
                            <button onClick={handleAddRule} className="px-6 py-2 bg-primary text-white font-bold text-sm rounded-lg hover:brightness-110 transition-colors shadow-md">
                                SUBMIT
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
};

export default Asset;