"use client";
import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertCircle, Wrench, Truck, MapPin, X } from 'lucide-react';

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
}

export default function FleetPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [trackingData, setTrackingData] = useState<TrackingData | null>(null);
  const [trackingLoading, setTrackingLoading] = useState(false);
  const [showTracking, setShowTracking] = useState(false);

  const trackTruck = async (unit_id: string) => {
    setShowTracking(true);
    setTrackingLoading(true);
    try {
      const res = await fetch(`/api/track/${unit_id}`);
      const data = await res.json();
      setTrackingData(data);
    } catch (e) {
      console.error(e);
    }
    setTrackingLoading(false);
  };

  useEffect(() => {
    fetch('/api/fleet')
      .then(res => res.json())
      .then(data => {
        setVehicles(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);
  return (
    <div className="animate-fade-in" style={{ padding: '40px' }}>
      <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Fleet & Driver Management</h2>
      
      <div className="dashboard-grid" style={{ padding: 0 }}>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header"><span>Active Drivers</span><Truck size={20}/></div>
          <div className="stat-value">18 / 20</div>
          <div className="stat-trend up">90% Utilization</div>
        </div>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header"><span>Upcoming Maintenance</span><Wrench size={20}/></div>
          <div className="stat-value">2</div>
          <div className="stat-trend down">Action Required soon</div>
        </div>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header"><span>Compliance Alerts</span><ShieldAlert size={20}/></div>
          <div className="stat-value">1</div>
          <div className="stat-trend down">IFTA filing due in 3 days</div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <h3 className="widget-title" style={{ marginBottom: '16px' }}>Vehicle Roster</h3>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '16px 8px' }}>Unit ID</th>
                <th>Type</th>
                <th>Assigned Driver</th>
                <th>Odometer</th>
                <th>Next Service</th>
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
                    <td style={{ color: u.status === 'Maintenance' ? 'var(--danger)' : '' }}>{u.service}</td>
                    <td><span className={u.status === 'Active' ? "status-badge delivered" : "status-badge pending"}>{u.status}</span></td>
                    <td>
                      <button 
                        onClick={() => trackTruck(u.unit_id)}
                        style={{ padding: '6px 12px', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
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
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card" style={{ width: '450px', padding: '24px', position: 'relative' }}>
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
    </div>
  );
}
