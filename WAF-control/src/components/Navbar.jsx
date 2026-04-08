import React from 'react';
import { Search, Bell, User } from 'lucide-react';

const Navbar = () => {
    return (
        <header className="bg-white h-17.5 border-b border-gray-100 flex items-center justify-between px-7.5 shrink-0 shadow-sm z-10">
            {/* Tiêu đề trang (Sử dụng màu primary) */}
            <h1 className="text-2xl font-bold text-primary">WAF Dashboard</h1>


        </header>
    );
};

export default Navbar;