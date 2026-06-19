"use client";
import { useState, useEffect } from 'react';
import { fetchLoads } from '@/lib/api';

export default function LoadBoard() {
  const [loads, setLoads] = useState<any[]>([]);

  useEffect(() => {
    const loadData = async () => {
      const data = await fetchLoads();
      setLoads(data);
    };
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'Pending': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'In Transit': return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
      case 'Delivered': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Dispatched': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default: return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    }
  };

  return (
    <div className="bg-bg-surface border border-border-color rounded-xl overflow-hidden">
      <table className="w-full text-left">
        <thead className="bg-bg-surface-hover text-text-secondary text-sm border-b border-border-color">
          <tr>
            <th className="py-4 px-6 font-medium">Load ID</th>
            <th className="py-4 px-6 font-medium">Route</th>
            <th className="py-4 px-6 font-medium">Date</th>
            <th className="py-4 px-6 font-medium">Rate</th>
            <th className="py-4 px-6 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-color">
          {loads.map((load) => (
            <tr key={load.id} className="hover:bg-bg-surface-hover/50 transition-colors">
              <td className="py-4 px-6 font-medium text-text-primary">{load.load_id}</td>
              <td className="py-4 px-6 text-text-secondary">{load.origin} → {load.destination}</td>
              <td className="py-4 px-6 text-text-secondary">{load.pickup_date}</td>
              <td className="py-4 px-6 font-medium text-text-primary">${load.rate}</td>
              <td className="py-4 px-6">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusColor(load.status)}`}>
                  {load.status.toUpperCase()}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
