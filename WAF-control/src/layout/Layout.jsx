import React, { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';

const Layout = () => {
    const [headerData, setHeaderData] = useState({ title: '' });
    const location = useLocation();

    useEffect(() => {
        const path = location.pathname;
        if (path === '/dashboard') {
            setHeaderData({ title: "WAF Dashboard" });
        } else if (path.startsWith('/live-traffic')) {
            setHeaderData({ title: 'WAF Traffic' });
        } else if (path.startsWith('/asset')) {
            setHeaderData({ title: "WAF Asset" });
        }
    }, [location.pathname]);
    return (
        // Thay thế class .dashboard-container bằng các utility classes của Tailwind
        <div className="flex h-screen w-full overflow-hidden bg-gray-50 font-sans text-black">
            <Sidebar />
            {/* Cột bên phải chứa Navbar ở trên và Nội dung cuộn ở dưới */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <Navbar title={headerData.title} />

                {/* Outlet là nơi các trang như Dashboard chui vào */}
                {/* overflow-y-auto ở đây giúp thanh cuộn chỉ xuất hiện ở nội dung, Navbar vẫn đứng im */}
                <main className="flex-1 overflow-y-auto relative">
                    <Outlet />
                </main>
            </div>
        </div>
    );
};

export default Layout;