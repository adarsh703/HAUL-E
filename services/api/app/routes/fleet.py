from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.driver import Driver

router = APIRouter(tags=["fleet"])

class VehicleCreate(BaseModel):
    unit_id: str
    type: str
    driver_id: int | None = None
    mileage: int = 0
    next_service_miles: int = 0
    status: str = "Active"

class DriverCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    status: str = "Available"

@router.get("/api/fleet")
async def get_fleet(db: AsyncSession = Depends(get_db)):
    stmt = select(Vehicle)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/api/fleet")
async def create_vehicle(vehicle: VehicleCreate, db: AsyncSession = Depends(get_db)):
    new_vehicle = Vehicle(**vehicle.model_dump())
    db.add(new_vehicle)
    await db.commit()
    await db.refresh(new_vehicle)
    return new_vehicle

@router.get("/api/drivers")
async def get_drivers(db: AsyncSession = Depends(get_db)):
    stmt = select(Driver)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/api/drivers")
async def create_driver(driver: DriverCreate, db: AsyncSession = Depends(get_db)):
    new_driver = Driver(**driver.model_dump())
    db.add(new_driver)
    await db.commit()
    await db.refresh(new_driver)
    return new_driver
