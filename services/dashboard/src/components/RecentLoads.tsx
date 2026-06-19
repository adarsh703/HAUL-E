"use client";
import { useState, useEffect } from 'react';
import { fetchLoads } from '@/lib/api';

export default function RecentLoads() {
  const [loads, setLoads] = useState<any[]>([]);

  useEffect(() => {
    const loadData = async () => {
      const data = await fetchLoads();
      setLoads(data.slice(-5).reverse());
    };
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-bg-surface border border-border-color rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-6 flex items-center justify-between">
        Recent Activity
        <span className="text-xs font-normal text-primary bg-primary-glow px-2 py-1 rounded-full">Live</span>
      </h3>
      
      <div className="space-y-4">
        {loads.map((load) => (
          <div key={load.id} className="flex items-center p-3 rounded-lg hover:bg-bg-base transition-colors group border border-transparent hover:border-border-color">
            <div className="w-10 h-10 rounded-full bg-bg-surface-hover flex items-center justify-center font-bold text-primary mr-4 group-hover:bg-primary-glow">
              {load.destination.substring(0, 2).toUpperCase()}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-text-primary">{load.origin.split(',')[0]} → {load.destination.split(',')[0]}</p>
              <p className="text-xs text-text-secondary">{load.load_id} • {load.pickup_date}</p>
            </div>
            <div className="text-right">
              <span className={`text-xs font-semibold px-2 py-1 rounded-full border ${load.status === 'Delivered' ? 'text-emerald-400 border-emerald-500/20' : load.status === 'In Transit' ? 'text-indigo-400 border-indigo-500/20' : 'text-amber-500 border-amber-500/20'}`}>
                {load.status}
              </span>
            </div>
          </div>
        ))}
        {loads.length === 0 && <p className="text-center text-text-secondary text-sm">No recent loads</p>}
      </div>
    </div>
  );
}
