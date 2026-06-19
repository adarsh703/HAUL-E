import React, { useState, useEffect } from 'react';
import { ShieldAlert, Wrench, Truck, MapPin, X, Plus } from 'lucide-react';

interface TrackingData {
  unit_id: string;
  driver: string;
  location: string;
  speed: number;
  status: string;
  hos: number;
}

interface Vehicle {
  id: number;
  unit_id: string;
  type: string;
  driver: string;
  miles: string;
  service: string;
  status: string;
  current_load?: string;
}

export default function Fleet() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [trackingData, setTrackingData] = useState<TrackingData | null>(null);
  const [trackingLoading, setTrackingLoading] = useState(false);
  const [showTracking, setShowTracking] = useState(false);

  const trackTruck = async (unit_id: string) => {
    setShowTracking(true);
    setTrackingLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/track/${unit_id}`);
      const data = await res.json();
      setTrackingData(data);
    } catch (e) {
      console.error(e);
    }
    setTrackingLoading(false);
  };

  const [showAddModal, setShowAddModal] = useState(false);
  const [newVehicle, setNewVehicle] = useState({ unit_id: '', type: 'Dry Van', driver: '', miles: '0', service: '', status: 'Active' });

  const fetchVehicles = () => {
    fetch(`${import.meta.env.VITE_API_URL}/api/fleet`)
      .then(res => res.json())
      .then(data => {
        setVehicles(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  const handleCreateVehicle = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/api/fleet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newVehicle)
      });
      setShowAddModal(false);
      setNewVehicle({ unit_id: '', type: 'Dry Van', driver: '', miles: '0', service: '', status: 'Active' });
      fetchVehicles();
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchVehicles();
  }, []);
  const totalVehicles = vehicles.length;
  const activeDriversCount = vehicles.filter(v => v.driver && v.driver !== 'Unassigned').length;
  const utilization = totalVehicles > 0 ? Math.round((activeDriversCount / totalVehicles) * 100) : 0;
  const maintenanceCount = vehicles.filter(v => v.status === 'Maintenance').length;

  return (
    <div className="animate-fade-in" style={{ padding: '40px' }}>
      <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Fleet & Driver Management</h2>
      
      <div className="dashboard-grid" style={{ padding: 0 }}>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header"><span>Active Drivers</span><Truck size={20}/></div>
          <div className="stat-value">{activeDriversCount} / {totalVehicles}</div>
          <div className="stat-trend up">{utilization}% Utilization</div>
        </div>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header"><span>Upcoming Maintenance</span><Wrench size={20}/></div>
          <div className="stat-value">{maintenanceCount}</div>
          <div className={maintenanceCount > 0 ? "stat-trend down" : "stat-trend up"}>
            {maintenanceCount > 0 ? "Action Required soon" : "All clear"}
          </div>
        </div>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header"><span>Compliance Alerts</span><ShieldAlert size={20}/></div>
          <div className="stat-value">0</div>
          <div className="stat-trend up">All fleets compliant</div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 className="widget-title" style={{ marginBottom: 0 }}>Vehicle Roster</h3>
            <button 
              onClick={() => setShowAddModal(true)}
              style={{ padding: '8px 16px', background: 'var(--primary)', color: 'var(--bg-base)', border: 'none', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: '500', fontSize: '14px' }}>
              <Plus size={16} /> Add Truck
            </button>
          </div>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '16px 8px' }}>Unit ID</th>
                <th>Type</th>
                <th>Assigned Driver</th>
                <th>Odometer</th>
                <th>Active Load</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} style={{ padding: '16px', textAlign: 'center' }}>Loading...</td></tr>
              ) : (
                vehicles.map(u => (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '16px 8px', fontWeight: 'bold' }}>{u.unit_id}</td>
                    <td>{u.type}</td>
                    <td>{u.driver}</td>
                    <td>{u.miles}</td>
                    <td>
                      {u.current_load && u.current_load !== 'None' ? (
                        <span style={{ color: 'var(--primary)', fontWeight: '500' }}>{u.current_load}</span>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)' }}>No Load</span>
                      )}
                    </td>
                    <td><span className={u.status === 'Active' ? "status-badge delivered" : "status-badge pending"}>{u.status}</span></td>
                    <td>
                      <button 
                        onClick={() => trackTruck(u.unit_id)}
                        style={{ padding: '6px 12px', background: 'var(--primary)', color: 'var(--bg-base)', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <MapPin size={14}/> Track
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showTracking && (
        <div onClick={() => {setShowTracking(false); setTrackingData(null);}} style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: '450px', padding: '24px', position: 'relative' }}>
            <button 
              onClick={() => {setShowTracking(false); setTrackingData(null);}} 
              style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <X size={20}/>
            </button>
            
            <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MapPin className="text-primary"/> Live ELD Tracking
            </h3>

            {trackingLoading || !trackingData ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Connecting to satellite...</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Unit ID</div>
                    <div style={{ fontWeight: 'bold' }}>{trackingData.unit_id}</div>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Driver</div>
                    <div style={{ fontWeight: 'bold' }}>{trackingData.driver}</div>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Current GPS Location</div>
                  <div style={{ fontWeight: 'bold', fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <MapPin size={16} color="var(--primary)"/> {trackingData.location}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Speed</div>
                    <div style={{ fontWeight: 'bold', color: trackingData.speed > 0 ? 'var(--primary)' : 'var(--text-primary)' }}>{trackingData.speed} mph</div>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Engine</div>
                    <div style={{ fontWeight: 'bold', color: trackingData.status === 'Driving' ? 'var(--primary)' : 'var(--danger)' }}>{trackingData.status}</div>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>HOS Left</div>
                    <div style={{ fontWeight: 'bold', color: trackingData.hos < 3 ? 'var(--danger)' : 'var(--text-primary)' }}>{trackingData.hos} hrs</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal - Add Vehicle */}
      {showAddModal && (
        <div className="animate-fade-in" onClick={() => setShowAddModal(false)} style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '24px' }}>
          <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: '100%', maxWidth: '500px', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}>
            <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '20px', fontWeight: '600' }}>Add New Truck & Driver</h3>
              <button onClick={() => setShowAddModal(false)} className="icon-button" style={{ border: 'none', background: 'transparent' }}>
                <X size={24} />
              </button>
            </div>
            <form onSubmit={handleCreateVehicle} style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Unit ID *</label>
                  <input placeholder="E.g. T-405" value={newVehicle.unit_id} onChange={e => setNewVehicle({...newVehicle, unit_id: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} required />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Assigned Driver *</label>
                  <input placeholder="Driver Name" value={newVehicle.driver} onChange={e => setNewVehicle({...newVehicle, driver: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} required />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Equipment Type</label>
                  <input placeholder="E.g. Dry Van, Reefer" value={newVehicle.type} onChange={e => setNewVehicle({...newVehicle, type: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} required />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Status</label>
                  <select value={newVehicle.status} onChange={e => setNewVehicle({...newVehicle, status: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }}>
                    <option value="Active">Active</option>
                    <option value="Maintenance">Maintenance</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Odometer</label>
                  <input placeholder="Current Miles" value={newVehicle.miles} onChange={e => setNewVehicle({...newVehicle, miles: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} required />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', display: 'block' }}>Next Service Date</label>
                  <input placeholder="MM/DD/YYYY" value={newVehicle.service} onChange={e => setNewVehicle({...newVehicle, service: e.target.value})} style={{ width: '100%', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', color: 'var(--text-primary)', outline: 'none', fontSize: '14px' }} required />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                <button type="button" onClick={() => setShowAddModal(false)} style={{ flex: 1, padding: '12px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-base)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', fontWeight: '600', cursor: 'pointer' }}>Cancel</button>
                <button type="submit" style={{ flex: 1, padding: '12px', borderRadius: 'var(--radius-sm)', background: 'var(--primary)', border: 'none', color: 'var(--bg-base)', fontWeight: '600', cursor: 'pointer', boxShadow: '0 4px 14px var(--primary-glow)' }}>Save Truck</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
