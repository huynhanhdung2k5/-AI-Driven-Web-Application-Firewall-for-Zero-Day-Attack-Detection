import React, { UseEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Search, Bell, User } from 'lucide-react';

const Navbar = ({ title }) => {
    return (
        <header className="bg-white h-17.5 border-b border-gray-100 flex items-center justify-between px-7.5 shrink-0 shadow-sm z-10">
            {/* Tiêu đề trang (Sử dụng màu primary) */}
            <h1 className="text-xl font-bold text-primary">{title}</h1>


        </header>
    );
};

export default Navbar;