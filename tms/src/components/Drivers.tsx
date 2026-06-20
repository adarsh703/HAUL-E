import { useState, useEffect } from 'react';
import { Search, Filter, ArrowUpDown } from 'lucide-react';

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
  passport: string;
  dob: string;
  notes: string;
  ticketYTD: number;
  status: string;
  compliance: string;
  hos: string;
}

export default function Drivers() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [activeTab, setActiveTab] = useState<'All' | 'External' | 'Unassigned'>('All');

  useEffect(() => {
    fetch(`/api/fleet`)
      .then(res => res.json())
      .then(data => setVehicles(Array.isArray(data) ? data : []))
      .catch(console.error);
  }, []);

  // Map vehicles to mock Driver profiles to replicate the TorqueAI UI look
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

    // Generate deterministic mock data based on the unit_id
    const hash = v.unit_id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    
    return {
      id: v.driver === 'Unassigned' ? '' : fName, // Just a visual mock like the screenshot
      firstName: fName.toUpperCase(),
      lastName: lName.toUpperCase(),
      license: v.driver === 'Unassigned' ? '' : `TAMP${hash * 1234}`,
      passport: '',
      dob: v.driver === 'Unassigned' ? '' : `1${hash % 9}/0${(hash % 8) + 1}/19${70 + (hash % 30)}`,
      notes: '',
      ticketYTD: 0,
      status: v.status === 'Active' ? 'ACTIVE' : 'INACTIVE',
      compliance: v.driver === 'Unassigned' ? 'NON COMPLIANT' : (hash % 3 === 0 ? 'EXPIRING SOON' : 'COMPLIANT'),
      hos: v.driver === 'Unassigned' ? 'LICENSE MISMATCHED' : (hash % 2 === 0 ? 'LOADING...' : 'LICENSE MISMATCHED')
    };
  });

  const allDrivers = drivers.filter(d => d.firstName !== 'UNASSIGNED');
  const unassignedCount = vehicles.filter(v => v.driver === 'Unassigned').length;

  return (
    <div className="page-container animate-fade-in" style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto', background: '#f5f7f9', minHeight: '100%', color: '#1a1d24' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: 'bold' }}>Drivers</h1>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button style={{ padding: '8px 24px', background: '#0e7452', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '500' }}>Drivers</button>
          <button style={{ padding: '8px 24px', background: '#e2e8f0', color: '#64748b', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '500' }}>Inbox</button>
        </div>
        <div style={{ fontSize: '24px', fontWeight: '300' }}>({allDrivers.length}) +</div>
      </div>

      <div style={{ display: 'flex', gap: '24px', borderBottom: '1px solid #e2e8f0', marginBottom: '24px' }}>
        <button 
          onClick={() => setActiveTab('All')}
          style={{ padding: '8px 0', border: 'none', background: 'none', color: activeTab === 'All' ? '#0e7452' : '#64748b', borderBottom: activeTab === 'All' ? '2px solid #0e7452' : '2px solid transparent', cursor: 'pointer', fontWeight: '500' }}
        >
          All ({allDrivers.length})
        </button>
        <button 
          onClick={() => setActiveTab('External')}
          style={{ padding: '8px 0', border: 'none', background: 'none', color: activeTab === 'External' ? '#0e7452' : '#64748b', borderBottom: activeTab === 'External' ? '2px solid #0e7452' : '2px solid transparent', cursor: 'pointer', fontWeight: '500' }}
        >
          External (0)
        </button>
        <button 
          onClick={() => setActiveTab('Unassigned')}
          style={{ padding: '8px 0', border: 'none', background: 'none', color: activeTab === 'Unassigned' ? '#0e7452' : '#64748b', borderBottom: activeTab === 'Unassigned' ? '2px solid #0e7452' : '2px solid transparent', cursor: 'pointer', fontWeight: '500' }}
        >
          Unassigned ({unassignedCount})
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr auto', gap: '16px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '12px', fontWeight: '600' }}>Search</label>
          <div style={{ display: 'flex', alignItems: 'center', background: '#e2e8f0', padding: '8px', borderRadius: '4px' }}>
            <input type="text" style={{ background: 'transparent', border: 'none', outline: 'none', width: '100%' }} />
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '12px', fontWeight: '600' }}>Status</label>
          <select style={{ background: '#e2e8f0', border: 'none', padding: '8px', borderRadius: '4px', outline: 'none' }}>
            <option>Active</option>
          </select>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '12px', fontWeight: '600' }}>Category</label>
          <select style={{ background: '#e2e8f0', border: 'none', padding: '8px', borderRadius: '4px', outline: 'none' }}>
            <option>All</option>
          </select>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '12px', fontWeight: '600' }}>Compliance</label>
          <select style={{ background: '#e2e8f0', border: 'none', padding: '8px', borderRadius: '4px', outline: 'none' }}>
            <option>All</option>
          </select>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '12px', fontWeight: '600' }}>Sort</label>
          <select style={{ background: '#e2e8f0', border: 'none', padding: '8px', borderRadius: '4px', outline: 'none' }}>
            <option>A To Z - Name</option>
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', paddingBottom: '8px', color: '#64748b' }}>
          <Filter size={18} />
          <Search size={18} />
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', background: 'white', borderRadius: '8px', overflow: 'hidden' }}>
          <thead style={{ background: '#f5f7f9', color: '#64748b' }}>
            <tr>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '500' }}>Driver ID <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '500' }}>First Name <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '500' }}>Last Name <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '500' }}>Drivers Licence <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '500' }}>Passport <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '500' }}>Date Of Birth <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '500' }}>Notes <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'center', fontWeight: '500' }}>Ticket (YTD) <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'center', fontWeight: '500' }}>Status <ArrowUpDown size={10} /></th>
              <th style={{ padding: '12px', textAlign: 'center', fontWeight: '500' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'center' }}>
                  Compliance <ArrowUpDown size={10} />
                  <select style={{ fontSize: '10px', background: '#e2e8f0', border: 'none', padding: '2px 4px', borderRadius: '2px' }}><option>All</option></select>
                </div>
              </th>
              <th style={{ padding: '12px', textAlign: 'center', fontWeight: '500' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'center' }}>
                  HOS <ArrowUpDown size={10} />
                  <select style={{ fontSize: '10px', background: '#e2e8f0', border: 'none', padding: '2px 4px', borderRadius: '2px' }}><option>All</option></select>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {(activeTab === 'All' ? allDrivers : activeTab === 'External' ? [] : drivers.filter(d => d.firstName === 'UNASSIGNED')).map((driver, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ padding: '12px', fontWeight: '600' }}>{driver.id}</td>
                <td style={{ padding: '12px' }}>{driver.firstName}</td>
                <td style={{ padding: '12px' }}>{driver.lastName}</td>
                <td style={{ padding: '12px' }}>{driver.license}</td>
                <td style={{ padding: '12px' }}>{driver.passport}</td>
                <td style={{ padding: '12px' }}>{driver.dob}</td>
                <td style={{ padding: '12px' }}>{driver.notes}</td>
                <td style={{ padding: '12px', textAlign: 'center' }}>{driver.ticketYTD}</td>
                <td style={{ padding: '12px', textAlign: 'center' }}>
                  {driver.firstName !== 'UNASSIGNED' && (
                    <span style={{ background: '#10b981', color: 'white', padding: '4px 12px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold' }}>
                      {driver.status}
                    </span>
                  )}
                </td>
                <td style={{ padding: '12px', textAlign: 'center' }}>
                  {driver.firstName !== 'UNASSIGNED' && (
                    <span style={{ 
                      background: driver.compliance === 'COMPLIANT' ? '#10b981' : driver.compliance === 'EXPIRING SOON' ? '#f59e0b' : '#ef4444', 
                      color: 'white', padding: '4px 12px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold' 
                    }}>
                      {driver.compliance}
                    </span>
                  )}
                </td>
                <td style={{ padding: '12px', textAlign: 'center' }}>
                  {driver.firstName !== 'UNASSIGNED' && (
                    <span style={{ 
                      background: driver.hos === 'LOADING...' ? 'transparent' : '#e2e8f0', 
                      color: '#475569', padding: '4px 12px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold' 
                    }}>
                      {driver.hos}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}
