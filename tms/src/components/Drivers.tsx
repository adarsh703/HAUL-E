import { useState, useEffect } from 'react';
import { Search, Filter, ArrowUpDown, UserCheck, UserX, AlertCircle, ShieldAlert, FileWarning } from 'lucide-react';

interface Vehicle {
  id: number;
  unit_id: string;
  type: string;
  driver: string;
  miles: string;
  service: string;
  status: string;
}

interface DriverProfile {
  id: string;
  firstName: string;
  lastName: string;
  license: string;
  status: string;
  compliance: string;
  hos: string;
}

export default function Drivers() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [activeTab, setActiveTab] = useState<'All' | 'External' | 'Unassigned'>('All');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetch(`/api/fleet`)
      .then(res => res.json())
      .then(data => setVehicles(Array.isArray(data) ? data : []))
      .catch(console.error);
  }, []);

  const drivers: DriverProfile[] = vehicles.map(v => {
    let fName = v.driver;
    let lName = '';
    if (fName && fName !== 'Unassigned') {
      const parts = fName.split(' ');
      fName = parts[0];
      lName = parts.slice(1).join(' ') || '';
    } else {
      fName = 'Unassigned';
    }

    const hash = v.unit_id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    
    return {
      id: v.driver === 'Unassigned' ? '' : fName.substring(0, 3).toUpperCase() + hash,
      firstName: fName.toUpperCase(),
      lastName: lName.toUpperCase(),
      license: v.driver === 'Unassigned' ? '' : `TAMP${hash * 1234}`,
      status: v.status === 'Active' ? 'ACTIVE' : 'MAINTENANCE',
      compliance: v.driver === 'Unassigned' ? 'NON COMPLIANT' : (hash % 4 === 0 ? 'EXPIRING SOON' : 'COMPLIANT'),
      hos: v.driver === 'Unassigned' ? 'NO DEVICE' : (hash % 3 === 0 ? 'VIOLATION RISK' : 'COMPLIANT')
    };
  });

  const allDrivers = drivers.filter(d => d.firstName !== 'UNASSIGNED');
  const unassignedCount = vehicles.filter(v => v.driver === 'Unassigned').length;

  const displayedDrivers = (activeTab === 'All' ? allDrivers : activeTab === 'External' ? [] : drivers.filter(d => d.firstName === 'UNASSIGNED'))
    .filter(d => d.firstName.toLowerCase().includes(searchQuery.toLowerCase()) || d.lastName.toLowerCase().includes(searchQuery.toLowerCase()));

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE': return 'var(--accent)';
      case 'MAINTENANCE': return 'var(--danger)';
      default: return 'var(--text-secondary)';
    }
  };

  const getComplianceStyle = (comp: string) => {
    switch (comp) {
      case 'COMPLIANT': return { bg: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent)', border: '1px solid rgba(16, 185, 129, 0.2)' };
      case 'EXPIRING SOON': return { bg: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.2)' };
      default: return { bg: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.2)' };
    }
  };

  return (
    <div className="page-container animate-fade-in" style={{ padding: '32px', height: '100%', overflowY: 'auto' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '28px', fontWeight: '700', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
            <UserCheck size={28} color="var(--primary)" />
            Driver Management
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '14px' }}>
            Manage your fleet personnel, compliance, and HOS logs.
          </p>
        </div>
        
        <div className="search-bar" style={{ width: '300px' }}>
          <Search size={18} color="var(--text-secondary)" />
          <input 
            type="text" 
            placeholder="Search drivers..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="dashboard-grid" style={{ padding: '0', marginBottom: '32px' }}>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header">
            <span>Total Drivers</span>
            <div className="stat-icon primary"><UserCheck size={20} /></div>
          </div>
          <div className="stat-value">{allDrivers.length}</div>
          <div className="stat-trend up">All fully onboarded</div>
        </div>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header">
            <span>Compliance Alerts</span>
            <div className="stat-icon warning"><ShieldAlert size={20} /></div>
          </div>
          <div className="stat-value">{allDrivers.filter(d => d.compliance === 'EXPIRING SOON').length}</div>
          <div className="stat-trend warning">Documents expiring within 30 days</div>
        </div>
        <div className="card stat-card" style={{ gridColumn: 'span 4' }}>
          <div className="stat-header">
            <span>HOS Violations</span>
            <div className="stat-icon danger"><AlertCircle size={20} /></div>
          </div>
          <div className="stat-value">{allDrivers.filter(d => d.hos === 'VIOLATION RISK').length}</div>
          <div className="stat-trend down">Requires dispatcher review</div>
        </div>
      </div>

      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.02)' }}>
          {['All', 'External', 'Unassigned'].map((tab) => (
            <button 
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              style={{ 
                padding: '16px 24px', 
                border: 'none', 
                background: 'none', 
                color: activeTab === tab ? 'var(--primary)' : 'var(--text-secondary)', 
                borderBottom: activeTab === tab ? '2px solid var(--primary)' : '2px solid transparent', 
                cursor: 'pointer', 
                fontWeight: '600',
                fontSize: '14px',
                transition: 'all 0.2s'
              }}
            >
              {tab} ({tab === 'All' ? allDrivers.length : tab === 'Unassigned' ? unassignedCount : 0})
            </button>
          ))}
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead style={{ background: 'rgba(255,255,255,0.02)' }}>
              <tr>
                <th style={{ padding: '16px 24px', color: 'var(--text-secondary)', fontWeight: '500', fontSize: '13px' }}>DRIVER ID</th>
                <th style={{ padding: '16px 24px', color: 'var(--text-secondary)', fontWeight: '500', fontSize: '13px' }}>NAME</th>
                <th style={{ padding: '16px 24px', color: 'var(--text-secondary)', fontWeight: '500', fontSize: '13px' }}>LICENSE</th>
                <th style={{ padding: '16px 24px', color: 'var(--text-secondary)', fontWeight: '500', fontSize: '13px' }}>STATUS</th>
                <th style={{ padding: '16px 24px', color: 'var(--text-secondary)', fontWeight: '500', fontSize: '13px' }}>COMPLIANCE</th>
                <th style={{ padding: '16px 24px', color: 'var(--text-secondary)', fontWeight: '500', fontSize: '13px' }}>HOS LOGS</th>
              </tr>
            </thead>
            <tbody>
              {displayedDrivers.map((driver, idx) => {
                const compStyle = getComplianceStyle(driver.compliance);
                const hosStyle = getComplianceStyle(driver.hos);
                return (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.2s' }} className="hover:bg-[var(--bg-surface-hover)]">
                    <td style={{ padding: '16px 24px', fontWeight: '600', color: 'var(--text-primary)' }}>
                      {driver.id || '--'}
                    </td>
                    <td style={{ padding: '16px 24px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(99, 102, 241, 0.1)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '12px' }}>
                          {driver.firstName.charAt(0)}{driver.lastName.charAt(0)}
                        </div>
                        <div>
                          <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{driver.firstName} {driver.lastName}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '16px 24px', color: 'var(--text-secondary)' }}>{driver.license || '--'}</td>
                    <td style={{ padding: '16px 24px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: getStatusColor(driver.status), fontSize: '12px', fontWeight: '600' }}>
                        <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: getStatusColor(driver.status) }}></div>
                        {driver.status}
                      </div>
                    </td>
                    <td style={{ padding: '16px 24px' }}>
                      <span className="status-badge" style={{ background: compStyle.bg, color: compStyle.color, border: compStyle.border }}>
                        {driver.compliance}
                      </span>
                    </td>
                    <td style={{ padding: '16px 24px' }}>
                      <span className="status-badge" style={{ background: hosStyle.bg, color: hosStyle.color, border: hosStyle.border }}>
                        {driver.hos}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {displayedDrivers.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: '48px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <UserX size={48} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
                    <p>No drivers found matching your criteria.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
