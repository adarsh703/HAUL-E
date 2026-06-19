"use client";
import React, { useState } from 'react';
import { Search, Bell, User, Settings, LogOut } from 'lucide-react';

export default function TopHeader() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      alert(`Searching the HAUL-E database for: ${searchQuery}`);
      setSearchQuery('');
    }
  };

  return (
    <header className="top-header" style={{ position: 'relative', zIndex: 50 }}>
      <div className="search-bar">
        <Search size={18} className="text-secondary" />
        <input 
          type="text" 
          placeholder="Search loads, drivers, or invoices... (Press Enter)" 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleSearch}
          style={{ width: '100%', background: 'transparent', border: 'none', outline: 'none', color: 'white' }}
        />
      </div>
      
      <div className="header-actions" style={{ position: 'relative' }}>
        <button className="icon-button" onClick={() => { setShowNotifications(!showNotifications); setShowProfile(false); }}>
          <Bell size={20} />
          <span className="badge">3</span>
        </button>
        
        {/* Notifications Dropdown */}
        {showNotifications && (
          <div className="card animate-fade-in" style={{ position: 'absolute', top: '120%', right: '50px', width: '320px', padding: '16px', zIndex: 100, boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}>
            <h4 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '12px' }}>Notifications</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary)', marginTop: '6px' }}></div>
                <div>
                  <p style={{ fontSize: '14px' }}>Load #L-8042 Delivered</p>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>2 mins ago</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--danger)', marginTop: '6px' }}></div>
                <div>
                  <p style={{ fontSize: '14px' }}>UNIT-102 Needs Maintenance</p>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>1 hour ago</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent)', marginTop: '6px' }}></div>
                <div>
                  <p style={{ fontSize: '14px' }}>Rate Confirmation Processed</p>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>3 hours ago</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="item-avatar" onClick={() => { setShowProfile(!showProfile); setShowNotifications(false); }} style={{ cursor: 'pointer', background: 'var(--primary)', color: 'white' }}>
          JD
        </div>
        
        {/* Profile Dropdown */}
        {showProfile && (
          <div className="card animate-fade-in" style={{ position: 'absolute', top: '120%', right: '0', width: '220px', padding: '16px', zIndex: 100, boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
              <div className="item-avatar" style={{ background: 'var(--primary)', color: 'white' }}>JD</div>
              <div>
                <p style={{ fontWeight: '600' }}>John Doe</p>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Dispatcher</p>
              </div>
            </div>
            
            <button className="icon-button" onClick={() => alert('Opening Profile Settings')} style={{ width: '100%', justifyContent: 'flex-start', background: 'transparent', border: 'none', padding: '8px', gap: '12px' }}>
              <User size={16} /> My Profile
            </button>
            <button className="icon-button" onClick={() => alert('Opening System Settings')} style={{ width: '100%', justifyContent: 'flex-start', background: 'transparent', border: 'none', padding: '8px', gap: '12px' }}>
              <Settings size={16} /> Preferences
            </button>
            <button className="icon-button" onClick={() => alert('Logging out...')} style={{ width: '100%', justifyContent: 'flex-start', background: 'transparent', border: 'none', padding: '8px', gap: '12px', color: 'var(--danger)' }}>
              <LogOut size={16} /> Sign Out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
