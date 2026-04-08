import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';

const Layout = () => {
    return (
        // Thay thế class .dashboard-container bằng các utility classes của Tailwind
        <div className="flex h-screen w-full overflow-hidden bg-gray-50 font-sans text-black">
            <Sidebar />
            {/* Cột bên phải chứa Navbar ở trên và Nội dung cuộn ở dưới */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <Navbar />

                {/* Outlet là nơi các trang như Dashboard chui vào */}
                {/* overflow-y-auto ở đây giúp thanh cuộn chỉ xuất hiện ở nội dung, Navbar vẫn đứng im */}
                <div className="flex-1 overflow-y-auto relative">
                    <Outlet />
                </div>
            </div>
        </div>
    );
};

export default Layout;