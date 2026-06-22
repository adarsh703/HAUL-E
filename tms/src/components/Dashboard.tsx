import { useState, useEffect } from 'react';
import { TrendingUp, AlertCircle, CheckCircle2, Package, MapPin, Truck, Calendar, DollarSign, List, Plus, Trash2 } from 'lucide-react';
import LiveMap from './LiveMap';

interface Load {
  id: number;
  load_id: string;
  origin?: string;
  destination?: string;
  origin_dest?: string;
  pickup_date: string;
  driver: string;
  rate: string;
  status: string;
}

interface Vehicle {
  id: number;
  unit_id: string;
  type: string;
  driver: string;
  miles: string;
  service: string;
  status: string;
}

export default function Dashboard({ onNavigate: _onNavigate }: { onNavigate?: (tab: string) => void }) {
  const [loads, setLoads] = useState<Load[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [selectedLoad, setSelectedLoad] = useState<Load | null>(null);

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

  const fetchData = () => {
    fetch(`/api/loads`)
      .then(res => res.json())
      .then(data => setLoads(Array.isArray(data) ? data : []))
      .catch(console.error);
    fetch(`/api/fleet`)
      .then(res => res.json())
      .then(data => setVehicles(Array.isArray(data) ? data : []))
      .catch(console.error);
  };

  const handleDeleteLoad = async (loadId: string) => {
    if (window.confirm('Are you sure you want to delete this load?')) {
      try {
        await fetch(`/api/loads/${encodeURIComponent(loadId)}`, { method: 'DELETE' });
        setSelectedLoad(null);
        fetchData();
      } catch (err) {
        console.error('Failed to delete load', err);
      }
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const activeLoads = loads.filter(l => !['Delivered', 'Invoiced'].includes(l.status));
  const activeVehicles = vehicles.filter(v => v.status === 'Active');
  const maintenanceVehicles = vehicles.filter(v => v.status === 'Maintenance');

  // Calculate total projected profit from all loads
  const totalRate = loads.reduce((sum, l) => {
    const num = parseFloat(String(l.rate).replace(/[$,]/g, '')) || 0;
    return sum + num;
  }, 0);
  const projectedProfit = totalRate * 0.20; // ~20% margin

  const getStateCode = (load: Load) => {
    const originStr = load.origin_dest || load.origin || '';
    if (!originStr) return '??';
    const match = String(originStr).match(/,\s*([A-Z]{2})/);
    if (match) return match[1];
    const fallbackMatch = String(originStr).match(/\b([A-Z]{2})\b/);
    return fallbackMatch ? fallbackMatch[1] : '??';
  };

  const formatRoute = (load: Load) => {
    let r = load.origin_dest || (load.origin ? `${load.origin} → ${load.destination}` : "Route TBD");
    return r.replace(/\s*\b\d{5}\b/g, '').trim();
  };

  // Recent loads = last 10 loads reversed (newest first)
  const recentLoads = [...loads].reverse().slice(0, 10);



  return (
    <div className="dashboard-grid animate-fade-in">
      {/* Stat Cards */}
      <div className="card stat-card">
        <div className="stat-header">
          <span>Active Loads</span>
          <div className="stat-icon primary"><Package size={20} /></div>
        </div>
        <div className="stat-value">{activeLoads.length}</div>
        <div className="stat-trend up">
          <TrendingUp size={14} />
          <span>{loads.length} total loads</span>
        </div>
      </div>

      <div className="card stat-card delay-1">
        <div className="stat-header">
          <span>Fleet Health</span>
          <div className="stat-icon success"><CheckCircle2 size={20} /></div>
        </div>
        <div className="stat-value">{vehicles.length > 0 ? Math.round((activeVehicles.length / vehicles.length) * 100) : 0}%</div>
        <div className="stat-trend up">
          <TrendingUp size={14} />
          <span>{activeVehicles.length} / {vehicles.length} units active</span>
        </div>
      </div>

      <div className="card stat-card delay-2">
        <div className="stat-header">
          <span>Projected Profit</span>
          <div className="stat-icon primary"><TrendingUp size={20} /></div>
        </div>
        <div className="stat-value">${projectedProfit.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
        <div className="stat-trend up">
          <TrendingUp size={14} />
          <span>~20% margin on ${totalRate.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        </div>
      </div>

      <div className="card stat-card delay-3">
        <div className="stat-header">
          <span>Alerts</span>
          <div className="stat-icon danger"><AlertCircle size={20} /></div>
        </div>
        <div className="stat-value">{maintenanceVehicles.length}</div>
        <div className="stat-trend down">
          <TrendingUp size={14} style={{ transform: 'rotate(180deg)' }} />
          <span>{maintenanceVehicles.length} truck(s) need service</span>
        </div>
      </div>

      {/* Map Widget */}
      <div className="card main-widget delay-1" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="widget-header">
          <h3 className="widget-title">Live Dispatch Map</h3>
          <span className="status-badge in-transit">Tracking {activeLoads.length} Active Routes</span>
        </div>
        <div className="map-container" style={{ padding: 0, flex: 1, minHeight: '400px', zIndex: 0 }}>
          <LiveMap />
        </div>
      </div>

      {/* Recent Activity Widget */}
      <div className="card side-widget delay-2">
        <div className="widget-header">
          <h3 className="widget-title">Recent Loads</h3>
        </div>
        <div className="activity-list" style={{ overflowY: 'auto', maxHeight: '400px', paddingRight: '4px' }}>
          {recentLoads.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-secondary)' }}>No loads yet</div>
          ) : (
            recentLoads.map(load => (
              <div className="list-item" key={load.id} onClick={() => setSelectedLoad(load)} style={{ cursor: 'pointer', transition: 'background 0.2s' }} onMouseOver={(e) => e.currentTarget.style.background = 'var(--bg-surface-hover)'} onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}>
                <div className="item-left" style={{ flex: 1, minWidth: 0, paddingRight: '16px' }}>
                  <div className="item-avatar" style={{
                    background: load.status === 'Delivered' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(99, 102, 241, 0.1)',
                    color: load.status === 'Delivered' ? 'var(--accent)' : 'var(--primary)'
                  }}>
                    {getStateCode(load)}
                  </div>
                  <div className="item-info" style={{ minWidth: 0, overflow: 'hidden' }}>
                    <h4 style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', lineHeight: '1.2' }}>{formatRoute(load)}</h4>
                    <p style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Driver: {load.driver} • {load.load_id}</p>
                  </div>
                </div>
                <span className={
                  load.status === 'Delivered' || load.status === 'Invoiced' ? "status-badge delivered" :
                  load.status === 'In Transit' ? "status-badge in-transit" :
                  load.status === 'Assigned' ? "status-badge assigned" :
                  "status-badge unassigned"
                }>{load.status}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Modal - Load Details */}
      {selectedLoad && (
        <div className="animate-fade-in" onClick={() => setSelectedLoad(null)} style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', zIndex: 1000, padding: '24px', overflowY: 'auto' }}>
          <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: '100%', maxWidth: '600px', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.5)', margin: 'auto', marginTop: '40px', marginBottom: '40px', flexShrink: 0 }}>
            
            <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {selectedLoad.load_id}
                  <span className={`status-badge ${['Delivered', 'Invoiced'].includes(selectedLoad.status) ? 'delivered' : selectedLoad.status === 'In Transit' ? 'in-transit' : selectedLoad.status === 'Assigned' ? 'assigned' : 'unassigned'}`} style={{ fontSize: '12px' }}>
                    {selectedLoad.status}
                  </span>
                </h3>
              </div>
              <button onClick={() => setSelectedLoad(null)} className="icon-button" style={{ border: 'none', background: 'transparent' }}>
                <Plus size={24} style={{ transform: 'rotate(45deg)' }} />
              </button>
            </div>
            
            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div style={{ background: 'var(--bg-base)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column' }}>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Route</p>
                  <p style={{ fontWeight: '600', wordBreak: 'break-word', alignItems: 'flex-start', gap: '8px', lineHeight: '1.3' }}>
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                      <div style={{ background: 'var(--primary-glow)', padding: '8px', borderRadius: '4px', color: 'var(--primary)', flexShrink: 0 }}>
                        <List size={20} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontWeight: '500', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Original_Rate_Confirmation.pdf</p>
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
                      className="icon-button" style={{ padding: '6px 12px', fontSize: '12px', border: '1px solid var(--border-color)', background: 'transparent', flexShrink: 0, marginLeft: '8px' }}>View</button>
                  </div>

                  {/* BOL Document */}
                  {(selectedLoad as any).bol_path && (
                    <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                        <div style={{ background: 'rgba(39, 201, 63, 0.1)', padding: '8px', borderRadius: '4px', color: '#27c93f', flexShrink: 0 }}>
                          <List size={20} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontWeight: '500', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Bill_of_Lading (BOL)</p>
                          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Uploaded by Driver</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => {
                          const url = (selectedLoad as any).bol_path.replace('/home/no_one/Desktop/broker-bot/uploads', `${import.meta.env.VITE_API_URL}/uploads`);
                          window.open(url, '_blank');
                        }}
                        className="icon-button" style={{ padding: '6px 12px', fontSize: '12px', border: '1px solid var(--border-color)', background: 'transparent', flexShrink: 0, marginLeft: '8px' }}>View</button>
                    </div>
                  )}

                  {/* POD Document */}
                  {(selectedLoad as any).pod_path && (
                    <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                        <div style={{ background: 'rgba(255, 189, 46, 0.1)', padding: '8px', borderRadius: '4px', color: '#ffbd2e', flexShrink: 0 }}>
                          <List size={20} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontWeight: '500', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Proof_of_Delivery (POD)</p>
                          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Uploaded by Driver</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => {
                          const url = `${import.meta.env.VITE_API_URL}/${(selectedLoad as any).pod_path}`;
                          window.open(url, '_blank');
                        }}
                        className="icon-button" style={{ padding: '6px 12px', fontSize: '12px', border: '1px solid var(--border-color)', background: 'transparent', flexShrink: 0, marginLeft: '8px' }}>View</button>
                    </div>
                  )}

                  {/* Invoice Document */}
                  {(selectedLoad as any).invoice_path && (
                    <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                        <div style={{ background: 'rgba(168, 85, 247, 0.1)', padding: '8px', borderRadius: '4px', color: '#a855f7', flexShrink: 0 }}>
                          <List size={20} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontWeight: '500', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Customer_Invoice</p>
                          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Auto-generated by HAUL-E</p>
                        </div>
                      </div>
                      <button 
                        onClick={() => {
                          const url = `${import.meta.env.VITE_API_URL}/${(selectedLoad as any).invoice_path}`;
                          window.open(url, '_blank');
                        }}
                        className="icon-button" style={{ padding: '6px 12px', fontSize: '12px', border: '1px solid var(--border-color)', background: 'transparent', flexShrink: 0, marginLeft: '8px' }}>View</button>
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
