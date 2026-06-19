from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime
from datetime import datetime
from app.database import Base

class CompanyProfile(Base):
    __tablename__ = 'company_profiles'

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(100))
    mc_number: Mapped[str] = mapped_column(String(50))
    dot_number: Mapped[str | None] = mapped_column(String(50))
    eld_provider: Mapped[str | None] = mapped_column(String(100))
    accounting_software: Mapped[str | None] = mapped_column(String(100))
    discord_user_id: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
