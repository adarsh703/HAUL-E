"use client";
import { useState, useEffect } from 'react';
import { fetchFleet } from '@/lib/api';
import TrackingModal from './TrackingModal';
import { MapPin } from 'lucide-react';

export default function FleetTable() {
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [trackingUnit, setTrackingUnit] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      const data = await fetchFleet();
      setVehicles(data);
    };
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div className="bg-bg-surface border border-border-color rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-bg-surface-hover text-text-secondary text-sm border-b border-border-color">
            <tr>
              <th className="py-4 px-6 font-medium">Unit ID</th>
              <th className="py-4 px-6 font-medium">Type</th>
              <th className="py-4 px-6 font-medium">Mileage</th>
              <th className="py-4 px-6 font-medium">Status</th>
              <th className="py-4 px-6 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-color">
            {vehicles.map((v) => (
              <tr key={v.id} className="hover:bg-bg-surface-hover/50 transition-colors">
                <td className="py-4 px-6 font-medium text-text-primary">{v.unit_id}</td>
                <td className="py-4 px-6 text-text-secondary">{v.type}</td>
                <td className="py-4 px-6 text-text-secondary">{v.mileage.toLocaleString()} mi</td>
                <td className="py-4 px-6">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${v.status === 'Active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                    {v.status.toUpperCase()}
                  </span>
                </td>
                <td className="py-4 px-6 text-right">
                  <button 
                    onClick={() => setTrackingUnit(v.unit_id)}
                    className="flex items-center justify-end w-full text-primary hover:text-indigo-400 transition-colors font-medium text-sm"
                  >
                    <MapPin className="w-4 h-4 mr-1" />
                    Track
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {trackingUnit && (
        <TrackingModal unitId={trackingUnit} onClose={() => setTrackingUnit(null)} />
      )}
    </>
  );
}
