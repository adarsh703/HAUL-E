import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Truck, MapPin } from 'lucide-react';
import { renderToString } from 'react-dom/server';

// Fix leaflet icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Create custom truck icon using Lucide
const createCustomIcon = (color: string) => {
  const iconHtml = renderToString(
    <div style={{ background: color, color: 'white', padding: '6px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid white', boxShadow: '0 2px 5px rgba(0,0,0,0.3)' }}>
      <Truck size={16} />
    </div>
  );
  
  return L.divIcon({
    html: iconHtml,
    className: 'custom-leaflet-icon',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16]
  });
};

const createCityIcon = () => {
  const iconHtml = renderToString(
    <div style={{ color: '#ef4444', filter: 'drop-shadow(0 2px 2px rgba(0,0,0,0.3))' }}>
      <MapPin size={24} fill="#ef4444" color="white" />
    </div>
  );
  
  return L.divIcon({
    html: iconHtml,
    className: 'custom-city-icon',
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24]
  });
};

interface GeoPoint {
  name?: string;
  lat: number;
  lon: number;
  description?: string;
  speed?: number;
}

interface LiveRoute {
  load_id: string;
  driver: string;
  origin: GeoPoint;
  destination: GeoPoint;
  truck: GeoPoint;
}

export default function LiveMap() {
  const [routes, setRoutes] = useState<LiveRoute[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/live_map')
      .then(res => res.json())
      .then(data => {
        setRoutes(data.routes || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>Loading Live Fleet Data...</div>;
  }

  if (routes.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)', gap: '12px' }}>
        <MapPin size={48} style={{ opacity: 0.5 }} />
        <p>No active loads in transit</p>
      </div>
    );
  }

  // Calculate center based on all active routes (fallback to center of US)
  const allLats = routes.map(r => r.truck.lat).filter(l => l);
  const allLons = routes.map(r => r.truck.lon).filter(l => l);
  const centerLat = allLats.length > 0 ? allLats.reduce((a,b)=>a+b)/allLats.length : 39.8283;
  const centerLon = allLons.length > 0 ? allLons.reduce((a,b)=>a+b)/allLons.length : -98.5795;

  return (
    <MapContainer 
      center={[centerLat, centerLon]} 
      zoom={4} 
      style={{ height: '100%', width: '100%', background: '#0f1115' }}
      zoomControl={false}
    >
      {/* Dark map theme tiles */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
      />

      {routes.map((route, i) => {
        const hasTruck = route.truck && route.truck.lat;
        const color = i % 2 === 0 ? '#6366f1' : '#10b981'; // Alternate colors per route
        
        return (
          <div key={route.load_id}>
            {/* Draw Path from Origin to Destination */}
            <Polyline 
              positions={[
                [route.origin.lat, route.origin.lon],
                [route.destination.lat, route.destination.lon]
              ]} 
              color={color}
              weight={3}
              opacity={0.4}
              dashArray="5, 10"
            />
            
            {/* Origin Marker */}
            <Marker position={[route.origin.lat, route.origin.lon]} icon={createCityIcon()}>
              <Popup>
                <strong>Origin:</strong> {route.origin.name} <br/>
                Load: {route.load_id}
              </Popup>
            </Marker>
            
            {/* Destination Marker */}
            <Marker position={[route.destination.lat, route.destination.lon]} icon={createCityIcon()}>
              <Popup>
                <strong>Destination:</strong> {route.destination.name} <br/>
                Load: {route.load_id}
              </Popup>
            </Marker>

            {/* Truck Location Marker */}
            {hasTruck && (
              <Marker position={[route.truck.lat, route.truck.lon]} icon={createCustomIcon(color)}>
                <Popup>
                  <div style={{ background: 'var(--bg-surface)', padding: '4px', color: 'var(--text-primary)', border: 'none' }}>
                    <h4 style={{ margin: '0 0 4px 0', fontSize: '14px' }}>{route.load_id} - {route.driver}</h4>
                    <p style={{ margin: '0 0 4px 0', fontSize: '12px', color: 'var(--text-secondary)' }}>{route.truck.description}</p>
                    <div style={{ display: 'flex', gap: '8px', fontSize: '12px' }}>
                      <span style={{ color: route.truck.speed ? 'var(--accent)' : 'var(--text-secondary)' }}>
                        {route.truck.speed ? `${route.truck.speed} mph` : 'Idle'}
                      </span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            )}
          </div>
        );
      })}
    </MapContainer>
  );
}
