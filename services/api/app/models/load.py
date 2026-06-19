from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric, ForeignKey, DateTime
from datetime import datetime
from app.database import Base

class Load(Base):
    __tablename__ = 'loads'

    id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[str] = mapped_column(String(50), unique=True)
    origin: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    pickup_date: Mapped[str] = mapped_column(String(50))
    delivery_date: Mapped[str | None] = mapped_column(String(50))
    driver_id: Mapped[int | None] = mapped_column(ForeignKey('drivers.id'))
    rate: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(50), default='Pending')
    broker_name: Mapped[str | None] = mapped_column(String(100))
    broker_email: Mapped[str | None] = mapped_column(String(100))
    commodity: Mapped[str | None] = mapped_column(String(100))
    document_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    driver = relationship("Driver", back_populates="loads")
