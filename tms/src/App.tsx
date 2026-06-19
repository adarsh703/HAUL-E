import { useState } from 'react';
import { LayoutDashboard, Truck, MapPin, BarChart3, Settings, Bell, Search } from 'lucide-react';
import './index.css';
import Dashboard from './components/Dashboard';
import Dispatch from './components/Dispatch';
import Fleet from './components/Fleet';
import ProfitPredictor from './components/ProfitPredictor';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-logo">
            <Truck size={28} className="text-primary" />
            Haul-E TMS
          </div>
        </div>
        <nav className="sidebar-nav">
          <a href="#" className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); setActiveTab('dashboard'); }}>
            <LayoutDashboard size={20} /> Dashboard
          </a>
          <a href="#" className={`nav-item ${activeTab === 'dispatch' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); setActiveTab('dispatch'); }}>
            <MapPin size={20} /> Dispatch Map
          </a>
          <a href="#" className={`nav-item ${activeTab === 'fleet' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); setActiveTab('fleet'); }}>
            <Truck size={20} /> Fleet Management
          </a>
          <a href="#" className={`nav-item ${activeTab === 'profits' ? 'active' : ''}`} onClick={(e) => { e.preventDefault(); setActiveTab('profits'); }}>
            <BarChart3 size={20} /> Profit Predictor
          </a>
          <div style={{ flex: 1 }}></div>
          <a href="#" className="nav-item" onClick={(e) => { e.preventDefault(); setShowSettings(true); }}>
            <Settings size={20} /> Settings
          </a>
        </nav>
      </aside>

      <main className="main-content" style={{ position: 'relative' }}>
        <header className="top-header">
          <div className="search-bar">
            <Search size={18} className="text-secondary" />
            <input 
              type="text" 
              placeholder="Search loads, drivers, or invoices..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="header-actions">
            <button className="icon-button" onClick={() => setShowNotifications(true)}>
              <Bell size={20} />
              <span className="badge">3</span>
            </button>
            <div className="item-avatar" onClick={() => setShowProfile(true)} style={{ cursor: 'pointer', background: 'var(--bg-surface-hover)' }}>JD</div>
          </div>
        </header>

        {searchQuery ? (
          <div style={{ padding: '40px' }}>
            <h2 style={{ marginBottom: '24px' }}>Search Results for "{searchQuery}"</h2>
            <div className="card">
              <p style={{ color: 'var(--text-secondary)' }}>No results found matching your query.</p>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'dashboard' && <Dashboard onNavigate={setActiveTab} />}
            {activeTab === 'dispatch' && <Dispatch />}
            {activeTab === 'fleet' && <Fleet />}
            {activeTab === 'profits' && <ProfitPredictor />}
          </>
        )}

        {/* Settings Modal */}
        {showSettings && (
          <div className="animate-fade-in" style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '24px' }}>
            <div className="card" style={{ width: '100%', maxWidth: '500px' }}>
              <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '20px' }}>Settings</h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>Settings integration is currently in development.</p>
              <button onClick={() => setShowSettings(false)} className="icon-button" style={{ width: '100%', padding: '12px', borderRadius: '8px', background: 'var(--primary)', color: 'var(--bg-base)', border: 'none', cursor: 'pointer' }}>Close</button>
            </div>
          </div>
        )}

        {/* Notifications Modal */}
        {showNotifications && (
          <div className="animate-fade-in" style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '24px' }}>
            <div className="card" style={{ width: '100%', maxWidth: '500px' }}>
              <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '20px' }}>Notifications</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                <div style={{ padding: '12px', background: 'var(--bg-base)', borderRadius: '8px', borderLeft: '4px solid var(--accent)' }}>
                  <p style={{ fontSize: '14px', fontWeight: '500' }}>Load #L-12345 delivered successfully</p>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>2 hours ago</p>
                </div>
                <div style={{ padding: '12px', background: 'var(--bg-base)', borderRadius: '8px', borderLeft: '4px solid var(--primary)' }}>
                  <p style={{ fontSize: '14px', fontWeight: '500' }}>New route assignment available</p>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>5 hours ago</p>
                </div>
                <div style={{ padding: '12px', background: 'var(--bg-base)', borderRadius: '8px', borderLeft: '4px solid var(--danger)' }}>
                  <p style={{ fontSize: '14px', fontWeight: '500' }}>Vehicle UNIT-102 requires maintenance</p>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>1 day ago</p>
                </div>
              </div>
              <button onClick={() => setShowNotifications(false)} className="icon-button" style={{ width: '100%', padding: '12px', borderRadius: '8px', background: 'var(--primary)', color: 'var(--bg-base)', border: 'none', cursor: 'pointer' }}>Close</button>
            </div>
          </div>
        )}

        {/* Profile Modal */}
        {showProfile && (
          <div className="animate-fade-in" style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '24px' }}>
            <div className="card" style={{ width: '100%', maxWidth: '400px', textAlign: 'center' }}>
              <div className="item-avatar" style={{ width: '80px', height: '80px', fontSize: '24px', margin: '0 auto 16px', background: 'var(--primary-glow)', color: 'var(--primary)' }}>JD</div>
              <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '4px' }}>John Doe</h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>Dispatcher</p>
              <button onClick={() => setShowProfile(false)} className="icon-button" style={{ width: '100%', padding: '12px', borderRadius: '8px', background: 'var(--primary)', color: 'var(--bg-base)', border: 'none', cursor: 'pointer' }}>Close</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
export default App;
