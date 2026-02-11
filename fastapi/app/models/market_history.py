"""시장 일별 히스토리 모델."""
from datetime import date as date_type
from typing import Optional
from sqlalchemy import Date, String, Numeric, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class MarketDailyHistory(Base):
    __tablename__ = "market_daily_history"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    index_code: Mapped[str] = mapped_column(String(10), nullable=False)
    open: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    high: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    low: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    close: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
