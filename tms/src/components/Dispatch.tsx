import React, { useState, useEffect } from 'react';
import { Plus, Map, List, Truck, Zap, Calendar, DollarSign, MapPin, Trash2, Settings as SettingsIcon } from 'lucide-react';

interface Load {
  id: number;
  load_id: string;
  origin?: string;
  destination?: string;
  origin_dest?: string;
  pickup_date: string;
  driver?: string;
  rate: string | number;
  status: string;
}

export default function Dispatch() {
  const [view, setView] = useState('list');
  const [loads, setLoads] = useState<Load[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedLoad, setSelectedLoad] = useState<Load | null>(null);
  const [toast, setToast] = useState('');
  const [newLoad, setNewLoad] = useState({ load_id: '', origin_dest: '', pickup_date: '', driver: '', rate: '', status: 'Pending' });
  const [showSettings, setShowSettings] = useState(false);
  const [settingsData, setSettingsData] = useState({ gmail_user: '', gmail_app_password: '' });
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'TBD';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const formatRoute = (load: Load) => {
    let r = load.origin_dest || (load.origin ? `${load.origin} → ${load.destination}` : "Route TBD");
    return r.replace(/\s*\b\d{5}\b/g, '').trim();
  };

  const fetchLoads = () => {
    fetch(`/api/loads`)
      .then(res => res.json())
      .then(data => {
        setLoads(Array.isArray(data) ? data.sort((a: Load, b: Load) => b.id - a.id) : []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchLoads();
    const interval = setInterval(fetchLoads, 10000);
    
    // Fetch settings
    fetch(`/api/settings`)
      .then(res => res.json())
      .then(data => {
        setSettingsData({
          gmail_user: data.gmail_user || '',
          gmail_app_password: data.gmail_app_password || ''
        });
      })
      .catch(console.error);
      
    return () => clearInterval(interval);
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingSettings(true);
    try {
      const res = await fetch(`/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsData)
      });
      if (res.ok) {
        setToast('Settings saved successfully!');
        setShowSettings(false);
        setTimeout(() => setToast(''), 3000);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to save settings');
    }
    setIsSavingSettings(false);
  };

  const handleCreateLoad = (e: React.FormEvent) => {
    e.preventDefault();
    fetch(`/api/loads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newLoad)
    }).then(res => res.json()).then(() => {
      setShowModal(false);
      fetchLoads();
      setNewLoad({ load_id: '', origin_dest: '', pickup_date: '', driver: '', rate: '', status: 'Pending' });
    });
  };

  const handleAutoDispatch = () => {
    fetch(`/api/dispatch/auto`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (data.assignments && data.assignments.length > 0) {
          setToast(`Assigned ${data.assignments.length} loads automatically.`);
        } else {
          setToast('No pending loads or available drivers found.');
        }
        setTimeout(() => setToast(''), 4000);
        fetchLoads();
      });
  };

  const handleDeleteLoad = async (loadId: string) => {
    if (window.confirm('Are you sure you want to delete this load?')) {
      try {
        await fetch(`/api/loads/${encodeURIComponent(loadId)}`, { method: 'DELETE' });
        setToast('Load deleted successfully.');
        setTimeout(() => setToast(''), 4000);
        setSelectedLoad(null);
        fetchLoads();
      } catch (err) {
        console.error('Failed to delete load', err);
      }
    }
  };

  return (
    <div className="animate-fade-in" style={{ padding: '32px 40px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      
      {/* Main Header Section */}
      <div className="widget-header" style={{ marginBottom: '24px', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '4px' }}>Dispatch Board</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Manage loads, assign drivers, and track active shipments.</p>
        </div>
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{ display: 'flex', background: 'var(--bg-surface)', padding: '4px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', gap: '4px' }}>
            <button 
              className="icon-button" 
              onClick={() => setView('list')} 
              style={{ background: view === 'list' ? 'var(--primary-glow)' : 'transparent', color: view === 'list' ? 'var(--primary)' : 'var(--text-secondary)', border: 'none', width: '36px', height: '36px' }}
            >
              <List size={18} />
            </button>
            <button 
              className="icon-button" 
              onClick={() => setView('map')} 
              style={{ background: view === 'map' ? 'var(--primary-glow)' : 'transparent', color: view === 'map' ? 'var(--primary)' : 'var(--text-secondary)', border: 'none', width: '36px', height: '36px' }}
            >
              <Map size={18} />
            </button>
          </div>
          
          <button 
            className="icon-button" 
            onClick={handleAutoDispatch} 
            style={{ width: 'auto', padding: '0 16px', borderRadius: 'var(--radius-md)', gap: '8px', fontSize: '14px', fontWeight: '500' }}
          >
            <Zap size={16} style={{ color: 'var(--primary)' }} /> Auto-Assign
          </button>
          
          <button 
            className="icon-button" 
            onClick={() => setShowSettings(true)} 
            style={{ width: 'auto', padding: '0 16px', borderRadius: 'var(--radius-md)', gap: '8px', fontSize: '14px', fontWeight: '500' }}
          >
            <SettingsIcon size={16} /> Config
          </button>
          
          <button 
            className="icon-button" 
            onClick={() => setShowModal(true)} 
            style={{ width: 'auto', padding: '0 20px', borderRadius: 'var(--radius-md)', background: 'var(--primary)', color: 'var(--bg-base)', border: 'none', gap: '8px', fontSize: '14px', fontWeight: '500', boxShadow: '0 4px 14px var(--primary-glow)' }}
          >
            <Plus size={16} /> New Load
          </button>
        </div>
      </div>

      {toast && (
        <div className="animate-fade-in" style={{ position: 'fixed', bottom: '24px', right: '24px', background: 'var(--bg-surface)', border: '1px solid var(--border-color)', padding: '16px 24px', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '12px', zIndex: 100, boxShadow: '0 10px 25px rgba(0,0,0,0.5)' }}>
          <div style={{ width: '8px', height: '8px', background: 'var(--accent)', borderRadius: '50%' }}></div>
          <span style={{ fontSize: '14px', fontWeight: '500' }}>{toast}</span>
        </div>
      )}

      {/* Content Area */}
      <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '0', overflow: 'hidden' }}>
        {view === 'list' ? (
          <div style={{ flex: 1, overflow: 'auto' }}>
            <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', minWidth: '800px' }}>
              <thead style={{ position: 'sticky', top: 0, background: 'rgba(26, 29, 36, 0.95)', backdropFilter: 'blur(8px)', zIndex: 10 }}>
                <tr style={{ color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  <th style={{ padding: '20px 24px', fontWeight: '600', borderBottom: '1px solid var(--border-color)' }}>Tracking ID</th>
                  <th style={{ padding: '20px 24px', fontWeight: '600', borderBottom: '1px solid var(--border-color)' }}>Route Details</th>
                  <th style={{ padding: '20px 24px', fontWeight: '600', borderBottom: '1px solid var(--border-color)' }}>Pickup Date</th>
                  <th style={{ padding: '20px 24px', fontWeight: '600', borderBottom: '1px solid var(--border-color)' }}>Assigned Driver</th>
                  <th style={{ padding: '20px 24px', fontWeight: '600', borderBottom: '1px solid var(--border-color)' }}>Rate</th>
                  <th style={{ padding: '20px 24px', fontWeight: '600', borderBottom: '1px solid var(--border-color)' }}>Status</th>
                </tr>
              </thead>
              <tbody style={{ fontSize: '14px' }}>
                {loading ? (
                  <tr><td colSpan={6} style={{ padding: '48px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading loads...</td></tr>
                ) : loads.length === 0 ? (
                  <tr><td colSpan={6} style={{ padding: '48px', textAlign: 'center', color: 'var(--text-secondary)' }}>No active loads available.</td></tr>
                ) : (
                  loads.map((load) => (
                    <tr key={load.id} onClick={() => setSelectedLoad(load)} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.2s', cursor: 'pointer' }} onMouseOver={(e) => e.currentTarget.style.background = 'var(--bg-surface-hover)'} onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '16px 24px', fontWeight: '600' }}>{load.load_id}</td>
                      <td style={{ padding: '16px 24px', maxWidth: '300px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <MapPin size={16} style={{ color: 'var(--primary)', flexShrink: 0 }} />
                          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{formatRoute(load)}</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px 24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
                          <Calendar size={16} />
                          <span>{formatDate(load.pickup_date)}</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px 24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: load.driver ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                          <Truck size={16} /> 
                          <span style={{ fontStyle: load.driver ? 'normal' : 'italic' }}>{load.driver || 'Unassigned'}</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px 24px', fontWeight: '500' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <DollarSign size={14} style={{ color: 'var(--accent)' }} />
                          <span>{String(load.rate).replace('$', '')}</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px 24px', maxWidth: '150px' }}>
                        <span className={`status-badge ${load.status === 'Pending' ? 'pending' : 'in-transit'}`} style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'inline-block', maxWidth: '100%' }}>
                          {load.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="map-container" style={{ flex: 1, borderRadius: 0, border: 'none', background: 'var(--bg-base)', position: 'relative' }}>
            <iframe 
              width="100%" 
              height="100%" 
              frameBorder="0" 
              scrolling="no" 
              marginHeight={0} 
              marginWidth={0} 
              src="https://www.google.com/maps/embed?pb=!1m14!1m12!1m3!1d15000000!2d-95.712891!3d37.09024!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!5e0!3m2!1sen!2sus!4v1" 
              style={{ filter: 'invert(90%) hue-rotate(180deg) brightness(85%) contrast(85%)', border: 'none' }}
            ></iframe>
            <div style={{ position: 'absolute', top: '24px', left: '24px', background: 'var(--bg-surface)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', boxShadow: '0 10px 30px rgba(0,0,0,0.5)', zIndex: 10 }}>
              <h4 style={{ fontWeight: '600', marginBottom: '8px' }}>Active Routes</h4>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{loads.length} total loads tracked</p>
            </div>
          </div>
        )}
      </div>


      {/* Modal - Create Load */}
      {showModal && (
        <div className="animate-fade-in" onClick={() => setShowModal(false)} style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '24px' }}>
          <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: '100%', maxWidth: '500px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}>
            
            <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '20px', fontWeight: '600' }}>Create New Load</h3>
              <button onClick={() => setShowModal(false)} className="icon-button" style={{ border: 'none', background: 'transparent' }}>
                <Plus size={24} style={{ transform: 'rotate(45deg)' }} />
              </button>
            </div>
            
            <form onSubmit={handleCreateLoad} style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto', flex: 1 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Tracking Number</label>
                  <input placeholder="Auto-generated if empty" value={newLoad.load_id} onChange={e => setNewLoad({...newLoad, load_id: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} onFocus={(e) => e.target.style.borderColor = 'var(--primary)'} onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'} />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Route Details *</label>
                  <input placeholder="E.g. Los Angeles, CA → Dallas, TX" value={newLoad.origin_dest} onChange={e => setNewLoad({...newLoad, origin_dest: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} required onFocus={(e) => e.target.style.borderColor = 'var(--primary)'} onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Pickup Date *</label>
                    <input placeholder="E.g. Jun 12, 2026" value={newLoad.pickup_date} onChange={e => setNewLoad({...newLoad, pickup_date: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} required onFocus={(e) => e.target.style.borderColor = 'var(--primary)'} onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'} />
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Rate ($) *</label>
                    <input placeholder="4500" value={newLoad.rate} onChange={e => setNewLoad({...newLoad, rate: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} required onFocus={(e) => e.target.style.borderColor = 'var(--primary)'} onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'} />
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Assigned Driver (Optional)</label>
                  <input placeholder="Leave blank for pending status" value={newLoad.driver} onChange={e => setNewLoad({...newLoad, driver: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} onFocus={(e) => e.target.style.borderColor = 'var(--primary)'} onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'} />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                <button type="button" onClick={() => setShowModal(false)} style={{ flex: 1, padding: '12px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-base)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', fontWeight: '600', cursor: 'pointer' }}>
                  Cancel
                </button>
                <button type="submit" style={{ flex: 1, padding: '12px', borderRadius: 'var(--radius-sm)', background: 'var(--primary)', border: 'none', color: 'var(--bg-base)', fontWeight: '600', cursor: 'pointer', boxShadow: '0 4px 14px var(--primary-glow)' }}>
                  Save Load
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal - Settings */}
      {showSettings && (
        <div className="animate-fade-in" onClick={() => setShowSettings(false)} style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '24px' }}>
          <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: '100%', maxWidth: '500px', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}>
            
            <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '20px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <SettingsIcon size={20} className="text-primary" /> System Configuration
              </h3>
              <button onClick={() => setShowSettings(false)} className="icon-button" style={{ border: 'none', background: 'transparent' }}>
                <Plus size={24} style={{ transform: 'rotate(45deg)' }} />
              </button>
            </div>
            
            <form onSubmit={handleSaveSettings} style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                Configure the dispatcher email address used to send out automated Rate Confirmations, Proof of Delivery, and Bill of Lading documents.
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Gmail Address</label>
                  <input type="email" placeholder="dispatcher@company.com" value={settingsData.gmail_user} onChange={e => setSettingsData({...settingsData, gmail_user: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} onFocus={(e) => e.target.style.borderColor = 'var(--primary)'} onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'} required />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>16-Digit App Password</label>
                  <input type="password" placeholder="abcd efgh ijkl mnop" value={settingsData.gmail_app_password} onChange={e => setSettingsData({...settingsData, gmail_app_password: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} onFocus={(e) => e.target.style.borderColor = 'var(--primary)'} onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'} />
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '8px' }}>Generate this in your Google Account Security settings.</p>
                </div>
              </div>

              <div style={{ marginTop: '8px' }}>
                <button type="submit" disabled={isSavingSettings} className="primary-button" style={{ width: '100%', padding: '14px', borderRadius: 'var(--radius-md)', fontWeight: '600', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                  {isSavingSettings ? <div style={{ width: '20px', height: '20px', border: '2px solid rgba(0,0,0,0.3)', borderTopColor: '#000', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div> : 'Save Configuration'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal - Load Details */}
      {selectedLoad && (
        <div className="animate-fade-in" onClick={() => setSelectedLoad(null)} style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '24px' }}>
          <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: '100%', maxWidth: '600px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}>
            
            <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {selectedLoad.load_id}
                  <span className={`status-badge ${selectedLoad.status === 'Pending' ? 'pending' : 'in-transit'}`} style={{ fontSize: '12px' }}>
                    {selectedLoad.status}
                  </span>
                </h3>
              </div>
              <button onClick={() => setSelectedLoad(null)} className="icon-button" style={{ border: 'none', background: 'transparent' }}>
                <Plus size={24} style={{ transform: 'rotate(45deg)' }} />
              </button>
            </div>
            
            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px', overflowY: 'auto', flex: 1 }}>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div style={{ background: 'var(--bg-base)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column' }}>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Route</p>
                  <p style={{ fontWeight: '600', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', alignItems: 'flex-start', gap: '8px', lineHeight: '1.3' }}>
                    <MapPin size={16} className="text-primary" style={{ display: 'inline', marginRight: '4px', position: 'relative', top: '2px' }} /> 
                    {formatRoute(selectedLoad)}
                  </p>
                </div>
                <div style={{ background: 'var(--bg-base)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Scheduled Pickup</p>
                  <p style={{ fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}><Calendar size={16} className="text-primary" /> {formatDate(selectedLoad.pickup_date)}</p>
                </div>
                <div style={{ background: 'var(--bg-base)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Assigned Driver</p>
                  <p style={{ fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}><Truck size={16} className="text-primary" /> {selectedLoad.driver || 'Unassigned'}</p>
                </div>
                <div style={{ background: 'var(--bg-base)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Agreed Rate</p>
                  <p style={{ fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent)' }}><DollarSign size={16} /> {String(selectedLoad.rate).replace('$', '')}</p>
                </div>
              </div>

              {/* Advanced Intelligence Display */}
              {(() => {
                let intel = null;
                try {
                  if ((selectedLoad as any).operational_intelligence) {
                    intel = JSON.parse((selectedLoad as any).operational_intelligence);
                  }
                } catch (e) {}
                
                if (intel && intel.operational_intelligence) {
                  const ops = intel.operational_intelligence;
                  return (
                    <div style={{ marginTop: '4px', background: 'var(--bg-base)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--primary-glow)' }}>
                      <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        🧠 TMS Intelligence Layer
                      </h4>
                      
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                        <div>
                          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Readiness Score:</span>
                          <div style={{ fontWeight: '600', color: ops.dispatch_readiness_score > 80 ? 'var(--accent)' : 'var(--warning)' }}>{ops.dispatch_readiness_score}/100</div>
                        </div>
                        <div>
                          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Risk Level:</span>
                          <div style={{ fontWeight: '600', color: ops.risk_analysis?.classification === 'Low' ? 'var(--accent)' : 'var(--danger)' }}>{ops.risk_analysis?.classification || 'Unknown'}</div>
                        </div>
                      </div>

                      <div style={{ marginBottom: '16px', background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                        <span style={{ fontSize: '11px', fontWeight: '600', textTransform: 'uppercase', color: 'var(--text-secondary)', letterSpacing: '0.5px' }}>Dispatcher Summary</span>
                        <p style={{ fontSize: '13px', lineHeight: '1.6', marginTop: '6px', color: 'var(--text-primary)' }}>{ops.dispatcher_summary}</p>
                      </div>

                      {ops.alerts && ops.alerts.length > 0 && (
                        <div>
                          <span style={{ fontSize: '11px', fontWeight: '600', textTransform: 'uppercase', color: 'var(--text-secondary)', letterSpacing: '0.5px' }}>Actionable Alerts</span>
                          <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px', fontSize: '13px', color: 'var(--warning)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {ops.alerts.map((alert: string, i: number) => <li key={i} style={{ lineHeight: '1.4' }}>{alert}</li>)}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              })()}

              {/* Load Trip Timeline */}
              {(selectedLoad as any).temp_logs && (selectedLoad as any).temp_logs.length > 0 && (
                <div style={{ marginBottom: '16px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-secondary)' }}>Trip Timeline</h4>
                  <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {((selectedLoad as any).temp_logs || []).map((log: any, idx: number) => (
                      <div key={log.id || idx} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary)', marginTop: '6px', flexShrink: 0 }}></div>
                        <div>
                          <p style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Driver Response: <span style={{ fontWeight: '600' }}>"{log.driver_response}"</span></p>
                          <p style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{new Date(log.timestamp + 'Z').toLocaleString()}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-secondary)' }}>Attached Documents</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ background: 'var(--primary-glow)', padding: '8px', borderRadius: '4px', color: 'var(--primary)' }}>
                        <List size={20} />
                      </div>
                      <div>
                        <p style={{ fontWeight: '500', fontSize: '14px' }}>Original_Rate_Confirmation.pdf</p>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Uploaded by HAUL-E Bot</p>
                      </div>
                    </div>
                    <button 
                      onClick={() => {
                        if ((selectedLoad as any).document_url) {
                          window.open((selectedLoad as any).document_url, '_blank');
                        } else {
                          alert("Document not found. This load was created before file storage was enabled.");
                        }
                      }}
                      className="icon-button" style={{ padding: '6px 12px', fontSize: '12px', border: '1px solid var(--border-color)', background: 'transparent' }}>View</button>
                  </div>

                  {/* BOL Document */}
                  {(selectedLoad as any).bol_path && (
                    <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ background: 'rgba(39, 201, 63, 0.1)', padding: '8px', borderRadius: '4px', color: '#27c93f' }}>
                          <List size={20} />
                        </div>
                        <div>
                          <p style={{ fontWeight: '500', fontSize: '14px' }}>Bill_of_Lading (BOL)</p>
                          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Uploaded by Driver</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => {
                          const url = (selectedLoad as any).bol_path.replace('/home/no_one/Desktop/broker-bot/uploads', `${import.meta.env.VITE_API_URL}/uploads`);
                          window.open(url, '_blank');
                        }}
                        className="icon-button" style={{ padding: '6px 12px', fontSize: '12px', border: '1px solid var(--border-color)', background: 'transparent' }}>View</button>
                    </div>
                  )}

                  {/* POD Document */}
                  {(selectedLoad as any).pod_path && (
                    <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ background: 'rgba(255, 189, 46, 0.1)', padding: '8px', borderRadius: '4px', color: '#ffbd2e' }}>
                          <List size={20} />
                        </div>
                        <div>
                          <p style={{ fontWeight: '500', fontSize: '14px' }}>Proof_of_Delivery (POD)</p>
                          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Uploaded by Driver</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => {
                          const url = (selectedLoad as any).pod_path.replace('/home/no_one/Desktop/broker-bot/uploads', `${import.meta.env.VITE_API_URL}/uploads`);
                          window.open(url, '_blank');
                        }}
                        className="icon-button" style={{ padding: '6px 12px', fontSize: '12px', border: '1px solid var(--border-color)', background: 'transparent' }}>View</button>
                    </div>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
                <button 
                  onClick={() => handleDeleteLoad(selectedLoad.load_id)} 
                  style={{ padding: '8px 16px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: '500', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s' }}
                  onMouseOver={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)'}
                  onMouseOut={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
                >
                  <Trash2 size={16} /> Delete Load
                </button>
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
}
