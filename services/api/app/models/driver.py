from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, DateTime
from datetime import datetime
from app.database import Base

class Driver(Base):
    __tablename__ = 'drivers'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(100))
    license_number: Mapped[str | None] = mapped_column(String(50))
    hos_remaining: Mapped[float] = mapped_column(Float, default=11.0)
    status: Mapped[str] = mapped_column(String(50), default='Available')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    loads = relationship("Load", back_populates="driver")
    vehicle = relationship("Vehicle", back_populates="driver", uselist=False)
