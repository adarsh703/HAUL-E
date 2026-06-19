"use client";
import React, { useState, useEffect } from 'react';
import { TrendingUp, AlertCircle, CheckCircle2, Package, MapPin, Truck } from 'lucide-react';
import LiveMap from '@/components/LiveMap';

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

interface Vehicle {
  id: number;
  unit_id: string;
  type: string;
  driver: string;
  miles: string;
  service: string;
  status: string;
}

import { useRouter } from 'next/navigation';

export default function Dashboard() {
  const router = useRouter();
  const [loads, setLoads] = useState<Load[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);

  const fetchData = () => {
    fetch('/api/loads')
      .then(res => res.json())
      .then(data => setLoads(Array.isArray(data) ? data : []))
      .catch(console.error);
    fetch('/api/fleet')
      .then(res => res.json())
      .then(data => setVehicles(Array.isArray(data) ? data : []))
      .catch(console.error);
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const activeLoads = loads.filter(l => l.status !== 'Delivered');
  const activeVehicles = vehicles.filter(v => v.status === 'Active');
  const maintenanceVehicles = vehicles.filter(v => v.status === 'Maintenance');

  // Calculate total projected profit from all loads
  const totalRate = loads.reduce((sum, l) => {
    const rateStr = String(l.rate || 0);
    const num = parseFloat(rateStr.replace(/[$,]/g, '')) || 0;
    return sum + num;
  }, 0);
  const projectedProfit = totalRate * 0.20; // ~20% margin

  // Get state abbreviation from origin
  const getStateCode = (originDest: string) => {
    if (!originDest) return '??';
    const match = originDest.match(/,\s*([A-Z]{2})/);
    return match ? match[1] : '??';
  };

  // Recent loads = last 5 loads reversed (newest first)
  const recentLoads = [...loads].reverse().slice(0, 5);

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
      <div className="card main-widget delay-1">
        <div className="widget-header">
          <h3 className="widget-title">Live Dispatch Map</h3>
          <button onClick={() => router.push('/dispatch')} className="icon-button" style={{ width: 'auto', padding: '0 12px', borderRadius: '8px', fontSize: '13px', background: 'var(--primary)', color: 'white', border: 'none', cursor: 'pointer' }}>
            Assign Load
          </button>
        </div>
        <div className="map-container" style={{ padding: 0, overflow: 'hidden' }}>
          <LiveMap loads={loads} />
        </div>
      </div>

      {/* Recent Activity Widget */}
      <div className="card side-widget delay-2">
        <div className="widget-header">
          <h3 className="widget-title">Recent Loads</h3>
        </div>
        <div className="list-container">
          {recentLoads.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-secondary)' }}>No loads yet</div>
          ) : (
            recentLoads.map(load => {
              const route = load.origin_dest || `${load.origin} → ${load.destination}`;
              return (
              <div className="list-item" key={load.id}>
                <div className="item-left">
                  <div className="item-avatar" style={{
                    background: load.status === 'Delivered' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(99, 102, 241, 0.1)',
                    color: load.status === 'Delivered' ? 'var(--accent)' : 'var(--primary)'
                  }}>
                    {getStateCode(route)}
                  </div>
                  <div className="item-info">
                    <h4>{route}</h4>
                    <p>Driver: {load.driver || 'Unassigned'} • {load.load_id}</p>
                  </div>
                </div>
                <span className={
                  load.status === 'Delivered' ? "status-badge delivered" :
                  load.status === 'In Transit' ? "status-badge in-transit" :
                  "status-badge pending"
                }>{load.status}</span>
              </div>
            )})
          )}
        </div>
      </div>
    </div>
  );
}
