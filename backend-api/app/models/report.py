"""Broker report model."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Text, Date, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BrokerReport(Base):
    """Broker report model."""
    
    __tablename__ = "broker_reports"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    broker_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="증권사명")
    report_title: Mapped[str] = mapped_column(String(300), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    stock_codes: Mapped[Optional[dict]] = mapped_column(JSONB, comment="관련 종목 코드 배열")
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), comment="원본 PDF URL")
    minio_path: Mapped[Optional[str]] = mapped_column(String(500), comment="MinIO 저장 경로")
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, comment="Vision API 추출 텍스트")
    summary: Mapped[Optional[str]] = mapped_column(Text, comment="AI 요약")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_broker_reports_date", "report_date"),
        Index("ix_broker_reports_broker_name", "broker_name"),
    )
