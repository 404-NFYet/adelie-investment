"""Portfolio and simulation models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, BigInteger, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserPortfolio(Base):
    """User portfolio model."""
    
    __tablename__ = "user_portfolios"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    portfolio_name: Mapped[str] = mapped_column(String(100), default="내 포트폴리오")
    initial_cash: Mapped[int] = mapped_column(BigInteger, default=1000000, comment="초기 자금 (원)")
    current_cash: Mapped[int] = mapped_column(BigInteger, default=1000000, comment="현재 현금")
    total_rewards_received: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0",
        comment="누적 보상 수령액 (수익률 계산에서 제외용)"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="portfolios")
    holdings: Mapped[list["PortfolioHolding"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    trades: Mapped[list["SimulationTrade"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_user_portfolios_user_id", "user_id", unique=True),
    )


class PortfolioHolding(Base):
    """Portfolio holding model."""
    
    __tablename__ = "portfolio_holdings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("user_portfolios.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_buy_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, comment="평균 매입가")
    position_side: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="long",
        server_default="long",
        comment="long | short",
    )
    leverage: Mapped[float] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        default=1.0,
        server_default="1.0",
        comment="레버리지 배수",
    )
    borrow_rate_bps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="공매도 차입수수료 (bps/일)",
    )
    last_funding_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="차입수수료 마지막 정산 시각",
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio: Mapped["UserPortfolio"] = relationship(back_populates="holdings")
    
    __table_args__ = (
        Index("ix_portfolio_holdings_portfolio_id", "portfolio_id"),
        Index("ix_portfolio_holdings_stock_code", "stock_code"),
    )


class SimulationTrade(Base):
    """Simulation trade model."""
    
    __tablename__ = "simulation_trades"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("user_portfolios.id"), nullable=False)
    trade_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="buy, sell")
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="실제 체결 수량",
    )
    price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    requested_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True, comment="요청 가격")
    executed_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True, comment="실제 체결 가격")
    slippage_bps: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True, comment="슬리피지 (bps)")
    fee_amount: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True, comment="수수료")
    order_kind: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="market",
        server_default="market",
        comment="market | limit",
    )
    order_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="filled",
        server_default="filled",
        comment="pending | partial | filled | cancelled",
    )
    position_side: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="long",
        server_default="long",
        comment="long | short",
    )
    leverage: Mapped[float] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        default=1.0,
        server_default="1.0",
        comment="레버리지 배수",
    )
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    trade_reason: Mapped[Optional[str]] = mapped_column(Text, comment="거래 사유 (학습 기록)")
    traded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    portfolio: Mapped["UserPortfolio"] = relationship(back_populates="trades")
    
    __table_args__ = (
        Index("ix_simulation_trades_portfolio_id", "portfolio_id"),
        Index("ix_simulation_trades_traded_at", "traded_at"),
    )


# Forward reference
from app.models.user import User
