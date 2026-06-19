"use client";
import React, { useEffect, useState } from 'react';
import { Truck, MapPin } from 'lucide-react';

export default function LiveMap({ loads }: { loads: any[] }) {
  const [progress, setProgress] = useState(0);
  const activeLoad = loads.find(l => l.status === 'In Transit') || loads[0];

  // Animate the truck moving
  useEffect(() => {
    let animationId: number;
    let start = Date.now();
    const duration = 15000; // 15 seconds loop

    const tick = () => {
      const elapsed = Date.now() - start;
      const currentProgress = (elapsed % duration) / duration;
      setProgress(currentProgress);
      animationId = requestAnimationFrame(tick);
    };

    animationId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationId);
  }, []);

  if (!activeLoad) {
    return <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>No active loads to display on map.</div>;
  }

  // Define a curved path from left to right for the truck route
  const startX = 50;
  const startY = 250;
  const endX = 550;
  const endY = 100;
  const controlX = 300;
  const controlY = 350;

  const path = `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`;

  // Calculate truck position on the curve
  const getPointOnCurve = (t: number) => {
    const x = Math.pow(1 - t, 2) * startX + 2 * (1 - t) * t * controlX + Math.pow(t, 2) * endX;
    const y = Math.pow(1 - t, 2) * startY + 2 * (1 - t) * t * controlY + Math.pow(t, 2) * endY;
    return { x, y };
  };

  const truckPos = getPointOnCurve(progress);

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%', overflow: 'hidden', background: '#111827', borderRadius: '8px' }}>
      {/* Decorative Grid Background representing map */}
      <div style={{ position: 'absolute', inset: 0, opacity: 0.1, backgroundImage: 'linear-gradient(var(--border-color) 1px, transparent 1px), linear-gradient(90deg, var(--border-color) 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>
      
      {/* SVG Path */}
      <svg width="100%" height="100%" viewBox="0 0 600 400" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', top: 0, left: 0 }}>
        {/* Shadow Path */}
        <path d={path} fill="none" stroke="rgba(99, 102, 241, 0.2)" strokeWidth="6" strokeLinecap="round" strokeDasharray="10 10" />
        
        {/* Active Path up to truck */}
        <path d={path} fill="none" stroke="var(--primary)" strokeWidth="3" strokeLinecap="round" strokeDasharray="800" strokeDashoffset={800 * (1 - progress)} />
      </svg>

      {/* Origin Marker */}
      <div style={{ position: 'absolute', left: `${(startX / 600) * 100}%`, top: `${(startY / 400) * 100}%`, transform: 'translate(-50%, -100%)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ background: 'var(--bg-surface)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', border: '1px solid var(--border-color)', marginBottom: '4px', whiteSpace: 'nowrap' }}>
          {activeLoad.origin || 'Origin'}
        </div>
        <MapPin size={24} className="text-secondary" />
      </div>

      {/* Destination Marker */}
      <div style={{ position: 'absolute', left: `${(endX / 600) * 100}%`, top: `${(endY / 400) * 100}%`, transform: 'translate(-50%, -100%)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ background: 'var(--bg-surface)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', border: '1px solid var(--primary)', marginBottom: '4px', color: 'var(--primary)', whiteSpace: 'nowrap' }}>
          {activeLoad.destination || 'Destination'}
        </div>
        <MapPin size={24} className="text-primary" />
      </div>

      {/* Live Truck Indicator */}
      <div style={{ 
        position: 'absolute', 
        left: `${(truckPos.x / 600) * 100}%`, 
        top: `${(truckPos.y / 400) * 100}%`, 
        transform: 'translate(-50%, -50%)',
        transition: 'all 0.1s linear',
        zIndex: 10
      }}>
        <div style={{ position: 'relative' }}>
          <div style={{ position: 'absolute', inset: -8, background: 'var(--primary)', opacity: 0.2, borderRadius: '50%', animation: 'pulse 2s infinite' }}></div>
          <div style={{ background: 'var(--primary)', padding: '6px', borderRadius: '50%', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 10px rgba(99, 102, 241, 0.5)' }}>
            <Truck size={16} />
          </div>
        </div>
        <div style={{ position: 'absolute', top: '100%', left: '50%', transform: 'translate(-50%, 8px)', background: 'rgba(0,0,0,0.8)', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', whiteSpace: 'nowrap', border: '1px solid var(--primary)' }}>
          {activeLoad.load_id} • 65 mph
        </div>
      </div>
      
      <div style={{ position: 'absolute', bottom: '16px', left: '16px', background: 'rgba(0,0,0,0.6)', padding: '8px 12px', borderRadius: '8px', backdropFilter: 'blur(4px)', border: '1px solid var(--border-color)', fontSize: '12px', display: 'flex', gap: '16px' }}>
        <div><span style={{ color: 'var(--text-secondary)' }}>Status:</span> <span className="text-accent">Live GPS Tracking</span></div>
        <div><span style={{ color: 'var(--text-secondary)' }}>Driver:</span> {activeLoad.driver || 'Assigned'}</div>
      </div>
      <style>{`
        @keyframes pulse {
          0% { transform: scale(1); opacity: 0.4; }
          100% { transform: scale(2); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
