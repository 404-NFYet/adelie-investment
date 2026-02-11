"""종목 매핑 테이블 모델."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Index, String
from app.core.database import Base


class StockListing(Base):
    """코스피/코스닥 종목 매핑 테이블.

    pykrx + FinanceDataReader로 초기 수집하여 뉴스-종목 매칭 시 정확한 후보 제공.
    """
    __tablename__ = "stock_listings"

    stock_code = Column(String(6), primary_key=True, comment="종목 코드 (예: 005930)")
    stock_name = Column(String(100), nullable=False, comment="종목명 (예: 삼성전자)")
    market = Column(String(10), nullable=False, comment="시장 구분 (KOSPI/KOSDAQ)")
    sector = Column(String(50), nullable=True, comment="섹터 (예: 반도체)")
    industry = Column(String(100), nullable=True, comment="산업 분류 (예: 전자부품 제조업)")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="업데이트 시각")
    is_active = Column(Boolean, default=True, comment="상장 여부 (False: 상장폐지)")

    __table_args__ = (
        Index("ix_stock_listings_name", "stock_name"),
        Index("ix_stock_listings_market_sector", "market", "sector"),
    )

    def __repr__(self) -> str:
        return f"<StockListing({self.stock_code}, {self.stock_name}, {self.market})>"
