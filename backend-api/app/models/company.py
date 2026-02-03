"""Company relation model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CompanyRelation(Base):
    """Company relation model - cache for Neo4j graph data."""
    
    __tablename__ = "company_relations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    target_stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    relation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="supplier, customer, competitor, subsidiary"
    )
    relation_detail: Mapped[Optional[str]] = mapped_column(Text)
    data_source: Mapped[Optional[str]] = mapped_column(String(50), comment="dart, news, manual")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_company_relations_source", "source_stock_code"),
        Index("ix_company_relations_target", "target_stock_code"),
        Index("ix_company_relations_type", "relation_type"),
        {"comment": "상세 그래프는 Neo4j에 저장, 이 테이블은 캐시/참조용"},
    )
