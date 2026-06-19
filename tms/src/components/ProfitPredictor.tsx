import React, { useState } from 'react';
import { DollarSign, TrendingUp, BarChart, Percent, Loader, AlertCircle } from 'lucide-react';

export default function ProfitPredictor() {
  const [origin, setOrigin] = useState('Chicago, IL');
  const [destination, setDestination] = useState('Dallas, TX');
  const [rate, setRate] = useState('2800');
  
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    setPrediction(null);
    try {
      const res = await fetch('http://localhost:8000/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ origin, destination, rate: parseFloat(rate) || 0 })
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      const data = await res.json();
      if (data.error || !data.profit) {
        throw new Error(data.error || 'Invalid prediction response');
      }
      setPrediction(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to analyze profit. Please verify the backend is running.');
    }
    setLoading(false);
  };
  return (
    <div className="animate-fade-in" style={{ padding: '40px' }}>
      <h2 style={{ fontSize: '24px', marginBottom: '8px' }}>AI Profit Predictor</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>Analyze load profitability instantly based on historical data, fuel prices, and market trends.</p>

      <div className="dashboard-grid" style={{ padding: 0 }}>
        {/* Input Form */}
        <div className="card" style={{ gridColumn: 'span 4' }}>
          <h3 className="widget-title">Analyze New Load</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Origin</label>
              <input type="text" value={origin} onChange={(e) => setOrigin(e.target.value)} className="search-bar" style={{ width: '100%', marginTop: '4px', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Destination</label>
              <input type="text" value={destination} onChange={(e) => setDestination(e.target.value)} className="search-bar" style={{ width: '100%', marginTop: '4px', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Offered Rate ($)</label>
              <input type="number" value={rate} onChange={(e) => setRate(e.target.value)} className="search-bar" style={{ width: '100%', marginTop: '4px', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)' }} />
            </div>
            <button onClick={handlePredict} disabled={loading} className="icon-button" style={{ width: '100%', borderRadius: '8px', background: 'var(--primary)', color: 'var(--bg-base)', border: 'none', marginTop: '8px', opacity: loading ? 0.7 : 1 }}>
              {loading ? 'Analyzing...' : 'Run AI Prediction'}
            </button>
          </div>
        </div>

        {/* Prediction Results */}
        {/* Prediction Results */}
        <div className="card" style={{ gridColumn: 'span 8', background: 'linear-gradient(145deg, var(--bg-surface) 0%, rgba(16, 185, 129, 0.05) 100%)', minHeight: '400px' }}>
          <h3 className="widget-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp className="text-accent" /> Prediction Results
          </h3>
          
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <div style={{ width: '40px', height: '40px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: '16px' }} />
              <p style={{ color: 'var(--text-secondary)' }}>Calculating fuel routes and driver pay...</p>
            </div>
          ) : error ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--danger)', padding: '40px 24px', textAlign: 'center', gap: '12px' }}>
              <AlertCircle size={48} style={{ opacity: 0.8 }} />
              <h4 style={{ fontSize: '18px', fontWeight: '600' }}>Prediction Failed</h4>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', maxWidth: '360px' }}>{error}</p>
            </div>
          ) : prediction ? (
            <div className="animate-fade-in">
              <div style={{ display: 'flex', gap: '40px', marginTop: '24px' }}>
                <div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Est. Cost (Overhead + Fuel)</p>
                  <h2 style={{ fontSize: '36px', marginTop: '4px', color: 'var(--danger)' }}>{prediction.fuel}</h2>
                </div>
                <div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Est. Profit</p>
                  <h2 style={{ fontSize: '36px', marginTop: '4px', color: 'var(--accent)' }}>{prediction.profit}</h2>
                </div>
                <div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Profit Margin</p>
                  <h2 style={{ fontSize: '36px', marginTop: '4px', color: 'var(--primary)' }}>{prediction.margin}</h2>
                </div>
              </div>

              <div style={{ marginTop: '32px' }}>
                <h4 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '12px' }}>Cost Breakdown</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Fuel</span>
                    <strong>{prediction.fuel}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Driver Pay</span>
                    <strong>{prediction.driver}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Tolls & Misc</span>
                    <strong>{prediction.tolls}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Fixed Overhead (Depreciation, Ins)</span>
                    <strong>{prediction.overhead}</strong>
                  </div>
                </div>
              </div>
              
              <div style={{ marginTop: '24px', padding: '16px', background: (prediction.profit && typeof prediction.profit === 'string' && prediction.profit.includes('-')) ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', border: `1px solid ${(prediction.profit && typeof prediction.profit === 'string' && prediction.profit.includes('-')) ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}` }}>
                <strong style={{ color: (prediction.profit && typeof prediction.profit === 'string' && prediction.profit.includes('-')) ? 'var(--danger)' : 'var(--accent)' }}>AI Recommendation:</strong> {prediction.recommendation}.
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
              Enter load details and click predict to see profitability.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
