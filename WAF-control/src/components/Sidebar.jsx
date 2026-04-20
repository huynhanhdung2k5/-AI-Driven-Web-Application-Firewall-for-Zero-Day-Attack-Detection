import React from 'react';
import { NavLink } from 'react-router-dom';
import { Shield, Activity, LayoutDashboard, Settings, Server } from 'lucide-react';

const Sidebar = () => {
    // Tạo một hàm nhỏ để render class cho NavLink, giúp code gọn gàng hơn
    const navItemClass = ({ isActive }) =>
        `flex items-center gap-[15px] px-5 py-[15px] transition-all duration-300 border-l-4 ${isActive
            ? "bg-[#2563eb] text-white border-[#2563eb] rounded-md  "
            : "text-[#a9b1d6] border-transparent  hover:text-[#2563eb]"
        }`;

    return (
        <aside className="w-65 bg-white  flex flex-col h-full shrink-0">
            <div className="flex items-center gap-2.5 p-5  text-primary">
                <Shield color="#2563eb" size={32} />
                <h2 className="text-xl font-bold m-0">AI-WAF Control</h2>
            </div>

            <nav className="flex flex-col py-5 m-2">
                <NavLink to="/dashboard" className={navItemClass}>
                    <LayoutDashboard size={20} /> Dashboard
                </NavLink>
                <NavLink to="/live-traffic" className={navItemClass}>
                    <Activity size={20} /> Live Traffic
                </NavLink>
                <NavLink to="/asset" className={navItemClass}>
                    <Server size={20} /> Assets
                </NavLink>
                <NavLink to="/settings" className={navItemClass}>
                    <Settings size={20} /> Settings
                </NavLink>
            </nav>
        </aside>
    );
};

export default Sidebar;