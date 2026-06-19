"use client";
import React, { useState, useEffect } from 'react';
import { Plus, Map, List, Truck, Zap } from 'lucide-react';
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

export default function DispatchPage() {
  const [view, setView] = useState('list');
  const [loads, setLoads] = useState<Load[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [toast, setToast] = useState('');
  const [newLoad, setNewLoad] = useState({ load_id: '', origin: '', destination: '', pickup_date: '', driver: '', rate: '', status: 'Pending' });
  const [selectedLoad, setSelectedLoad] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchLoads = () => {
    fetch('/api/loads')
      .then(res => res.json())
      .then(data => {
        setLoads(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchLoads();
    const interval = setInterval(fetchLoads, 10000); // Auto-refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const handleCreateLoad = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    fetch('/api/loads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newLoad)
    }).then(res => res.json()).then(() => {
      setIsSubmitting(false);
      setShowModal(false);
      setToast('Load Created Successfully! Auto-ID Assigned.');
      setTimeout(() => setToast(''), 3000);
      fetchLoads();
      setNewLoad({ load_id: '', origin: '', destination: '', pickup_date: '', driver: '', rate: '', status: 'Pending' });
    });
  };

  const handleAutoDispatch = () => {
    fetch('/api/dispatch/auto', { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (data.assignments && data.assignments.length > 0) {
          setToast(`Auto-Dispatch Complete: ${data.assignments.length} load(s) assigned!`);
        } else {
          setToast('No pending high-paying loads or available trucks found.');
        }
        setTimeout(() => setToast(''), 4000);
        fetchLoads();
      });
  };

  return (
    <div className="flex flex-col h-full w-full p-8 lg:p-12 animate-fade-in space-y-8 bg-[var(--bg-base)] text-[var(--text-primary)]">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b border-[var(--border-color)] pb-6">
        <div className="space-y-1">
          <p className="text-[var(--primary)] text-xs font-mono uppercase tracking-widest font-semibold">Active Logistics</p>
          <h2 className="text-4xl font-light tracking-tight">Dispatch</h2>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-[var(--bg-surface)] p-1 rounded-full border border-[var(--border-color)]">
            <button 
              className={`p-2 rounded-full transition-colors ${view === 'map' ? 'bg-[var(--border-color)] text-[var(--primary)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
              onClick={() => setView('map')}
            >
              <Map size={16} />
            </button>
            <button 
              className={`p-2 rounded-full transition-colors ${view === 'list' ? 'bg-[var(--border-color)] text-[var(--primary)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
              onClick={() => setView('list')}
            >
              <List size={16} />
            </button>
          </div>
          <button 
            onClick={handleAutoDispatch} 
            className="flex items-center gap-2 px-5 py-2.5 text-sm rounded-full bg-[#18181b] hover:bg-[#27282d] border border-[var(--border-color)] transition-all cursor-pointer"
          >
            <Zap size={14} className="text-[var(--primary)]" /> 
            <span>Auto Dispatch AI</span>
          </button>
          <button 
            onClick={() => setShowModal(true)} 
            className="flex items-center gap-2 px-6 py-2.5 text-sm rounded-full bg-[var(--primary)] hover:bg-[#d4f954] text-[#070708] font-semibold transition-all shadow-[0_0_20px_rgba(199,242,58,0.2)] hover:shadow-[0_0_30px_rgba(199,242,58,0.4)] cursor-pointer"
          >
            <Plus size={16} /> 
            <span>New Load</span>
          </button>
        </div>
      </div>

      {toast && (
        <div className="fixed bottom-8 right-8 bg-[var(--primary)] text-[#070708] px-6 py-3 rounded-full font-medium flex items-center gap-3 shadow-[0_8px_30px_rgba(199,242,58,0.3)] z-50 animate-fade-in border border-[rgba(0,0,0,0.1)]">
          <div className="w-2 h-2 rounded-full bg-[#070708]"></div>
          {toast}
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 min-h-0 bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-[1.5rem] overflow-hidden flex flex-col relative shadow-xl">
        {view === 'list' ? (
          <div className="flex-1 overflow-auto w-full">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead className="sticky top-0 bg-[var(--bg-surface)]/95 backdrop-blur-md z-10 border-b border-[var(--border-color)] shadow-sm">
                <tr className="text-[var(--text-secondary)] text-xs uppercase tracking-wider">
                  <th className="py-5 px-8 font-medium whitespace-nowrap">Load ID</th>
                  <th className="py-5 px-6 font-medium whitespace-nowrap">Route</th>
                  <th className="py-5 px-6 font-medium whitespace-nowrap">Pickup Date</th>
                  <th className="py-5 px-6 font-medium whitespace-nowrap">Assignment</th>
                  <th className="py-5 px-6 font-medium whitespace-nowrap">Rate</th>
                  <th className="py-5 px-8 font-medium whitespace-nowrap">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)]/50">
                {loading ? (
                  <tr><td colSpan={6} className="py-12 text-center text-[var(--text-secondary)]">Syncing logistics data...</td></tr>
                ) : loads.length === 0 ? (
                  <tr><td colSpan={6} className="py-12 text-center text-[var(--text-secondary)]">No loads currently available.</td></tr>
                ) : (
                  loads.map((load, i) => (
                    <tr key={load.id} onClick={() => setSelectedLoad(load)} className="group hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer">
                      <td className="py-4 px-8 font-mono text-sm text-[var(--text-primary)]">{load.load_id}</td>
                      <td className="py-4 px-6 text-sm">{load.origin_dest || `${load.origin} → ${load.destination}`}</td>
                      <td className="py-4 px-6 text-sm text-[var(--text-secondary)]">{load.pickup_date}</td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors">
                          <Truck size={14} className={load.driver ? "text-[var(--primary)]" : ""} /> 
                          {load.driver || 'Unassigned'}
                        </div>
                      </td>
                      <td className="py-4 px-6 text-sm font-medium">${Number(load.rate).toLocaleString()}</td>
                      <td className="py-4 px-8">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                          load.status === 'Rejected'
                            ? "bg-[var(--danger)]/10 text-[var(--danger)] border-[var(--danger)]/20"
                            : load.status === 'Pending' || load.status === 'Awaiting Approval'
                            ? "bg-amber-500/10 text-amber-500 border-amber-500/20" 
                            : "bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/20"
                        }`}>
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
          <div className="flex-1 w-full relative">
            <LiveMap loads={loads} />
            <div className="absolute top-4 left-4 bg-[var(--bg-base)]/80 backdrop-blur-md border border-[var(--border-color)] p-3 rounded-xl flex flex-col gap-2 pointer-events-none">
              <div className="flex items-center gap-2 text-xs font-medium"><div className="w-2 h-2 rounded-full bg-[var(--primary)]"></div> Dispatched</div>
              <div className="flex items-center gap-2 text-xs font-medium"><div className="w-2 h-2 rounded-full bg-[var(--danger)]"></div> Pending</div>
            </div>
          </div>
        )}
      </div>

      {/* Premium Create Load Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-[#000000]/80 backdrop-blur-sm flex items-center justify-center z-[1000] p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-[2rem] w-full max-w-md overflow-hidden shadow-2xl animate-fade-in relative">
            <div className="absolute -top-32 -left-32 w-64 h-64 bg-[var(--primary)]/10 rounded-full blur-[80px] pointer-events-none"></div>
            
            <div className="p-8 border-b border-[var(--border-color)] flex justify-between items-center relative z-10">
              <div>
                <p className="text-[var(--primary)] text-xs font-mono uppercase tracking-widest font-semibold mb-1">New Entry</p>
                <h3 className="text-2xl font-light">Create Load</h3>
              </div>
              <button onClick={() => setShowModal(false)} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors p-2 bg-[var(--bg-surface-hover)] rounded-full cursor-pointer">
                <Plus size={20} className="rotate-45" />
              </button>
            </div>
            
            <form onSubmit={handleCreateLoad} className="p-8 flex flex-col gap-5 relative z-10">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block font-semibold">Load ID</label>
                  <input placeholder="Auto-generated if empty" value={newLoad.load_id} onChange={e => setNewLoad({...newLoad, load_id: e.target.value})} className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition-all text-[var(--text-primary)] placeholder:text-[#4a4b52]" />
                </div>
                <div className="col-span-1">
                  <label className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block font-semibold">Origin *</label>
                  <input placeholder="City, ST" value={newLoad.origin} onChange={e => setNewLoad({...newLoad, origin: e.target.value})} className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition-all text-[var(--text-primary)] placeholder:text-[#4a4b52]" required />
                </div>
                <div className="col-span-1">
                  <label className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block font-semibold">Destination *</label>
                  <input placeholder="City, ST" value={newLoad.destination} onChange={e => setNewLoad({...newLoad, destination: e.target.value})} className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition-all text-[var(--text-primary)] placeholder:text-[#4a4b52]" required />
                </div>
                <div className="col-span-1">
                  <label className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block font-semibold">Pickup Date *</label>
                  <input placeholder="e.g. Jun 12, 2026" value={newLoad.pickup_date} onChange={e => setNewLoad({...newLoad, pickup_date: e.target.value})} className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition-all text-[var(--text-primary)] placeholder:text-[#4a4b52]" required />
                </div>
                <div className="col-span-1">
                  <label className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block font-semibold">Rate ($) *</label>
                  <input placeholder="4500" value={newLoad.rate} onChange={e => setNewLoad({...newLoad, rate: e.target.value})} className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition-all text-[var(--text-primary)] placeholder:text-[#4a4b52]" required />
                </div>
                <div className="col-span-2">
                  <label className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block font-semibold">Driver / Unit (Optional)</label>
                  <input placeholder="Assign later if empty" value={newLoad.driver} onChange={e => setNewLoad({...newLoad, driver: e.target.value})} className="w-full bg-[var(--bg-base)] border border-[var(--border-color)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition-all text-[var(--text-primary)] placeholder:text-[#4a4b52]" />
                </div>
              </div>

              <div className="mt-4">
                <button type="submit" disabled={isSubmitting} className="w-full py-3.5 rounded-xl bg-[var(--primary)] hover:bg-[#d4f954] text-[#070708] font-bold tracking-wide transition-all flex items-center justify-center gap-2 group cursor-pointer shadow-[0_0_15px_rgba(199,242,58,0.15)]">
                  {isSubmitting ? <span className="w-5 h-5 border-2 border-[#070708]/30 border-t-[#070708] rounded-full animate-spin"></span> : 'Confirm Dispatch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Load Details Modal */}
      {selectedLoad && (
        <div className="fixed inset-0 bg-[#000000]/80 backdrop-blur-sm flex items-center justify-center z-[1000] p-4">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-color)] rounded-[2rem] w-full max-w-2xl overflow-hidden shadow-2xl animate-fade-in relative max-h-[90vh] flex flex-col">
            <div className="p-8 border-b border-[var(--border-color)] flex justify-between items-center relative z-10 shrink-0">
              <div>
                <p className="text-[var(--primary)] text-xs font-mono uppercase tracking-widest font-semibold mb-1">Load Details</p>
                <h3 className="text-2xl font-light">{selectedLoad.load_id}</h3>
              </div>
              <button onClick={() => setSelectedLoad(null)} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors p-2 bg-[var(--bg-surface-hover)] rounded-full cursor-pointer">
                <Plus size={20} className="rotate-45" />
              </button>
            </div>
            
            <div className="p-8 overflow-y-auto relative z-10 space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1 block font-semibold">Route</p>
                  <p className="text-sm">{selectedLoad.origin_dest}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1 block font-semibold">Status</p>
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/20`}>
                    {selectedLoad.status}
                  </span>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1 block font-semibold">Driver</p>
                  <p className="text-sm">{selectedLoad.driver || 'Unassigned'}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1 block font-semibold">Rate</p>
                  <p className="text-sm font-medium">${selectedLoad.rate}</p>
                </div>
              </div>

              {(selectedLoad.bol_path || selectedLoad.pod_path) && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-2 block font-semibold">Documents</p>
                  <div className="flex gap-4">
                    {selectedLoad.bol_path && <div className="text-sm flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-[var(--primary)]"></div>BOL Received</div>}
                    {selectedLoad.pod_path && <div className="text-sm flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-[var(--primary)]"></div>POD Received</div>}
                  </div>
                </div>
              )}

              {selectedLoad.operational_intelligence && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-2 block font-semibold">Rate Confirmation Extraction (JSON)</p>
                  <div className="bg-[#0a0a0b] p-4 rounded-xl border border-[var(--border-color)] overflow-x-auto text-xs font-mono text-[var(--hairline-strong)]">
                    <pre>{JSON.stringify(JSON.parse(selectedLoad.operational_intelligence), null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
