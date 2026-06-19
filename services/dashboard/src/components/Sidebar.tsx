"use client";
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Truck, MapPin, BarChart3, FileScan, Settings } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-logo">
          <Truck size={28} className="text-primary" />
          Haul-E TMS
        </div>
      </div>
      <nav className="sidebar-nav">
        <Link href="/" className={`nav-item ${pathname === '/' ? 'active' : ''}`}>
          <LayoutDashboard size={20} /> Dashboard
        </Link>
        <Link href="/dispatch" className={`nav-item ${pathname === '/dispatch' ? 'active' : ''}`}>
          <MapPin size={20} /> Dispatch Map
        </Link>
        <Link href="/fleet" className={`nav-item ${pathname === '/fleet' ? 'active' : ''}`}>
          <Truck size={20} /> Fleet Management
        </Link>
        <Link href="/profits" className={`nav-item ${pathname === '/profits' ? 'active' : ''}`}>
          <BarChart3 size={20} /> Profit Predictor
        </Link>
        <Link href="/documents" className={`nav-item ${pathname === '/documents' ? 'active' : ''}`}>
          <FileScan size={20} /> Document OCR
        </Link>
        <div style={{ flex: 1 }}></div>
        <a href="#" className="nav-item">
          <Settings size={20} /> Settings
        </a>
      </nav>
    </aside>
  );
}
