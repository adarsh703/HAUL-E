from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Text
from datetime import datetime
import os

Base = declarative_base()

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50))
    command_name: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class EmailLog(Base):
    __tablename__ = "email_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    broker_email: Mapped[str] = mapped_column(String(100))
    broker_name: Mapped[str] = mapped_column(String(100))
    lane: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class OperationalTask(Base):
    __tablename__ = "operational_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Load(Base):
    __tablename__ = "loads"
    id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[str] = mapped_column(String(50))
    origin_dest: Mapped[str] = mapped_column(String(200))
    pickup_date: Mapped[str] = mapped_column(String(100))
    driver: Mapped[str] = mapped_column(String(100))
    rate: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    document_url: Mapped[str] = mapped_column(String(500), nullable=True)
    operational_intelligence: Mapped[str] = mapped_column(Text, nullable=True)
    driver_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    broker_email: Mapped[str] = mapped_column(String(200), nullable=True)
    shipper_email: Mapped[str] = mapped_column(String(200), nullable=True)
    dispatcher_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    hard_copy_pod_required: Mapped[bool] = mapped_column(default=False, nullable=True)
    bol_path: Mapped[str] = mapped_column(String(500), nullable=True)
    pod_path: Mapped[str] = mapped_column(String(500), nullable=True)
    invoice_path: Mapped[str] = mapped_column(String(500), nullable=True)
    temp_check_active: Mapped[bool] = mapped_column(default=False, nullable=True)
    discord_thread_id: Mapped[str] = mapped_column(String(50), nullable=True)

class TempCheckLog(Base):
    __tablename__ = "temp_check_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[str] = mapped_column(String(50))
    driver_response: Mapped[str] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    forwarded_to_shipper: Mapped[bool] = mapped_column(default=False)
    forwarded_to_dispatcher: Mapped[bool] = mapped_column(default=False)

class Settings(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))

class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(50))
    driver: Mapped[str] = mapped_column(String(100))
    miles: Mapped[str] = mapped_column(String(50))
    service: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))

class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(100))
    mc_number: Mapped[str] = mapped_column(String(50))
    eld_provider: Mapped[str] = mapped_column(String(100))
    accounting_software: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

engine = create_async_engine("sqlite+aiosqlite:///bot_database.db", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
