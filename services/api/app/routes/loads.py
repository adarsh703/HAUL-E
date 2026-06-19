from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException
from app.database import get_db
from app.models.load import Load

router = APIRouter(prefix="/api/loads", tags=["loads"])

import random

class LoadCreate(BaseModel):
    load_id: str | None = None
    origin: str
    destination: str
    pickup_date: str
    rate: float | str
    status: str = "Pending"
    driver_id: int | None = None

@router.get("")
async def get_loads(status: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Load)
    if status:
        stmt = stmt.where(Load.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{load_id}")
async def get_load(load_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Load).where(Load.load_id == load_id)
    result = await db.execute(stmt)
    load = result.scalars().first()
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")
    return load

@router.post("")
async def create_load(load_data: LoadCreate, db: AsyncSession = Depends(get_db)):
    dump = load_data.model_dump()
    if not dump.get("load_id"):
        dump["load_id"] = f"#L-{random.randint(10000, 99999)}"
        
    if isinstance(dump["rate"], str):
        try:
            dump["rate"] = float(dump["rate"].replace("$", "").replace(",", ""))
        except:
            dump["rate"] = 0.0

    new_load = Load(**dump)
    db.add(new_load)
    await db.commit()
    await db.refresh(new_load)
    return new_load

@router.patch("/{load_id}")
async def update_load(load_id: str, load_data: dict, db: AsyncSession = Depends(get_db)):
    stmt = select(Load).where(Load.load_id == load_id)
    result = await db.execute(stmt)
    load = result.scalars().first()
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")
    
    for key, value in load_data.items():
        setattr(load, key, value)
    
    await db.commit()
    await db.refresh(load)
    return load

@router.delete("/{load_id}")
async def delete_load(load_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Load).where(Load.load_id == load_id)
    result = await db.execute(stmt)
    load = result.scalars().first()
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")
    
    await db.delete(load)
    await db.commit()
    return {"message": "Load deleted successfully"}
