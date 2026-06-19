from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime
from datetime import datetime
from app.database import Base

class Vehicle(Base):
    __tablename__ = 'vehicles'

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[str] = mapped_column(String(50), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    driver_id: Mapped[int | None] = mapped_column(ForeignKey('drivers.id'))
    mileage: Mapped[int] = mapped_column(Integer, default=0)
    next_service_miles: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default='Active')
    current_location: Mapped[str | None] = mapped_column(String(200))
    current_speed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    driver = relationship("Driver", back_populates="vehicle")
