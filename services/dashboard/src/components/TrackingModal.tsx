"use client";
import { useState, useEffect } from 'react';
import { trackVehicle } from '@/lib/api';
import { X, MapPin, Navigation, Clock, Activity } from 'lucide-react';

export default function TrackingModal({ unitId, onClose }: { unitId: string, onClose: () => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTracking = async () => {
      try {
        const result = await trackVehicle(unitId);
        setData(result);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchTracking();
  }, [unitId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-bg-surface border border-border-color rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-fade-in">
        <div className="flex justify-between items-center p-6 border-b border-border-color">
          <h2 className="text-xl font-bold flex items-center">
            <MapPin className="w-5 h-5 mr-2 text-primary" />
            Tracking {unitId}
          </h2>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>
        
        <div className="p-6">
          {loading ? (
            <div className="flex justify-center py-10">
              <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div>
            </div>
          ) : data ? (
            <div className="space-y-6">
              <div className="flex items-start">
                <Navigation className="w-5 h-5 text-text-secondary mr-3 mt-1" />
                <div>
                  <p className="text-sm text-text-secondary">Current Location</p>
                  <p className="text-lg font-medium text-text-primary">{data.location}</p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-bg-base border border-border-color rounded-xl p-4">
                  <div className="flex items-center text-text-secondary mb-1">
                    <Activity className="w-4 h-4 mr-2" />
                    <span className="text-sm">Status & Speed</span>
                  </div>
                  <p className={`text-xl font-bold ${data.status === 'Driving' ? 'text-emerald-400' : 'text-amber-500'}`}>
                    {data.status} • {data.speed} mph
                  </p>
                </div>
                
                <div className="bg-bg-base border border-border-color rounded-xl p-4">
                  <div className="flex items-center text-text-secondary mb-1">
                    <Clock className="w-4 h-4 mr-2" />
                    <span className="text-sm">HOS Remaining</span>
                  </div>
                  <p className={`text-xl font-bold ${data.hos_remaining < 3 ? 'text-danger' : 'text-primary'}`}>
                    {data.hos_remaining} hrs
                  </p>
                </div>
              </div>
              
              <div className="text-sm text-text-secondary pt-4 border-t border-border-color flex justify-between">
                <span>Driver: {data.driver}</span>
                <span>Updated just now</span>
              </div>
            </div>
          ) : (
            <p className="text-center text-danger py-10">Failed to load tracking data.</p>
          )}
        </div>
      </div>
    </div>
  );
}
