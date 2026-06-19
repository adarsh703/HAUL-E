from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.vehicle import Vehicle
import random

router = APIRouter(prefix="/api/track", tags=["tracking"])

@router.get("/{unit_id}")
async def track_vehicle(unit_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Vehicle).where(Vehicle.unit_id == unit_id)
    result = await db.execute(stmt)
    vehicle = result.scalars().first()
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    mock_locations = [
        "I-40 East, near Amarillo, TX",
        "Rest Stop, outside Little Rock, AR",
        "Stuck in traffic, I-95 North, Richmond, VA",
        "Pilot Travel Center, I-80, Cheyenne, WY",
        "Loading Dock, Sysco Facility, Atlanta, GA"
    ]
    
    current_location = random.choice(mock_locations)
    speed = random.choice([0, 0, 55, 65, 70])
    hos_remaining = round(random.uniform(2.5, 10.0), 1)
    
    return {
        "unit_id": vehicle.unit_id,
        "driver": f"Driver {vehicle.driver_id}" if vehicle.driver_id else "Unassigned",
        "location": current_location,
        "speed": speed,
        "status": "Driving" if speed > 0 else "Stopped",
        "hos_remaining": hos_remaining
    }
