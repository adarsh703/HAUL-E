const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export async function fetchLoads() {
  const res = await fetch(`${API_BASE}/api/loads`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchFleet() {
  const res = await fetch(`${API_BASE}/api/fleet`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchDrivers() {
  const res = await fetch(`${API_BASE}/api/drivers`);
  if (!res.ok) return [];
  return res.json();
}

export async function trackVehicle(unitId: string) {
  const res = await fetch(`${API_BASE}/api/track/${unitId}`);
  if (!res.ok) throw new Error('Failed to track');
  return res.json();
}

export async function predictProfit(data: { origin: string, destination: string, rate: number }) {
  const res = await fetch(`${API_BASE}/api/dispatch/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Prediction failed');
  return res.json();
}

export async function autoDispatch() {
  const res = await fetch(`${API_BASE}/api/dispatch/auto`, { method: 'POST' });
  if (!res.ok) throw new Error('Dispatch failed');
  return res.json();
}

export async function createLoad(data: any) {
  const res = await fetch(`${API_BASE}/api/loads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create load');
  return res.json();
}
