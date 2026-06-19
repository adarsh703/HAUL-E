"use client";
import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle2, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function DocumentOCRPage() {
  const [uploadState, setUploadState] = useState<'idle' | 'uploading' | 'done'>('idle');
  const [ocrData, setOcrData] = useState<any>(null);
  const [toast, setToast] = useState('');
  const router = useRouter();

  const handleCreateLoad = async () => {
    try {
      const res = await fetch('/api/loads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin: ocrData.origin || '',
          destination: ocrData.destination || '',
          pickup_date: ocrData.pickup_date || '',
          rate: ocrData.rate || '0',
          status: 'Pending'
        })
      });
      if (res.ok) {
        setToast('Load Created Successfully! Auto-ID Assigned.');
        setTimeout(() => {
          router.push('/dispatch');
        }, 1500);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadState('uploading');
      const formData = new FormData();
      formData.append('file', e.target.files[0]);

      try {
        const res = await fetch('/api/ocr', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        setOcrData(data);
        setUploadState('done');
      } catch (err) {
        console.error(err);
        setUploadState('idle');
      }
    }
  };

  return (
    <div className="animate-fade-in" style={{ padding: '40px', display: 'flex', gap: '24px', height: '100%' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ fontSize: '24px', marginBottom: '8px' }}>Rate Confirmation OCR</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>Upload a PDF or Image of your Rate Confirmation. Our AI will automatically extract all load details and auto-fill the dispatch form.</p>

        <label 
          style={{
            flex: 1,
            border: '2px dashed var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(255, 255, 255, 0.02)',
            cursor: uploadState === 'idle' ? 'pointer' : 'default',
            transition: 'all 0.3s ease',
            borderColor: uploadState === 'uploading' ? 'var(--primary)' : 'var(--border-color)'
          }}
        >
          {uploadState === 'idle' && (
            <>
              <input type="file" style={{ display: 'none' }} onChange={handleFileChange} accept="image/*,application/pdf" />
              <UploadCloud size={64} style={{ color: 'var(--text-secondary)', marginBottom: '16px' }} />
              <h3 style={{ fontSize: '18px', fontWeight: '500' }}>Click or drag file to this area to upload</h3>
              <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>Supports PDF, JPG, PNG, WEBP</p>
            </>
          )}

          {uploadState === 'uploading' && (
            <>
              <div style={{ width: '40px', height: '40px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
              <h3 style={{ fontSize: '18px', fontWeight: '500', marginTop: '16px' }}>Extracting data with AI...</h3>
              <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>Scanning document for dates, locations, and rates</p>
            </>
          )}

          {uploadState === 'done' && (
            <>
              <CheckCircle2 size={64} style={{ color: 'var(--accent)', marginBottom: '16px' }} />
              <h3 style={{ fontSize: '18px', fontWeight: '500' }}>Extraction Complete!</h3>
              <button 
                onClick={() => setUploadState('idle')}
                className="icon-button" 
                style={{ width: 'auto', padding: '8px 16px', borderRadius: '8px', background: 'var(--bg-surface-hover)', color: 'white', border: 'none', marginTop: '16px' }}
              >
                Upload another
              </button>
            </>
          )}
        </label>
      </div>

      {uploadState === 'done' && (
        <div className="card animate-fade-in" style={{ width: '400px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
            <FileText className="text-primary" />
            <h3 style={{ fontSize: '18px', fontWeight: '600' }}>Extracted Data</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Broker Name</label>
              <input type="text" value={ocrData?.broker || ''} onChange={(e) => setOcrData({...ocrData, broker: e.target.value})} className="search-bar" style={{ width: '100%', marginTop: '4px' }} />
            </div>
            
            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Origin</label>
                <input type="text" value={ocrData?.origin || ''} onChange={(e) => setOcrData({...ocrData, origin: e.target.value})} className="search-bar" style={{ width: '100%', marginTop: '4px' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Destination</label>
                <input type="text" value={ocrData?.destination || ''} onChange={(e) => setOcrData({...ocrData, destination: e.target.value})} className="search-bar" style={{ width: '100%', marginTop: '4px' }} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Pickup Date</label>
                <input type="text" value={ocrData?.pickup_date || ''} onChange={(e) => setOcrData({...ocrData, pickup_date: e.target.value})} className="search-bar" style={{ width: '100%', marginTop: '4px' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Rate ($)</label>
                <input type="text" value={ocrData?.rate || ''} onChange={(e) => setOcrData({...ocrData, rate: e.target.value})} className="search-bar" style={{ width: '100%', marginTop: '4px' }} />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Commodity</label>
              <input type="text" value={ocrData?.commodity || ''} onChange={(e) => setOcrData({...ocrData, commodity: e.target.value})} className="search-bar" style={{ width: '100%', marginTop: '4px' }} />
            </div>
          </div>

          <button onClick={handleCreateLoad} className="icon-button" style={{ width: '100%', borderRadius: '8px', background: 'var(--primary)', color: 'white', border: 'none', marginTop: '24px', display: 'flex', gap: '8px' }}>
            Create Load <ArrowRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
