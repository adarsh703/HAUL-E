from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    from app.models import load, driver, vehicle, company
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
async def seed_data():
    from app.models.load import Load
    from app.models.driver import Driver
    from app.models.vehicle import Vehicle
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Driver))
        if not result.scalars().first():
            d1 = Driver(name='John Doe', status='Available')
            d2 = Driver(name='Jane Smith', status='On Duty')
            d3 = Driver(name='Mike Johnson', status='Available')
            session.add_all([d1, d2, d3])
            await session.commit()
            
            v1 = Vehicle(unit_id='UNIT-101', type='Sleeper', driver_id=d1.id, mileage=142000, next_service_miles=150000, status='Active')
            v2 = Vehicle(unit_id='UNIT-102', type='Day Cab', driver_id=d2.id, mileage=89500, next_service_miles=90000, status='Maintenance')
            v3 = Vehicle(unit_id='UNIT-103', type='Reefer', driver_id=d3.id, mileage=210300, next_service_miles=220000, status='Active')
            session.add_all([v1, v2, v3])
            await session.commit()
            
            # Only seed vehicles and drivers, NO loads.
            # Loads should be added manually via OCR or UI.
