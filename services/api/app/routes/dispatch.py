from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.load import Load
from app.models.vehicle import Vehicle

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])

class PredictRequest(BaseModel):
    origin: str
    destination: str
    rate: float

@router.post("/auto")
async def auto_dispatch(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Load).where(Load.status == 'Pending').where(Load.rate > 3000))
    loads = result.scalars().all()
    
    result = await db.execute(select(Vehicle).where(Vehicle.status == 'Active'))
    vehicles = result.scalars().all()
    
    assignments = []
    for load in loads:
        if not vehicles:
            break
        vehicle = vehicles.pop(0)
        
        load.status = 'Dispatched'
        load.driver_id = vehicle.driver_id
        
        assignments.append({
            "load_id": load.load_id,
            "unit_id": vehicle.unit_id
        })
        
    await db.commit()
    return {"assignments": assignments}

import urllib.request
import urllib.parse
import json

def get_coords(city_state: str):
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(city_state)}&format=json&limit=1"
    req = urllib.request.Request(url, headers={'User-Agent': 'HAUL-E-TMS/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data:
                return float(data[0]['lon']), float(data[0]['lat'])
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None

def get_driving_distance(lon1, lat1, lon2, lat2):
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data and 'routes' in data and len(data['routes']) > 0:
                # distance is in meters, convert to miles
                return data['routes'][0]['distance'] * 0.000621371
    except Exception as e:
        print(f"Routing error: {e}")
    return None

@router.post("/predict")
async def predict_profit(req: PredictRequest):
    rate = req.rate
    
    # Attempt to get real distance using free APIs
    miles = 1000 # fallback default
    coords1 = get_coords(req.origin)
    coords2 = get_coords(req.destination)
    if coords1 and coords2:
        dist = get_driving_distance(coords1[0], coords1[1], coords2[0], coords2[1])
        if dist:
            miles = dist
            
    # Realistic trucking math based on real miles
    # 6.5 MPG at $3.80 per gallon
    fuel = (miles / 6.5) * 3.80
    # Driver pay: $0.65 per mile
    driver = miles * 0.65
    # Tolls & maintenance estimate per mile
    tolls = miles * 0.15
    # Fixed overhead
    overhead = rate * 0.10
    
    cost = fuel + driver + tolls + overhead
    profit = rate - cost
    margin = (profit / rate) * 100 if rate > 0 else 0
    
    sign = "+" if profit >= 0 else "-"
    abs_profit = abs(profit)
    
    if margin >= 15:
        rec = f"Excellent. Calculated {miles:,.0f} miles. Accept this load immediately"
    elif margin >= 5:
        rec = f"Acceptable. Calculated {miles:,.0f} miles. Consider negotiating for slightly more"
    else:
        rec = f"Poor margin. Calculated {miles:,.0f} miles. Reject or negotiate higher"
        
    return {
        "fuel": f"${fuel:,.0f}",
        "driver": f"${driver:,.0f}",
        "tolls": f"${tolls:,.0f}",
        "overhead": f"${overhead:,.0f}",
        "profit": f"{sign}${abs_profit:,.0f}",
        "margin": f"{margin:.1f}%",
        "recommendation": rec
    }
